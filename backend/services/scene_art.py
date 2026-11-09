"""
Scene art: background + objects that match what the text says.

For one scene:
  1. split its objects into PAINTED (fixed scenery: painted into the background, clickable area
     on top) and SPRITES (things that can disappear or appear: portable, hidden, characters);
  2. Gemini writes the English prompts (background with the painted objects; one line per sprite);
  3. the background is generated (style reference = another scene, if given);
  4. Gemini looks at the background: where each painted object is, and where each sprite should
     stand (on the ground, at a believable size);
  5. the sprites are generated together on one sheet in the scene's style, cut out with a
     transparent background, colour-matched to the scene and fitted to their places
     (local_image_worker /sprites).

The game player hides a sprite when the engine says the object is gone (taken, removed) and shows
it in the inventory, so "pegar garrafa" makes the bottle leave the picture.
"""

import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx
from PIL import Image

from backend.config.user_settings import get_gemini_key, get_gemini_model, get_generation_source
from backend.services.local_image_generator import WORKER_URL, local_image_service
from backend.services.project_service import project_service
from backend.ses import director_tools

logger = logging.getLogger(__name__)

SCENE_W, SCENE_H = 1920, 1080
SHEET_MAX = 4                    # objects per sprite sheet
SPRITE_KINDS = {"personagem", "character", "npc"}

STYLE_HINT = ("hand-painted 2D digital painting for a point-and-click adventure game, visible brushstrokes")


class ArtError(RuntimeError):
    pass


def is_sprite(obj: dict) -> bool:
    """Objects that can leave or enter the picture get their own sprite; the rest is painted."""
    props = obj.get("properties") or {}
    return bool(props.get("portable") or props.get("hidden") or obj.get("type") in SPRITE_KINDS)


def scene_objects(scene: dict) -> List[dict]:
    return [o for o in scene.get("objects", []) if o.get("type") != "background" and o.get("name") != "Background"]


def background_path(scene: dict) -> Optional[str]:
    for obj in scene.get("objects", []):
        if obj.get("type") == "background" and obj.get("sprite"):
            return obj["sprite"].split("?")[0]
    return None


# --- Gemini: prompts and vision ---------------------------------------------------------------

def _client():
    from google import genai
    key = get_gemini_key()
    if not key:
        raise ArtError("chave da Gemini não configurada (Configurações → API Keys)")
    return genai.Client(api_key=key)


async def _ask_json(contents, schema_hint: str) -> Any:
    from google.genai import types
    client = _client()
    for attempt in range(4):
        try:
            r = await client.aio.models.generate_content(
                model=get_gemini_model(), contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4))
            return json.loads(r.text)
        except json.JSONDecodeError:
            if attempt == 3:
                raise ArtError(f"a Gemini não devolveu JSON válido ({schema_hint})")
        except Exception as e:
            if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < 3:
                await asyncio.sleep(20 * (attempt + 1))
                continue
            raise


async def plan_prompts(scene: dict, painted: List[dict], sprites: List[dict], style: str) -> dict:
    def describe(o):
        return {"id": o["id"], "name": o.get("name"), "description": o.get("description", "")}
    prompt = f"""You write prompts for an image model (FLUX) for one scene of an adventure game.
Answer ONLY with JSON: {{"background_prompt": "...", "sprites": [{{"id": "...", "prompt": "..."}}]}}

Scene: {scene.get('name')} — {scene.get('description', '')}
Art direction from the user: {style or '(none: match the reference)'}

PAINTED objects (fixed scenery; the background MUST clearly show each of them, recognisable,
reasonably prominent, in a believable place): {json.dumps([describe(o) for o in painted], ensure_ascii=False)}

SPRITE objects (drawn separately later; the background must NOT show them):
{json.dumps([describe(o) for o in sprites], ensure_ascii=False)}

Rules:
- English only. Describe what IS there (FLUX ignores negations like "no X" or "unlit").
- background_prompt: one paragraph: place, every painted object, light, mood, and this style:
  {STYLE_HINT}. Wide shot, empty floor/ground space in the foreground where items could lie.
  No people, no animals, no text.
- sprites: for EACH sprite object, a short visual description of the object alone (shape,
  material, colour, state), e.g. "a green glass bottle with a cork and a rolled paper inside".
"""
    plan = await _ask_json(prompt, "plano de prompts")
    if not isinstance(plan, dict) or not plan.get("background_prompt"):
        raise ArtError(f"plano inválido da Gemini: {str(plan)[:200]}")
    by_id = {s.get("id"): s.get("prompt") for s in plan.get("sprites", []) if isinstance(s, dict)}
    plan["sprites"] = {o["id"]: by_id.get(o["id"]) or o.get("name") for o in sprites}
    return plan


