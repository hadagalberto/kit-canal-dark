"""Baixar páginas e deixar o texto comparável (trava de checagem literal)."""
import gzip
import html
import re
import unicodedata
import urllib.request
from urllib.parse import urlparse

from .config import UA


def fetch_bytes(url, t=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=t) as r:
        raw = r.read()
        if raw[:2] == bytes((0x1F, 0x8B)):  # alguns servidores mandam gzip sem pedir
            raw = gzip.decompress(raw)
        return raw, r.headers.get_content_charset()


def fetch(url, t=25):
    raw, charset = fetch_bytes(url, t)
    return raw.decode(charset or "utf-8", "replace")


def host_ok(url, dominios):
    """Domínio da lista ou subdomínio dele (www., blog., news., ...)."""
    host = urlparse(url or "").netloc.lower().split(":")[0]
    return any(host == d or host.endswith("." + d) for d in dominios)


def norm_url(u):
    p = urlparse((u or "").strip())
    return (p.netloc.lower().removeprefix("www.") + p.path.rstrip("/")).lower()


def words(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z0-9]+", s) if len(w) > 2}


def flat(s):
    """Texto comparável: sem HTML, tipografia normalizada, espaços colapsados, minúsculo."""
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", s or "")
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(html.unescape(s))
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"),
                 ("—", "-"), (" ", " "), (" ", " "), (" ", " ")):
        s = s.replace(a, b)
    s = re.sub(r"[\"'`´«»]", "'", s)  # o checador troca " por ' ao citar: aspa é aspa
    s = re.sub(r"\s+", " ", s)
    # tag inline vira espaço ("<a>Galaxy S25</a>," -> "galaxy s25 ,"): espaço antes de pontuação não conta
    s = re.sub(r" ([,.;:!?)\]])", r"\1", s)
    s = re.sub(r"([(\[]) ", r"\1", s)
    return s.strip().lower()


def unmark(s):
    """Tira markdown (link, negrito, crase) antes de comparar com o HTML."""
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1), s or "")
    return re.sub(r"[*_`#>]+", " ", s)


def texto_pagina(raw):
    """HTML -> texto na caixa original, para o checador citar do MESMO texto que confere() verifica."""
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw or "")
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(html.unescape(s))
    return re.sub(r"\s+", " ", s).strip()
