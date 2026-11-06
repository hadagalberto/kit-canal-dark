"""Etapa 2: apuração (o LLM escolhe a notícia e escreve o pacote) + validação por código + travas de fonte."""
import datetime
import re

from . import llm
from .banco import recent_titles, seen
from .config import APP, VIDEO, load_json, log, now, save_json
from .fontes import fetch, host_ok, texto_pagina

REQUIRED = {"hero": ["kicker", "title"], "stat": ["value", "label"], "compare": ["label", "items"],
            "bars": ["label", "items"], "list": ["label", "items"], "statement": ["kicker", "text"],
            "end": ["where", "source"]}
MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO",
         "NOVEMBRO", "DEZEMBRO"]
PT_MARCAS = {"de", "que", "não", "nao", "para", "com", "uma", "um", "os", "as", "do", "da", "dos", "das", "em",
             "no", "na", "nos", "é", "são", "mais", "por", "agora", "também", "já", "você", "ele", "ela", "isso",
             "como", "quem", "pra", "até", "sem", "seu", "sua", "foi", "vai", "tem", "ao", "às", "pelo", "pela"}
EN_MARCAS = {"the", "and", "is", "are", "with", "for", "this", "that", "of", "to", "will", "it", "its", "your",
             "you", "from", "now", "has", "have", "be", "on", "at", "by", "an", "or", "can", "new", "just"}


def fontes_aceitas(perfil):
    return set(perfil["dominios"]) - set(perfil.get("so_pauta", []))


def anexos(perfil):
    """Contexto fixo da apuração (vai para o cache do LLM): formato, estilos do canal, exemplo, domínios."""
    with open(VIDEO / "src" / "styles" / "README.md", encoding="utf-8") as f:  # cada canal vê só os estilos dele
        estilos = "".join(ln for ln in f
                          if not (m := re.match(r"^\|[^|]*\| `([a-z0-9]+)` \|", ln)) or m.group(1) in perfil["estilos"])
    return {
        "dominios": "\n".join(sorted(fontes_aceitas(perfil))),
        "types.ts": (VIDEO / "src" / "news" / "types.ts").read_text(encoding="utf-8"),
        "styles.md": estilos,
        "exemplo-1": (APP / "exemplos" / "noticias" / "2026-10-09-gemini-colega.json").read_text(encoding="utf-8"),
        "meta-exemplo": (APP / "exemplos" / "meta-exemplo.json").read_text(encoding="utf-8"),
    }


def apuracao(wd, db, cfg, perfil, candidatos, tema=None):
    """Grava news.json, meta.json, escolha.json (e midia.json) em wd, ou skip.txt."""
    recentes = "; ".join(recent_titles(db)[-30:]) or "(nenhum)"
    if llm.PROVEDOR == "openrouter":
        r = apuracao_em_dois_passos(wd, cfg, perfil, candidatos, recentes, tema)
    else:
        r = llm.apurar(perfil, anexos(perfil), now().strftime("%Y-%m-%d"), recentes, candidatos,
                       bool(cfg.get("media_enabled")), tema=tema)
    if not isinstance(r, dict):
        raise RuntimeError("apuração sem JSON na resposta")
    if r.get("skip"):
        (wd / "skip.txt").write_text(str(r["skip"]), encoding="utf-8")
        return
    for b in (r.get("news") or {}).get("beats") or []:
        if isinstance(b, dict):
            b.pop("media", None)  # mídia só vem de midia.json (baixada e conferida); o modelo pode inventar
    for nome in ("news", "meta", "escolha", "midia"):
        if isinstance(r.get(nome), dict):
            save_json(wd / f"{nome}.json", r[nome])
    log("apuração:", (r.get("news") or {}).get("id"))