async def locate(image_path: Path, painted: List[dict], sprites: List[dict]) -> Dict[str, dict]:
    """Boxes in scene units (1920x1080): where painted objects are; where sprites should stand."""
    from google.genai import types
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((1280, 1280))
    import io
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    items = ([{"id": o["id"], "name": o.get("name"), "description": o.get("description", ""), "task": "find"}
              for o in painted] +
             [{"id": o["id"], "name": o.get("name"), "description": o.get("description", ""), "task": "place"}
              for o in sprites])
    prompt = f"""This is the background of an adventure game scene. For each item:
- task "find": locate the object in the picture. found=false if it is not clearly visible.
- task "place": the object is NOT in the picture; it will be pasted on top later. Choose where it
  should stand so it looks natural: resting on the ground/floor/a surface (never floating in the
  sky or on a wall unless it hangs there), at a believable size for the perspective, not covering
  the other items and not hiding an important part of the scene. found=true.
Answer ONLY with JSON: [{{"id": "...", "found": true, "box_2d": [ymin, xmin, ymax, xmax]}}], coordinates
normalised to 0-1000.
Items: {json.dumps(items, ensure_ascii=False)}"""
    data = await _ask_json([types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"), prompt],
                           "posições")
    out = {}
    for d in data if isinstance(data, list) else []:
        box = d.get("box_2d")
        if not d.get("id") or not isinstance(box, list) or len(box) != 4:
            continue
        ymin, xmin, ymax, xmax = [max(0, min(1000, float(v))) for v in box]
        if xmax - xmin < 5 or ymax - ymin < 5:
            continue
        out[d["id"]] = {"found": bool(d.get("found", True)),
                        "box": [round(xmin * SCENE_W / 1000), round(ymin * SCENE_H / 1000),
                                round(xmax * SCENE_W / 1000), round(ymax * SCENE_H / 1000)]}
    return out


# --- images ------------------------------------------------------------------------------------

async def generate(prompt: str, width: int, height: int, reference: Optional[Path]) -> Image.Image:
    if get_generation_source() == "cloud":
        from backend.services.gemini_imagen import GeminiImagenExtractor
        extractor = GeminiImagenExtractor(get_gemini_key())
        return await asyncio.to_thread(extractor.generate_image, prompt=prompt, negative_prompt="",
                                       width=width, height=height,
                                       reference_image_path=str(reference) if reference else None)
    return await asyncio.to_thread(local_image_service.generate_image, prompt=prompt, width=width, height=height,
                                   reference_image_path=str(reference) if reference else None)


def sheet_prompt(descriptions: List[str]) -> str:
    n = len(descriptions)
    order = ["leftmost", "second from the left", "third from the left", "rightmost"] if n == 4 else \
        ["left", "middle", "right"] if n == 3 else ["left", "right"] if n == 2 else ["center"]
    items = " ".join(f"{pos.capitalize()}: {d}." for pos, d in zip(order, descriptions))
    return (f"{'One single object' if n == 1 else f'{n} separate objects'} for an adventure game, {STYLE_HINT}, "
            f"with the same palette and lighting as the reference. Evenly spaced in one row, well apart, on a plain "
            f"flat light grey background, nothing else, no scenery, no ground, no frame. {items} "
            f"Each object complete and fully visible.")


async def cut_sprites(sheet: Path, count: int, background: Path, boxes: List[list]) -> List[dict]:
    async with httpx.AsyncClient(timeout=600) as client:
        try:
            r = await client.post(f"{WORKER_URL}/sprites", json={
                "sheet": str(sheet), "count": count, "background": str(background), "boxes": boxes})
        except httpx.ConnectError:
            raise ArtError("o recorte de sprites usa o gerador local (local_image_worker), que não está rodando")
    data = r.json()
    if "error" in data:
        raise ArtError(data["error"])
    return data["sprites"]


# --- the whole scene ---------------------------------------------------------------------------

async def create_scene_art(project_name: str, scene_ref: str, style: str = "", reference_scene: str = "",
                           keep_background: bool = False,
                           progress: Optional[Callable[[str], None]] = None) -> dict:
    say = progress or (lambda m: logger.info("arte: %s", m))
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene_ref)
    scene = project["scenes"][sid]
    objs = scene_objects(scene)
    painted = [o for o in objs if not is_sprite(o)]
    sprites = [o for o in objs if is_sprite(o)]
    report: Dict[str, Any] = {"scene": scene.get("name"), "painted": [], "sprites": [], "problems": []}

    plan = await plan_prompts(scene, painted, sprites, style)

    ref_path = None
    if reference_scene:
        ref_sid = director_tools._scene(project, reference_scene)
        rel = background_path(project["scenes"][ref_sid])
        if not rel:
            raise ArtError(f"a cena de referência '{reference_scene}' ainda não tem imagem")
        ref_path = root / rel

    # 1. background
    if keep_background and background_path(scene):
        bg_rel = background_path(scene)
    else:
        say(f"gerando o cenário de '{scene.get('name')}'")
        img = await generate(plan["background_prompt"], SCENE_W, SCENE_H, ref_path)
        bg_rel = f"backgrounds/Scene_{uuid.uuid4().hex[:8]}.png"
        (root / "backgrounds").mkdir(exist_ok=True)
        img.save(root / bg_rel, "PNG")
    bg_path = root / bg_rel
    report["background"] = bg_rel
    report["background_prompt"] = plan["background_prompt"]

    # 2. where things are / go
    say("localizando os objetos na imagem")
    boxes = await locate(bg_path, painted, sprites) if objs else {}

    # 3. sprites, a few per sheet, in the style of this scene's background
    made: Dict[str, dict] = {}
    for i in range(0, len(sprites), SHEET_MAX):
        group = sprites[i:i + SHEET_MAX]
        say(f"gerando sprites: {', '.join(o.get('name', o['id']) for o in group)}")
        group_boxes = [boxes.get(o["id"], {}).get("box") or default_box(o) for o in group]
        err = None
        for attempt in range(2):           # a sheet occasionally merges two objects: try once more
            sheet = await generate(sheet_prompt([plan["sprites"][o["id"]] for o in group]), 1456, 720, bg_path)
            sheet_path = root / "sprites" / f"_sheet_{uuid.uuid4().hex[:8]}.png"
            sheet_path.parent.mkdir(exist_ok=True)
            sheet.save(sheet_path, "PNG")
            try:
                cuts = await cut_sprites(sheet_path, len(group), bg_path, group_boxes)
                err = None
                break
            except ArtError as e:
                err = str(e)
            finally:
                sheet_path.unlink(missing_ok=True)
        if err:
            report["problems"].append(f"sprites de {[o.get('name') for o in group]}: {err}")
            continue
        for o, cut in zip(group, cuts):
            rel = f"sprites/Sprite_{o['id']}_{uuid.uuid4().hex[:6]}.png"
            (root / rel).write_bytes(base64.b64decode(cut["png"]))
            made[o["id"]] = {"sprite": rel, "box": cut["box"]}

    # 4. apply to the project (reload: generation took minutes)
    project = project_service.load_project(project_name)
    scene = project["scenes"][sid]
    set_background(scene, bg_rel)
    for o in scene_objects(scene):
        oid, props = o["id"], o.setdefault("properties", {})
        if oid in made:
            o["sprite"] = made[oid]["sprite"]
            props.pop("painted", None)
            place(o, made[oid]["box"])
            report["sprites"].append(o.get("name"))
        elif not is_sprite(o):
            found = boxes.get(oid)
            o["sprite"] = ""
            props["painted"] = True
            if found and found["found"]:
                place(o, found["box"])
                report["painted"].append(o.get("name"))
            else:
                report["problems"].append(f"'{o.get('name')}' não aparece no cenário (gere de novo a cena)")
    project_service.save_project_data(project_name, project)
    return report


