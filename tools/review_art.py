"""
Reviews the art of a game that already has it: Gemini looks at each background and variant the way
a player would (the fixed objects are there? the picture agrees with the text and with the state the
scene starts in? the variant shows its change, and nothing else new?).

    python tools/review_art.py "Neve sobre o Claustro"                    # only reports (Gemini, no GPU)
    python tools/review_art.py "Neve sobre o Claustro" --cena Biblioteca  # one scene
    python tools/review_art.py "Neve sobre o Claustro" --corrigir         # also fixes (GPU, ~5 min per fix)

What is still wrong is stored in project.json and shown in the Ficha panel. Exit code 0 when
nothing is wrong.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services import scene_art  # noqa: E402
from backend.services.project_service import project_service  # noqa: E402


async def run(project: str, scenes: list, fix: bool) -> int:
    say = lambda m: print(time.strftime("%H:%M:%S"), m, flush=True)  # noqa: E731
    wrong = 0
    for ref in scenes:
        r = await scene_art.review_scene(project, ref, fix=fix, progress=say)
        skipped = (["cenário"] if r["background"] is None else []) + \
            [f"variante {w}" for w, ps in r["variants"].items() if ps is None]
        lines = [f"cenário: {p}" for p in r["background"] or []]
        lines += [f"variante {w}: {p}" for w, ps in r["variants"].items() for p in ps or []]
        lines += [f"{k}: NÃO REVISADO (Gemini indisponível)" for k in skipped]
        wrong += len(lines)
        print(f"== {r['scene']}: " + ("OK" if not lines else f"{len(lines)} problema(s)")
              + (f"  (corrigido: {', '.join(r['fixed'])})" if r["fixed"] else ""), flush=True)
        for line in lines:
            print(f"   - {line}", flush=True)
    print(f"\n{len(scenes)} cena(s); {wrong} problema(s) ou item(ns) não revisado(s).")
    return 0 if wrong == 0 else 1


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projeto")
    ap.add_argument("--cena", action="append", help="só esta cena (pode repetir)")
    ap.add_argument("--corrigir", action="store_true", help="corrige o que achar (usa a GPU)")
    a = ap.parse_args()
    project = project_service.load_project(a.projeto)
    scenes = a.cena or [s.get("name") for s in project["scenes"].values() if scene_art.background_path(s)]
    return asyncio.run(run(a.projeto, scenes, a.corrigir))


if __name__ == "__main__":
    sys.exit(main())
