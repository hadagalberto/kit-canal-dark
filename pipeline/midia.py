"""Etapa 4: mídia (opcional). Logo da empresa (logo.dev) e uma foto: oficial ou gerada por IA.

Regra do sistema original: mídia é enfeite. Qualquer falha só tira a mídia, nunca descarta a notícia.
Liga com "media_enabled": true no pipeline.json do canal e as chaves LOGODEV_TOKEN / OPENROUTER_API_KEY no .env.
"""
import base64
import json
import os
import re
import urllib.request
from urllib.parse import urlparse

from .config import DATA, log, now, run, save_json, CONFIG
from .fontes import fetch_bytes, host_ok, words

TLDS = {"com", "br", "net", "org", "io", "ai", "co", "app", "dev", "tech", "www", "us", "uk", "de", "jp", "cn", "gov", "edu"}
CREDITO_LOGO = "Logos: logo.dev"
CUSTO = {"ia_imagens": 0, "ia_usd": 0.0}


def salva_jpg(raw, dest):
    """Qualquer imagem -> JPG de até 1080 px de largura (render sem GPU: pixel custa)."""
    tmp = str(dest) + ".in"
    with open(tmp, "wb") as f:
        f.write(raw)
    rc, _, _ = run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-vf", "scale='min(1080,iw)':-2", "-q:v", "3", str(dest)], t=60)
    os.remove(tmp)
    if rc != 0:
        return None
    rc, out, _ = run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(dest)], t=20)
    try:
        w, h = (int(x) for x in out.strip().split(",")[:2])
        return w, h
    except ValueError:
        return None


def logo(pedido, texto, nid, pasta):
    token = os.environ.get("LOGODEV_TOKEN", "").strip()
    if not token:
        return None, "sem LOGODEV_TOKEN no .env"
    dominio = str(pedido.get("dominio") or "") if isinstance(pedido, dict) else str(pedido)
    nome = str(pedido.get("nome") or "") if isinstance(pedido, dict) else ""
    dominio = re.sub(r"^https?://", "", dominio.strip().lower()).split("/")[0].removeprefix("www.")
    if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", dominio):
        return None, f"dominio invalido: {dominio!r}"
    rotulos = {r for r in dominio.split(".") if r not in TLDS and len(r) > 2}
    if not (rotulos | words(nome)) & words(texto):
        return None, f"marca {nome or dominio} nao aparece na noticia"
    arquivos = {}
    for tema, arq in (("light", "logo.png"), ("dark", "logo-dark.png")):
        url = f"https://img.logo.dev/{dominio}?token={token}&format=png&size=512&theme={tema}&fallback=404"
        try:
            raw, _ = fetch_bytes(url, t=30)
        except Exception as e:
            return None, f"logo.dev sem logo para {dominio} ({type(e).__name__})"
        if not raw.startswith(bytes((0x89, 0x50, 0x4E, 0x47))) or len(raw) < 500:
            return None, f"logo.dev devolveu algo que nao e PNG para {dominio}"
        (pasta / arq).write_bytes(raw)
        arquivos[tema] = f"filmes/{nid}/media/{arq}"
    nome = nome or dominio.split(".")[0].capitalize()
    return {"kind": "logo", "domain": dominio, "name": nome[:40], "src": arquivos["light"], "srcDark": arquivos["dark"]}, ""


def foto_oficial(url, dest, oficiais):
    if not host_ok(url, oficiais):
        return None, f"foto fora de dominio oficial: {urlparse(url).netloc}"
    try:
        raw, _ = fetch_bytes(url, t=30)
    except Exception as e:
        return None, f"foto oficial nao baixou ({str(e)[:50]})"
    magic = raw[:12]
    if not (magic.startswith(bytes((0xFF, 0xD8))) or magic.startswith(bytes((0x89, 0x50, 0x4E, 0x47)))
            or (magic[:4] == b"RIFF" and magic[8:12] == b"WEBP")):
        return None, "url da foto oficial nao e imagem"
    if len(raw) < 20_000:
        return None, "foto oficial pequena demais"
    wh = salva_jpg(raw, dest)
    return (wh, "") if wh else (None, "ffmpeg nao leu a foto oficial")