def default_box(o: dict) -> list:
    x, y = o.get("position", {}).get("x", 960), o.get("position", {}).get("y", 800)
    return [x - 90, y - 90, x + 90, y + 90]


def place(o: dict, box: list):
    x0, y0, x1, y1 = box
    o["position"] = {"x": round((x0 + x1) / 2), "y": round((y0 + y1) / 2)}
    o["size"] = {"width": max(10, x1 - x0), "height": max(10, y1 - y0)}
    o["scale"] = {"x": 1, "y": 1}


def set_background(scene: dict, rel: str):
    for obj in scene.get("objects", []):
        if obj.get("type") == "background":
            obj["sprite"] = rel
            return
    scene.setdefault("objects", []).insert(0, {
        "id": f"background_{uuid.uuid4().hex[:8]}", "name": "Background", "type": "background", "sprite": rel,
        "position": {"x": SCENE_W // 2, "y": SCENE_H // 2}, "origin": {"x": SCENE_W // 2, "y": SCENE_H // 2},
        "size": {"width": SCENE_W, "height": SCENE_H}, "scale": {"x": 1, "y": 1}, "rotation": 0, "zIndex": 0,
        "properties": {}, "actions": [], "ses": ""})


# --- state variants: the same picture with something changed (an open door, a lit lamp) -------

async def create_variant(project_name: str, scene_ref: str, when: str, change: str) -> dict:
    """Edits the scene's background (same framing, same clickable areas) and shows the edited
    picture while `when` (an SES condition, e.g. 'flag(porta_aberta)') holds."""
    from backend.ses.language import SESError, parse_condition
    try:
        parse_condition(when)
    except SESError as e:
        raise ArtError(f"condição inválida {when!r}: {e}")
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene_ref)
    base = background_path(project["scenes"][sid])
    if not base:
        raise ArtError("a cena ainda não tem cenário; crie a arte dela primeiro (create_scene_art)")
    plan = await _ask_json(
        f"""Rewrite this change to an adventure game background as a short English image-EDIT instruction
for FLUX Kontext. Keep everything else identical (camera, composition, style, light). Describe the
result positively (no negations). Change: {change}
Scene: {project['scenes'][sid].get('description', '')}
Answer ONLY with JSON: {{"instruction": "..."}}""", "instrução de edição")
    instruction = (plan or {}).get("instruction") or change
    prompt = f"{instruction}. Keep the exact same composition, camera, style and lighting; change nothing else."
    if get_generation_source() == "cloud":
        img = await generate(prompt, SCENE_W, SCENE_H, root / base)
    else:
        img = await asyncio.to_thread(local_image_service.generate_image, prompt=prompt, width=SCENE_W,
                                      height=SCENE_H, reference_image_path=str(root / base), edit=True)
    rel = f"backgrounds/Variant_{uuid.uuid4().hex[:8]}.png"
    img.save(root / rel, "PNG")
    project = project_service.load_project(project_name)
    variants = project["scenes"][sid].setdefault("variants", [])
    variants[:] = [v for v in variants if v.get("when", "").replace(" ", "") != when.replace(" ", "")]
    variants.append({"when": when, "background": rel, "change": change})
    project_service.save_project_data(project_name, project)
    return {"scene": project["scenes"][sid].get("name"), "when": when, "background": rel, "instruction": instruction}