def apuracao_em_dois_passos(wd, cfg, perfil, candidatos, recentes, tema):
    """OpenRouter não tem web_fetch: o modelo escolhe, o script baixa a matéria, o modelo escreve com ela.
    Só entram candidatos cujo link já é fonte aceita, porque a matéria do candidato vira a fonte do vídeo."""
    aceitas = fontes_aceitas(perfil)
    cands = [c for c in candidatos if host_ok(c.get("link"), aceitas)]
    if not cands and not tema:
        return {"skip": "nenhum candidato com link em dominio aceito como fonte (os outros sao so_pauta ou fora da lista)"}
    r = llm.escolher(perfil, recentes, cands, tema=tema)
    if not isinstance(r, dict) or r.get("skip"):
        return r
    esc = r.get("escolha") or {}
    url = esc.get("link", "")
    if not tema and url not in {c["link"] for c in cands}:
        return {"skip": f"escolha fora da lista de candidatos: {url[:120]}"}
    if not host_ok(url, aceitas):
        return {"skip": f"fonte fora da lista de dominios: {url[:120]}"}
    try:
        texto = texto_pagina(fetch(url))[:60000]
    except Exception as e:
        return {"skip": f"nao consegui abrir a materia escolhida ({str(e)[:80]})"}
    if len(texto) < 1500:
        return {"skip": "materia escolhida com texto curto demais (paywall ou pagina vazia)"}
    if tema:  # a pauta pedida não passou pelo RSS: grava o candidato para a trava de data
        save_json(wd / "candidatos.json", [{"title": esc.get("manchete", ""), "link": url, "outlet": "pauta pedida",
                                            "date": now().strftime("%Y-%m-%d %H:%M")}])
    log(f"apuração: escolhida {url} ({len(texto)} caracteres de texto)")
    r = llm.escrever(perfil, anexos(perfil), now().strftime("%Y-%m-%d"), esc, url, texto, bool(cfg.get("media_enabled")))
    if isinstance(r, dict) and not r.get("skip"):
        r["escolha"] = esc  # o link/manchete do passo 1 é o que as travas conferem
    return r


def em_portugues(texto):
    """Heurística sem IA: palavras comuns do português têm de dominar as do inglês."""
    ws = re.findall(r"[a-zà-ú]+", (texto or "").lower())
    if len(ws) < 6:
        return True
    pt = sum(w in PT_MARCAS for w in ws)
    en = sum(w in EN_MARCAS for w in ws)
    return pt >= 3 and pt >= 2 * en