def foto_ia(prompt, dest, cfg):
    """Imagem ilustrativa pelo OpenRouter (modelo em IMAGEM_IA_MODELO). Respeita o teto diário."""
    hoje = now().strftime("%Y-%m-%d")
    usadas = cfg.setdefault("ai_images", {}).get(hoje, 0)
    if usadas >= cfg.get("ai_images_per_day", 10):
        return None, "teto diario de imagens de IA atingido"
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None, "sem OPENROUTER_API_KEY no .env"
    texto = (f"Editorial photo, vertical 9:16, cinematic lighting: {prompt[:400]}. "
             "No text, no letters, no numbers, no logos, no brand names, no real product likeness, no real people.")
    body = {"model": os.environ.get("IMAGEM_IA_MODELO", "google/gemini-3.1-flash-lite-image"),
            "modalities": ["image", "text"], "image_config": {"aspect_ratio": "9:16"},
            "messages": [{"role": "user", "content": texto}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120))
        raw = base64.b64decode(r["choices"][0]["message"]["images"][0]["image_url"]["url"].split(",", 1)[1])
    except Exception as e:
        return None, f"IA nao gerou ({type(e).__name__})"
    cfg["ai_images"] = {hoje: usadas + 1}
    save_json(CONFIG, cfg)
    CUSTO["ia_imagens"] += 1
    CUSTO["ia_usd"] = round(CUSTO["ia_usd"] + float(r.get("usage", {}).get("cost") or 0), 5)
    wh = salva_jpg(raw, dest)
    return (wh, "") if wh else (None, "ffmpeg nao leu a imagem de IA")


def resolve(news, meta, pedido, cfg, perfil):
    """Põe `media` nos beats a partir do midia.json da apuração. Devolve avisos (nunca levanta)."""
    if not cfg.get("media_enabled") or not isinstance(pedido, dict):
        return []
    beats, avisos = news["beats"], []
    pasta = DATA / "filmes" / news["id"] / "media"
    pasta.mkdir(parents=True, exist_ok=True)
    texto = " ".join([meta.get("title", ""), meta.get("caption", ""), json.dumps(beats[0], ensure_ascii=False)]
                     + [s.get("url", "") for s in news["sources"]])
    if pedido.get("logo"):
        lg, erro = logo(pedido["logo"], texto, news["id"], pasta)
        if lg:
            beats[0]["media"] = lg
            beats[-1]["media"] = dict(lg)
            for campo in ("description", "caption"):
                if CREDITO_LOGO not in (meta.get(campo) or ""):
                    meta[campo] = (meta.get(campo) or "").rstrip() + f"\n\n{CREDITO_LOGO}"
        else:
            avisos.append(f"logo: {erro}")
    foto = pedido.get("foto")
    if isinstance(foto, dict):
        i = foto.get("beat")
        if not isinstance(i, int) or not 0 < i < len(beats) - 1 or "media" in beats[i]:
            avisos.append(f"foto: beat invalido {i}")
        else:
            dest = pasta / f"foto-{i}.jpg"
            if foto.get("tipo") == "newsroom":
                wh, erro = foto_oficial(foto.get("url", ""), dest, set(perfil.get("oficiais", [])))
                credito, fonte = f"Imagem: {str(foto.get('empresa') or 'divulgação')[:22].strip()}", "newsroom"
            elif foto.get("tipo") == "ia" and foto.get("prompt"):
                wh, erro = foto_ia(str(foto["prompt"]), dest, cfg)
                credito, fonte = "Imagem ilustrativa gerada por IA", "ai"
            else:
                wh, erro = None, "tipo de foto invalido"
            if wh:
                beats[i]["media"] = {"kind": "photo", "file": f"foto-{i}.jpg", "source": fonte, "credit": credito,
                                     "width": wh[0], "height": wh[1]}
            else:
                avisos.append(f"foto: {erro}")
    log("mídia:", [(j, b["media"]["kind"]) for j, b in enumerate(beats) if b.get("media")], avisos or "")
    return avisos
