"""The game blueprint (ficha): assembled, checked and played without the editor or the LLM."""

import copy
import json
from pathlib import Path

from backend.ses import blueprint as bp

ROOT = Path(__file__).resolve().parents[1]

FICHA = """
nome: Cofre
inicio: Sala
arte: {estilo: noir, referencia: Sala}
requisitos: {puzzles: 2, mortes: 1}
cenas:
  - nome: Sala
    descricao: Uma sala com um quadro torto.
    saidas: {norte: Corredor}
    objetos:
      - nome: quadro
        descricao: Um quadro de um navio.
        script: |
          on push { if flag(cofre_visto) { say "Já mexeu." } else { set cofre_visto; show cofre; say "Atrás dele, um cofre!" } }
      - nome: cofre
        descricao: Um cofre de aço.
        escondido: true
        script: |
          on use with chave { set aberto; link leste to Saida; say "O cofre se abre e a parede gira." }
  - nome: Corredor
    descricao: Um corredor escuro.
    objetos:
      - nome: chave
        descricao: Uma chave pequena.
        pegavel: true
      - nome: botao
        descricao: Um botão vermelho.
        script: |
          on push { end "Um alarme dispara. A polícia chega. Fim." }
  - nome: Saida
    descricao: A rua.
    script: |
      on enter { end "Você escapa com o conteúdo do cofre. Vitória!" }
    variantes:
      - {quando: flag(aberto), mudanca: a porta está aberta}
testes:
  vitoria: Vitória
  solucao: [norte, pegar chave, sul, empurrar quadro, usar chave no cofre, leste]
  mortes:
    - {nome: alarme, comandos: [norte, empurrar botao], fim: alarme}
"""


def load():
    return bp.load(FICHA)


def errors(report):
    return [p["msg"] for p in report["problemas"] if p["nivel"] == "erro"]


def test_a_good_blueprint_builds_and_is_won_by_the_automatic_player():
    project, report = bp.check(load())
    assert report["ok"], report["problemas"]
    assert [t["ok"] for t in report["testes"]] == [True, True]
    assert report["testes"][0]["acoes_de_puzzle"] == ["empurrar quadro", "usar chave no cofre"]
    assert report["explorador"]["venceu"] and report["explorador"]["confirmado"]
    assert report["numeros"] == {"cenas": 3, "objetos": 4, "pegaveis": 1, "variantes": 1}
    assert report["arte"]["cenas_sem_arte"] == ["Sala", "Corredor", "Saida"]
    corredor = next(s for s in project["scenes"].values() if s["name"] == "Corredor")
    assert set(corredor["exits"]) == {"sul"}              # the way back is created


def test_logic_holes_are_errors():
    b = load()
    b["cenas"].append({"nome": "Porão", "descricao": "Ninguém chega aqui."})
    b["cenas"][1]["objetos"].append({"nome": "moeda", "descricao": "x", "escondido": True, "pegavel": True})
    b["cenas"][1]["objetos"][1]["script"] = 'on push { if flag(energia) { end "Alarme. Fim." } }'
    _, report = bp.check(b, explore_budget=0)
    errs = " | ".join(errors(report))
    assert "'Porão' não tem caminho" in errs
    assert "'moeda' começa escondido" in errs
    assert "flag 'energia' é testada" in errs
    assert "morte: alarme" in errs                         # the death no longer happens


def test_a_shortcut_to_the_victory_is_caught():
    b = load()
    b["cenas"][1]["saidas"] = {"leste": {"para": "Saida", "volta": False}}   # a door around the safe
    _, report = bp.check(b)
    assert any(e.startswith("ATALHO") for e in errors(report)), report["problemas"]


def test_requirements_and_refused_commands():
    b = load()
    b["requisitos"] = {"puzzles": 5}
    b["testes"]["solucao"] = ["olhar", "pegar vassoura"] + b["testes"]["solucao"]
    _, report = bp.check(b, explore_budget=0)
    errs = " | ".join(errors(report))
    assert "requisitos.puzzles = 5" in errs
    assert "recusou 1 comando(s): pegar vassoura" in errs


def test_script_errors_come_back_with_line_and_column():
    b = load()
    b["cenas"][0]["objetos"][0]["script"] = 'on push { say "sem fim" '
    _, report = bp.check(b, explore_budget=0)
    assert not report["ok"]
    assert any("linha 1, coluna" in e for e in errors(report))


def test_a_rebuild_keeps_ids_and_art():
    first, _ = bp.check(load(), explore_budget=0)
    sala_id = next(sid for sid, s in first["scenes"].items() if s["name"] == "Sala")
    sala = first["scenes"][sala_id]
    sala["objects"][0]["sprite"] = "backgrounds/sala.png"
    quadro = next(o for o in sala["objects"] if o["name"] == "quadro")
    quadro.update({"sprite": "", "position": {"x": 500, "y": 400}, "size": {"width": 90, "height": 120}})
    quadro["properties"]["painted"] = True
    saida = next(s for s in first["scenes"].values() if s["name"] == "Saida")
    saida["variants"][0]["background"] = "backgrounds/aberta.png"

    b = load()
    b["cenas"][0]["descricao"] = "Uma sala nova."
    second, report = bp.check(b, first, explore_budget=0)
    assert report["ok"]
    assert sala_id in second["scenes"] and second["start_scene"] == sala_id
    s2 = second["scenes"][sala_id]
    assert s2["description"] == "Uma sala nova."
    assert s2["objects"][0]["sprite"] == "backgrounds/sala.png"
    q2 = next(o for o in s2["objects"] if o["name"] == "quadro")
    assert q2["id"] == quadro["id"] and q2["position"] == {"x": 500, "y": 400} and q2["properties"]["painted"]
    assert next(s for s in second["scenes"].values() if s["name"] == "Saida")["variants"][0]["background"] == "backgrounds/aberta.png"
    assert report["arte"]["cenas_sem_arte"] == ["Corredor", "Saida"]


def test_export_and_rebuild_of_the_demo_is_still_winnable():
    project = json.loads((ROOT / "tests" / "fixtures" / "o_farol_project.json").read_text(encoding="utf-8"))
    b = bp.load(bp.dump(bp.export(project)))
    import importlib.util
    spec = importlib.util.spec_from_file_location("demo", ROOT / "tools" / "build_demo_farol.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    b["testes"] = {"vitoria": "FIM", "solucao": demo.SOLUTION}
    rebuilt, report = bp.check(b, copy.deepcopy(project))
    assert report["ok"], report["problemas"]
    assert set(rebuilt["scenes"]) == set(project["scenes"])
    assert report["arte"]["pronta"]


def test_the_claustro_blueprint_passes():
    root = ROOT / "projects" / "Neve sobre o Claustro"
    if not (root / bp.FILE_NAME).exists():
        return
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    _, report = bp.check(bp.load((root / bp.FILE_NAME).read_text(encoding="utf-8")), project)
    assert report["ok"], errors(report)
    assert report["explorador"]["venceu"]
