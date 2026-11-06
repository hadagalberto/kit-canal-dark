"""Uma rodada do canal: pauta -> apuração -> checagem -> mídia -> narração -> render -> publicação.

Uso (dentro do container):
  python -m pipeline.rodada                 rodada completa, com o MOTOR do .env
  python -m pipeline.rodada --exemplo       sem chave nenhuma: notícia e voz de exemplo, gera o MP4
  python -m pipeline.rodada --until pauta   para depois da etapa (pauta|apuracao|checagem|render)
  python -m pipeline.rodada --tema "..."    pauta pedida no lugar dos feeds (motor api)
  python -m pipeline.rodada --estilo vidro  força o estilo do vídeo

Sem aprovação humana: só publica se passar em todas as travas.
  (a) checagem: cada beat tem um trecho LITERAL da fonte, conferido por código na página baixada
  (b) toda fonte está na lista de domínios do canal
  (c) o MP4 passa no ffprobe (1080x1920, 30 fps, h264+aac) e a duração fica entre 15 e 45 s
  (d) a notícia não está no banco de publicados/descartados
Falhou qualquer uma: descarta, registra e segue. Nunca publica "meio certo".
Publicar de verdade exige as duas chaves: DRY_RUN=0 no .env (trava geral) e "publicar": true na ficha do
canal, que também diz em quais redes ("redes").
"""
import argparse
import fcntl
import json
import os
import re
import sys
import traceback

from . import apuracao as ap
from . import checagem as ck
from . import estado, llm, midia, publicar as pub, video
from . import avisos
from .banco import db_load, registra
from .config import (APP, COSTS, DATA, LOCK, MOTOR, T0, append_jsonl, caminhos, canal, lista_canais, load_json,
                     log, now, pipeline_cfg, publica, save_json)
from .pauta import pauta

ETAPAS_ATE = ["pauta", "apuracao", "checagem", "render", "publicar"]
EXEMPLO_ID = "2026-10-09-gemini-colega"


class Fim(Exception):
    """Fim antecipado e esperado da rodada (pulou, descartou, teto...)."""

    def __init__(self, resultado, motivo=""):
        super().__init__(motivo)
        self.resultado, self.motivo = resultado, motivo


def descarta(db, news, etapa, erros, identidade=None):
    registra(db, news, f"descartada:{etapa}", **(identidade or {}))
    nid = news.get("id", "?") if isinstance(news, dict) else "?"
    avisos.descarte(((identidade or {}).get("titles") or [nid])[0], etapa, erros)
    log("descarte na trava de", etapa + ":", erros)
    raise Fim("descartado", f"{etapa}: {'; '.join(erros)[:250]}")


def rodada_exemplo(perfil, estilo, dry):
    """Modo sem chave: usa exemplos/ e passa só pelas etapas que não pedem API (narração copiada, render real)."""
    base = load_json(APP / "exemplos" / "noticias" / f"{EXEMPLO_ID}.json", None)
    meta = load_json(APP / "exemplos" / "meta-exemplo.json", {})
    for e in ("pauta", "apuracao", "checagem", "midia"):
        estado.etapa(e)
        log(f"{e}: pulada no modo exemplo")
    nid = f"exemplo-{now():%Y%m%d-%H%M%S}"
    news = {**base, "id": nid, "brand": perfil["brand"]}
    news["style"] = estilo or os.environ.get("ESTILO_EXEMPLO") or base["style"]
    if news["style"] not in os.listdir(video.VIDEO / "src" / "styles"):
        raise Fim("erro", f"estilo desconhecido: {news['style']}")
    estado.etapa("narracao", noticia=nid, titulo=meta.get("title"))
    video.liga_dados()
    save_json(DATA / "news" / f"{nid}.json", news)
    video.voz_exemplo(nid, APP / "exemplos" / "voz" / EXEMPLO_ID)
    estado.etapa("render")
    mp4, seg, erros = video.render(news["style"], nid)
    if erros:
        raise Fim("erro", "; ".join(erros))
    save_json(mp4.with_suffix(".json"), meta)  # legenda e título ao lado do MP4, para conferir
    log(f"render ok: {mp4} ({seg:.1f} s, estilo {news['style']})")
    estado.etapa("publicacao")
    log("modo exemplo: nada é publicado (a notícia de exemplo é antiga e de teste)")
    return {"resultado": "dry-run", "mp4": str(mp4), "segundos": round(seg, 1)}


