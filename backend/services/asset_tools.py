"""
Pictures and sounds in and out of a game, for whichever AI is building it:

- render_scene: the scene as the player sees it (background or the variant that holds, and the
  sprites that are there), so the AI can look at what it made;
- import_background / import_sprite / import_sound: art and sound made anywhere (another AI, an
  image or voice service, the creator's own files) brought into the game.

A source is an http(s) URL or a file on this computer. Imported files are copied into the
project, so the game never depends on the source staying where it was.
"""

import base64
import io
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from PIL import Image, ImageDraw

from backend.services.project_service import project_service
from backend.ses import director_tools
from backend.ses.engine import GameEngine
from backend.ses.world import slug, sound_key

SCENE_W, SCENE_H = 1920, 1080
MAX_BYTES = 40 * 1024 * 1024
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
SOUND_EXT = {".ogg", ".mp3", ".wav"}


class AssetError(Exception):
    pass


# --- reading a source ----------------------------------------------------------------------------

async def _read_source(source: str, kinds: set) -> tuple:
    """(bytes, extension) of a URL or a local file. Only pictures or sounds, at most 40 MB."""
    source = (source or "").strip()
    if not source:
        raise AssetError("falta `source`: uma URL http(s) ou o caminho de um arquivo neste computador")
    if source.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            r = await client.get(source)
        if r.status_code >= 400:
            raise AssetError(f"a URL respondeu {r.status_code}")
        data = r.content
        ext = Path(source.split("?")[0]).suffix.lower()
        ctype = r.headers.get("content-type", "")
        if ext not in kinds:
            ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "audio/mpeg": ".mp3",
                   "audio/ogg": ".ogg", "audio/wav": ".wav", "audio/x-wav": ".wav"}.get(ctype.split(";")[0], ext)
    else:
        path = Path(source).expanduser()
        if not path.is_file():
            raise AssetError(f"arquivo não encontrado: {source}")
        ext = path.suffix.lower()
        if ext not in kinds:
            raise AssetError(f"tipo de arquivo não aceito ({ext}); aceitos: {', '.join(sorted(kinds))}")
        if path.stat().st_size > MAX_BYTES:
            raise AssetError("arquivo grande demais (máximo 40 MB)")
        data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise AssetError("arquivo grande demais (máximo 40 MB)")
    if ext not in kinds:
        raise AssetError(f"não consegui saber o tipo do arquivo; aceitos: {', '.join(sorted(kinds))}")
    return data, ext


def _open_image(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        return img
    except Exception as e:
        raise AssetError(f"não é uma imagem válida: {e}")


# --- render_scene --------------------------------------------------------------------------------

def _flags_state(engine: GameEngine, sid: str, flags: Optional[List[str]]) -> dict:
    state = engine.new_state()
    state["scene"] = sid
    for f in flags or []:
        state["flags"][slug(f)] = True
    return state


def render_scene(project_name: str, scene: str, flags: Optional[List[str]] = None,
                 width: int = 1280) -> Dict[str, Any]:
    """The scene as the player sees it at the start, or with these flags set. Returns the picture
    under "_image" (JPEG, base64) for the caller to show, plus what is drawn and what is missing."""
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene)
    engine = GameEngine(project)
    engine.state = _flags_state(engine, sid, flags)
    s = project["scenes"][sid]
    bg_rel = engine.background(sid) or next((o.get("sprite") for o in s.get("objects", [])
                                             if o.get("type") == "background" and o.get("sprite")), None)
    notes: List[str] = []
    if bg_rel and (root / bg_rel.split("?")[0]).is_file():
        canvas = Image.open(root / bg_rel.split("?")[0]).convert("RGBA").resize((SCENE_W, SCENE_H))
    else:
        canvas = Image.new("RGBA", (SCENE_W, SCENE_H), (40, 40, 40, 255))
        notes.append("a cena não tem cenário")
    draw = ImageDraw.Draw(canvas)
    here = set(engine.here())
    drawn = []
    for o in sorted(s.get("objects", []), key=lambda o: o.get("zIndex", 0)):
        if o.get("type") == "background" or o["id"] not in here:
            continue
        pos, size = o.get("position") or {}, o.get("size") or {}
        w, h = int(size.get("width") or 0), int(size.get("height") or 0)
        x, y = int(pos.get("x") or 0), int(pos.get("y") or 0)
        sprite = (o.get("sprite") or "").split("?")[0]
        if (o.get("properties") or {}).get("painted") or not sprite and not w:
            continue                                   # part of the background picture
        if "/" in sprite and (root / sprite).is_file() and w and h:
            canvas.alpha_composite(Image.open(root / sprite).convert("RGBA").resize((w, h)),
                                   (int(x - w / 2), int(y - h / 2)))
            drawn.append({"name": o.get("name"), "x": x, "y": y, "width": w, "height": h})
        else:                                          # no picture yet: a labelled box where it goes
            w, h = w or 100, h or 100
            draw.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], outline=(255, 80, 80, 255), width=4)
            draw.text((x - w / 2 + 6, y - h / 2 + 6), o.get("name") or o["id"], fill=(255, 80, 80, 255))
            notes.append(f"'{o.get('name')}' ainda não tem imagem (caixa vermelha)")
    out = canvas.convert("RGB")
    if width and width < SCENE_W:
        out = out.resize((width, round(width * SCENE_H / SCENE_W)), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=85)
    return {"scene": s.get("name"), "flags": flags or [], "background": bg_rel, "objects": drawn,
            **({"notes": notes} if notes else {}),
            "_image": base64.b64encode(buf.getvalue()).decode("ascii")}


# --- imports -------------------------------------------------------------------------------------

