"""
Character visual references: one picture per character, so the same person looks the same in every
scene.

Sprites are drawn per scene, a few per sheet, in the style of that scene: a character drawn in the
beach and again in the temple comes out as two different people. A character with a reference is
drawn alone instead, from the reference picture (FLUX Kontext keeps the face, hair and clothes of the
picture it is given), and then takes the light of the scene (sprite_light.py).

project["characters"] = {"tomas_albuquerque": {"name": "Tomás Albuquerque", "description": "...",
                                               "reference": "characters/Ref_tomas_albuquerque_ab12cd.png"}}

An object of type "personagem" is that character when its name gives the same key, or when its
properties say so: {"character": "tomas_albuquerque"}.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

from backend.services.project_service import project_service
from backend.ses import director_tools
from backend.ses.world import slug

GREY = (208, 208, 208)
REF_W, REF_H = 768, 1024              # portrait: never the size of a sprite sheet, so Kontext draws anew


class CharacterError(Exception):
    pass


def key_of(obj: dict) -> str:
    return (obj.get("properties") or {}).get("character") or slug(obj.get("name") or "")


def find(project: dict, obj: dict) -> Optional[dict]:
    if obj.get("type") != "personagem" and not (obj.get("properties") or {}).get("character"):
        return None
    return (project.get("characters") or {}).get(key_of(obj))


def reference_path(project: dict, root: Path, obj: dict) -> Optional[Path]:
    c = find(project, obj)
    if c and c.get("reference") and (root / c["reference"]).is_file():
        return root / c["reference"]
    return None


def sprite_prompt(character: dict, pose: str, style_hint: str) -> str:
    return (f"The same character as in the reference picture: the same face, hair, beard, body, clothes and "
            f"colours. {pose}. {style_hint}. One single figure, the whole body visible, alone on a plain flat "
            f"light grey background, nothing else, no scenery, no ground, no shadow. "
            f"{character.get('description', '')}").strip()


def _on_grey(img: Image.Image) -> Image.Image:
    """The figure centred on a plain grey portrait card (transparency becomes grey)."""
    img = img.convert("RGBA")
    box = img.getchannel("A").getbbox()
    if box:
        img = img.crop(box)
    scale = min((REF_W * 0.85) / img.width, (REF_H * 0.92) / img.height)
    img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    card = Image.new("RGBA", (REF_W, REF_H), GREY + (255,))
    card.alpha_composite(img, ((REF_W - img.width) // 2, (REF_H - img.height) // 2))
    return card.convert("RGB")


def list_characters(project_name: str) -> Dict[str, Any]:
    project = project_service.load_project(project_name)
    chars = project.get("characters") or {}
    people = []
    for sid, s in project.get("scenes", {}).items():
        for o in s.get("objects", []):
            if o.get("type") == "personagem":
                people.append({"object": o.get("name"), "scene": s.get("name"), "character": key_of(o),
                               "has_reference": key_of(o) in chars})
    return {"characters": [{"key": k, **v} for k, v in chars.items()], "character_objects": people}


async def set_reference(project_name: str, name: str, from_object: str = "", source: str = "",
                        generate: bool = False, description: str = "", style_scene: str = "",
                        remove_background: bool = True) -> Dict[str, Any]:
    """Makes `name` a character with a reference picture, taken from an object's current sprite
    (from_object), from a picture file or URL (source), or drawn now (generate, from the
    description, in the style of style_scene's background)."""
    if sum(bool(x) for x in (from_object, source, generate)) != 1:
        raise CharacterError("use exatamente um: from_object, source ou generate")
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    key = slug(name or "")
    if not key:
        raise CharacterError("falta o nome do personagem")
    chars = project.setdefault("characters", {})
    entry = dict(chars.get(key) or {"name": name})
    if description:
        entry["description"] = description

    if from_object:
        _, _, obj = director_tools._object(project, from_object)
        rel = obj.get("sprite_original") or obj.get("sprite") or ""
        if "/" not in rel or not (root / rel.split("?")[0]).is_file():
            raise CharacterError(f"'{obj.get('name')}' não tem sprite para servir de referência")
        with Image.open(root / rel.split("?")[0]) as im:
            card = _on_grey(im.copy())
        if key_of(obj) != key:                         # its name differs: link it explicitly
            obj.setdefault("properties", {})["character"] = key
    elif source:
        from backend.services import asset_tools
        data, _ = await asset_tools._read_source(source, asset_tools.IMAGE_EXT)
        img = asset_tools._open_image(data).convert("RGBA")
        if remove_background:
            import asyncio
            from rembg import remove
            img = await asyncio.to_thread(remove, img)
        card = _on_grey(img)
    else:
        from backend.services import scene_art
        if not entry.get("description"):
            raise CharacterError("para gerar, dê a descrição do personagem (description)")
        ref = None
        if style_scene:
            sid = director_tools._scene(project, style_scene)
            bg = scene_art.background_path(project["scenes"][sid])
            if not bg:
                raise CharacterError(f"a cena '{style_scene}' ainda não tem cenário")
            ref = root / bg
        prompt = (f"Character design for an adventure game, {scene_art.STYLE_HINT}"
                  f"{', with the palette of the reference' if ref else ''}: {entry['description']}. "
                  f"One single full-body figure standing, seen from the front, arms relaxed, from head to feet, "
                  f"on a plain flat light grey background, nothing else.")
        card = _on_grey((await scene_art.generate(prompt, REF_W, REF_H, ref)).convert("RGBA"))

    (root / "characters").mkdir(exist_ok=True)
    rel = f"characters/Ref_{key}_{uuid.uuid4().hex[:6]}.png"
    card.save(root / rel, "PNG")
    old = entry.get("reference")
    entry["reference"] = rel
    chars[key] = entry
    project_service.save_project_data(project_name, project)
    if old and old != rel:
        (root / old).unlink(missing_ok=True)
    return {"character": key, "name": entry["name"], "reference": rel,
            "note": "os próximos sprites deste personagem (create_scene_art) partem desta referência"}
