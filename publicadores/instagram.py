"""Publicador do Instagram Reels pela instagrapi (API NÃO oficial). Passo a passo no README ("Conectar as contas").

Leia antes de ligar:
- A instagrapi entra como o app do celular, com usuário e senha. Isso fere os termos do Instagram e pode levar
  a bloqueio ou banimento da conta. A alternativa oficial é a Graph API da Meta (conta profissional + app).
- Login repetido é o que mais dispara bloqueio: o kit loga UMA vez e reaproveita a sessão salva.
- A sessão fica presa ao IP. Se o canal usa proxy, troque o proxy só junto com um login novo.
- Instalação: INSTALAR_INSTAGRAM=1 no .env e docker compose build.

Um login por canal. O comando pergunta usuário, senha e proxy (opcional) na hora; a senha não é gravada.
Ficam em /dados/segredos/<canal>/instagram/: sessao.json (a sessão) e proxy (se informado), só para o dono.
  docker compose run --rm -e CANAL=<canal> --entrypoint python worker -m publicadores.instagram login
  docker compose run --rm -e CANAL=<canal> --entrypoint python worker -m publicadores.instagram verificar
"""
import getpass
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DADOS = Path(os.environ.get("KIT_DADOS", "/dados"))


def _canal():
    from pipeline.config import CANAL
    return CANAL


def _pasta():
    return DADOS / "segredos" / _canal() / "instagram"


def _sessao():
    return _pasta() / "sessao.json"


def _proxy():
    try:
        return (_pasta() / "proxy").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _client():
    from instagrapi import Client
    cl = Client()
    if _sessao().exists():
        cl.load_settings(_sessao())  # mesma identidade de aparelho em toda rodada
    else:
        cl.set_country("BR")
        cl.set_country_code(55)
        cl.set_locale("pt_BR")
        cl.set_timezone_offset(int(float(os.environ.get("FUSO_HORAS", "-3")) * 3600))
    if _proxy():
        cl.set_proxy(_proxy())
    cl.delay_range = [1, 3]
    return cl


def _salva(cl):
    _pasta().mkdir(parents=True, exist_ok=True)
    tmp = _sessao().with_suffix(".tmp")
    cl.dump_settings(tmp)
    os.chmod(tmp, 0o600)
    os.replace(tmp, _sessao())


def _classifica(e):
    from instagrapi.exceptions import (BadPassword, ChallengeError, ClientThrottledError, FeedbackRequired,
                                       LoginRequired, PleaseWaitFewMinutes, RateLimitError, SentryBlock)
    nome = type(e).__name__
    if isinstance(e, ChallengeError):
        return f"challenge: {nome}"
    if isinstance(e, (LoginRequired, BadPassword)):
        return f"login_required: {nome}"
    if isinstance(e, (FeedbackRequired, PleaseWaitFewMinutes, ClientThrottledError, RateLimitError, SentryBlock)):
        return f"blocked: {nome}: {str(e)[:160]}"
    return f"{nome}: {str(e)[:200]}"


def publicar(mp4, meta, dry):
    caption = meta.get("caption") or ""
    if not os.path.exists(mp4) or not caption or len(caption) > 2200:
        return {"ok": False, "error": "entrada inválida: mp4 ausente ou caption vazia/longa"}
    if not _sessao().exists():
        return {"ok": False, "error": f"login_required: rode 'publicadores.instagram login' com CANAL={_canal()}"}
    if dry:
        return {"ok": True, "dryRun": True}
    try:
        cl = _client()
        cl.account_info()
    except Exception as e:
        return {"ok": False, "error": _classifica(e)}
    with tempfile.TemporaryDirectory() as tmp:
        capa = Path(tmp) / "capa.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", mp4, "-frames:v", "1", "-q:v", "3", str(capa)],
                       check=True)
        try:
            media = cl.clip_upload(Path(mp4), caption, thumbnail=capa)
        except Exception as e:
            return {"ok": False, "error": _classifica(e)}
        finally:
            _salva(cl)  # a sessão pode ter sido renovada nas chamadas
    return {"ok": True, "url": f"https://www.instagram.com/reel/{media.code}/"}


def login():
    from instagrapi.exceptions import TwoFactorRequired
    print(f"Login do Instagram do canal '{_canal()}'. Faça UMA vez; repetir login é o que mais leva bloqueio.")
    user = input("Usuário do Instagram: ").strip().lstrip("@")
    senha = getpass.getpass("Senha (não aparece e não é gravada): ")
    proxy = input("Proxy (socks5://usuario:senha@host:porta), Enter para nenhum: ").strip()
    if not user or not senha:
        sys.exit("usuário e senha são obrigatórios")
    _pasta().mkdir(parents=True, exist_ok=True)
    if proxy:
        (_pasta() / "proxy").write_text(proxy, encoding="utf-8")
        os.chmod(_pasta() / "proxy", 0o600)
    cl = _client()
    cl.challenge_code_handler = lambda username, choice: input(f"Código enviado por {choice}: ").strip()
    try:
        cl.login(user, senha)
    except TwoFactorRequired:
        cl.login(user, senha, verification_code=input("Código de dois fatores: ").strip())
    cl.account_info()  # só salva sessão que funciona de verdade
    _salva(cl)
    print(f"ok: sessão do canal '{_canal()}' salva em {_sessao()}")


def verificar():
    """Confere se a sessão do canal ainda vale, sem postar nada."""
    if not _sessao().exists():
        sys.exit(f"canal '{_canal()}' sem login no Instagram: rode 'login'")
    try:
        nome = _client().account_info().username
    except Exception as e:
        sys.exit(f"sessão do canal '{_canal()}' não vale: {_classifica(e)}")
    print(f"canal '{_canal()}' posta no Instagram como @{nome}")


if __name__ == "__main__":
    acoes = {"login": login, "verificar": verificar}
    if len(sys.argv) != 2 or sys.argv[1] not in acoes:
        sys.exit("uso: python -m publicadores.instagram login|verificar  (com CANAL=<canal> no ambiente)")
    acoes[sys.argv[1]]()
