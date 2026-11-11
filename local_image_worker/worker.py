"""
Saga local image worker: FLUX.1 Kontext [dev] (GGUF) on your own GPU.

Runs in its own virtualenv (heavy deps: torch, diffusers) and listens on 127.0.0.1:8071.
The Saga backend calls it when Settings > image source = Local.

    POST /generate  {"prompt", "width", "height", "reference_image": "<abs path>"?, "edit"?, "steps"?, "seed"?}
                    -> image/png
    POST /sprites   {"sheet", "count", "background"?, "boxes"?} -> {"sprites": [{"png" (base64), "box"}]}
    POST /audio     {"prompt", "seconds", "loop"?, "steps"?, "seed"?} -> audio/ogg   (Stable Audio Open)
    GET  /health    -> {"ok": true, "loaded": "...", "busy": bool}

Built for a 12 GB card / 16 GB RAM: the T5 text encoder (~9.5 GB) and the transformer (~7 GB, Q4)
never sit in the GPU together. Prompts are encoded first (T5 straight onto the GPU), then T5 is
dropped and the transformer is loaded; it stays loaded while prompts come back from the cache.

Style reference: with a reference image, Kontext generates a NEW scene in the style of the
reference only when the output size differs from the reference; with the same size it just edits
the reference. So a referenced image is generated at 1456x720 and then cropped/resized.

Models (see README.md): FLUX_BASE (pipeline: text encoders, VAE, configs) and FLUX_GGUF.
The official base repo is gated: accept the license on Hugging Face and `huggingface-cli login`.
"""

import gc
import io
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SETTINGS = Path.home() / ".saga_engine_settings.json"
try:   # HF_HOME must be set before huggingface_hub is imported (models may live on another disk)
    _hf_home = json.loads(SETTINGS.read_text(encoding="utf-8")).get("hf_home")
    if _hf_home:
        os.environ.setdefault("HF_HOME", _hf_home)
except Exception:
    pass

import torch
from PIL import Image

HOST, PORT = "127.0.0.1", int(os.environ.get("SAGA_IMAGE_WORKER_PORT", 8071))
DT = torch.bfloat16
NEW_SCENE_SIZE = (1456, 720)      # different from any reference size we produce (see docstring)
MAX_CACHE = 64

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("saga-image-worker")


def settings() -> dict:
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def model_sources():
    s = settings()
    base = os.environ.get("FLUX_BASE") or s.get("flux_base_repo") or "black-forest-labs/FLUX.1-Kontext-dev"
    rev = os.environ.get("FLUX_BASE_REVISION") or s.get("flux_base_revision") or None
    gguf_repo = os.environ.get("FLUX_GGUF_REPO") or s.get("flux_gguf_repo") or "QuantStack/FLUX.1-Kontext-dev-GGUF"
    gguf_file = os.environ.get("FLUX_GGUF_FILE") or s.get("flux_gguf_file") or "flux1-kontext-dev-Q4_K_S.gguf"
    return base, rev, gguf_repo, gguf_file


