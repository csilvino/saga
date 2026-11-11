"""
Sound for a game, from what its blueprint says: background sounds of scenes (and their variants),
sounds of objects (a clock ticking, a crow now and then) and the 'play "..."' of the scripts.

    1. Gemini turns every Portuguese description into an English prompt for Stable Audio Open and
       picks a length for the event sounds (one request for the whole batch);
    2. the local worker (local_image_worker, POST /audio) makes each sound on the GPU: background
       and object sounds as seamless loops, events trimmed;
    3. each file is saved in audio/ and written into project.json at once, so this can stop and
       resume any time (like the art).
"""

import json
import logging
import uuid
from typing import Callable, Dict, List, Optional

import httpx

from backend.services.local_image_generator import WORKER_URL
from backend.services.project_service import project_service
from backend.ses import blueprint
from backend.ses.world import sound_key, slug

logger = logging.getLogger(__name__)

SECONDS = {"ambient": 30.0, "object": 10.0}      # loops; events: Gemini picks 1-8 s
TIMEOUT = 900                                    # the first sound also loads the model


class SoundError(RuntimeError):
    pass


async def plan(items: List[tuple]) -> Dict[str, dict]:
    """{text: {"prompt", "seconds"}} for [(kind, text)], from one Gemini request."""
    from backend.services.scene_art import _ask_json
    asked = [{"id": i, "kind": k, "text": t} for i, (k, t) in enumerate(items)]
    data = await _ask_json(f"""You write prompts for Stable Audio Open (a sound-effects model) for an adventure game.
For each item write a short English prompt that describes ONLY the sound: its source, material,
space (small room, open air, stone hall), distance and character. No music, no voices or speech.
kind "ambient": a steady background ambience that can loop (e.g. "howling winter wind outside a
wooden cabin, creaking timber, steady"). kind "object": a steady repeating sound of one thing
(e.g. "slow tick-tock of a pendulum clock in a quiet room"). kind "event": one short sound
(e.g. "a heavy iron door creaks open slowly, stone hall reverb"); also give "seconds" (1 to 8)
for how long it lasts.
Items: {json.dumps(asked, ensure_ascii=False)}
Answer ONLY with JSON: [{{"id": 0, "prompt": "...", "seconds": 3}}]""", "prompts de som")
    out = {}
    for d in data if isinstance(data, list) else []:
        try:
            kind, text = items[int(d["id"])]
        except (KeyError, ValueError, IndexError, TypeError):
            continue
        secs = SECONDS.get(kind) or max(1.0, min(8.0, float(d.get("seconds") or 3)))
        out[text] = {"prompt": str(d.get("prompt") or text), "seconds": secs}
    return out


async def make(prompt: str, seconds: float, loop: bool) -> bytes:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(f"{WORKER_URL}/audio", json={"prompt": prompt, "seconds": seconds, "loop": loop})
        except httpx.ConnectError:
            raise SoundError("o gerador local (local_image_worker) não está rodando")
    if r.status_code != 200:
        try:
            detail = r.json().get("error")
        except Exception:
            detail = r.text[:300]
        if "gated" in str(detail).lower() or "401" in str(detail):
            detail = ("o modelo stabilityai/stable-audio-open-1.0 é restrito: aceite a licença no Hugging Face "
                      "e faça login (veja local_image_worker/README.md)")
        raise SoundError(f"gerador de som falhou: {detail}")
    return r.content


def _save_file(project_name: str, kind: str, text: str, data: bytes) -> str:
    root = project_service.load_project_path(project_name)
    (root / "audio").mkdir(exist_ok=True)
    rel = f"audio/Sound_{slug(text)[:32]}_{uuid.uuid4().hex[:6]}.ogg"
    (root / rel).write_bytes(data)
    project = project_service.load_project(project_name)       # reload: generation took a while
    for k, t, holder in blueprint._sound_items(project):
        if k == kind and sound_key(t) == sound_key(text) and not holder.get("file"):
            holder["file"] = rel
    project_service.save_project_data(project_name, project)
    return rel


async def make_sounds(project_name: str, progress: Optional[Callable[[str], None]] = None) -> dict:
    """The sounds still missing. Each one is saved at once (stop and resume any time)."""
    say = progress or (lambda m: None)
    project = project_service.load_project(project_name)
    todo, seen = [], set()
    for kind, text, _h in blueprint.sound_jobs(project):
        if (kind, sound_key(text)) not in seen:
            seen.add((kind, sound_key(text)))
            todo.append((kind, text))
    done, failed = [], []
    if todo:
        say(f"{len(todo)} som(ns) para fazer; escrevendo os prompts")
        prompts = await plan(todo)
        for kind, text in todo:
            p = prompts.get(text) or {"prompt": text, "seconds": SECONDS.get(kind, 3.0)}
            say(f"som ({kind}): {text}")
            try:
                data = await make(p["prompt"], p["seconds"], loop=kind != "event")
                _save_file(project_name, kind, text, data)
                done.append(text)
            except SoundError as e:
                failed.append(f"{text}: {e}")
                say(f"falhou: {e}")
                if "não está rodando" in str(e) or "restrito" in str(e):
                    break                                # the rest would fail the same way
            except Exception as e:                       # noqa: BLE001 - keep going with the rest
                failed.append(f"{text}: {str(e)[:200]}")
                say(f"falhou: {str(e)[:200]}")
    return {"feitos": done, "falhas": failed, **blueprint.sound_status(project_service.load_project(project_name))}
