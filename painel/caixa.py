"""Caixa do painel: gastos por período, views, saldos dos fornecedores e cotação do dólar.

Portado do painel da VPS (fabrica_status.py / fabrica_saldos.py), lendo /dados direto.
As chaves vêm do ambiente (.env) e só vão no cabeçalho de cada consulta: nenhuma chave,
corpo de resposta ou mensagem de erro do fornecedor sai daqui ("HTTP 401", "timeout" etc.).

  ElevenLabs  GET /v1/user/subscription  (a chave precisa da permissão User -> Read)
  OpenRouter  GET /api/v1/credits; se a chave não ler a conta, GET /api/v1/key (limite da chave)
  Anthropic   a API não informa saldo. Com "custos": {"anthropic_saldo": {"usd": <saldo do console>,
              "em": "AAAA-MM-DD"}} no pipeline.json do canal, o saldo estimado é esse valor menos o
              llm_usd gasto desde aquele dia.
  Dólar       USD_BRL do .env, ou a PTAX de venda do Banco Central (uma consulta por dia).
"""
import datetime
import json
import os
import threading
import time
import urllib.error
import urllib.request

from pipeline import config as C

SALDOS_S = 300  # no máximo uma consulta aos fornecedores a cada 5 min
_trava = threading.Lock()
_cache = {"saldos": (0.0, None), "cotacao": (0.0, None)}


def _linhas(path):
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                try:
                    yield json.loads(ln)
                except ValueError:
                    continue
    except OSError:
        return


def custos(hoje, p):
    """Gasto por período (hoje, 7 dias, mês corrente): LLM e imagens em US$ exatos, voz em créditos."""
    ini = {"hoje": hoje, "semana": hoje - datetime.timedelta(days=6), "mes": hoje.replace(day=1)}
    r = {k: {"llm_usd": 0.0, "ia_usd": 0.0, "creditos": 0, "rodadas": 0, "publicadas": 0} for k in ini}
    menor = min(ini.values()).isoformat()
    for c in _linhas(p["costs"]):
        d = c.get("at", "")[:10]
        if d < menor:
            continue
        d = datetime.date.fromisoformat(d)
        for k, desde in ini.items():
            if d >= desde:
                x = r[k]
                x["llm_usd"] += float(c.get("llm_usd") or 0)
                x["ia_usd"] += float(c.get("ia_usd") or 0)
                x["creditos"] += int(c.get("eleven_creditos") or 0)
                x["rodadas"] += 1
                x["publicadas"] += c.get("resultado") == "publicado"
    for x in r.values():
        x["llm_usd"] = round(x["llm_usd"], 2)
        x["ia_usd"] = round(x["ia_usd"], 2)
    return r


def estatisticas(hoje_s, periodos, p):
    """stats.jsonl do canal ({id, rede, at, views, likes}, uma linha por leitura). Sem arquivo, tudo zero.
    Total = última leitura de cada (reel, rede); ganho do período = total menos a última leitura antes dele."""
    base = {n: {} for n in periodos}
    ult, antes, leitura = {}, {}, None
    for s in _linhas(p["stats"]):
        k, at = (s.get("id"), s.get("rede")), s.get("at", "")
        ult[k] = s
        if at < hoje_s:
            antes[k] = s
        for n, desde in periodos.items():
            if at < desde:
                base[n][k] = s.get("views") or 0
        leitura = max(leitura or at, at)
    redes = {}
    for (nid, rede), s in ult.items():
        d = redes.setdefault(rede, {"views": 0, "likes": 0, "views_hoje": 0, "likes_hoje": 0, "videos": 0})
        a = antes.get((nid, rede), {})
        d["views"] += s.get("views") or 0
        d["likes"] += s.get("likes") or 0
        d["videos"] += 1
        if s.get("at", "") >= hoje_s:
            d["views_hoje"] += (s.get("views") or 0) - (a.get("views") or 0)
            d["likes_hoje"] += (s.get("likes") or 0) - (a.get("likes") or 0)
    top = sorted(ult.items(), key=lambda kv: kv[1].get("views") or 0, reverse=True)[:3]
    total = sum(s.get("views") or 0 for s in ult.values())
    return {"leitura": leitura, "redes": redes, "views_total": total,
            "views_ganho": {n: total - sum(b.values()) for n, b in base.items()},
            "top": [{"id": k[0], "rede": k[1], "views": v.get("views"), "likes": v.get("likes")} for k, v in top]}


