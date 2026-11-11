"""
Scene art: background + objects that match what the text says.

For one scene:
  1. split its objects into PAINTED (fixed scenery: painted into the background, clickable area
     on top) and SPRITES (things that can disappear or appear: portable, hidden, characters);
  2. Gemini writes the English prompts (background with the painted objects; one line per sprite);
  3. the background is generated (style reference = another scene, if given);
  4. Gemini looks at the background: where each painted object is, and where each sprite should
     stand (on the ground, at a believable size);
  3b. Gemini reviews the background (shows its objects? agrees with the text and the starting
     state?) and it is fixed when it does not (see "art review" below);
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
import time
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


class DailyQuotaExhausted(ArtError):
    """The model's quota for the day is used up (free tier: few requests a day on the better
    models). Waiting minutes does not help; the next calls to that model fail at once."""


_DAILY_OUT: Dict[str, tuple] = {}       # model -> (time.time() until which it is out, message)


def _daily_quota_message(e: Exception, model: str) -> Optional[str]:
    text = str(e)
    if "429" not in text or "per day" not in text.lower():
        return None
    import re
    m = re.search(r"retry in ((?:\d+h)?(?:\d+m)?[\d.]+s)", text)
    limit = re.search(r"limit: (\d+)", text)
    return (f"a cota diária da Gemini para {model.replace('models/', '')} acabou"
            + (f" ({limit.group(1)} pedidos por dia no plano gratuito)" if limit else "")
            + (f"; volta em {m.group(1).split('.')[0]}s" if m else "")
            + ". Use uma chave paga ou outro modelo (gemini_review_model / SAGA_REVIEW_MODEL).")


async def _ask_json(contents, schema_hint: str, model: Optional[str] = None) -> Any:
    from google.genai import types
    client = _client()
    model = model or get_gemini_model()
    out = _DAILY_OUT.get(model)
    if out and time.time() < out[0]:
        raise DailyQuotaExhausted(out[1])
    for attempt in range(6):            # busy spells (503) on Gemini often last a few minutes
        try:
            r = await client.aio.models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4))
            return json.loads(r.text)
        except json.JSONDecodeError:
            if attempt == 5:
                raise ArtError(f"a Gemini não devolveu JSON válido ({schema_hint})")
        except Exception as e:
            daily = _daily_quota_message(e, model)
            if daily:                               # minutes of waiting would not help
                _DAILY_OUT[model] = (time.time() + 3600, daily)
                raise DailyQuotaExhausted(daily)
            if any(k in str(e) for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")) and attempt < 5:
                await asyncio.sleep(min(90, 20 * (attempt + 1)))
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
                           keep_background: bool = False, review: bool = True,
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
    bg_problems: Optional[List[str]] = []
    if review and not (keep_background and background_path(scene)):
        async def check(rel):
            return await review_background(root, rel, scene)

        async def redo(fix):
            return await generate(f"{plan['background_prompt']} {fix}", SCENE_W, SCENE_H, ref_path)
        bg_rel, bg_problems = await _review_and_fix(f"o cenário de {scene.get('name')}", root, bg_rel,
                                                    check, redo, say)
        report["problems"] += ([f"cenário: {p}" for p in bg_problems] if bg_problems is not None
                               else ["cenário: não revisado (Gemini indisponível)"])
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
    if review and not keep_background:
        set_review(next(o for o in scene["objects"] if o.get("type") == "background"), bg_problems)
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
            if obj.get("sprite") != rel:
                obj.pop("review", None)              # it was about the old picture
            obj["sprite"] = rel
            return
    scene.setdefault("objects", []).insert(0, {
        "id": f"background_{uuid.uuid4().hex[:8]}", "name": "Background", "type": "background", "sprite": rel,
        "position": {"x": SCENE_W // 2, "y": SCENE_H // 2}, "origin": {"x": SCENE_W // 2, "y": SCENE_H // 2},
        "size": {"width": SCENE_W, "height": SCENE_H}, "scale": {"x": 1, "y": 1}, "rotation": 0, "zIndex": 0,
        "properties": {}, "actions": [], "ses": ""})


# --- art review: Gemini looks at each picture the way a player would -------------------------
#
# A background must show its fixed objects, agree with the text and show the scene as it STARTS
# (a fire the player has yet to light is cold; a variant shows it burning). A variant must show
# its change, clearly, and nothing else new. When a picture fails, the reviewer writes the fix and
# it is applied (an edit of the same picture, or a new one when editing cannot save it), up to
# REVIEW_ROUNDS times; what is still wrong after that is stored for the creator (Ficha panel).

REVIEW_ROUNDS = 2


# Comparing two pictures is where the lite models fail (2026-11: flash-lite passed a variant that
# changed nothing and failed a good one; 3.5-flash got all five test cases right).
DEFAULT_REVIEW_MODEL = "models/gemini-3.5-flash"


def get_review_model() -> str:
    """The model that looks at the pictures: env var SAGA_REVIEW_MODEL, else the key
    'gemini_review_model' in ~/.saga_engine_settings.json, else DEFAULT_REVIEW_MODEL."""
    import os
    from backend.config.user_settings import get_user_settings
    return (os.environ.get("SAGA_REVIEW_MODEL") or get_user_settings().get("gemini_review_model")
            or DEFAULT_REVIEW_MODEL)


def where(o: dict) -> str:
    """'left of centre, lower half' from the object's position in scene units."""
    x = (o.get("position") or {}).get("x", SCENE_W / 2) / SCENE_W
    y = (o.get("position") or {}).get("y", SCENE_H / 2) / SCENE_H
    h = ("far left" if x < 0.2 else "left of centre" if x < 0.42 else "centre" if x < 0.58
         else "right of centre" if x < 0.8 else "far right")
    v = "upper part" if y < 0.4 else "middle" if y < 0.65 else "lower part"
    return f"{h}, {v} of the picture"


