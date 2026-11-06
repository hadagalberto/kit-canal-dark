"""Etapa 7: publicação. Cada rede é um plugin em publicadores/<rede>.py com a função
publicar(mp4, meta, dry) -> {"ok": bool, "url"?: str, "error"?: str}.

Erro com prefixo muda o comportamento:
- "challenge:", "login_required:", "blocked:"  pausa a rede até você resolver e pôr "<x>_paused": false
- "rejected:"  a rede recusou ESTE post; só pausa depois de 3 seguidas (mudança de API, não de conteúdo)
"""
import datetime
import importlib

from .banco import published_today
from .config import CONFIG, log, now, save_json

# rede -> prefixo das chaves no pipeline.json
NETS = {"instagram": "ig", "youtube": "yt", "tiktok": "tt"}


def limite(net, cfg):
    """Posts por dia permitidos hoje: rampa de aquecimento para as redes em ramp.nets, fixo para as outras."""
    ramp = cfg.get("ramp") or {}
    if net not in ramp.get("nets", []):
        return cfg[f"{NETS[net]}_max_per_day"]
    steps = sorted(ramp["steps"])
    dias = (now().date() - datetime.date.fromisoformat(ramp["start"])).days
    i = max([j for j, (d, _) in enumerate(steps) if dias >= d] or [0])
    corte = (now() - datetime.timedelta(days=ramp.get("cooldown_days", 7))).isoformat()
    if any(pz.get("net") == net and pz.get("at", "") >= corte for pz in cfg.get("pause_log", [])):
        i = max(i - 1, 0)
    return steps[i][1]


def redes_livres(cfg, db, perfil):
    """Redes da ficha do canal ("redes"), sem pausa e abaixo do teto do dia."""
    nets = []
    for net in perfil.get("redes") or []:
        if net not in NETS:
            log(f"rede desconhecida na ficha: {net}")
            continue
        k = NETS[net]
        if cfg.get(f"{k}_paused"):
            log(f"{net} pausado:", cfg.get(f"{k}_paused_reason"))
        elif published_today(db, net) >= limite(net, cfg):
            log(f"{net}: teto do dia atingido")
        else:
            nets.append(net)
    return nets


def publicar(mp4, meta, nets, dry):
    """-> {rede: resultado}. Uma rede que quebra não derruba as outras."""
    res = {}
    for net in nets:
        try:
            mod = importlib.import_module(f"publicadores.{net}")
            res[net] = mod.publicar(str(mp4), meta, dry)
        except Exception as e:
            res[net] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
        log(f"publicar {net}:", res[net])
    return res


def trata_erros(res, cfg):
    """Conta recusas e pausa redes com problema de conta. -> (links, erros, pausadas)."""
    links = {n: r["url"] for n, r in res.items() if r.get("ok") and r.get("url")}
    erros = {n: r.get("error", "") for n, r in res.items() if not r.get("ok") and r.get("error")}
    rej = cfg.setdefault("rejects", {})
    for net in res:
        if net in links:
            rej[net] = 0
        elif erros.get(net, "").startswith("rejected:"):
            rej[net] = rej.get(net, 0) + 1
            if rej[net] >= 3:
                erros[net] = "blocked: 3 recusas seguidas, " + erros[net]
    pausadas = []
    for net, e in erros.items():
        if e.split(":")[0] in ("challenge", "login_required", "blocked"):
            k = NETS[net]
            cfg[f"{k}_paused"], cfg[f"{k}_paused_reason"] = True, f"{now():%d/%m %H:%M} {e[:120]}"
            cfg.setdefault("pause_log", []).append({"net": net, "at": now().isoformat(timespec="seconds"), "reason": e[:120]})
            pausadas.append(net)
    save_json(CONFIG, cfg)
    return links, erros, pausadas
