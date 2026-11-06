"""Etapa 3: checagem de fatos.

O LLM aponta, para cada beat, um trecho LITERAL da fonte que sustenta o que o
vídeo diz. Quem decide é o código: o trecho tem de estar caractere por
caractere na página que o próprio script baixou. Sem isso, a notícia cai.
"""
from . import llm
from .config import log, save_json
from .fontes import fetch, flat, texto_pagina, unmark


def confere(rep, news, pages):
    """-> (problemas, trechos que não bateram, beats cobertos)."""
    p = [f"checador: {x}" for x in rep.get("problems") or []]
    urls = {s["url"] for s in news["sources"]}
    falhas, cobertos = [], set()
    for c in rep.get("claims") or []:
        url, q = c.get("url", ""), flat(unmark(c.get("quote", "")))
        if url not in urls:
            p.append(f"beat {c.get('beat')}: url fora de sources: {url}")
            continue
        if len(q) < 20:
            falhas.append(c)
            continue
        if pages.get(url) and q in pages[url]:
            cobertos.add(c.get("beat"))
        elif pages.get(url):
            falhas.append(c)
    return p, falhas, cobertos


def baixa_fontes(news):
    """-> (textos para o checador, páginas achatadas para conferir, problemas)."""
    textos, pages, p = {}, {}, []
    for s in news["sources"]:
        url = s["url"]
        try:
            raw = fetch(url)
        except Exception as e:
            p.append(f"nao consegui abrir a fonte para conferir o trecho: {url} ({str(e)[:60]})")
            continue
        textos[url] = texto_pagina(raw)[:60000]
        pages[url] = flat(raw)
    return textos, pages, p


def checagem(wd, news):
    cd = wd / "checagem"
    cd.mkdir(parents=True, exist_ok=True)
    save_json(cd / "pacote.json", news)
    textos, pages, p = baixa_fontes(news)
    if not textos:
        return p or ["nenhuma fonte abriu"], textos
    rep = llm.checar(news, textos)
    if not isinstance(rep, dict):
        return ["checagem sem JSON"], textos
    save_json(cd / "checagem.json", rep)
    p2, falhas, cobertos = confere(rep, news, pages)
    if falhas and not p2:
        log(f"checagem: {len(falhas)} trecho(s) não literais, pedindo reparo")
        rep2 = llm.reparar(news, textos, rep, falhas)
        if isinstance(rep2, dict):
            rep = rep2
            save_json(cd / "checagem.json", rep)
            p2, falhas, cobertos = confere(rep, news, pages)
    p += p2
    for c in falhas:
        p.append(f"beat {c.get('beat')}: trecho nao esta na pagina: \"{c.get('quote', '')[:90]}\"")
    for i in range(len(news["beats"])):
        if i not in cobertos:
            p.append(f"beat {i}: nenhum fato confirmado com trecho literal")
    log(f"checagem: {len(rep.get('claims') or [])} claims, {len(cobertos)}/{len(news['beats'])} beats confirmados")
    return sorted(set(p)), textos