def placed_objects(scene: dict) -> List[str]:
    """The painted objects that already have a place in the picture, with where they are."""
    return [f"{o.get('name')} ({where(o)})" for o in scene_objects(scene)
            if not is_sprite(o) and (o.get("properties") or {}).get("painted")]


def _image_part(path: Path):
    import io
    from google.genai import types
    img = Image.open(path).convert("RGB")
    img.thumbnail((1280, 1280))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


REVIEW_RULES = """Flag only what a player would notice as WRONG for the story. Never flag taste, style,
weather or atmosphere (snow, dust, cobwebs, colours), camera choices, or small details. Write the
problems in Portuguese (short, one per item). "fix" is ONE image-edit instruction IN ENGLISH for
FLUX Kontext that fixes all the problems, saying where in the picture and how the result looks
(positively, no negations), and ending with "keep everything else identical"."""


def _verdict(data: Any) -> dict:
    data = data if isinstance(data, dict) else {}
    problems = [str(p).strip() for p in data.get("problems") or [] if str(p).strip()]
    ok = bool(data.get("ok")) and not problems
    return {"ok": ok, "problems": [] if ok else problems or ["a revisão não explicou o problema"],
            "fix": str(data.get("fix") or "").strip(), "redo": bool(data.get("redo")) and not ok}


async def review_background(root: Path, bg_rel: str, scene: dict) -> dict:
    """{'ok', 'problems', 'fix', 'redo'} for a scene's own (starting) background."""
    objs = scene_objects(scene)
    painted = [{"name": o.get("name"), "looks": o.get("description", "")} for o in objs if not is_sprite(o)]
    later = [v.get("change") for v in scene.get("variants") or [] if v.get("change")]
    prompt = f"""You review the background picture of one scene of an adventure game before players see it.
Scene: {scene.get('name')}: {scene.get('description', '')}
Fixed scenery the picture must clearly show, recognisable: {json.dumps(painted, ensure_ascii=False)}
This picture is the scene as it STARTS. These changes happen only LATER in the game (another picture
shows them), so here they must NOT be visible yet: {json.dumps(later, ensure_ascii=False)}
Check: 1) each fixed object is visible; 2) nothing contradicts the scene text or the starting state
(a fire burning that the player lights later, a door open that opens later, a passage that is
revealed later); 3) the kind of place matches the text (e.g. a kitchen looks like a kitchen).
{REVIEW_RULES}
"redo": true only when the picture is wrong as a whole and an edit cannot save it.
Answer ONLY with JSON: {{"ok": true, "problems": [], "fix": "", "redo": false}}"""
    return _verdict(await _ask_json([_image_part(root / bg_rel), prompt], "revisão do cenário", get_review_model()))