async def _edit(root: Path, base: str, change: str, scene_desc: str):
    plan = await _ask_json(
        f"""Rewrite this change to an adventure game background as a short English image-EDIT instruction
for FLUX Kontext. Keep everything else identical (camera, composition, style, light). Say what to
change and how the result looks (e.g. "Remove the flame inside the lamp; the glass is dark and cold").
Change: {change}
Scene: {scene_desc}
Answer ONLY with JSON: {{"instruction": "..."}}""", "instrução de edição")
    instruction = (plan or {}).get("instruction") or change
    prompt = f"{instruction}. Keep the exact same composition, camera, style and lighting; change nothing else."
    if get_generation_source() == "cloud":
        img = await generate(prompt, SCENE_W, SCENE_H, root / base)
    else:
        img = await asyncio.to_thread(local_image_service.generate_image, prompt=prompt, width=SCENE_W,
                                      height=SCENE_H, reference_image_path=str(root / base), edit=True)
    return img, instruction


async def edit_background(project_name: str, scene_ref: str, change: str) -> dict:
    """Fixes the scene's own background in place (same framing, clickable areas stay valid):
    'the lamp is unlit', 'the door is closed', 'no fire on the rocks'."""
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene_ref)
    base = background_path(project["scenes"][sid])
    if not base:
        raise ArtError("a cena ainda não tem cenário; crie a arte dela primeiro (create_scene_art)")
    img, instruction = await _edit(root, base, change, project["scenes"][sid].get("description", ""))
    rel = f"backgrounds/Scene_{uuid.uuid4().hex[:8]}.png"
    img.save(root / rel, "PNG")
    project = project_service.load_project(project_name)
    set_background(project["scenes"][sid], rel)
    project_service.save_project_data(project_name, project)
    return {"scene": project["scenes"][sid].get("name"), "background": rel, "previous": base,
            "instruction": instruction}
