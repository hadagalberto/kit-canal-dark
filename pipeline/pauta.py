"""Etapa 1: pauta. Lê os feeds RSS do canal e devolve os candidatos das últimas horas."""
import datetime
import html
import re
import time
import xml.etree.ElementTree as ET

from .banco import seen
from .config import FUSO, log, now
from .fontes import fetch_bytes


def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%d %b %Y %H:%M:%S %z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            d = datetime.datetime.strptime(s.replace("Z", "+0000") if "T" in s else s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
    return None


def pauta(db, perfil, hours=36, por_veiculo_max=5, total=60):
    cut = now() - datetime.timedelta(hours=hours)
    out, falhas = [], []
    for outlet, url in perfil["feeds"].items():
        root, erro = None, ""
        for _ in range(2):
            try:
                root = ET.fromstring(fetch_bytes(url)[0])  # bytes: o parser respeita o encoding do feed
                break
            except Exception as e:
                erro = str(e)[:60]
                time.sleep(2)
        if root is None:
            falhas.append(f"{outlet}: {erro}")
            continue
        for el in root.iter():
            if el.tag.split("}")[-1] not in ("item", "entry"):
                continue
            kids = {c.tag.split("}")[-1]: c for c in el}
            title = (kids["title"].text or "").strip() if kids.get("title") is not None else ""
            link = ""
            if kids.get("link") is not None:
                link = (kids["link"].text or kids["link"].get("href") or "").strip()
            when = None
            for k in ("pubDate", "published", "updated", "date"):
                if kids.get(k) is not None:
                    when = parse_date(kids[k].text)
                    if when:
                        break
            if not title or not link or not when or when < cut or seen(db, link, title):
                continue
            out.append({"title": html.unescape(title)[:160], "link": link, "outlet": outlet,
                        "date": when.astimezone(FUSO).strftime("%Y-%m-%d %H:%M")})
    out.sort(key=lambda c: c["date"], reverse=True)
    # "prioridade" da ficha (regex de manchete, ex.: o assunto principal do canal): essas manchetes vêm primeiro e furam o limite por veículo
    prio_re = perfil.get("prioridade")
    prio = [c for c in out if prio_re and re.search(prio_re, c["title"], re.I)][:25]
    contagem = {}
    resto = []
    for c in out:
        if c in prio:
            continue
        contagem[c["outlet"]] = contagem.get(c["outlet"], 0) + 1
        if contagem[c["outlet"]] <= por_veiculo_max:
            resto.append(c)
    if falhas:
        log("feeds com falha:", "; ".join(falhas))
    return (prio + resto)[:total]
