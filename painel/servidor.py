"""Painel "Fábrica de reels": servidor local que lê /dados direto (sem SSH).

GET  /             a página (index.html, pixel art, um robô por etapa)
GET  /status.json  estado de todos os canais, montado a partir de /dados (cache de 3 s)
POST /rodar?canal= cria /dados/rodar-agora.<canal>; o agendador pega no próximo tick
POST /canais       cria /dados/canais/<id>.json (novo_canal.py); o agendador passa a ver o canal
POST /ficha?canal=<id>&acao=ler|salvar   lê ou grava a ficha de um canal criado pelo painel (validada)

Só leitura, fora o gatilho e a criação de canal. Nunca abre segredos/ nem a sessão das redes. A Caixa
(caixa.py) consulta o saldo de ElevenLabs e OpenRouter com as chaves do ambiente, no máximo a cada 5 min,
sem imprimi-las.
O compose publica a porta só em 127.0.0.1. O POST só vale vindo da própria página:
Host local (contra DNS rebinding), Origin igual quando vier e o cabeçalho X-Fabrica,
que obriga um preflight de CORS ao qual este servidor nunca responde.
"""
import datetime
import json
import os
import pathlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pipeline import config as C
from pipeline.estado import ETAPAS
from pipeline.publicar import NETS, limite
from pipeline.robos import ROBOS, TITO

from . import caixa, novo_canal

AQUI = pathlib.Path(__file__).resolve().parent
PORTA = int(os.environ.get("PAINEL_PORTA", "8787"))  # porta publicada no Windows (compose)
CACHE_S = 3


def _linhas(path, n=None):
    try:
        with open(path, encoding="utf-8") as f:
            linhas = [json.loads(ln) for ln in f if ln.strip()]
    except (OSError, ValueError):
        return []
    return linhas[-n:] if n else linhas


