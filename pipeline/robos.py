"""Os robôs da Fábrica: um por estação da rodada, mais o Tito, que cuida do turno.

Fonte única dos nomes (glossário em docs/GLOSSARIO.md). O apelido começa com a mesma letra da função,
para decorar fácil: Bento Busca, Ester Escreve, Caco Confere, Íris acha as Imagens, Vavá grava a Voz,
Mila Monta, Paco Posta, Tito cuida do Turno. Os logs saem com o apelido na frente ([Caco] ...), então
quem lê o log sabe na hora qual estação falou.

A chave de cada estação (pauta, apuracao...) é a que fica gravada nos dados (estado.json, rodadas.jsonl):
não mude a chave, só o apelido e a função.
"""

ROBOS = [
    {"estacao": "pauta", "apelido": "Bento", "funcao": "busca as notícias", "arquivo": "pipeline/pauta.py"},
    {"estacao": "apuracao", "apelido": "Ester", "funcao": "escreve o roteiro", "arquivo": "pipeline/apuracao.py"},
    {"estacao": "checagem", "apelido": "Caco", "funcao": "confere os fatos", "arquivo": "pipeline/checagem.py"},
    {"estacao": "midia", "apelido": "Íris", "funcao": "acha as imagens", "arquivo": "pipeline/midia.py"},
    {"estacao": "narracao", "apelido": "Vavá", "funcao": "grava a voz", "arquivo": "pipeline/video.py"},
    {"estacao": "render", "apelido": "Mila", "funcao": "monta o vídeo", "arquivo": "video/ (Remotion)"},
    {"estacao": "publicacao", "apelido": "Paco", "funcao": "posta nas redes", "arquivo": "publicadores/"},
]

TITO = {"apelido": "Tito", "funcao": "cuida do turno", "arquivo": "agendador/agendador.py"}

ESTACOES = [r["estacao"] for r in ROBOS]
POR_ESTACAO = {r["estacao"]: r for r in ROBOS}


def apelido(estacao):
    return POR_ESTACAO[estacao]["apelido"] if estacao in POR_ESTACAO else ""
