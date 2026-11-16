"""
A sprite takes the light of the place where it stands.

Sprites are drawn alone, on a plain grey background, so they come out in neutral light and look
pasted onto a scene lit in green, by a fire or by moonlight. This moves the sprite's colour and
brightness toward the part of the background around it, in the Lab colour space (Reinhard colour
transfer), without any AI: fast, the same every time, and undoable, since the untouched picture
is kept as the object's "sprite_original".
"""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

DEFAULT_STRENGTH = 0.5
SCENE_W, SCENE_H = 1920, 1080


def scene_background(scene: dict) -> Optional[str]:
    """The scene's own background picture (not a variant)."""
    return next((o.get("sprite") for o in scene.get("objects", [])
                 if o.get("type") == "background" and "/" in (o.get("sprite") or "")), None)


def _lab(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)


def surroundings(background: Image.Image, box: list) -> np.ndarray:
    """The background around where the sprite stands (its box, grown by half on each side), RGB."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    W, H = background.size
    region = (max(0, int(x0 - w / 2)), max(0, int(y0 - h / 2)), min(W, int(x1 + w / 2)), min(H, int(y1 + h / 2)))
    if region[2] - region[0] < 4 or region[3] - region[1] < 4:
        region = (0, 0, W, H)
    return np.asarray(background.convert("RGB").crop(region))


def match(sprite: Image.Image, background: Image.Image, box: list, strength: float = DEFAULT_STRENGTH) -> Image.Image:
    """The sprite with the colour cast and brightness of its surroundings, by `strength` (0 to 1).
    The colour (a, b) moves fully by strength; the brightness (L) by half of it, so a dark scene
    darkens the sprite without turning it into a silhouette."""
    strength = max(0.0, min(1.0, float(strength)))
    rgba = np.asarray(sprite.convert("RGBA")).astype(np.float32)
    alpha = rgba[..., 3]
    solid = alpha > 32
    if strength == 0 or solid.sum() < 16:
        return sprite.convert("RGBA")
    src = _lab(rgba[..., :3])
    ref = _lab(surroundings(background, box)).reshape(-1, 3)
    s_mean, s_std = src[solid].mean(0), src[solid].std(0) + 1e-3
    r_mean, r_std = ref.mean(0), ref.std(0) + 1e-3
    out = src.copy()
    for c, k in ((0, strength * 0.5), (1, strength), (2, strength)):
        moved = (src[..., c] - s_mean[c]) * (1 + k * (r_std[c] / s_std[c] - 1)) + s_mean[c] + k * (r_mean[c] - s_mean[c])
        out[..., c] = moved
    out[..., 0] = np.clip(out[..., 0], 0, 255)
    out[..., 1:] = np.clip(out[..., 1:], 0, 255)
    rgb = cv2.cvtColor(out.astype(np.uint8), cv2.COLOR_LAB2RGB)
    return Image.fromarray(np.dstack([rgb, alpha.astype(np.uint8)]), "RGBA")


def box_of(obj: dict) -> Optional[list]:
    pos, size = obj.get("position") or {}, obj.get("size") or {}
    if not size.get("width") or not size.get("height"):
        return None
    x, y, w, h = pos.get("x", 960), pos.get("y", 540), size["width"], size["height"]
    return [x - w / 2, y - h / 2, x + w / 2, y + h / 2]


def apply_to_object(root: Path, obj: dict, background_rel: str, strength: float = DEFAULT_STRENGTH) -> str:
    """Re-lights an object's sprite from its untouched original (kept on first use) and returns the
    new sprite's path. strength 0 puts the original back."""
    import uuid
    current = obj.get("sprite") or ""
    # the original only counts while the sprite is still a lighting of it; any other tool that set
    # a new picture made that picture the new original
    lit_now = Path(current.split("?")[0]).name.startswith("Lit_")
    original = obj.get("sprite_original") if lit_now and obj.get("sprite_original") else current
    if not original or "/" not in original:
        raise ValueError(f"'{obj.get('name')}' não tem sprite")
    obj["sprite_original"] = original
    if lit_now and original != current:
        (root / current.split("?")[0]).unlink(missing_ok=True)   # an earlier lighting of the same original
    box = box_of(obj)
    if strength <= 0 or box is None:
        obj["sprite"] = original
        obj.pop("light", None)
        return original
    with Image.open(root / original.split("?")[0]) as sp, Image.open(root / background_rel.split("?")[0]) as bg:
        fx, fy = bg.width / SCENE_W, bg.height / SCENE_H    # the box is on the 1920x1080 stage
        lit = match(sp, bg.copy(), [box[0] * fx, box[1] * fy, box[2] * fx, box[3] * fy], strength)
    rel = f"sprites/Lit_{obj['id']}_{uuid.uuid4().hex[:6]}.png"
    lit.save(root / rel, "PNG")
    obj["sprite"] = rel
    obj["light"] = round(float(strength), 2)
    return rel
