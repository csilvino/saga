"""
Builds projects/O Farol: a small text adventure written in SES v2, assembled with the same tools the
AI director uses (backend/ses/director_tools.py), then played to the end to prove it is solvable.

    python tools/build_demo_farol.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.ses.director_tools import run_tool  # noqa: E402

NAME = "O Farol"
SOLUTION = [
    "olhar", "pegar garrafa", "abrir garrafa", "ler bilhete", "norte",
    "leste", "abrir gaveta", "pegar fosforos", "examinar lampiao", "pegar chave", "oeste",
    "norte", "usar chave na porta", "norte", "cima", "usar fosforos na lampada",
]


def tool(p, tool_name, **args):
    r = run_tool(p, tool_name, args)
    if "error" in r:
        raise SystemExit(f"{tool_name} {args}: {r}")
    for w in r.get("warnings", []):
        print(f"  aviso em {tool_name}: {w}")
    return r


def build():
    p = {"name": NAME, "version": "1.0.0", "start_scene": "", "navigation_mode": "text",
         "metadata": {"action_history": [], "deleted_objects": [], "narrative_directives": ""},
         "scenes": {}, "assets": {"sprites": {}, "items": {}, "audio": {}},
         "launcher": {"title": NAME, "description": "Náufrago numa ilha, você precisa reacender o farol.",
                      "version": "1.0.0"}}

    tool(p, "create_scene", name="Praia",
         description="Areia fria e destroços por toda parte. A tempestade passou, mas o seu barco não. "
                     "Ao norte, uma trilha sobe entre as rochas.",
         script='on first_enter { say "Você acorda com o gosto de sal na boca. Está vivo, e sozinho." }')
    tool(p, "create_scene", name="Trilha",
         description="Uma trilha estreita entre rochas escuras. O farol se ergue ao norte, apagado. "
                     "A leste, uma casinha de pedra.")
    tool(p, "create_scene", name="Casa do Faroleiro",
         description="Uma casa de um cômodo só, abandonada há anos. Cheira a querosene e mofo.")
    tool(p, "create_scene", name="Base do Farol",
         description="A base de pedra do farol. Uma porta de ferro enferrujada dá para dentro.")
    tool(p, "create_scene", name="Dentro do Farol",
         description="Uma escada em espiral sobe na escuridão. O vento assobia lá no alto.")
    tool(p, "create_scene", name="Topo do Farol",
         description="A sala da lâmpada. Pelo vidro rachado, você vê o mar inteiro — e, muito longe, "
                     "as luzes de um navio.")

    tool(p, "connect_scenes", from_scene="Praia", direction="norte", to_scene="Trilha")
    tool(p, "connect_scenes", from_scene="Trilha", direction="leste", to_scene="Casa do Faroleiro")
    tool(p, "connect_scenes", from_scene="Trilha", direction="norte", to_scene="Base do Farol")
    # Base -> Dentro is opened by the key (link in the door's script); only the way back exists
    tool(p, "connect_scenes", from_scene="Dentro do Farol", direction="sul", to_scene="Base do Farol", one_way=True)
    tool(p, "connect_scenes", from_scene="Dentro do Farol", direction="cima", to_scene="Topo do Farol")

    # Praia
    tool(p, "create_object", scene="Praia", name="garrafa", portable=True, object_type="item",
         description="Uma garrafa de vidro verde, arrolhada. Tem um papel dentro.",
         script='''on open {
  if flag(garrafa_aberta) { say "Já está aberta e vazia." }
  else { set garrafa_aberta; take bilhete; say "Você tira a rolha e puxa o papel: um bilhete." }
}''')
    tool(p, "create_object", scene="Praia", name="bilhete", hidden=True, portable=True, object_type="item",
         aliases=["papel"],
         description='Letra tremida: "Se alguém achar isto — a chave do farol fica onde a luz dorme. '
                     'O fogo está na gaveta."')
    tool(p, "create_object", scene="Praia", name="barco", object_type="cenario", aliases=["destrocos"],
         description="O que sobrou do seu barco: meia quilha e um mastro partido. Não vai a lugar nenhum.")
    tool(p, "create_object", scene="Praia", name="gaivota", object_type="personagem",
         description="Uma gaivota gorda observa você de cima de uma pedra.",
         script='''on talk {
  inc conversas_gaivota
  if flag(conversas_gaivota) >= 3 { say "A gaivota suspira e olha para o farol. Parece até que entendeu." }
  else { say "A gaivota inclina a cabeça e grita. Não ajuda muito." }
}
on take { say "Ela sai voando e pousa de novo, um pouco mais longe." }''')

    # Casa do Faroleiro
    tool(p, "create_object", scene="Casa do Faroleiro", name="gaveta", object_type="movel",
         aliases=["comoda", "cômoda"], description="Uma cômoda com uma gaveta emperrada.",
         script='''on open {
  if flag(gaveta_aberta) { say "A gaveta já está aberta." }
  else { set gaveta_aberta; show fosforos; say "Você força a gaveta. Dentro, uma caixa de fósforos." }
}''')
    tool(p, "create_object", scene="Casa do Faroleiro", name="fósforos", hidden=True, portable=True,
         object_type="item", aliases=["fosforos", "caixa de fosforos"],
         description="Uma caixa de fósforos, quase cheia. Secos, por milagre.")
    tool(p, "create_object", scene="Casa do Faroleiro", name="lampião", object_type="movel",
         aliases=["lampiao", "lamparina"],
         description="Um lampião velho pendurado sobre a cama — a luz que dorme.",
         script='''on examine {
  if flag(chave_achada) { say "Um lampião velho, vazio." }
  else { set chave_achada; show chave; say "Você levanta o lampião. Embaixo da base, presa com cera, uma chave grande!" }
}''')
    tool(p, "create_object", scene="Casa do Faroleiro", name="chave", hidden=True, portable=True,
         object_type="chave", aliases=["chave grande", "chave de ferro"],
         description="Uma chave de ferro, pesada, do tamanho da sua mão.")
    tool(p, "create_object", scene="Casa do Faroleiro", name="cama", object_type="movel",
         description="Uma cama estreita com um cobertor comido pelas traças.")

    # Base do Farol
    tool(p, "create_object", scene="Base do Farol", name="porta", object_type="porta",
         aliases=["porta de ferro"], description="Uma porta de ferro, trancada, com uma fechadura grande.",
         script='''on examine {
  if flag(porta_aberta) { say "A porta está aberta. Lá dentro, uma escada sobe." }
  else { say "Uma porta de ferro, trancada, com uma fechadura grande." }
}
on open {
  if flag(porta_aberta) { say "Já está aberta." }
  else { say "Trancada. Precisa de uma chave." }
}
on use with chave {
  if flag(porta_aberta) { say "Já está aberta." }
  else { set porta_aberta; link norte to "Dentro do Farol"; say "A chave gira com um rangido. A porta se abre para o norte." }
}''')

    # Topo do Farol
    tool(p, "create_object", scene="Topo do Farol", name="lâmpada", object_type="movel",
         aliases=["lampada", "lente", "pavio"],
         description="A grande lente do farol, com um pavio grosso no centro. Precisa de fogo.",
         script='''on use with fosforos {
  end "Você risca um fósforo e acende o pavio. A lente gira e o facho varre o mar. Minutos depois, o navio muda de rumo e apita três vezes: viram você. FIM."
}
on use { say "Com o quê? O pavio precisa de fogo." }''')
    tool(p, "set_start_scene", scene="Praia")
    return p


def main():
    p = build()
    r = run_tool(p, "playtest", {"commands": SOLUTION})
    print(r["transcript"])
    if not r["ended"] or r["script_errors"]:
        raise SystemExit(f"\nO jogo não terminou: ended={r['ended']} erros={r['script_errors']}")
    out = ROOT / "projects" / NAME
    for sub in ("backgrounds", "sprites", "items", "audio", "fonts"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    (out / "project.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nOK: {out / 'project.json'}")


if __name__ == "__main__":
    main()
