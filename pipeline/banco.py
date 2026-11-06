"""Banco de publicados e descartados (published.json): a trava contra notícia repetida."""
import datetime

from .config import DB, load_json, now, save_json
from .fontes import norm_url, words


def db_load():
    db = load_json(DB, None)
    if db is None:
        db = {"items": []}
        save_json(DB, db)
    return db


def db_add(db, item):
    db["items"].append(item)
    save_json(DB, db)


def seen(db, url="", title=""):
    """True se a URL ou um título parecido já passou pelo banco (publicada ou descartada).
    Título parecido = Jaccard >= 0,5 com pelo menos 3 palavras."""
    u = norm_url(url)
    tw = words(title)
    for it in db["items"]:
        if u and u in it.get("urls", []):
            return True
        if len(tw) >= 3:
            for t in it.get("titles") or [it.get("title", "")]:
                iw = words(t)
                if len(iw) >= 3 and len(tw & iw) / len(tw | iw) >= 0.5:
                    return True
    return False


def published_today(db, net):
    day = now().strftime("%Y-%m-%d")
    return sum(1 for it in db["items"] if it.get("at", "").startswith(day) and it.get("links", {}).get(net))


def recent_titles(db, days=10):
    """Publicadas e descartadas: a apuração não pode escolher de novo uma notícia que já caiu numa trava."""
    lim = (now() - datetime.timedelta(days=days)).isoformat()
    out = []
    for it in db["items"]:
        if it.get("at", "") >= lim:
            t = (it.get("titles") or [it.get("title", "")])[0]
            if t:
                out.append(t if it.get("status") == "publicada" else f"{t} (descartada)")
    return out


def registra(db, news, status, titles=(), urls=(), links=None, errors=None):
    hero = (news.get("beats") or [{}])[0] if isinstance(news, dict) else {}
    title = f"{hero.get('title', '')} {hero.get('highlight', '')}".strip() if isinstance(news, dict) else str(news)
    fontes = [s.get("url", "") for s in (news.get("sources") or [])] if isinstance(news, dict) else []
    db_add(db, {"id": news.get("id", "") if isinstance(news, dict) else "", "status": status,
                "at": now().isoformat(timespec="seconds"), "title": title, "titles": list(titles) or [title],
                "urls": sorted({norm_url(u) for u in list(fontes) + list(urls) if u}),
                "style": news.get("style", "") if isinstance(news, dict) else "",
                "links": links or {}, "errors": errors or {}})
