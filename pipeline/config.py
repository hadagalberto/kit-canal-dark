"""Configuração, caminhos e utilidades comuns do pipeline.

Duas fontes, sem misturar:
- .env (ambiente do docker compose): o que vale para a máquina inteira. Chaves de API, provedor do LLM,
  MOTOR, a trava geral DRY_RUN, limites de máquina.
- Ficha do canal (/dados/canais/<id>.json, criada pelo painel; ou a ficha-modelo canais/exemplo.json):
  tudo que é de um canal. Marca, assunto, feeds, fontes, voz, estilos, redes, turno e "publicar".
Nenhum caminho fixo de máquina: dentro do container os dados ficam em /dados (volume) e os vídeos
prontos em /saida (pasta do Windows).
"""
import datetime
import json
import os
import subprocess
import time
from pathlib import Path

APP = Path(os.environ.get("KIT_APP", "/app"))
VIDEO = APP / "video"  # projeto Remotion
DADOS = Path(os.environ.get("KIT_DADOS", "/dados"))
SAIDA = Path(os.environ.get("KIT_SAIDA", "/saida"))

CANAIS_CRIADOS = DADOS / "canais"  # fichas dos canais em operação (criadas pelo painel, no volume)
MODELOS = APP / "canais"  # fichas-modelo que vêm no kit (só "exemplo"); servem de base para as novas


def lista_canais():
    """Canais em operação: as fichas em /dados/canais. Sem nenhuma ainda, o canal "exemplo" (modelo do kit)."""
    nomes = sorted(p.stem for p in CANAIS_CRIADOS.glob("*.json"))
    return nomes or ["exemplo"]


# Canal desta execução: o Tito passa CANAL=<id> para cada rodada; à mão, docker compose run -e CANAL=<id>.
# Sem CANAL, o primeiro canal em operação.
CANAL = os.environ.get("CANAL", "").strip() or lista_canais()[0]
MOTOR = os.environ.get("MOTOR", "exemplo").strip() or "exemplo"  # exemplo | api
DRY_RUN = os.environ.get("DRY_RUN", "1").strip() != "0"  # trava geral: 1 = nenhum canal publica
FUSO = datetime.timezone(datetime.timedelta(hours=float(os.environ.get("FUSO_HORAS", "-3"))))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# Cada canal tem a própria pasta dentro de /dados: vários canais dividem o mesmo volume.
DATA = DADOS / CANAL
DB = DATA / "published.json"
CONFIG = DATA / "pipeline.json"
COSTS = DATA / "costs.jsonl"
RODADAS = DATA / "rodadas.jsonl"
LOCK = DADOS / ".rodada.lock"  # um render por vez no PC, qualquer canal
ESTADO = DADOS / "estado.json"
SEGREDOS = DADOS / "segredos"  # tokens de login das redes (nunca no git)

T0 = time.time()

DEFAULT_CONFIG = {
    # Teto de posts por dia em cada rede. A rampa vale para as redes em ramp.nets: começa baixo e sobe com os
    # dias, porque conta nova postando muito no primeiro dia é o que mais leva bloqueio.
    "ig_max_per_day": 3,
    "yt_max_per_day": 6,
    "tt_max_per_day": 6,
    "ramp": {"start": "", "nets": ["instagram"], "cooldown_days": 7, "steps": [[0, 2], [14, 3], [21, 4], [28, 6]]},
    "pause_log": [],
    "media_enabled": False,  # logo e foto no vídeo (pede LOGODEV_TOKEN / OPENROUTER_API_KEY)
    "llm_usd_dia": 5,  # teto de gasto com a API de LLM por dia; passou, as rodadas do dia pulam
    "ai_images_per_day": 10,
    "ai_images": {},
    "ig_paused": False, "ig_paused_reason": "",
    "yt_paused": False, "yt_paused_reason": "",
    "tt_paused": False, "tt_paused_reason": "",
    "rejects": {},
}


ROBO = {"atual": ""}  # apelido do robô da estação em andamento (estado.etapa troca)


def log(*a):
    quem = f"[{ROBO['atual']}]" if ROBO["atual"] else ""
    print(f"[{time.time() - T0:6.0f}s]", *([quem] if quem else []), *a, flush=True)


def now():
    return datetime.datetime.now(FUSO)


def run(cmd, t, cwd=None, env=None):
    """(rc, stdout, stderr), sem levantar exceção."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t,
                           cwd=cwd, env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout {t}s"
    except Exception as e:
        return 1, "", str(e)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def arquivo_canal(nome):
    """A ficha criada pelo painel ganha da ficha-modelo de mesmo nome."""
    criado = CANAIS_CRIADOS / f"{nome}.json"
    return criado if criado.exists() else MODELOS / f"{nome}.json"


def caminhos(nome):
    """Arquivos de dados de um canal (cada canal tem a própria pasta em /dados)."""
    d = DADOS / nome
    return {"data": d, "db": d / "published.json", "config": d / "pipeline.json", "costs": d / "costs.jsonl",
            "rodadas": d / "rodadas.jsonl", "stats": d / "stats.jsonl"}


def agenda_de(nome, perfil=None):
    """Turno do canal: campo "agenda" da ficha (cron). Vazio = só pelo botão."""
    perfil = perfil if perfil is not None else load_json(arquivo_canal(nome), {})
    return str(perfil.get("agenda") or "").strip()


def gatilho(nome):
    """Arquivo que o botão "Rodar agora" cria para um canal."""
    return DADOS / f"rodar-agora.{nome}"


def canal(nome=None):
    """Ficha do canal. Falha alto se não existir."""
    nome = nome or CANAL
    p = arquivo_canal(nome)
    if not p.exists():
        raise SystemExit(f"canal '{nome}' não existe: crie pelo painel (+ Novo canal)")
    perfil = json.loads(p.read_text(encoding="utf-8"))
    # sem voz própria na ficha, a voz padrão do .env
    perfil["voice_id"] = perfil.get("voice_id") or os.environ.get("ELEVENLABS_VOICE_ID", "")
    return perfil


def publica(perfil):
    """O canal só publica com as duas chaves abertas: DRY_RUN=0 no .env e "publicar": true na ficha."""
    return not DRY_RUN and perfil.get("publicar") is True


def pipeline_cfg():
    cfg = {**DEFAULT_CONFIG, **load_json(CONFIG, {})}
    if not cfg["ramp"].get("start"):
        cfg["ramp"]["start"] = now().strftime("%Y-%m-%d")  # a rampa começa no primeiro dia do canal
    save_json(CONFIG, cfg)
    return cfg