def _pair_part(root: Path, before: str, after: str):
    """Both pictures in ONE image, BEFORE on top and AFTER below, labelled: small models compare
    far better inside one picture than across two."""
    import io
    from google.genai import types
    from PIL import ImageDraw, ImageFont
    w = 1024
    imgs = [Image.open(root / r).convert("RGB") for r in (before, after)]
    imgs = [im.resize((w, round(im.height * w / im.width))) for im in imgs]
    band = 44
    out = Image.new("RGB", (w, sum(im.height for im in imgs) + 2 * band), "white")
    try:
        font = ImageFont.load_default(size=30)
    except TypeError:                                # Pillow < 10.1
        font = ImageFont.load_default()
    y = 0
    for label, im in zip(("1 - BEFORE", "2 - AFTER"), imgs):
        ImageDraw.Draw(out).text((12, y + 6), label, fill="black", font=font)
        out.paste(im, (0, y + band))
        y += band + im.height
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=88)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


async def review_variant(root: Path, base_rel: str, var_rel: str, scene: dict, change: str) -> dict:
    """{'ok', 'problems', 'fix', 'redo'} for a variant against the scene's background."""
    prompt = f"""The image shows two pictures of the same adventure game scene: 1 - BEFORE (top) is the scene
as it starts; 2 - AFTER (bottom) must be the SAME picture after this change, and only this change:
{change}
Scene: {scene.get('name')}: {scene.get('description', '')}
Objects and where they are: {json.dumps(placed_objects(scene), ensure_ascii=False)}

Work step by step and write it in the JSON:
- "inventory": the 6-10 most visible things in BEFORE (furniture, openings, fire, windows, ceiling
  decoration), each with where it is in BEFORE and in AFTER ("same place", "moved left", "missing",
  "different"). Look carefully at the AFTER picture before writing "missing".
- "change_visible": is the change clearly visible in AFTER, so a player who did the action sees it
  at once? Say what you see in "change_evidence".
- "unrelated": things that appeared, vanished or became clearly different in AFTER although the change
  does not explain it (e.g. portraits painted on a plain ceiling; the fireplace on the other side gone;
  a different room). What stands on or next to the changed thing, the wall behind it and the place
  where something opens may move or be redrawn: that is NOT unrelated. Small redraw noise is fine.
- "ok": change_visible and nothing unrelated.
{REVIEW_RULES} The fix is applied to AFTER.
"redo": true when AFTER drifted so far from BEFORE that it should be made again from BEFORE.
Answer ONLY with JSON: {{"inventory": [{{"thing": "", "before": "", "after": ""}}], "change_visible": true,
"change_evidence": "", "unrelated": [], "ok": true, "problems": [], "fix": "", "redo": false}}"""
    data = await _ask_json([_pair_part(root, base_rel, var_rel), prompt], "revisão da variante", get_review_model())
    if isinstance(data, dict):                     # the steps outrank a careless final answer
        found = ([] if data.get("change_visible") is not False else ["a mudança não aparece na imagem"]) +             [f"mudou sem motivo: {u}" for u in data.get("unrelated") or [] if str(u).strip()]
        if found:
            data["ok"] = False
            data["problems"] = data.get("problems") or found
    return _verdict(data)


async def _review_and_fix(kind: str, root: Path, rel: str, check, redo, say, keep_first: bool = False) -> tuple:
    """Reviews the picture at `rel` and fixes it up to REVIEW_ROUNDS times.
    check(rel) -> verdict; redo(fix) -> a new image made again from the start. Returns (rel, problems
    left, or None when the reviewer could not be reached). Replaced pictures are deleted, except the first one when keep_first (it belongs to the
    project already)."""
    first = rel
    for round_ in range(REVIEW_ROUNDS + 1):
        say(f"revisando {kind}")
        try:
            v = await check(rel)
        except Exception as e:                       # noqa: BLE001 - the picture stays; the creator decides
            say(f"revisão de {kind} indisponível: {str(e)[:160]}")
            return rel, None                         # not reviewed: nothing is stored about it
        if v["ok"]:
            return rel, []
        say(f"revisão de {kind}: {'; '.join(v['problems'])}")
        if round_ == REVIEW_ROUNDS or not v["fix"]:
            return rel, v["problems"]
        say(f"corrigindo {kind} ({'de novo' if v['redo'] else 'edição'})")
        img = await redo(v["fix"]) if v["redo"] else await _apply_edit(root, rel, v["fix"])
        new_rel = f"{rel.rsplit('_', 1)[0]}_{uuid.uuid4().hex[:8]}.png"
        img.save(root / new_rel, "PNG")
        if not (keep_first and rel == first):
            (root / rel).unlink(missing_ok=True)
        rel = new_rel
    return rel, []