def validate(news, meta, estilos, idade_max=4):
    p = []
    nid = news.get("id", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*", nid) or len(nid) > 60:
        p.append(f'id invalido "{nid}" (AAAA-MM-DD-slug, ascii minusculo)')
    if news.get("style") not in estilos:
        p.append(f'style "{news.get("style")}" fora de {estilos}')
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", news.get("date", ""))
    if not m:
        p.append('date tem de ser "DD.MM.AAAA"')
    else:
        try:
            d = datetime.date(int(m[3]), int(m[2]), int(m[1]))
            idade = (now().date() - d).days
            if idade_max is not None and not 0 <= idade <= idade_max:
                p.append(f"date {news['date']} fora dos ultimos {idade_max} dias")
            esperado = f"{d.day:02d} DE {MESES[d.month - 1]} DE {d.year}"
            if news.get("dateLong", "").upper() != esperado:
                p.append(f'dateLong tem de ser "{esperado}"')
        except ValueError:
            p.append("date invalida")
    src = news.get("sources") or []
    if not src or not all(isinstance(s, dict) and s.get("url", "").startswith("http") and s.get("label") for s in src):
        p.append("sources vazio ou sem label/url")
    beats = news.get("beats") or []
    if not 4 <= len(beats) <= 9:
        p.append(f"{len(beats)} beats (use de 5 a 8)")
    if beats and beats[0].get("type") != "hero":
        p.append("primeiro beat tem de ser hero")
    if beats and beats[-1].get("type") != "end":
        p.append("ultimo beat tem de ser end")
    ids, falado = set(), 0
    for i, b in enumerate(beats):
        at = f"beat {i} ({b.get('type')})"
        if b.get("type") not in REQUIRED:
            p.append(f"{at}: tipo desconhecido")
            continue
        for f in REQUIRED[b["type"]]:
            if b.get(f) in (None, "", []):
                p.append(f"{at}: falta {f}")
        v = b.get("voice") or {}
        if not re.fullmatch(r"[a-z0-9-]+", v.get("id", "")) or not v.get("text"):
            p.append(f"{at}: voice.id (a-z0-9-) e voice.text obrigatorios")
        if v.get("id") in ids:
            p.append(f"{at}: voice.id repetido")
        ids.add(v.get("id"))
        fala = re.sub(r"\[[^\]]*\]", "", v.get("text", ""))
        falado += len(fala)
        if re.search(r"\d", fala):
            p.append(f'{at}: fala com digito, escreva por extenso: "{fala.strip()}"')
        if re.search(r"\bIA\b", fala):
            p.append(f'{at}: fala com a sigla IA, diga "inteligencia artificial"')
        c = b.get("caption") or {}
        if not c.get("kicker") or not c.get("text"):
            p.append(f"{at}: falta caption.kicker ou caption.text")
        if len((c.get("text") or "").split("\n")) > 2:
            p.append(f"{at}: caption com mais de 2 linhas")
        if isinstance(b.get("items"), list) and not 1 <= len(b["items"]) <= 4:
            p.append(f"{at}: items de 1 a 4")
    # acima de ~560 caracteres falados (mais a chamada final) o vídeo passa de 45 s
    if not 250 <= falado <= 560:
        p.append(f"fala total com {falado} caracteres: encurte para 350-520")
    if beats:
        gancho = re.sub(r"\[[^\]]*\]", "", (beats[0].get("voice") or {}).get("text", "")).split()
        if len(gancho) > 11:
            p.append(f"gancho (fala do beat 0) com {len(gancho)} palavras: no maximo 9")
    fala = " ".join(re.sub(r"\[[^\]]*\]", "", (b.get("voice") or {}).get("text", "")) for b in beats)
    tela = " ".join(f"{(b.get('caption') or {}).get('kicker', '')} {(b.get('caption') or {}).get('text', '')}" for b in beats)
    redes = f"{meta.get('caption', '')} {meta.get('title', '')}" if isinstance(meta, dict) else ""
    for nome, texto in (("fala", fala), ("legenda da tela", tela), ("texto das redes", redes)):
        if not em_portugues(texto):
            p.append(f"{nome} nao parece estar em portugues do Brasil")
    if not isinstance(meta, dict):
        p.append("meta.json ausente ou invalido")
    else:
        if not meta.get("caption") or len(meta["caption"]) > 2000:
            p.append("meta.caption vazia ou > 2000 caracteres")
        if not meta.get("title") or len(meta["title"]) > 90:
            p.append("meta.title vazio ou > 90 caracteres")
        if not meta.get("description"):
            p.append("meta.description vazia")
        if not isinstance(meta.get("tags"), list) or not meta["tags"]:
            p.append("meta.tags vazia")
    return p


def travas_fonte(news, db, perfil, identidade):
    """Travas de fonte (lista de domínios) e de repetição (banco), determinísticas."""
    p = []
    aceitas = fontes_aceitas(perfil)
    for s in news.get("sources", []):
        if not host_ok(s.get("url"), aceitas):
            p.append(f"fonte fora da lista de veiculos/blogs oficiais: {s.get('url')}")
        if seen(db, s.get("url")):
            p.append(f"fonte ja usada: {s.get('url')}")
    for u in identidade["urls"]:
        if seen(db, u):
            p.append(f"candidato ja usado: {u}")
    for t in identidade["titles"]:
        if seen(db, title=t):
            p.append(f"tema repetido: {t}")
    return p


def data_do_feed(news, wd, tema=None):
    """A data do vídeo confere com a publicação do candidato no RSS (de 3 dias antes a 1 depois)."""
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", news.get("date", ""))
    d = datetime.date(int(m[3]), int(m[2]), int(m[1])) if m else None
    if tema:
        if not d or not 0 <= (now().date() - d).days <= 7:
            return [f"pauta pedida: data do video {news.get('date')} fora dos ultimos 7 dias"]
        return []
    esc = load_json(wd / "escolha.json", {})
    cand = next((c for c in load_json(wd / "candidatos.json", []) if c.get("link") == esc.get("link")), None)
    if not cand:
        return ["escolha.json nao aponta para um link de candidatos.json"]
    feed = datetime.date.fromisoformat(cand["date"][:10])
    if not d or not feed - datetime.timedelta(days=3) <= d <= feed + datetime.timedelta(days=1):
        return [f"data do video {news.get('date')} nao bate com a publicacao no feed ({feed:%d.%m.%Y})"]
    return []
