"""Etapas 5 e 6: narração (ElevenLabs ou exemplo) e render Remotion.

Os scripts Node do projeto em video/ fazem o trabalho pesado:
- voice.mjs        uma fala por MP3, na ElevenLabs (só no motor api)
- render-style.mjs valida o pacote, mede a voz, gera trilha e efeitos, renderiza e confere no ffprobe
Dentro da imagem, video/news, video/public/filmes e video/out/filmes apontam para /dados/<canal>.
"""
import os
import re
import shutil

from .config import DATA, SAIDA, VIDEO, load_json, log, run


def liga_dados():
    """Os links da imagem apontam para /dados/{news,filmes,out}. Cada canal tem a própria pasta, então o link
    /dados/news -> /dados/<canal>/news é refeito a cada rodada (só uma rodada roda por vez: lock)."""
    for nome in ("news", "filmes", "out"):
        (DATA / nome).mkdir(parents=True, exist_ok=True)
        link = DATA.parent / nome
        if link.is_symlink() or link.exists():
            if link.is_symlink() and os.readlink(link) == str(DATA / nome):
                continue
            if link.is_dir() and not link.is_symlink():
                raise RuntimeError(f"{link} é pasta, esperava link: apague o volume ou mova a pasta")
            link.unlink()
        link.symlink_to(DATA / nome)


# Erros comuns da ElevenLabs -> o que fazer. A resposta crua continua no fim, para o log.
ERROS_ELEVENLABS = [
    ("quota_exceeded", "os créditos do plano da ElevenLabs acabaram (renove ou suba o plano)"),
    ("voice_not_found", "o voice_id da ficha (ou ELEVENLABS_VOICE_ID) não existe nesta conta"),
    ("invalid_api_key", "ELEVENLABS_API_KEY inválida"),
    ("missing_permissions", "a chave da ElevenLabs não tem a permissão Text to Speech"),
    ("401", "ELEVENLABS_API_KEY recusada (chave errada ou sem permissão Text to Speech)"),
    ("429", "muitos pedidos ao mesmo tempo na ElevenLabs; tente de novo em alguns minutos"),
    ("ELEVENLABS_VOICE_ID vazio", "o canal não tem voz: ponha voice_id na ficha ou ELEVENLABS_VOICE_ID no .env"),
    ("ELEVENLABS_API_KEY vazia", "falta ELEVENLABS_API_KEY no .env"),
]


def explica_elevenlabs(err):
    for chave, texto in ERROS_ELEVENLABS:
        if chave in err:
            return f"{texto} ({err.strip()[-160:]})"
    return err.strip()[-300:]


def narracao(nid, voice_id):
    env = {**os.environ, "ELEVENLABS_VOICE_ID": voice_id or ""}
    rc, out, err = run(["node", "scripts/voice.mjs", nid], t=300, cwd=VIDEO, env=env)
    log("voz:", out.strip().replace("\n", " | ")[-300:])
    if rc != 0:
        raise RuntimeError(f"voz falhou: {explica_elevenlabs(err)}")
    m = re.search(r"creditos (\d+)", out)
    return int(m.group(1)) if m else None


def voz_exemplo(nid, pasta_mp3):
    """Modo sem chave: copia as falas gravadas de exemplo."""
    dest = DATA / "filmes" / nid / "voice"
    dest.mkdir(parents=True, exist_ok=True)
    for mp3 in pasta_mp3.glob("*.mp3"):
        shutil.copy(mp3, dest / mp3.name)
    log(f"voz: exemplo, {len(list(dest.glob('*.mp3')))} falas copiadas")


def render(estilo, nid):
    """-> (mp4 em /saida ou None, segundos, erros)."""
    env = {**os.environ, "RENDER_CONCURRENCY": os.environ.get("RENDER_CONCURRENCY", "4")}
    rc, out, err = run(["node", "scripts/render-style.mjs", estilo, nid], t=1800, cwd=VIDEO, env=env)
    for ln in out.strip().splitlines()[-12:]:
        log("  render |", ln)
    mp4 = out.strip().splitlines()[-1] if out.strip() else ""
    story = load_json(DATA / "filmes" / nid / "story.json", {})
    total = (story.get("timing") or {}).get("total", 0)
    if rc != 0 or not mp4.endswith(".mp4") or not os.path.exists(mp4):
        return None, 0, [f"render falhou (rc={rc}): {(err or out).strip()[-400:]}"]
    if not 450 <= total <= 1350:
        os.remove(mp4)
        return None, 0, [f"duracao fora do limite: {total} frames ({total / 30:.1f} s)"]
    SAIDA.mkdir(parents=True, exist_ok=True)
    final = SAIDA / f"{nid}-{estilo}.mp4"
    shutil.move(mp4, final)
    return final, total / 30, []
