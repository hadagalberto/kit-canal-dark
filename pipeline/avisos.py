"""Avisos no Telegram, num formato só para todos os eventos.

Cada mensagem tem o mesmo esqueleto:

    <ícone> <Nome do canal> · <evento>
    <título da notícia ou motivo>
    <detalhes, uma linha cada>

  🎬 publicado         links de cada rede, estilo, duração, fonte
  🧪 ensaio pronto     caminho do MP4 (só com TELEGRAM_AVISAR_ENSAIO=1)
  🗑️ descarte          a trava e o robô que barrou, com os motivos
  ⏸️ rede pausada      o motivo e como religar
  💸 teto do dia       gasto de LLM do dia (um aviso por dia)
  🚨 erro              a estação onde quebrou e onde olhar o log

Bot: TELEGRAM_BOT_TOKEN no .env (um só para a máquina). Chat: TELEGRAM_CHAT_ID no .env, ou "telegram_chat_id" na
ficha do canal, para mandar cada canal a um grupo diferente. Sem token ou chat, os avisos ficam só no log.
O token nunca vai para o log.
"""
import json
import os
import urllib.request

from .config import CANAL, DATA, canal, log, now
from .robos import POR_ESTACAO

REDE_NOME = {"youtube": "YouTube", "instagram": "Instagram", "tiktok": "TikTok"}
PREFIXO = {"instagram": "ig", "youtube": "yt", "tiktok": "tt"}  # chaves <x>_paused no pipeline.json


def _perfil():
    try:
        return canal()
    except (Exception, SystemExit):
        return {"brand": {"name": CANAL}}


def _envia(icone, evento, linhas):
    perfil = _perfil()
    texto = "\n".join([f"{icone} {perfil['brand']['name']} · {evento}"] + [ln for ln in linhas if ln])[:4000]
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = str(perfil.get("telegram_chat_id") or os.environ.get("TELEGRAM_CHAT_ID", "")).strip()
    if not token or not chat:
        return
    body = json.dumps({"chat_id": chat, "text": texto, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:
        log("telegram falhou:", type(e).__name__)  # nunca imprime o token


def _robo(estacao):
    r = POR_ESTACAO.get(estacao)
    return f"{r['apelido']}, {r['funcao']}" if r else estacao


def publicado(titulo, links, erros, pausadas, estilo, segundos, fonte):
    linhas = [titulo]
    linhas += [f"{REDE_NOME.get(n, n)}: {u}" for n, u in links.items()]
    linhas += [f"⚠️ {REDE_NOME.get(n, n)} falhou: {e[:200]}" for n, e in erros.items()]
    linhas.append(f"Estilo {estilo} · {segundos:.0f} s · Fonte: {fonte}")
    _envia("🎬", "publicado" if links else "não publicado", linhas)
    for net, motivo in pausadas.items():
        pausa(net, motivo)


def ensaio(titulo, mp4):
    if os.environ.get("TELEGRAM_AVISAR_ENSAIO", "0") == "1":
        _envia("🧪", "ensaio pronto (nada publicado)", [titulo, f"MP4: {mp4}"])


# trava -> estação que a aplica
TRAVA_ESTACAO = {"formato": "apuracao", "fonte": "apuracao", "checagem": "checagem", "render": "render",
                 "publicacao": "publicacao"}


def descarte(titulo, trava, motivos):
    est = TRAVA_ESTACAO.get(trava, trava)
    _envia("🗑️", f"descarte na trava de {trava} ({_robo(est)})",
           [titulo] + [f"• {m[:180]}" for m in motivos[:8]] + [f"Rascunho: /dados/{CANAL}/work/"])


def pausa(net, motivo):
    _envia("⏸️", f"{REDE_NOME.get(net, net)} pausado",
           [motivo[:200], f"Para religar: refaça o login da rede (README, Conectar as contas) e ponha "
                          f"\"{PREFIXO.get(net, net)}_paused\": false em /dados/{CANAL}/pipeline.json"])


def teto(motivo):
    """Um aviso por dia por canal."""
    marca = DATA / f".aviso-teto-{now():%Y%m%d}"
    if marca.exists():
        return
    marca.parent.mkdir(parents=True, exist_ok=True)
    marca.touch()
    _envia("💸", "teto de gasto do dia", [motivo, "As rodadas do canal voltam amanhã. O teto fica em llm_usd_dia "
                                                   f"(/dados/{CANAL}/pipeline.json) e LLM_USD_DIA_TOTAL (.env)."])


def erro(estacao, mensagem):
    _envia("🚨", f"erro na rodada ({_robo(estacao)})" if estacao in POR_ESTACAO else "erro na rodada",
           [mensagem[:300], "Log: docker compose logs --tail 100 agendador"])