def set_review(target: dict, problems: Optional[List[str]]):
    """Stores what the reviewer still finds wrong (on the background object or the variant).
    None (not reviewed) leaves it as it is."""
    if problems is None:
        return
    if problems:
        target["review"] = {"problems": problems, "at": time.strftime("%Y-%m-%d %H:%M")}
    else:
        target.pop("review", None)


# --- state variants: the same picture with something changed (an open door, a lit lamp) -------

async def _rewrite(change: str, scene: dict, example: str) -> str:
    plan = await _ask_json(
        f"""Rewrite this change to an adventure game background as a short English image-EDIT instruction
for FLUX Kontext. Keep everything else identical (camera, composition, style, light). Say WHICH thing
changes and WHERE it is in the picture (use the object list), and how the result looks, positively
(no negations), e.g. "{example}".
Change: {change}
Scene: {scene.get('name')}: {scene.get('description', '')}
Objects and where they are: {json.dumps(placed_objects(scene), ensure_ascii=False)}
Answer ONLY with JSON: {{"instruction": "..."}}""", "instrução de edição")
    return (plan or {}).get("instruction") or change


async def _apply_edit(root: Path, base: str, instruction: str) -> Image.Image:
    prompt = instruction.rstrip(". ")
    if "keep everything else" not in prompt.lower():
        prompt += ". Keep the exact same composition, camera, style and lighting; change nothing else"
    if get_generation_source() == "cloud":
        return await generate(prompt + ".", SCENE_W, SCENE_H, root / base)
    return await asyncio.to_thread(local_image_service.generate_image, prompt=prompt + ".", width=SCENE_W,
                                   height=SCENE_H, reference_image_path=str(root / base), edit=True)


async def create_variant(project_name: str, scene_ref: str, when: str, change: str, review: bool = True,
                         progress: Optional[Callable[[str], None]] = None) -> dict:
    """Edits the scene's background (same framing, same clickable areas) and shows the edited
    picture while `when` (an SES condition, e.g. 'flag(porta_aberta)') holds. The result is
    reviewed against the background and fixed when the change is missing or something else moved."""
    from backend.ses.language import SESError, parse_condition
    say = progress or (lambda m: logger.info("variante: %s", m))
    try:
        parse_condition(when)
    except SESError as e:
        raise ArtError(f"condição inválida {when!r}: {e}")
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene_ref)
    scene = project["scenes"][sid]
    base = background_path(scene)
    if not base:
        raise ArtError("a cena ainda não tem cenário; crie a arte dela primeiro (create_scene_art)")
    instruction = await _rewrite(change, scene, "Slide the tall wooden bookcase on the left of centre "
                                                "to the left; a dark stone archway opens where it stood")
    img = await _apply_edit(root, base, instruction)
    rel = f"backgrounds/Variant_{uuid.uuid4().hex[:8]}.png"
    img.save(root / rel, "PNG")
    problems: Optional[List[str]] = []
    if review:
        async def check(r):
            return await review_variant(root, base, r, scene, change)

        async def redo(fix):
            return await _apply_edit(root, base, f"{instruction.rstrip('. ')}. {fix}")
        rel, problems = await _review_and_fix(f"a variante {when}", root, rel, check, redo, say)
    project = project_service.load_project(project_name)
    variants = project["scenes"][sid].setdefault("variants", [])
    entry = {"when": when, "background": rel, "change": change}
    set_review(entry, problems)
    same = [i for i, v in enumerate(variants) if v.get("when", "").replace(" ", "") == when.replace(" ", "")]
    if same:                    # keep its place: when several hold, the last one in the list wins
        variants[same[0]] = entry
        variants[:] = [v for i, v in enumerate(variants) if i not in same[1:]]
    else:
        variants.append(entry)
    project_service.save_project_data(project_name, project)
    return {"scene": project["scenes"][sid].get("name"), "when": when, "background": rel,
            "instruction": instruction, "problems": problems or [], "reviewed": problems is not None}