def _variant_entry(scene: dict, when: str) -> Optional[dict]:
    for v in scene.get("variants") or []:
        if v.get("when", "").replace(" ", "") == when.replace(" ", ""):
            return v
    return None


async def import_background(project_name: str, scene: str, source: str, when: str = "",
                            change: str = "") -> Dict[str, Any]:
    """A picture as the scene's background (cropped to 16:9, 1920x1080), or, with `when`, as the
    variant shown while that SES condition holds."""
    from backend.services import scene_art
    data, _ = await _read_source(source, IMAGE_EXT)
    img = scene_art.fit_scene(_open_image(data))
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene)
    s = project["scenes"][sid]
    kind = "Variant" if when else "Scene"
    rel = f"backgrounds/{kind}_import_{uuid.uuid4().hex[:8]}.png"
    (root / "backgrounds").mkdir(exist_ok=True)
    img.save(root / rel, "PNG")
    if when:
        entry = _variant_entry(s, when)
        if entry:
            entry.update({"background": rel, "change": change or entry.get("change", "")})
            entry.pop("review", None)
        else:
            s.setdefault("variants", []).append({"when": when, "background": rel, "change": change})
    else:
        scene_art.set_background(s, rel)
    project_service.save_project_data(project_name, project)
    return {"scene": sid, "background": rel, **({"when": when} if when else {})}


def _trim(img: Image.Image) -> Image.Image:
    box = img.getchannel("A").getbbox()
    return img.crop(box) if box else img


async def import_sprite(project_name: str, object: str, source: str, remove_background: bool = True,
                        x: Optional[int] = None, y: Optional[int] = None, height: Optional[int] = None) -> Dict[str, Any]:
    """A picture as an object's sprite. remove_background cuts out the figure (for pictures that
    come on a plain or scenic background); transparent margins are trimmed. Placed at x/y (center)
    with this height, or where the object already is, keeping the picture's proportions."""
    data, _ = await _read_source(source, IMAGE_EXT)
    img = _open_image(data).convert("RGBA")
    if remove_background:
        import asyncio
        from rembg import remove
        img = await asyncio.to_thread(remove, img)       # seconds of CPU: keep the server answering
    img = _trim(img)
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    oid, sid, obj = director_tools._object(project, object)
    if obj.get("type") == "background":
        raise AssetError("isso é o cenário: use import_background")
    rel = f"sprites/Sprite_{oid}_import_{uuid.uuid4().hex[:6]}.png"
    (root / "sprites").mkdir(exist_ok=True)
    img.save(root / rel, "PNG")
    obj["sprite"] = rel
    obj.setdefault("properties", {}).pop("painted", None)
    pos = dict(obj.get("position") or {"x": SCENE_W // 2, "y": SCENE_H * 3 // 4})
    old_h = (obj.get("size") or {}).get("height") or 200
    h = int(height or old_h)
    w = max(10, round(h * img.width / max(1, img.height)))
    if x is not None:
        pos["x"] = int(x)
    if y is not None:
        pos["y"] = int(y)
    obj["position"], obj["size"], obj["scale"] = pos, {"width": w, "height": h}, {"x": 1, "y": 1}
    project_service.save_project_data(project_name, project)
    return {"object": oid, "scene": sid, "sprite": rel, "place": director_tools._placement(obj)}


async def import_sound(project_name: str, source: str, kind: str, scene: str = "", object: str = "",
                       text: str = "", mode: str = "loop") -> Dict[str, Any]:
    """A sound file into the game.
    kind "ambient": the scene's background sound (loops). kind "object": an object's own sound
    (mode "loop" or "random", now and then). kind "play": the sound of a script's play "text"
    (a door, a voice line): `text` must be exactly the text in the script."""
    if kind not in ("ambient", "object", "play"):
        raise AssetError("kind deve ser ambient, object ou play")
    if kind == "play" and not text:
        raise AssetError("kind play precisa de `text`: o texto exato do play \"...\" no script")
    if kind == "object" and mode not in ("loop", "random"):
        raise AssetError("mode deve ser loop ou random")
    project = project_service.load_project(project_name)
    if kind == "ambient":
        director_tools._scene(project, scene)              # the target exists before anything is written
    elif kind == "object":
        director_tools._object(project, object)
    data, ext = await _read_source(source, SOUND_EXT)
    root = project_service.load_project_path(project_name)
    label = text or kind
    rel = f"audio/Sound_import_{slug(label)[:32]}_{uuid.uuid4().hex[:6]}{ext}"
    (root / "audio").mkdir(exist_ok=True)
    (root / rel).write_bytes(data)
    if kind == "ambient":
        sid = director_tools._scene(project, scene)
        snd = project["scenes"][sid].setdefault("sound", {})
        snd["file"] = rel
        snd.setdefault("ambient", text or f"som importado de {project['scenes'][sid].get('name')}")
        where = {"scene": sid}
    elif kind == "object":
        oid, sid, obj = director_tools._object(project, object)
        if mode not in ("loop", "random"):
            raise AssetError("mode deve ser loop ou random")
        snd = obj.setdefault("sound", {})
        snd.update({"file": rel, "mode": mode})
        snd.setdefault("desc", text or f"som importado de {obj.get('name')}")
        where = {"object": oid}
    elif kind == "play":
        if not text:
            raise AssetError("kind play precisa de `text`: o texto exato do play \"...\" no script")
        project.setdefault("sounds", {})[sound_key(text)] = {"text": text, "file": rel}
        where = {"play": text}
    else:
        raise AssetError("kind deve ser ambient, object ou play")
    project_service.save_project_data(project_name, project)
    return {"file": rel, **where}
