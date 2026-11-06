"""Publicador do YouTube Shorts pela API oficial (YouTube Data API v3). Passo a passo no README ("Conectar as contas").

Um login por canal: cada canal da Fábrica posta na conta do YouTube dele.
- client_secret.json (o "app" do Google Cloud) é um só para a máquina: /dados/segredos/youtube/client_secret.json.
  Um projeto do Google Cloud autoriza quantos canais você quiser.
- O token de cada canal fica em /dados/segredos/<canal>/youtube/token.json (no volume, nunca no git).

Comandos (troque <canal> pelo id do canal):
  docker compose run --rm --service-ports -e CANAL=<canal> --entrypoint python worker -m publicadores.youtube autorizar
  docker compose run --rm -e CANAL=<canal> --entrypoint python worker -m publicadores.youtube verificar

Cota: upload tem limite diário próprio na API (confira no console do Google Cloud).
Todo vídeo sai marcado como conteúdo sintético (voz gerada por IA).
"""
import os
import sys
from pathlib import Path

DADOS = Path(os.environ.get("KIT_DADOS", "/dados"))
CLIENT = DADOS / "segredos" / "youtube" / "client_secret.json"
ESCOPOS = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


def _canal():
    from pipeline.config import CANAL
    return CANAL


def _token():
    return DADOS / "segredos" / _canal() / "youtube" / "token.json"


def _credenciais():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    token = _token()
    if not token.exists():
        return None
    cred = Credentials.from_authorized_user_file(str(token), ESCOPOS)
    if not cred.valid and cred.expired and cred.refresh_token:
        cred.refresh(Request())
        _salva(cred)
    return cred if cred.valid else None


def _salva(cred):
    token = _token()
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(cred.to_json(), encoding="utf-8")
    os.chmod(token, 0o600)


def publicar(mp4, meta, dry):
    titulo = (meta.get("title") or "").strip()[:95]
    if not titulo or not os.path.exists(mp4):
        return {"ok": False, "error": "entrada inválida: sem título ou sem MP4"}
    try:
        cred = _credenciais()
    except Exception as e:
        return {"ok": False, "error": f"login_required: token inválido ({type(e).__name__})"}
    if cred is None:
        return {"ok": False, "error": f"login_required: rode 'publicadores.youtube autorizar' com CANAL={_canal()}"}
    if dry:
        return {"ok": True, "dryRun": True}
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube", "v3", credentials=cred, cache_discovery=False)
    corpo = {
        "snippet": {"title": titulo, "description": (meta.get("description") or "")[:4900],
                    "tags": [t for t in meta.get("tags") or []][:15], "categoryId": "28",
                    "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"},
        "status": {"privacyStatus": os.environ.get("YOUTUBE_PRIVACIDADE", "public"), "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},
    }
    try:
        req = yt.videos().insert(part="snippet,status", body=corpo,
                                 media_body=MediaFileUpload(mp4, mimetype="video/mp4", resumable=True))
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
    except HttpError as e:
        motivo = str(e)[:200]
        if e.resp.status in (401, 403) and "quota" not in motivo.lower():
            return {"ok": False, "error": f"login_required: {motivo}"}
        return {"ok": False, "error": f"HttpError {e.resp.status}: {motivo}"}
    return {"ok": True, "url": f"https://youtube.com/shorts/{resp['id']}"}


def autorizar():
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not CLIENT.exists():
        sys.exit(f"falta {CLIENT}: crie o ID de cliente OAuth ('App para computador') no Google Cloud e copie o JSON "
                 "para lá (README, Conectar as contas)")
    print(f"Autorizando o canal '{_canal()}'. Entre com a conta Google DONA do canal do YouTube dele.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), ESCOPOS)
    # O navegador do Windows volta para localhost:8090, que o compose liga ao container (--service-ports).
    cred = flow.run_local_server(host="localhost", bind_addr="0.0.0.0", port=8090, open_browser=False,
                                 authorization_prompt_message="Abra este link no navegador do Windows:\n{url}\n")
    _salva(cred)
    print(f"ok: token do canal '{_canal()}' salvo em {_token()}")
    verificar()


def verificar():
    """Mostra em qual canal do YouTube o login caiu, sem postar nada."""
    cred = _credenciais()
    if cred is None:
        sys.exit(f"canal '{_canal()}' sem login no YouTube: rode 'autorizar'")
    from googleapiclient.discovery import build
    r = build("youtube", "v3", credentials=cred, cache_discovery=False).channels().list(part="snippet", mine=True).execute()
    nomes = [i["snippet"]["title"] for i in r.get("items") or []]
    print(f"canal '{_canal()}' posta no YouTube em: {', '.join(nomes) or '(conta sem canal do YouTube)'}")


if __name__ == "__main__":
    acoes = {"autorizar": autorizar, "verificar": verificar}
    if len(sys.argv) != 2 or sys.argv[1] not in acoes:
        sys.exit("uso: python -m publicadores.youtube autorizar|verificar  (com CANAL=<canal> no ambiente)")
    acoes[sys.argv[1]]()
