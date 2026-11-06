"""Tito, o agendador: cuida do turno de cada canal (faz o papel do cron, dentro do Docker).

Canais em operação: as fichas em /dados/canais/*.json (criadas pelo painel); sem nenhuma, o canal "exemplo".
A lista é relida a cada volta, então um canal criado no painel entra sem reiniciar nada.

Cada canal tem o próprio turno (expressão cron, ex.: "0 7-23 * * *" = de hora em hora das 7h às 23h):
campo "agenda" da ficha. Turno vazio =
nada automático: o canal só roda pelo botão do painel (/dados/rodar-agora.<canal>) ou por docker compose run.

Cada rodada é um subprocesso (CANAL=<canal> python -m pipeline.rodada): se ela quebrar, o agendador continua
vivo. Uma rodada por vez no PC inteiro (render pesa); o lock /dados/.rodada.lock garante isso.
"""
import datetime
import os
import subprocess
import sys
import time

from croniter import croniter

from pipeline import config as C

STATUS = C.DADOS / "agendador.json"
TETO_S = int(os.environ.get("RODADA_TETO_S", "3300"))  # mata rodada travada


def agora():
    return datetime.datetime.now(C.FUSO)


def proxima(agenda, depois):
    return croniter(agenda, depois).get_next(datetime.datetime) if agenda else None


def roda(nome, origem):
    print(f"[Tito] {agora():%d/%m %H:%M:%S} rodada do canal {nome} ({origem})", flush=True)
    try:
        r = subprocess.run([sys.executable, "-m", "pipeline.rodada"], env={**os.environ, "CANAL": nome}, timeout=TETO_S)
        print(f"[Tito] canal {nome}: rodada terminou rc={r.returncode}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"[Tito] canal {nome}: rodada passou de {TETO_S}s e foi encerrada", flush=True)


def main():
    C.DADOS.mkdir(parents=True, exist_ok=True)
    agendas, prox = {}, {}
    while True:
        # relê os canais: entra canal novo, muda agenda editada no perfil
        for nome in C.lista_canais():
            ag = C.agenda_de(nome)
            if ag and not croniter.is_valid(ag):
                if agendas.get(nome) != ag:
                    print(f"[Tito] canal {nome}: agenda inválida {ag!r}, ignorada", flush=True)
                agendas[nome], prox[nome] = ag, None
                continue
            if agendas.get(nome) != ag or nome not in prox:
                agendas[nome], prox[nome] = ag, proxima(ag, agora())
                print(f"[Tito] canal {nome}: agenda {ag or '(vazia: só pelo botão)'} · próxima: {prox[nome] or '-'}",
                      flush=True)
        rodando = None
        C.save_json(STATUS, {"vivo_em": agora().isoformat(timespec="seconds"), "pid": os.getpid(),
                             "canais": {n: {"agenda": agendas.get(n, ""), "proxima": p.isoformat(timespec="seconds") if p else None}
                                        for n, p in prox.items()}})
        for nome in list(prox):
            gat = C.gatilho(nome)
            if gat.exists():
                gat.unlink(missing_ok=True)
                rodando = (nome, "botão do painel")
                break
            if prox[nome] and agora() >= prox[nome]:
                prox[nome] = proxima(agendas[nome], agora())
                rodando = (nome, "agenda")
                break
        if rodando:
            roda(*rodando)
        else:
            time.sleep(5)


if __name__ == "__main__":
    main()