class Flux:
    def __init__(self):
        self.lock = threading.Lock()
        self.pipe = None            # transformer + VAE (no text encoders)
        self.base_path = None
        self.embeds = {}            # prompt -> (prompt_embeds, pooled) on CPU
        self.busy = False

    def _paths(self):
        if self.base_path:
            return self.base_path, self.gguf_path
        from huggingface_hub import hf_hub_download, snapshot_download
        base, rev, gguf_repo, gguf_file = model_sources()
        log.info("modelos: base=%s rev=%s gguf=%s/%s", base, rev, gguf_repo, gguf_file)
        self.base_path = snapshot_download(base, revision=rev, allow_patterns=[
            "model_index.json", "scheduler/*", "text_encoder/*", "text_encoder_2/*", "tokenizer/*",
            "tokenizer_2/*", "vae/*", "transformer/config.json"])
        self.gguf_path = hf_hub_download(gguf_repo, gguf_file)
        return self.base_path, self.gguf_path

    def _free(self):
        gc.collect()
        torch.cuda.empty_cache()

    def unload(self):
        if self.pipe is not None:
            log.info("descarregando o transformer")
            self.pipe = None
            self._free()

    def _encode(self, prompts):
        """CLIP + T5 straight onto the GPU (the transformer must not be loaded)."""
        from diffusers import FluxKontextPipeline
        from transformers import CLIPTextModel, T5EncoderModel
        base, _ = self._paths()
        AUDIO.unload()
        if self.pipe is not None:
            log.info("descarregando o transformer para codificar prompts")
            self.pipe = None
            self._free()
        t = time.time()
        t5 = T5EncoderModel.from_pretrained(base, subfolder="text_encoder_2", torch_dtype=DT, device_map="cuda")
        clip = CLIPTextModel.from_pretrained(base, subfolder="text_encoder", torch_dtype=DT, device_map="cuda")
        enc = FluxKontextPipeline.from_pretrained(base, transformer=None, vae=None, text_encoder=clip,
                                                  text_encoder_2=t5, torch_dtype=DT)
        with torch.no_grad():
            for p in prompts:
                pe, pooled, _ = enc.encode_prompt(prompt=p, prompt_2=None, device="cuda", max_sequence_length=512)
                self.embeds[p] = (pe.cpu(), pooled.cpu())
        while len(self.embeds) > MAX_CACHE:
            self.embeds.pop(next(iter(self.embeds)))
        del enc, t5, clip
        self._free()
        log.info("prompts codificados em %.0fs", time.time() - t)

    def _load_transformer(self):
        if self.pipe is not None:
            return
        AUDIO.unload()
        from diffusers import FluxKontextPipeline, FluxTransformer2DModel, GGUFQuantizationConfig
        base, gguf = self._paths()
        t = time.time()
        transformer = FluxTransformer2DModel.from_single_file(
            gguf, quantization_config=GGUFQuantizationConfig(compute_dtype=DT), torch_dtype=DT,
            config=base, subfolder="transformer")
        self.pipe = FluxKontextPipeline.from_pretrained(
            base, transformer=transformer, text_encoder=None, text_encoder_2=None,
            tokenizer=None, tokenizer_2=None, torch_dtype=DT).to("cuda")
        log.info("transformer carregado em %.0fs", time.time() - t)

    def generate(self, prompt, width, height, reference=None, steps=24, seed=None, edit=False):
        with self.lock:
            self.busy = True
            try:
                if prompt not in self.embeds:
                    self._encode([prompt])
                self._load_transformer()
                pe, pooled = self.embeds[prompt]
                kwargs = dict(prompt_embeds=pe.to("cuda", DT), pooled_prompt_embeds=pooled.to("cuda", DT),
                              num_inference_steps=steps, guidance_scale=2.5,
                              generator=torch.Generator("cuda").manual_seed(seed if seed is not None else int(time.time())))
                if reference and edit:
                    # same size in and out: Kontext edits the picture (e.g. "the door is now open")
                    size = gen_size(width, height)
                    kwargs["image"] = Image.open(reference).convert("RGB").resize(size, Image.LANCZOS)
                    kwargs["width"], kwargs["height"] = size
                    kwargs["_auto_resize"] = False
                elif reference:
                    kwargs["image"] = Image.open(reference).convert("RGB")
                    kwargs["width"], kwargs["height"] = NEW_SCENE_SIZE
                else:
                    kwargs["width"], kwargs["height"] = gen_size(width, height)
                t = time.time()
                img = self.pipe(**kwargs).images[0]
                log.info("imagem %sx%s em %.0fs (pedido %sx%s, ref=%s)", img.width, img.height,
                         time.time() - t, width, height, bool(reference))
                return fit(img, width, height)
            finally:
                self.busy = False


def gen_size(width, height):
    """A ~1 MP size with the requested aspect ratio, multiple of 16."""
    ratio = width / max(1, height)
    h = (1024 * 1024 / ratio) ** 0.5
    w = h * ratio
    return int(round(w / 16) * 16), int(round(h / 16) * 16)