def _iso(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def andar(nome, dia, est, ag_status, ag_vivo):
    """Um canal (um andar da fábrica) a partir de /dados/<canal>."""
    p = C.caminhos(nome)
    perfil = C.canal(nome)
    hoje = dia.isoformat()
    cfg = {**C.DEFAULT_CONFIG, **C.load_json(p["config"], {})}
    if not cfg["ramp"].get("start"):
        cfg["ramp"]["start"] = hoje
    db = C.load_json(p["db"], {"items": []})
    ag = (ag_status.get("canais") or {}).get(nome, {})

    agora = None
    if est.get("rodando") and est.get("canal") == nome:
        ini = _iso(est.get("inicio"))
        agora = {"etapa": ETAPAS.index(est.get("etapa", "pauta")), "inicio": est.get("inicio"),
                 "decorrido_s": (C.now() - ini).total_seconds() if ini else 0,
                 "noticia": est.get("noticia"), "manchete": est.get("titulo"), "estilo": None}

    rodadas = []
    for r in reversed(_linhas(p["rodadas"], 12)):
        ini, fim = _iso(r.get("inicio")), _iso(r.get("fim"))
        rodadas.append({"resultado": r.get("resultado", "sem_resultado"),
                        "etapa": ETAPAS.index(r["etapa"]) if r.get("etapa") in ETAPAS else 0,
                        "fim": r.get("fim"), "noticia": r.get("noticia"), "motivo": r.get("motivo", ""),
                        "links": r.get("links") or {}, "duracao_s": (fim - ini).total_seconds() if ini and fim else 0,
                        "imagem_ia": None, "redes_no_teto": [], "mp4": r.get("mp4")})

    pubs = [{"at": it["at"], "id": it["id"], "titulo": (it.get("titles") or [it.get("title")])[0], "links": it["links"]}
            for it in db["items"] if it.get("at", "").startswith(hoje) and it.get("links")]
    redes = {}
    for net in perfil.get("redes") or []:
        if net in NETS:
            k = NETS[net]
            redes[net] = {"hoje": sum(1 for x in pubs if net in x["links"]), "teto": limite(net, cfg),
                          "pausada": bool(cfg.get(f"{k}_paused")), "motivo_pausa": cfg.get(f"{k}_paused_reason", "")}
    custos = [c for c in _linhas(p["costs"]) if c.get("at", "").startswith(hoje)]
    res = [c.get("resultado") for c in custos]
    return {
        "id": nome, "nome": perfil["brand"]["name"], "job_id": nome, "criado_no_painel": C.arquivo_canal(nome).parent == C.CANAIS_CRIADOS,
        "motor": "exemplo" if C.MOTOR == "exemplo" else "api", "dry_run": C.MOTOR == "exemplo" or not C.publica(perfil),
        "trava_geral": C.DRY_RUN, "ficha_publica": perfil.get("publicar") is True,
        "job": {"ligado": ag_vivo, "estado": "ok" if ag_vivo else "paused", "agenda": C.agenda_de(nome, perfil),
                "proxima": ag.get("proxima"), "motivo_pausa": "" if ag_vivo else "sem sinal do Tito"},
        "agora": agora, "rodadas": rodadas, "publicados_hoje": pubs, "redes": redes,
        "stats": caixa.estatisticas(hoje, {"hoje": hoje, "semana": (dia - datetime.timedelta(days=6)).isoformat(),
                                            "mes": dia.replace(day=1).isoformat()}, p),
        "custos": caixa.custos(dia, p), "teto_llm_dia": cfg.get("llm_usd_dia", 5),
        "custos_hoje": {"rodadas": len(custos), "publicadas": res.count("publicado"),
                        "descartadas": res.count("descartado"), "puladas": res.count("pulou") + res.count("teto"),
                        "usd": round(sum(float(c.get("llm_usd") or 0) + float(c.get("ia_usd") or 0) for c in custos), 2)},
        "imagens_ia": {"hoje": (cfg.get("ai_images") or {}).get(hoje, 0), "teto": cfg.get("ai_images_per_day", 10)},
    }


def status():
    dia = C.now().date()
    est = C.load_json(C.ESTADO, {"rodando": False})
    ag_status = C.load_json(C.DADOS / "agendador.json", {})
    vivo = _iso(ag_status.get("vivo_em"))
    ag_vivo = bool(vivo and (C.now() - vivo).total_seconds() < 60)
    canais, erros = [], []
    for nome in C.lista_canais():
        try:
            canais.append(andar(nome, dia, est, ag_status, ag_vivo))
        except (Exception, SystemExit) as e:  # um perfil quebrado não derruba o painel inteiro
            erros.append(f"{nome}: {type(e).__name__}: {e}"[:200])
    return {
        "gerado_em": C.now().isoformat(timespec="seconds"), "hoje": dia.isoformat(),
        "provedor": os.environ.get("LLM_PROVEDOR", "anthropic").strip().lower() or "anthropic",
        "cotacao": caixa.cotacao(), "saldos": caixa.saldos(), "canais": canais, "erros_canais": erros,
        "robos": ROBOS, "tito": TITO,
        "novo_canal": {"modelos": novo_canal.modelos(), "estilos": novo_canal.estilos(), "redes": list(novo_canal.REDES)},
    }


class Cache:
    def __init__(self):
        self.trava, self.quando, self.ultimo = threading.Lock(), 0.0, None

    def get(self):
        with self.trava:
            if time.time() - self.quando >= CACHE_S or self.ultimo is None:
                try:
                    self.ultimo = {"ok": True, "erro": None, "dados": status()}
                except Exception as e:  # mostra o último dado bom e o erro
                    self.ultimo = {**(self.ultimo or {"dados": None}), "ok": False, "erro": f"{type(e).__name__}: {e}"[:300]}
                self.quando = time.time()
            return self.ultimo


CACHE = Cache()


def rodar(canal):
    if canal not in C.lista_canais():
        return {"ok": False, "mensagem": f"canal desconhecido: {canal}"}
    if C.load_json(C.ESTADO, {}).get("rodando"):
        return {"ok": False, "mensagem": "já tem rodada em andamento"}
    if C.gatilho(canal).exists():
        return {"ok": False, "mensagem": "já pedido, aguardando o agendador"}
    C.save_json(C.gatilho(canal), {"em": C.now().isoformat(timespec="seconds")})
    CACHE.quando = 0.0
    return {"ok": True, "mensagem": "pedido: o agendador começa em até 5 s"}


def criar_canal(corpo):
    try:
        cid, _ = novo_canal.criar(json.loads(corpo or b"{}"))
    except FileExistsError:
        return {"ok": False, "mensagem": "já existe um canal com esse id"}
    except ValueError as e:  # inclui JSON inválido
        return {"ok": False, "mensagem": str(e)[:300]}
    except Exception as e:
        return {"ok": False, "mensagem": f"{type(e).__name__}: {e}"[:200]}
    CACHE.quando = 0.0
    return {"ok": True, "id": cid, "mensagem": f"canal {cid} criado. Sem turno, ele só roda pelo botão."}


def ficha(cid, acao, corpo):
    """Ler ou salvar a ficha de um canal criado pelo painel. Fica atrás do mesmo guarda dos POSTs."""
    try:
        if acao == "ler":
            return {"ok": True, "ficha": novo_canal.ler(cid)}
        if acao == "salvar":
            novo_canal.salvar(cid, json.loads(corpo or b"{}"))
            CACHE.quando = 0.0
            return {"ok": True, "mensagem": f"ficha do canal {cid} salva. O Tito relê na próxima volta."}
    except ValueError as e:  # inclui JSON inválido
        return {"ok": False, "mensagem": str(e)[:300]}
    return {"ok": False, "mensagem": "ação desconhecida"}


class Pagina(BaseHTTPRequestHandler):
    def envia(self, corpo, tipo):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        rota = self.path.split("?")[0]
        if rota in ("/", "/index.html"):
            self.envia((AQUI / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif rota == "/status.json":
            self.envia(json.dumps(CACHE.get(), ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        local = {f"127.0.0.1:{PORTA}", f"localhost:{PORTA}"}
        origem = self.headers.get("Origin")
        acao = self.headers.get("X-Fabrica")
        if (self.headers.get("Host") not in local or acao not in ("rodar", "canal")
                or (origem and origem.split("://", 1)[-1] not in local)):
            self.send_error(403)
            return
        rota, _, qs = self.path.partition("?")
        if rota == "/rodar" and acao == "rodar":
            r = rodar(qs.removeprefix("canal="))
        elif rota == "/canais" and acao == "canal":
            n = int(self.headers.get("Content-Length") or 0)
            if n > 64_000:
                self.send_error(413)
                return
            r = criar_canal(self.rfile.read(n))
        elif rota == "/ficha" and acao == "canal":
            q = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
            n = int(self.headers.get("Content-Length") or 0)
            if n > 64_000:
                self.send_error(413)
                return
            r = ficha(q.get("canal", ""), q.get("acao", ""), self.rfile.read(n))
        else:
            self.send_error(404)
            return
        self.envia(json.dumps(r, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def log_message(self, *a):
        pass


def main():
    # 0.0.0.0 dentro do container; o compose só publica em 127.0.0.1 no Windows
    # PAINEL_HOST=127.0.0.1 para rodar fora do Docker sem abrir a porta na rede
    srv = ThreadingHTTPServer((os.environ.get("PAINEL_HOST", "0.0.0.0"), int(os.environ.get("PAINEL_PORTA_INTERNA", "8787"))), Pagina)
    print(f"Fábrica de reels em http://127.0.0.1:{PORTA}/", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
