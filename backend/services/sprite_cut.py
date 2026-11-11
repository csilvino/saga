"""
Sprites from a sheet: the objects of a scene drawn side by side on a plain background (by FLUX, by
the Gemini image API or by a web AI) become transparent PNGs that sit well in the scene.

CPU only (rembg + scipy), so it runs in the backend itself; the local worker uses it too.
"""

import base64
import io
from typing import List, Optional

from PIL import Image

_rembg_session = None


def _remove_bg(img: Image.Image) -> Image.Image:
    global _rembg_session
    from rembg import new_session, remove
    if _rembg_session is None:          # CPU: the GPU, when there is one, belongs to FLUX
        _rembg_session = new_session("isnet-general-use", providers=["CPUExecutionProvider"])
    return remove(img, session=_rembg_session)


def cut_sheet(sheet: Image.Image, count: int) -> List[Image.Image]:
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
        out.append(Image.fromarray(a))
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
    # towards the scene's light and tint, but the object keeps its own colours and contrast: a flat
    # surrounding (a plain wall) once turned a dark wooden clock into a grey, flat one
    scale = np.clip(bs * 1.6 / ss, 0.75, 1.25)
    matched = np.clip((rgb - sm) * scale + sm + 0.5 * (bm * 1.25 - sm), 0, 1)
    out = rgb * (1 - strength) + matched * strength
    return Image.fromarray((np.concatenate([out, a], -1) * 255).astype(np.uint8))


def fit_box(sprite: Image.Image, box):
    """Scale the sprite into the box (keeping its proportions), standing on the box's bottom edge."""
    x0, y0, x1, y1 = box
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    k = min(bw / sprite.width, bh / sprite.height)
    w, h = max(1, int(sprite.width * k)), max(1, int(sprite.height * k))
    cx = (x0 + x1) / 2
    return sprite.resize((w, h), Image.LANCZOS), [int(cx - w / 2), int(y1 - h), int(cx + w / 2), int(y1)]


def fit_part(part: Image.Image, parent_box, at: dict, height: float,
             background: Optional[Image.Image] = None) -> tuple:
    """A moving part (a clock's pendulum) on its object: hung by its top centre at `at` (fractions of
    the object's picture), `height` of the object's height. -> (picture, rect as fractions of the object)."""
    x0, y0, x1, y1 = parent_box
    pw, ph = max(1, x1 - x0), max(1, y1 - y0)
    h = max(4, height * ph)
    w = max(2, part.width * h / part.height)
    rect = {"x": at["x"] - w / pw / 2, "y": at["y"], "w": w / pw, "h": h / ph}
    k = min(1.0, (h * 2) / part.height)              # twice the scene size: sharp on big screens
    if k < 1:
        part = part.resize((max(1, int(part.width * k)), max(1, int(part.height * k))), Image.LANCZOS)
    if background is not None:
        sx, sy = background.width / 1920, background.height / 1080
        px, py = x0 + rect["x"] * pw, y0 + rect["y"] * ph
        part = grade(part, background, [px * sx, py * sy, (px + w) * sx, (py + h) * sy], strength=0.5)
    return part, {k_: round(v, 4) for k_, v in rect.items()}


def make_sprites(sheet: Image.Image, count: int, background: Optional[Image.Image] = None,
                 boxes: Optional[list] = None) -> dict:
    """{"sprites": [{"png" (base64), "box" (scene units), "size"}]} or {"error", "found"}.
    `boxes` (scene units, 1920x1080) are where each object should stand, left to right."""
    cuts = cut_sheet(sheet, count)
    if len(cuts) != count:
        return {"error": f"a folha tinha {len(cuts)} objetos separados, esperava {count}", "found": len(cuts)}
    sprites = []
    for i, sp in enumerate(cuts):
        box = (boxes or [None] * count)[i]
        if box and background is not None:
            sx, sy = background.width / 1920, background.height / 1080
            pbox = [box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy]
            sp, pbox = fit_box(sp, pbox)
            sp = grade(sp, background, pbox)
            box = [round(pbox[0] / sx), round(pbox[1] / sy), round(pbox[2] / sx), round(pbox[3] / sy)]
        buf = io.BytesIO()
        sp.save(buf, "PNG")
        sprites.append({"png": base64.b64encode(buf.getvalue()).decode(), "box": box,
                        "size": [sp.width, sp.height]})
    return {"sprites": sprites}