def fit(img: Image.Image, width, height) -> Image.Image:
    """Center-crop to the requested aspect ratio, then resize to the requested size."""
    target = width / height
    w, h = img.size
    if w / h > target:
        nw = int(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize((width, height), Image.LANCZOS)


FLUX = Flux()


# --- sound: Stable Audio Open ------------------------------------------------------------------
#
# Shares the GPU with FLUX (same lock): whichever is asked for unloads the other. Background
# sounds come out as seamless loops (the tail is crossfaded into the head); event sounds are
# trimmed of leading/trailing silence. Everything is peak-normalised; the player sets volumes.

AUDIO_REPO_DEFAULT = "stabilityai/stable-audio-open-1.0"   # gated: accept the license on Hugging Face
AUDIO_MAX_SECONDS = 47.0
LOOP_CROSSFADE = 2.0


class Audio:
    def __init__(self):
        self.pipe = None

    def unload(self):
        if self.pipe is not None:
            log.info("descarregando o modelo de som")
            self.pipe = None
            gc.collect()
            torch.cuda.empty_cache()

    def _load(self):
        if self.pipe is not None:
            return
        from diffusers import StableAudioPipeline
        FLUX.unload()
        s = settings()
        repo = os.environ.get("AUDIO_REPO") or s.get("audio_repo") or AUDIO_REPO_DEFAULT
        t = time.time()
        from huggingface_hub import snapshot_download
        # only what diffusers uses: the repo root also has the original 4.8 GB checkpoints
        path = repo if os.path.isdir(repo) else snapshot_download(repo, allow_patterns=[
            "model_index.json", "scheduler/*", "text_encoder/*", "tokenizer/*",
            "transformer/*", "vae/*", "projection_model/*"])
        self.pipe = StableAudioPipeline.from_pretrained(path, torch_dtype=torch.float16).to("cuda")
        log.info("modelo de som %s carregado em %.0fs", repo, time.time() - t)

    def generate(self, prompt: str, seconds: float, loop: bool, steps: int = 100, seed=None) -> bytes:
        import numpy as np
        import soundfile as sf
        with FLUX.lock:
            FLUX.busy = True
            try:
                self._load()
                seconds = max(1.0, min(float(seconds), AUDIO_MAX_SECONDS - (LOOP_CROSSFADE if loop else 0)))
                length = seconds + (LOOP_CROSSFADE if loop else 0)
                g = torch.Generator("cuda").manual_seed(int(seed)) if seed is not None else None
                t = time.time()
                out = self.pipe(prompt, negative_prompt="Low quality, distorted, music, speech, voices.",
                                num_inference_steps=int(steps), audio_end_in_s=length,
                                num_waveforms_per_prompt=1, generator=g).audios[0]
                rate = self.pipe.vae.sampling_rate
                y = out.T.float().cpu().numpy()                  # (samples, channels)
                log.info("som %.0fs em %.0fs: %s", length, time.time() - t, prompt[:80])
            finally:
                FLUX.busy = False
        y = make_loop(y, rate) if loop else trim(y, rate)
        peak = float(np.abs(y).max()) or 1.0
        y = (y * (0.89 / peak)).astype("float32")                # -1 dBFS
        buf = io.BytesIO()
        # in small blocks: libsndfile 1.2 kills the process writing a long OGG in one go
        with sf.SoundFile(buf, "w", rate, y.shape[1] if y.ndim > 1 else 1,
                          format="OGG", subtype="VORBIS") as f:
            for i in range(0, len(y), 8192):
                f.write(y[i:i + 8192])
        return buf.getvalue()


def make_loop(y, rate):
    """The last LOOP_CROSSFADE seconds fade into the first ones, so the end runs into the start."""
    import numpy as np
    xf = min(int(LOOP_CROSSFADE * rate), len(y) // 3)
    body = y[:len(y) - xf].copy()
    ramp = np.linspace(0.0, 1.0, xf, dtype=y.dtype)[:, None]
    body[:xf] = y[:xf] * ramp + y[len(y) - xf:] * (1.0 - ramp)
    return body


def trim(y, rate, threshold_db=-45.0):
    """Cuts silence at both ends and fades the last 50 ms."""
    import numpy as np
    level = np.abs(y).max(axis=1)
    loud = np.where(level > 10 ** (threshold_db / 20) * max(level.max(), 1e-9))[0]
    if len(loud):
        y = y[max(0, loud[0] - int(0.01 * rate)): loud[-1] + int(0.05 * rate)]
    fade = min(int(0.05 * rate), len(y))
    if fade:
        y = y.copy()
        y[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=y.dtype)[:, None]
    return y


AUDIO = Audio()


# --- sprites: cut a sheet of objects into transparent PNGs that sit well in the scene -------------

_rembg_session = None


def _remove_bg(img: Image.Image) -> Image.Image:
    global _rembg_session
    from rembg import new_session, remove
    if _rembg_session is None:          # CPU: the GPU belongs to FLUX
        _rembg_session = new_session("isnet-general-use", providers=["CPUExecutionProvider"])
    return remove(img, session=_rembg_session)


def cut_sheet(sheet: Image.Image, count: int):
    """Transparent cutouts of the `count` largest objects on the sheet, left to right."""
    import numpy as np
    from scipy import ndimage
    rgba = _remove_bg(sheet.convert("RGB"))
    alpha = np.asarray(rgba)[:, :, 3] > 40
    labels, _ = ndimage.label(ndimage.binary_dilation(alpha, iterations=6))
    boxes = ndimage.find_objects(labels)
    areas = [int((labels[b] == i + 1).sum()) for i, b in enumerate(boxes)]
    keep = sorted(range(len(boxes)), key=lambda i: -areas[i])[:count]
    keep = [i for i in keep if areas[i] > 0.002 * alpha.size]
    keep.sort(key=lambda i: boxes[i][1].start)
    out = []
    for i in keep:
        ys, xs = boxes[i]
        crop = rgba.crop((xs.start, ys.start, xs.stop, ys.stop))
        mask = (labels[ys, xs] == i + 1)                  # drop bits of neighbours inside the box
        a = np.asarray(crop).copy()
        a[:, :, 3] = a[:, :, 3] * mask
        out.append(Image.fromarray(a, "RGBA"))
    return out


def grade(sprite: Image.Image, background: Image.Image, box, strength=0.8) -> Image.Image:
    """Pull the sprite's colours and contrast towards the scene around `box`, so it does not look pasted."""
    import numpy as np
    s = np.asarray(sprite, dtype=np.float32) / 255
    rgb, a = s[..., :3], s[..., 3:]
    m = a[..., 0] > 0.5
    if m.sum() < 10:
        return sprite
    B = np.asarray(background.convert("RGB"), dtype=np.float32) / 255
    x0, y0, x1, y1 = [int(v) for v in box]
    pad = max(x1 - x0, y1 - y0)
    reg = B[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad].reshape(-1, 3)
    sm, ss = rgb[m].mean(0), rgb[m].std(0) + 1e-3
    bm, bs = reg.mean(0), reg.std(0) + 1e-3
    matched = np.clip((rgb - sm) / ss * (bs * 1.6) + bm * 1.25, 0, 1)
    out = rgb * (1 - strength) + matched * strength
    return Image.fromarray((np.concatenate([out, a], -1) * 255).astype(np.uint8), "RGBA")


def fit_box(sprite: Image.Image, box):
    """Scale the sprite into the box (keeping its proportions), standing on the box's bottom edge."""
    x0, y0, x1, y1 = box
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    k = min(bw / sprite.width, bh / sprite.height)
    w, h = max(1, int(sprite.width * k)), max(1, int(sprite.height * k))
    cx = (x0 + x1) / 2
    return sprite.resize((w, h), Image.LANCZOS), [int(cx - w / 2), int(y1 - h), int(cx + w / 2), int(y1)]


def make_sprites(job):
    import base64
    sheet = Image.open(job["sheet"])
    count = int(job["count"])
    cuts = cut_sheet(sheet, count)
    if len(cuts) != count:
        return {"error": f"a folha tinha {len(cuts)} objetos separados, esperava {count}", "found": len(cuts)}
    bg = Image.open(job["background"]) if job.get("background") else None
    sprites = []
    for i, sp in enumerate(cuts):
        box = (job.get("boxes") or [None] * count)[i]
        if box and bg is not None:
            sx, sy = bg.width / 1920, bg.height / 1080          # boxes come in scene units (1920x1080)
            pbox = [box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy]
            sp, pbox = fit_box(sp, pbox)
            sp = grade(sp, bg, pbox)
            box = [round(pbox[0] / sx), round(pbox[1] / sy), round(pbox[2] / sx), round(pbox[3] / sy)]
        buf = io.BytesIO()
        sp.save(buf, "PNG")
        sprites.append({"png": base64.b64encode(buf.getvalue()).decode(), "box": box,
                        "size": [sp.width, sp.height]})
    return {"sprites": sprites}


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._json(200, {"ok": True, "model": "FLUX.1-Kontext-dev",
                                    "loaded": FLUX.pipe is not None, "busy": FLUX.busy,
                                    "audio_loaded": AUDIO.pipe is not None,
                                    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/audio":
            try:
                job = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                data = AUDIO.generate(job["prompt"], float(job.get("seconds", 10)), bool(job.get("loop")),
                                      int(job.get("steps", 100)), job.get("seed"))
                self.send_response(200)
                self.send_header("Content-Type", "audio/ogg")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                log.exception("falha ao gerar som")
                self._json(500, {"error": f"{type(e).__name__}: {e}"})
            return
        if self.path == "/sprites":
            try:
                job = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                for key in ("sheet", "background"):
                    if job.get(key) and not Path(job[key]).is_file():
                        return self._json(400, {"error": f"arquivo não existe: {job[key]}"})
                result = make_sprites(job)
                return self._json(200 if "error" not in result else 422, result)
            except Exception as e:
                log.exception("falha ao recortar sprites")
                return self._json(500, {"error": f"{type(e).__name__}: {e}"})
        if self.path != "/generate":
            return self._json(404, {"error": "not found"})
        try:
            job = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            ref = job.get("reference_image")
            if ref and not Path(ref).is_file():
                return self._json(400, {"error": f"imagem de referência não existe: {ref}"})
            img = FLUX.generate(job["prompt"], int(job.get("width", 1024)), int(job.get("height", 1024)),
                                ref, int(job.get("steps", 24)), job.get("seed"), bool(job.get("edit")))
            buf = io.BytesIO()
            img.save(buf, "PNG")
            data = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            log.exception("falha ao gerar")
            self._json(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    if not torch.cuda.is_available():
        raise SystemExit("CUDA não disponível: o gerador local precisa de uma GPU NVIDIA.")
    log.info("Saga image worker em http://%s:%s (%s)", HOST, PORT, torch.cuda.get_device_name(0))
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