def rodada(until, dry, tema, estilo):
    perfil = canal()
    db = db_load()
    cfg = pipeline_cfg()
    custo = {"llm_usd": 0.0, "eleven_creditos": None}

    # Confere chaves e voz antes de gastar: sem isso, a rodada pagaria o LLM e quebraria só na narração.
    faltando = []
    try:
        llm.chave()
    except RuntimeError as e:
        faltando.append(str(e))
    if not os.environ.get("ELEVENLABS_API_KEY", "").strip():
        faltando.append("falta ELEVENLABS_API_KEY no .env")
    if not perfil.get("voice_id"):
        faltando.append("o canal não tem voz: ponha voice_id na ficha ou ELEVENLABS_VOICE_ID no .env")
    if faltando:
        avisos.erro("", "configuração incompleta: " + "; ".join(faltando))
        raise Fim("erro", "configuração incompleta: " + "; ".join(faltando))

    nets = pub.redes_livres(cfg, db, perfil)
    if not dry and not nets:
        raise Fim("teto", "nenhuma rede livre (\"redes\" vazio na ficha, rede pausada ou no teto do dia)")
    hoje = now().strftime("%Y-%m-%d")
    gasto = sum(float(x.get("llm_usd") or 0) for x in _linhas(COSTS) if x.get("at", "").startswith(hoje))
    if gasto >= cfg.get("llm_usd_dia", 5):
        avisos.teto(f"Este canal já gastou US$ {gasto:.2f} de LLM hoje (teto US$ {cfg.get('llm_usd_dia', 5)}).")
        raise Fim("teto", f"teto diário de LLM do canal atingido: US$ {gasto:.2f}")
    teto_total = os.environ.get("LLM_USD_DIA_TOTAL", "").strip()
    if teto_total:  # a chave de API é uma só: um teto para a soma de todos os canais
        total = sum(float(x.get("llm_usd") or 0) for n in lista_canais()
                    for x in _linhas(caminhos(n)["costs"]) if x.get("at", "").startswith(hoje))
        if total >= float(teto_total):
            avisos.teto(f"Os canais somados já gastaram US$ {total:.2f} de LLM hoje (teto US$ {teto_total}).")
            raise Fim("teto", f"teto diário de LLM da máquina atingido: US$ {total:.2f}")

    # 1. pauta
    estado.etapa("pauta")
    cands = [] if tema else pauta(db, perfil)
    log(f"pauta: {len(cands)} candidatos" if not tema else f"pauta pedida: {tema}")
    if not cands and not tema:
        raise Fim("pulou", "pauta vazia")
    if until == "pauta":
        print(json.dumps(cands[:15], ensure_ascii=False, indent=1))
        raise Fim("pulou", "parou na pauta (--until)")

    # 2. apuração + validação + travas de fonte
    estado.etapa("apuracao")
    wd = DATA / "work" / now().strftime("%Y%m%d-%H%M%S")
    wd.mkdir(parents=True, exist_ok=True)
    save_json(wd / "candidatos.json", cands)
    try:
        ap.apuracao(wd, db, cfg, perfil, cands, tema=tema)
    finally:
        custo["llm_usd"] = llm.CUSTO["llm_usd"]
    if (wd / "skip.txt").exists():
        raise Fim("pulou", "apuração pulou: " + (wd / "skip.txt").read_text(encoding="utf-8")[:200])
    news, meta = load_json(wd / "news.json", None), load_json(wd / "meta.json", None)
    if not isinstance(news, dict):
        raise RuntimeError(f"apuração não gerou news.json ({wd})")
    if estilo:
        news["style"] = estilo
    erros = ap.validate(news, meta, perfil["estilos"])
    if erros:
        log("validação falhou, pedindo correção:", erros)
        r = llm.corrigir((video.VIDEO / "src" / "news" / "types.ts").read_text(encoding="utf-8"), news, meta, erros)
        if isinstance(r, dict) and isinstance(r.get("news"), dict):
            for b in r["news"].get("beats") or []:
                if isinstance(b, dict):
                    b.pop("media", None)
            news, meta = r["news"], r.get("meta") if isinstance(r.get("meta"), dict) else meta
            save_json(wd / "news.json", news)
            save_json(wd / "meta.json", meta)
        erros = ap.validate(news, meta, perfil["estilos"])
    esc = load_json(wd / "escolha.json", {})
    hero = (news.get("beats") or [{}])[0]
    ident = {"titles": [t for t in (esc.get("manchete", ""), (meta or {}).get("title", ""),
                                    f"{hero.get('title', '')} {hero.get('highlight', '')}".strip()) if t],
             "urls": [u for u in [esc.get("link", "")] if u]}
    estado.etapa("apuracao", noticia=news.get("id"), titulo=(meta or {}).get("title"))
    if erros:
        descarta(db, news, "formato", erros, ident)
    nid = news["id"]
    if (DATA / "news" / f"{nid}.json").exists() or any(it.get("id") == nid for it in db["items"]):
        nid = news["id"] = f"{nid}-{now():%H%M}"
    v = news.setdefault("voice", {})
    v["tempo"] = min(max(float(v.get("tempo", 1.12)), 1.0), 1.15)
    erros = ap.travas_fonte(news, db, perfil, ident) + ap.data_do_feed(news, wd, tema)
    if erros:
        descarta(db, news, "fonte", erros, ident)
    if until == "apuracao":
        raise Fim("pulou", f"parou na apuração: {wd}/news.json")

    # 3. checagem (com uma revisão se o erro for corrigível)
    estado.etapa("checagem")
    erros, textos = ck.checagem(wd, news)
    if erros and textos and not any("nao consegui abrir" in e for e in erros):
        log("revisão: reescrevendo as cenas reprovadas")
        r = llm.revisar(news, meta, textos, erros)
        if isinstance(r, dict) and isinstance(r.get("news"), dict):
            novo, novo_meta = r["news"], r.get("meta") if isinstance(r.get("meta"), dict) else meta
            for b in novo.get("beats") or []:
                if isinstance(b, dict):
                    b.pop("media", None)
            novo["id"], novo["voice"] = news["id"], news.get("voice")
            if not ap.validate(novo, novo_meta, perfil["estilos"]):
                news, meta = novo, novo_meta
                erros, _ = ck.checagem(wd, news)
                log("revisão:", "aprovada" if not erros else f"ainda reprovada: {erros[:3]}")
    custo["llm_usd"] = llm.CUSTO["llm_usd"]
    if erros:
        descarta(db, news, "checagem", erros, ident)
    if until == "checagem":
        raise Fim("pulou", f"parou na checagem: {nid} aprovada")

    # 4. mídia (nunca derruba a rodada)
    estado.etapa("midia")
    video.liga_dados()
    try:
        midia.resolve(news, meta, load_json(wd / "midia.json", {}), cfg, perfil)
    except Exception as e:
        log("mídia falhou:", type(e).__name__, str(e)[:200])
        for b in news["beats"]:
            b.pop("media", None)

    # 5. narração (gasta crédito de voz: só depois da checagem)
    estado.etapa("narracao")
    cta = perfil.get("cta", "")
    fim = news["beats"][-1]["voice"]
    if cta and cta.split("]")[-1].strip().lower() not in fim["text"].lower():
        fim["text"] = f"{fim['text'].rstrip()} {cta}"
    news["brand"] = perfil["brand"]
    save_json(DATA / "news" / f"{nid}.json", news)
    save_json(wd / "meta.json", meta)
    custo["eleven_creditos"] = video.narracao(nid, perfil.get("voice_id"))

    # 6. render (trava c)
    estado.etapa("render")
    mp4, seg, erros = video.render(news["style"], nid)
    if erros:
        descarta(db, news, "render", erros, ident)
    save_json(mp4.with_suffix(".json"), meta)
    log(f"render ok: {mp4} ({seg:.1f} s)")
    if until == "render":
        raise Fim("dry-run", f"parou no render: {mp4}")

    # 7. publicação
    estado.etapa("publicacao")
    if dry or not nets:
        log("ensaio: nada publicado; MP4 em", mp4)
        avisos.ensaio(meta.get("title", nid), mp4)
        # sem registro no banco: a mesma notícia pode sair de verdade quando DRY_RUN=0
        return {"resultado": "dry-run", "mp4": str(mp4), "segundos": round(seg, 1), **custo}
    res = pub.publicar(mp4, meta, nets, dry=False)
    links, erros_rede, pausadas = pub.trata_erros(res, cfg)
    registra(db, news, "publicada" if links else "descartada:publicacao", links=links, errors=erros_rede, **ident)
    avisos.publicado(meta.get("title", nid), links, erros_rede, {n: erros_rede.get(n, "") for n in pausadas},
                     news["style"], seg, news["sources"][0].get("label", "") if news.get("sources") else "")
    if os.environ.get("APAGAR_MP4_PUBLICADO", "0") == "1" and links:
        os.remove(mp4)
    return {"resultado": "publicado" if links else "descartado", "mp4": str(mp4), "links": links, **custo}