async def edit_background(project_name: str, scene_ref: str, change: str) -> dict:
    """Fixes the scene's own background in place (same framing, clickable areas stay valid):
    'the lamp is unlit', 'the door is closed', 'no fire on the rocks'."""
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene_ref)
    scene = project["scenes"][sid]
    base = background_path(scene)
    if not base:
        raise ArtError("a cena ainda não tem cenário; crie a arte dela primeiro (create_scene_art)")
    instruction = await _rewrite(change, scene, "Remove the flame inside the lamp; the glass is dark and cold")
    img = await _apply_edit(root, base, instruction)
    rel = f"backgrounds/Scene_{uuid.uuid4().hex[:8]}.png"
    img.save(root / rel, "PNG")
    project = project_service.load_project(project_name)
    set_background(project["scenes"][sid], rel)
    project_service.save_project_data(project_name, project)
    return {"scene": project["scenes"][sid].get("name"), "background": rel, "previous": base,
            "instruction": instruction}


# --- reviewing a whole scene that already has art (tools/review_art.py, the director) ---------

async def review_scene(project_name: str, scene_ref: str, fix: bool = False,
                       progress: Optional[Callable[[str], None]] = None) -> dict:
    """Reviews the scene's background and its variants. With fix=True, also fixes them (the
    background by editing it, then the painted objects are located again; the variants by
    editing them). Stores what is still wrong. Returns {'scene', 'background': [...], 'variants': {...},
    'fixed': [...]}; a list is None when the reviewer could not be reached."""
    say = progress or (lambda m: logger.info("revisão: %s", m))
    project = project_service.load_project(project_name)
    root = project_service.load_project_path(project_name)
    sid = director_tools._scene(project, scene_ref)
    scene = project["scenes"][sid]
    base = background_path(scene)
    if not base:
        raise ArtError("a cena ainda não tem cenário")
    name = scene.get("name")
    out: Dict[str, Any] = {"scene": name, "background": [], "variants": {}, "fixed": []}

    async def check_bg(r):
        return await review_background(root, r, scene)

    if fix:
        async def redo_bg(fix_text):                 # an existing scene keeps its framing: edit instead
            return await _apply_edit(root, base, fix_text)
        new_bg, problems = await _review_and_fix(f"o cenário de {name}", root, base, check_bg, redo_bg, say, keep_first=True)
    else:
        say(f"revisando o cenário de {name}")
        new_bg, problems = base, await _report_only(check_bg, base, say)
    out["background"] = problems
    if new_bg != base:
        out["fixed"].append("cenário")
        painted = [o for o in scene_objects(scene) if not is_sprite(o)]
        boxes = await locate(root / new_bg, painted, []) if painted else {}
    project = project_service.load_project(project_name)
    scene = project["scenes"][sid]
    if new_bg != base:
        set_background(scene, new_bg)
        for o in scene_objects(scene):
            found = boxes.get(o["id"])
            if found and found["found"] and not is_sprite(o):
                place(o, found["box"])
    set_review(next(o for o in scene["objects"] if o.get("type") == "background"), problems)
    project_service.save_project_data(project_name, project)

    for v in list(scene.get("variants") or []):
        if not v.get("background"):
            continue
        when, change, var_rel = v["when"], v.get("change") or "", v["background"]

        async def check_var(r, change=change):
            return await review_variant(root, new_bg, r, scene, change)

        if fix:
            async def redo_var(fix_text, change=change):
                instruction = await _rewrite(change, scene, "Open the iron door on the right; a stairway is visible")
                return await _apply_edit(root, new_bg, f"{instruction.rstrip('. ')}. {fix_text}")
            new_var, vp = await _review_and_fix(f"a variante {when}", root, var_rel, check_var, redo_var, say,
                                                   keep_first=True)
        else:
            say(f"revisando a variante {when}")
            new_var, vp = var_rel, await _report_only(check_var, var_rel, say)
        out["variants"][when] = vp
        project = project_service.load_project(project_name)
        for pv in project["scenes"][sid].get("variants") or []:
            if pv.get("when") == when:
                if new_var != var_rel:
                    pv["background"] = new_var
                    out["fixed"].append(f"variante {when}")
                set_review(pv, vp)
        project_service.save_project_data(project_name, project)
    return out


async def _report_only(check, rel, say) -> Optional[List[str]]:
    try:
        return (await check(rel))["problems"]
    except Exception as e:                           # noqa: BLE001 - not reviewed; the run goes on
        say(f"revisão indisponível: {str(e)[:160]}")
        return None
