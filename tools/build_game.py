"""
Builds a game from its blueprint (ficha.yaml), outside the editor.

    python tools/build_game.py "Neve sobre o Claustro"                 # checks projects/<nome>/ficha.yaml
    python tools/build_game.py "Meu Jogo" --ficha rascunho.yaml        # checks another file
    python tools/build_game.py "Meu Jogo" --ficha rascunho.yaml --salvar   # checks and builds
    python tools/build_game.py "Meu Jogo" --arte                       # makes the art still missing (hours)
    python tools/build_game.py "Meu Jogo" --som                        # makes the sounds still missing
    python tools/build_game.py "Meu Jogo" --exportar > ficha.yaml      # a blueprint from a project made by hand

The exit code is 0 when the blueprint has no errors.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.ses import blueprint  # noqa: E402


def show(report: dict):
    for p in report.get("problemas", []):
        print(f"  [{p['nivel']}] {p['msg']}" + (f"  ({p['onde']})" if p.get("onde") else ""))
    for t in report.get("testes", []):
        print(f"  teste {t['teste']}: {'OK' if t['ok'] else 'FALHOU'} ({t['comandos']} comandos)"
              + (f" — {t['motivo']}" if t.get("motivo") else ""))
    e = report.get("explorador")
    if e:
        print(f"  jogador automático: {'venceu' if e['venceu'] else 'não venceu'} "
              f"({e['comandos_testados']} comandos testados, {e['estados']} estados"
              + (f", vitória em {len(e['caminho'])} comandos" if e["venceu"] else "") + ")")
    if "numeros" in report:
        print(f"  {json.dumps(report['numeros'], ensure_ascii=False)}")
    if "arte" in report:
        a = report["arte"]
        print(f"  arte: {len(a['cenas_sem_arte'])} cenas e {len(a['variantes_sem_arte'])} variantes por fazer")
    if "som" in report:
        print(f"  som: {len(report['som']['sons_sem_arquivo'])} de {report['som']['sons']} sons por fazer")
    print("OK" + (" — salvo" if report.get("salvo") else "") if report.get("ok") else "COM ERROS")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projeto")
    ap.add_argument("--ficha", help="arquivo da ficha (padrão: projects/<projeto>/ficha.yaml)")
    ap.add_argument("--salvar", action="store_true", help="monta o projeto se a ficha não tiver erros")
    ap.add_argument("--arte", action="store_true", help="gera a arte que falta (cenas e variantes)")
    ap.add_argument("--som", action="store_true", help="gera os sons que faltam (ambiente, objetos, play)")
    ap.add_argument("--exportar", action="store_true", help="imprime uma ficha tirada do project.json")
    a = ap.parse_args()

    if a.exportar:
        from backend.services.project_service import project_service
        sys.stdout.reconfigure(encoding="utf-8")
        print(blueprint.dump(blueprint.export(project_service.load_project(a.projeto))))
        return 0
    if a.arte:
        result = asyncio.run(blueprint.make_art(a.projeto, lambda m: print(time.strftime("%H:%M:%S"), m, flush=True)))
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result.get("pronta") else 1
    if a.som:
        from backend.services import sound_gen
        sys.stdout.reconfigure(encoding="utf-8")
        result = asyncio.run(sound_gen.make_sounds(a.projeto, lambda m: print(time.strftime("%H:%M:%S"), m, flush=True)))
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result.get("som_pronto") else 1
    text = Path(a.ficha).read_text(encoding="utf-8") if a.ficha else None
    report = blueprint.build(a.projeto, text, save=a.salvar)
    show(report)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