def _linhas(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(ln) for ln in f if ln.strip()]
    except (OSError, ValueError):
        return []


def main():
    a = argparse.ArgumentParser(description="Uma rodada do canal dark")
    a.add_argument("--exemplo", action="store_true", help="sem chave: notícia e voz de exemplo")
    a.add_argument("--until", choices=ETAPAS_ATE, default="publicar")
    a.add_argument("--dry-run", action="store_true", help="ensaio: não publica, mesmo com a ficha liberada")
    a.add_argument("--tema", help="pauta pedida no lugar dos feeds")
    a.add_argument("--estilo", help="força um estilo (pasta de video/src/styles)")
    args = a.parse_args()
    motor = "exemplo" if args.exemplo or MOTOR == "exemplo" else "api"
    try:
        dry = args.dry_run or motor == "exemplo" or not publica(canal())
    except SystemExit as e:
        log(str(e))
        return 1

    LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("outra rodada em andamento, saindo")
        return 0
    modo = "ENSAIO (não publica: DRY_RUN=1 no .env ou publicar=false na ficha)" if dry else "PUBLICA DE VERDADE"
    log(f"rodada: canal {DATA.name}, motor {motor}, {modo}")
    estado.inicio(motor, dry)
    custo = {"at": now().isoformat(timespec="seconds"), "motor": motor}
    try:
        if motor == "exemplo":
            r = rodada_exemplo(canal(), args.estilo, dry)
        else:
            r = rodada(args.until, dry, args.tema, args.estilo)
        estado.fim(r["resultado"], mp4=r.get("mp4"), links=r.get("links"))
        custo.update(r)
        log("fim:", r["resultado"], r.get("mp4", ""))
        return 0
    except Fim as f:
        estado.fim(f.resultado, f.motivo)
        custo.update({"resultado": f.resultado, "motivo": f.motivo[:200]})
        log(f"fim: {f.resultado} — {f.motivo}")
        return 0
    except Exception as e:
        log(traceback.format_exc())
        estado.fim("erro", f"{type(e).__name__}: {str(e)[:250]}")
        custo.update({"resultado": "erro", "motivo": str(e)[:200]})
        avisos.erro(estado.ler().get("etapa", ""), f"{type(e).__name__}: {e}")
        return 1
    finally:
        custo.update({"llm_usd": llm.CUSTO["llm_usd"], "ia_usd": midia.CUSTO["ia_usd"],
                      "total_s": round(__import__("time").time() - T0, 1)})
        append_jsonl(COSTS, custo)


if __name__ == "__main__":
    sys.exit(main())
