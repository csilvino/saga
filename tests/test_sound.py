"""Sound: the blueprint's 'som' fields and 'play' -> project.json -> what the engine tells the player."""

from backend.ses import blueprint as bp
from backend.ses.engine import GameEngine

FICHA = """
nome: Sino
inicio: Torre
cenas:
  - nome: Torre
    descricao: O alto da torre.
    som:
      ambiente: vento uivando
      quando:
        - {quando: flag(tocou), ambiente: eco de sino ao longe}
    saidas: {baixo: Capela}
    objetos:
      - nome: sino
        descricao: Um sino de bronze.
        tipo: movel
        script: |
          on push { set tocou; play "badalada grave de sino"; say "DONG." }
      - nome: corvo
        descricao: Um corvo no parapeito.
        tipo: personagem
        som: {descricao: um corvo grasna, repete: as vezes, intervalo: [10, 30], quando: not flag(tocou)}
  - nome: Capela
    descricao: Bancos vazios.
    som: goteira lenta
    objetos:
      - nome: relogio
        descricao: Um relógio de pêndulo.
        tipo: movel
        som: tique-taque de relógio
        script: |
          on push {
            if flag(tocou) { play "badalada grave de sino"; end "O tempo para. Vitória!" }
            else { say "O pêndulo não se mexe." }
          }
testes:
  vitoria: Vitória
  solucao: [empurrar sino, baixo, empurrar relogio]
"""


def build(text=FICHA, previous=None):
    project, report = bp.check(bp.load(text), previous, explore_budget=2000)
    assert report["ok"], report["problemas"]
    return project


def scene(project, name):
    return next(s for s in project["scenes"].values() if s["name"] == name)


def test_the_blueprint_sounds_reach_the_project():
    p = build()
    assert scene(p, "Torre")["sound"] == {"ambient": "vento uivando",
                                          "variants": [{"when": "flag(tocou)", "ambient": "eco de sino ao longe"}]}
    assert scene(p, "Capela")["sound"] == {"ambient": "goteira lenta", "variants": []}
    corvo = next(o for o in scene(p, "Torre")["objects"] if o["name"] == "corvo")
    assert corvo["sound"] == {"desc": "um corvo grasna", "mode": "random", "every": [10.0, 30.0],
                              "when": "not flag(tocou)"}
    assert list(p["sounds"]) == ["badalada_grave_de_sino"]            # the same 'play' twice = one sound
    st = bp.sound_status(p)
    assert st["sons"] == 6 and not st["som_pronto"]


def test_bad_sound_fields_are_errors():
    bad = FICHA.replace("intervalo: [10, 30]", "intervalo: [30]").replace("ambiente: vento uivando", "ambiente: ''")
    report = bp.check(bp.load(bad), None, explore_budget=2000)[1]
    msgs = [p["msg"] for p in report["problemas"] if p["nivel"] == "erro"]
    assert any("intervalo" in m for m in msgs) and any("sem 'ambiente'" in m for m in msgs)
    bad = FICHA.replace("quando: not flag(tocou)", "quando: flag(")
    assert not bp.check(bp.load(bad), None, explore_budget=2000)[1]["ok"]


def test_a_comma_inside_braces_without_quotes_is_caught():
    # YAML cuts "eco de sino ao longe, grave" at the comma and makes "grave" a key
    for old, new in (("ambiente: eco de sino ao longe}", "ambiente: eco de sino ao longe, grave}"),
                     ("descricao: um corvo grasna,", "descricao: um corvo grasna, rouco,")):
        report = bp.check(bp.load(FICHA.replace(old, new)), None, explore_budget=2000)[1]
        assert any("precisa de aspas" in p["msg"] for p in report["problemas"]), new
    quoted = FICHA.replace("ambiente: eco de sino ao longe}", 'ambiente: "eco de sino ao longe, grave"}')
    assert scene(build(quoted), "Torre")["sound"]["variants"][0]["ambient"] == "eco de sino ao longe, grave"


def test_rebuilding_keeps_the_files_of_sounds_whose_text_did_not_change():
    p = build()
    for _kind, _text, holder in bp._sound_items(p):
        holder["file"] = "audio/x.ogg"
    p2 = build(FICHA.replace("goteira lenta", "goteira rápida"), previous=p)
    missing = bp.sound_status(p2)["sons_sem_arquivo"]
    assert missing == ["goteira rápida"]


