"""Estado ao vivo da rodada, para o painel.

No sistema original o painel adivinhava a etapa por /proc/locks e pelos
arquivos da pasta de trabalho. Entre containers isso não funciona (o painel não
vê os processos do worker), então aqui a própria rodada escreve /dados/estado.json
a cada troca de etapa. O painel só lê.
"""
import os

from . import config
from .config import CANAL, ESTADO, RODADAS, append_jsonl, load_json, now, save_json
from .robos import ESTACOES, apelido

ETAPAS = ESTACOES  # pauta, apuracao, checagem, midia, narracao, render, publicacao (ver robos.py)

_atual = {}


def inicio(motor, dry):
    _atual.clear()
    _atual.update({"rodando": True, "canal": CANAL, "motor": motor, "dry_run": dry, "pid": os.getpid(),
                   "inicio": now().isoformat(timespec="seconds"), "etapa": "pauta", "etapa_desde": now().isoformat(timespec="seconds"),
                   "noticia": None, "titulo": None})
    save_json(ESTADO, _atual)


def etapa(nome, **extra):
    assert nome in ETAPAS, nome
    config.ROBO["atual"] = apelido(nome)
    _atual.update({"etapa": nome, "etapa_desde": now().isoformat(timespec="seconds"), **extra})
    save_json(ESTADO, _atual)


def fim(resultado, motivo="", **extra):
    """resultado: publicado | dry-run (ensaio) | descartado | pulou | teto | erro."""
    config.ROBO["atual"] = ""
    registro = {"canal": CANAL, "inicio": _atual.get("inicio"), "fim": now().isoformat(timespec="seconds"),
                "resultado": resultado, "motivo": motivo[:300], "etapa": _atual.get("etapa"),
                "noticia": _atual.get("noticia"), "titulo": _atual.get("titulo"), "motor": _atual.get("motor"), **extra}
    append_jsonl(RODADAS, registro)
    save_json(ESTADO, {"rodando": False, "canal": CANAL, "ultima": registro})


def ler():
    return load_json(ESTADO, {"rodando": False})