def _pega(url, cabecalhos):
    """(json, None) ou (None, motivo curto, sem nada do corpo da resposta)."""
    try:
        req = urllib.request.Request(url, headers={**cabecalhos, "User-Agent": "canal-dark-kit"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:
        return None, type(e).__name__


def _elevenlabs():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k:
        return {"ok": False, "erro": "sem ELEVENLABS_API_KEY no .env"}
    d, erro = _pega("https://api.elevenlabs.io/v1/user/subscription", {"xi-api-key": k})
    if erro:
        return {"ok": False, "erro": erro + (" (a chave precisa da permissão user_read)" if erro in ("HTTP 401", "HTTP 403") else "")}
    reset = d.get("next_character_count_reset_unix")
    return {"ok": True, "usados": d.get("character_count"), "limite": d.get("character_limit"), "plano": d.get("tier"),
            "renova_em": datetime.datetime.fromtimestamp(reset, C.FUSO).isoformat() if reset else None}


def _openrouter():
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not k:
        return {"ok": False, "erro": "sem OPENROUTER_API_KEY no .env"}
    h = {"Authorization": f"Bearer {k}"}
    d, erro = _pega("https://openrouter.ai/api/v1/credits", h)
    if not erro:
        d = d.get("data") or {}
        tot, uso = d.get("total_credits"), d.get("total_usage")
        return {"ok": True, "fonte": "conta", "comprado_usd": tot, "usado_usd": uso,
                "restante_usd": round(tot - uso, 2) if tot is not None and uso is not None else None}
    d2, erro2 = _pega("https://openrouter.ai/api/v1/key", h)
    if erro2:
        return {"ok": False, "erro": erro}
    d2 = d2.get("data") or {}
    return {"ok": True, "fonte": "chave", "limite_usd": d2.get("limit"), "usado_usd": d2.get("usage"),
            "restante_usd": d2.get("limit_remaining")}


def _anthropic():
    # o saldo informado fica no pipeline.json do canal do .env; o gasto soma todos os canais
    s = ((C.load_json(C.caminhos(C.CANAL)["config"], {}) or {}).get("custos") or {}).get("anthropic_saldo") or {}
    if not isinstance(s.get("usd"), (int, float)) or not s.get("em"):
        return {"ok": False, "erro": "a API não informa saldo; ponha custos.anthropic_saldo no pipeline.json"}
    gasto = sum(float(x.get("llm_usd") or 0) for n in C.lista_canais()
                for x in _linhas(C.caminhos(n)["costs"]) if x.get("at", "")[:10] >= s["em"])
    return {"ok": True, "informado_usd": s["usd"], "em": s["em"], "gasto_desde_usd": round(gasto, 2),
            "restante_usd": round(s["usd"] - gasto, 2)}


def saldos():
    with _trava:
        quando, valor = _cache["saldos"]
        if valor is None or time.time() - quando >= SALDOS_S:
            valor = {"consultado_em": C.now().isoformat(timespec="seconds"), "elevenlabs": _elevenlabs(),
                     "openrouter": _openrouter(), "anthropic": _anthropic()}
            _cache["saldos"] = (time.time(), valor)
        return valor


def cotacao():
    fixa = os.environ.get("USD_BRL", "").strip().replace(",", ".")
    if fixa:
        try:
            return {"usd_brl": float(fixa), "fonte": ".env"}
        except ValueError:
            pass
    with _trava:
        quando, valor = _cache["cotacao"]
        if valor is not None and time.time() - quando < 6 * 3600:
            return valor
        valor = {"usd_brl": None, "fonte": None}
        hoje = C.now().date()
        ini = (hoje - datetime.timedelta(days=7)).strftime("%m-%d-%Y")
        url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo("
               f"dataInicial=@i,dataFinalCotacao=@f)?@i='{ini}'&@f='{hoje:%m-%d-%Y}'&$format=json")
        d, erro = _pega(url, {})
        if not erro and (d.get("value") or []):
            valor = {"usd_brl": round(float(d["value"][-1]["cotacaoVenda"]), 4), "fonte": "PTAX"}
        _cache["cotacao"] = (time.time(), valor)
        return valor