def test_export_gives_the_same_sounds_back():
    p = build()
    again = build(bp.dump(bp.export(p)).replace("solucao: []", "solucao: [empurrar sino, baixo, empurrar relogio]")
                  .replace("vitoria: ''", "vitoria: Vitória"))
    assert [(k, t) for k, t, _ in bp._sound_items(again)] == [(k, t) for k, t, _ in bp._sound_items(p)]


def test_the_engine_tells_the_player_what_to_hear():
    p = build()
    for kind, text, holder in bp._sound_items(p):
        holder["file"] = f"audio/{kind}_{text[:5]}.ogg"
    e = GameEngine(p)
    out = e.start()
    assert out["view"]["ambient"] == "audio/ambient_vento.ogg"
    assert [s["mode"] for s in out["view"]["object_sounds"]] == ["random"]
    assert out["sounds"] == []
    out = e.command(out["state"], "empurrar sino")
    assert out["sounds"] == [{"text": "badalada grave de sino", "file": "audio/event_badal.ogg"}]
    assert out["view"]["ambient"] == "audio/ambient_eco d.ogg"         # the sound variant
    assert out["view"]["object_sounds"] == []                         # the crow is quiet now
    out = e.command(out["state"], "baixo")
    assert out["view"]["ambient"] == "audio/ambient_gotei.ogg"
    assert out["view"]["object_sounds"][0]["mode"] == "loop"


def test_a_sound_without_a_file_is_silent():
    e = GameEngine(build())
    out = e.command(e.start()["state"], "empurrar sino")
    assert out["view"]["ambient"] is None and out["sounds"][0]["file"] is None


def test_make_sounds_fills_every_file_and_resumes(tmp_path, monkeypatch):
    import asyncio
    import copy
    from backend.services import sound_gen
    state = {"project": build()}
    ps = sound_gen.project_service
    monkeypatch.setattr(ps, "load_project", lambda name: copy.deepcopy(state["project"]))
    monkeypatch.setattr(ps, "load_project_path", lambda name: tmp_path)
    monkeypatch.setattr(ps, "save_project_data", lambda name, p: state.__setitem__("project", copy.deepcopy(p)))
    made = []

    async def plan(items):
        return {t: {"prompt": f"EN {t}", "seconds": 30.0 if k == "ambient" else 2.0} for k, t in items}

    async def make(prompt, seconds, loop):
        made.append((prompt, seconds, loop))
        if len(made) == 3:
            raise sound_gen.SoundError("gerador de som falhou: CUDA out of memory")
        return b"OggS fake"

    monkeypatch.setattr(sound_gen, "plan", plan)
    monkeypatch.setattr(sound_gen, "make", make)
    r = asyncio.run(sound_gen.make_sounds("T"))
    assert len(r["falhas"]) == 1 and len(r["feitos"]) == len(made) - 1
    assert ("EN vento uivando", 30.0, True) in made                    # background: a loop
    assert ("EN badalada grave de sino", 2.0, False) in made           # event: once
    left = bp.sound_status(state["project"])["sons_sem_arquivo"]
    assert len(left) == 1
    r = asyncio.run(sound_gen.make_sounds("T"))                        # resumes: only what failed
    assert r["som_pronto"] and len(r["feitos"]) == 1
    files = [h["file"] for _k, _t, h in bp._sound_items(state["project"])]
    assert all((tmp_path / f).read_bytes() == b"OggS fake" for f in files)


def test_without_the_worker_it_stops_at_once(monkeypatch):
    import asyncio
    import copy
    from backend.services import sound_gen
    state = {"project": build()}
    monkeypatch.setattr(sound_gen.project_service, "load_project", lambda name: copy.deepcopy(state["project"]))
    calls = []

    async def plan(items):
        return {}

    async def make(prompt, seconds, loop):
        calls.append(prompt)
        raise sound_gen.SoundError("o gerador local (local_image_worker) não está rodando")
    monkeypatch.setattr(sound_gen, "plan", plan)
    monkeypatch.setattr(sound_gen, "make", make)
    r = asyncio.run(sound_gen.make_sounds("T"))
    assert len(calls) == 1 and not r["som_pronto"]
