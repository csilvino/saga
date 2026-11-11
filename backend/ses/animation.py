"""Looping animations written in the blueprint (ficha) and played by the player with CSS.

In the ficha, an object (or a whole scene) gets one line:

    animacao: balanco                                   # the defaults
    animacao: {tipo: balanco, angulo: 10, periodo: 2}   # or with values

and an object can have moving parts, each drawn as its own small picture on top of the object
(the pendulum of a clock, the hands of a mill):

    partes:
      - nome: pêndulo
        descricao: um pêndulo de latão com um disco dourado
        animacao: {tipo: balanco, angulo: 12, periodo: 2}
        onde: [0.5, 0.45]     # where it hangs from: fractions of the object's picture (x, y)
        altura: 0.4           # its height, as a fraction of the object's height

Effects (the project stores the English name):
    balanco  swing    rotates back and forth around its top (pendulum, hanging lamp, sign)
    oscilar  sway     rotates gently around its base (plant, flag, mast)
    flutuar  bob      goes up and down (boat, buoy); on a scene, the whole picture rocks
    tremular flicker  an irregular glow of colour on top (torch, candle, fire)
    pulsar   pulse    a slow glow that grows and fades (crystal, magic, screen)

swing, sway and bob move the object's pixels, so such an object (and any object with parts)
becomes a loose picture (sprite) instead of being painted in the background. flicker and pulse
only add light on top, so they also work on painted objects.
"""

from typing import List, Optional, Tuple

from backend.ses.world import slug

EFFECTS = {"balanco": "swing", "oscilar": "sway", "flutuar": "bob", "tremular": "flicker", "pulsar": "pulse"}
MOVING = {"swing", "sway", "bob"}
# amount: degrees (swing, sway), scene pixels (bob), strength 0-1 (flicker, pulse)
AMOUNT_KEY = {"swing": "angulo", "sway": "angulo", "bob": "amplitude", "flicker": "intensidade", "pulse": "intensidade"}
DEFAULTS = {"swing": (8, 2.0), "sway": (3, 4.0), "bob": (6, 3.5), "flicker": (0.5, 0.9), "pulse": (0.5, 2.5)}
LIMITS = {"swing": (0.5, 60), "sway": (0.5, 30), "bob": (1, 60), "flicker": (0.05, 1), "pulse": (0.05, 1)}
COLORS = {"laranja": "#ffa040", "amarelo": "#ffd75a", "azul": "#7fd4ff", "verde": "#7dffb0",
          "vermelho": "#ff5a4a", "roxo": "#c88cff", "branco": "#ffffff", "rosa": "#ff8ad8"}
DEFAULT_COLOR = {"flicker": "#ffa040", "pulse": "#7fd4ff"}
KEYS = {"tipo", "angulo", "amplitude", "intensidade", "periodo", "cor"}
PART_KEYS = {"nome", "descricao", "animacao", "onde", "altura"}


def _num(v) -> Optional[float]:
    if isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_effect(raw, where: str = "") -> Tuple[Optional[dict], List[str]]:
    """The stored effect ({"type", "amount", "period", "color"?}) and what is wrong with `raw`."""
    if raw is None or raw == "":
        return None, []
    if isinstance(raw, str):
        raw = {"tipo": raw}
    if not isinstance(raw, dict):
        return None, [f"{where}animacao precisa ser um tipo (ex.: balanco) ou um mapa {{tipo: ..., periodo: ...}}"]
    errs = []
    unknown = sorted(set(map(str, raw)) - KEYS)
    if unknown:
        errs.append(f"{where}animacao: não conheço {', '.join(unknown)} (use {', '.join(sorted(KEYS))})")
    kind = EFFECTS.get(slug(raw.get("tipo")))
    if not kind:
        return None, errs + [f"{where}animacao: tipo {raw.get('tipo')!r} não existe "
                             f"(use {', '.join(EFFECTS)})"]
    amount, period = DEFAULTS[kind]
    key = AMOUNT_KEY[kind]
    for k in ("angulo", "amplitude", "intensidade"):
        if k in raw and k != key:
            errs.append(f"{where}animacao: '{k}' não vale para {raw.get('tipo')} (use '{key}')")
    if key in raw:
        v, (lo, hi) = _num(raw[key]), LIMITS[kind]
        if v is None or not lo <= v <= hi:
            errs.append(f"{where}animacao: '{key}' precisa ser um número entre {lo} e {hi}")
        else:
            amount = v
    if "periodo" in raw:
        v = _num(raw["periodo"])
        if v is None or not 0.2 <= v <= 30:
            errs.append(f"{where}animacao: 'periodo' (segundos por ciclo) precisa ser entre 0.2 e 30")
        else:
            period = v
    effect = {"type": kind, "amount": amount, "period": period}
    if kind in DEFAULT_COLOR:
        color = raw.get("cor")
        if color is None:
            effect["color"] = DEFAULT_COLOR[kind]
        elif str(color).startswith("#") and len(str(color)) in (4, 7):
            effect["color"] = str(color)
        elif slug(color) in COLORS:
            effect["color"] = COLORS[slug(color)]
        else:
            errs.append(f"{where}animacao: cor {color!r} desconhecida (use {', '.join(COLORS)} ou #rrggbb)")
    elif "cor" in raw:
        errs.append(f"{where}animacao: 'cor' só vale para tremular e pulsar")
    return effect, errs


def parse_parts(raw, where: str = "") -> Tuple[List[dict], List[str]]:
    """The stored parts ([{"name", "description", "effect", "at": {x, y}, "height"}]) and the errors."""
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], [f"{where}partes precisa ser uma lista"]
    parts, errs, seen = [], [], set()
    for i, r in enumerate(raw):
        w = f"{where}parte nº {i + 1}: "
        if not isinstance(r, dict) or not str(r.get("nome") or "").strip():
            errs.append(f"{w}precisa de 'nome'")
            continue
        unknown = sorted(set(map(str, r)) - PART_KEYS)
        if unknown:
            errs.append(f"{w}não conheço {', '.join(unknown)} (use {', '.join(sorted(PART_KEYS))})")
        if slug(r["nome"]) in seen:
            errs.append(f"{w}duas partes com o nome {r['nome']!r}")
        seen.add(slug(r["nome"]))
        effect, e = parse_effect(r.get("animacao"), w)
        errs += e
        at = r.get("onde", [0.5, 0.3])
        xy = [_num(v) for v in at] if isinstance(at, list) and len(at) == 2 else None
        if not xy or any(v is None or not 0 <= v <= 1 for v in xy):
            errs.append(f"{w}'onde' precisa ser [x, y] com frações de 0 a 1 do desenho do objeto")
            xy = [0.5, 0.3]
        height = _num(r.get("altura", 0.4))
        if height is None or not 0.05 <= height <= 1:
            errs.append(f"{w}'altura' precisa ser uma fração entre 0.05 e 1 da altura do objeto")
            height = 0.4
        parts.append({"name": str(r["nome"]).strip(), "description": str(r.get("descricao") or r["nome"]).strip(),
                      "effect": effect, "at": {"x": xy[0], "y": xy[1]}, "height": height})
    return parts, errs


def moves(obj: dict) -> bool:
    """The object's own pixels move (or it has parts): it must be a loose picture, not painted."""
    return bool(obj.get("parts")) or (obj.get("effect") or {}).get("type") in MOVING


def to_ficha(effect: Optional[dict]):
    """The ficha form of a stored effect (for export)."""
    if not effect:
        return None
    name = next(k for k, v in EFFECTS.items() if v == effect["type"])
    out = {"tipo": name, AMOUNT_KEY[effect["type"]]: effect["amount"], "periodo": effect["period"]}
    if effect.get("color"):
        out["cor"] = next((k for k, v in COLORS.items() if v == effect["color"]), effect["color"])
    return out
