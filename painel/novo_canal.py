"""Cria um canal pelo painel: /dados/canais/<id>.json, a partir de uma ficha-modelo do kit (canais/exemplo.json).

O canal nasce sem turno (só roda pelo botão) e em ensaio ("publicar": false), a menos que o formulário diga
outra coisa. Mesmo com "publicar": true, nada sai com DRY_RUN=1 no .env (trava geral). Chaves de API nunca
entram na ficha.
"""
import json
import os
import re
from urllib.parse import urlparse

from croniter import croniter

from pipeline import config as C

ID = re.compile(r"[a-z][a-z0-9-]{1,29}")
DOMINIO = re.compile(r"(?:[a-z0-9-]+\.)+[a-z]{2,}")
REDES = ("youtube", "instagram", "tiktok")
PRIORIDADE_PADRAO = ("Prefira o que afeta o dia a dia de quem mora no Brasil, o que mexe no bolso e o que tem numero "
                     "forte ou mudanca concreta. Noticia de nicho so se nao houver opcao melhor.")


def modelos():
    return sorted(p.stem for p in C.MODELOS.glob("*.json"))


def estilos():
    pasta = C.APP / "video" / "src" / "styles"
    return sorted(p.name for p in pasta.iterdir() if (p / "entry.tsx").exists()) if pasta.exists() else []


def _texto(d, campo, maximo, obrigatorio=False):
    v = str(d.get(campo) or "").strip()
    if obrigatorio and not v:
        raise ValueError(f"preencha {campo}")
    if len(v) > maximo:
        raise ValueError(f"{campo} com mais de {maximo} caracteres")
    return v


def _feeds(texto, padrao):
    """Uma por linha: "Nome | https://site/feed" ou só a URL. Vazio = os feeds do modelo."""
    linhas = [ln.strip() for ln in (texto or "").splitlines() if ln.strip()]
    if not linhas:
        return padrao
    if len(linhas) > 40:
        raise ValueError("no máximo 40 feeds")
    feeds = {}
    for ln in linhas:
        nome, _, url = ln.rpartition("|") if "|" in ln else ("", "", ln)
        url = url.strip()
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.netloc:
            raise ValueError(f"feed sem URL http(s): {ln[:80]}")
        feeds[(nome.strip() or u.netloc.removeprefix("www."))[:40]] = url
    return feeds


def _dominios(texto):
    ds = {d.strip().lower().removeprefix("www.") for d in re.split(r"[\s,]+", texto or "") if d.strip()}
    ruins = [d for d in ds if not DOMINIO.fullmatch(d)]
    if ruins:
        raise ValueError(f"domínio inválido: {ruins[0][:60]}")
    return ds


def criar(d):
    """d: campos do formulário. -> (id, caminho). Levanta ValueError com a mensagem para a página."""
    cid = _texto(d, "id", 30, True).lower()
    if not ID.fullmatch(cid):
        raise ValueError("id: minúsculas, números e hífen, começando por letra (ex.: futebol, carros-br)")
    if cid in modelos() or C.arquivo_canal(cid).exists() or cid in C.lista_canais():
        raise ValueError(f"já existe um canal '{cid}'")
    base = str(d.get("modelo") or "exemplo")
    if base not in modelos():
        raise ValueError(f"modelo desconhecido: {base}")
    modelo = json.loads((C.MODELOS / f"{base}.json").read_text(encoding="utf-8"))

    nome = _texto(d, "nome", 40, True)
    handle = _texto(d, "handle", 31)
    if handle and not re.fullmatch(r"@[A-Za-z0-9._]{1,30}", handle):
        raise ValueError("@ do canal: comece com @ e use letras, números, ponto ou _")
    assunto = _texto(d, "assunto", 80, True)
    frase = _texto(d, "frase", 60) or f"Notícias de {assunto} todos os dias"
    prioridade = _texto(d, "prioridade", 800) or PRIORIDADE_PADRAO
    voz = _texto(d, "voice_id", 40)
    if voz and not re.fullmatch(r"[A-Za-z0-9]{10,40}", voz):
        raise ValueError("id da voz: só letras e números (copie da Voice Library da ElevenLabs)")
    agenda = _texto(d, "agenda", 60)
    if agenda and not croniter.is_valid(agenda):
        raise ValueError("agenda inválida: formato cron, ex.: 0 9,13,18 * * *")

    todos = estilos()
    escolhidos = [e for e in (d.get("estilos") or []) if e in todos] or [e for e in modelo["estilos"] if e in todos]
    redes = [r for r in (d.get("redes") or []) if r in REDES] or ["youtube"]
    feeds = _feeds(d.get("feeds"), modelo["feeds"])
    dominios = _dominios(d.get("dominios"))
    if not dominios:
        dominios = set(modelo["dominios"])
        if feeds is not modelo["feeds"]:
            raise ValueError("com feeds próprios, liste os domínios aceitos como fonte (os sites confiáveis do nicho)")

    perfil = {
        "_leia": f"Criado pelo painel a partir do modelo {base}. Pode editar à mão; o agendador relê a cada volta.",
        "brand": {"name": nome, "handle": handle or "@" + re.sub(r"[^a-z0-9.]", "", cid.replace("-", ".")),
                  "short": nome.upper(), "tagline": frase},
        "perfil": f"Voce e o editor do canal {nome}, reels de noticia de {assunto} em PT-BR.",
        "regra1": (f"1. Escolha UMA noticia dos CANDIDATOS (ultimas 36 h) sobre {assunto}. {prioridade} Evite opiniao, "
                   "rumor, vazamento, processo judicial sem decisao, e qualquer coisa parecida com os JA PUBLICADOS OU "
                   "DESCARTADOS da mensagem (mesmo assunto com outra manchete conta como repetido)."),
        "caption_cta": f"Noticias de {assunto} todos os dias -> siga {handle or 'o canal'}",
        # formato, sem fato inventado: o exemplo do modelo (Windows, Claude...) puxaria o título para o nicho errado
        "titulo_exemplos": '"<protagonista da noticia>: <a novidade concreta em poucas palavras>"',
        "cta": "[warm] Curtiu? Segue o canal agora, que todo dia tem notícia nova.",
        "voice_id": voz,
        "estilos": escolhidos,
        "redes": redes,
        "prioridade": None,
        "feeds": feeds,
        "dominios": sorted(dominios),
        "so_pauta": [x for x in modelo.get("so_pauta", []) if x in dominios],
        "oficiais": modelo.get("oficiais", []),
        "agenda": agenda,
        "publicar": d.get("publicar") is True,  # só publica com DRY_RUN=0 no .env também
    }
    C.CANAIS_CRIADOS.mkdir(parents=True, exist_ok=True)
    caminho = C.CANAIS_CRIADOS / f"{cid}.json"
    with open(caminho, "x", encoding="utf-8") as f:  # "x": nunca sobrescreve um canal
        json.dump(perfil, f, ensure_ascii=False, indent=2)
    os.chmod(caminho, 0o644)
    return cid, caminho


# ---------------------------------------------------------------- editar uma ficha existente (painel, "Editar ficha")

def ler(cid):
    if cid not in C.lista_canais() or C.arquivo_canal(cid).parent != C.CANAIS_CRIADOS:
        raise ValueError("só dá para editar canais criados pelo painel (a ficha-modelo do kit fica como está)")
    return json.loads(C.arquivo_canal(cid).read_text(encoding="utf-8"))


def valida(f):
    """Confere uma ficha inteira (edição à mão no painel). Levanta ValueError com o primeiro problema."""
    if not isinstance(f, dict):
        raise ValueError("a ficha tem de ser um objeto JSON")
    b = f.get("brand")
    if not isinstance(b, dict) or not str(b.get("name") or "").strip():
        raise ValueError("brand.name é obrigatório")
    for chave in ("perfil", "regra1", "caption_cta", "titulo_exemplos"):
        if not isinstance(f.get(chave), str) or not f[chave].strip():
            raise ValueError(f"{chave} é obrigatório (texto)")
    feeds = f.get("feeds")
    if not isinstance(feeds, dict) or not feeds:
        raise ValueError("feeds: objeto {\"Nome\": \"https://...\"} com pelo menos um feed")
    for nome, url in feeds.items():
        u = urlparse(str(url))
        if u.scheme not in ("http", "https") or not u.netloc:
            raise ValueError(f"feed {nome}: URL http(s) inválida")
    dom = f.get("dominios")
    if not isinstance(dom, list) or not dom or not all(isinstance(d, str) and DOMINIO.fullmatch(d) for d in dom):
        raise ValueError("dominios: lista de domínios (ex.: [\"ge.globo.com\"]), pelo menos um")
    todos = estilos()
    est = f.get("estilos")
    if not isinstance(est, list) or not est or any(e not in todos for e in est):
        raise ValueError(f"estilos: lista com ids de video/src/styles ({', '.join(todos)})")
    redes = f.get("redes")
    if not isinstance(redes, list) or any(r not in REDES for r in redes):
        raise ValueError(f"redes: lista com {', '.join(REDES)}")
    ag = str(f.get("agenda") or "")
    if ag and not croniter.is_valid(ag):
        raise ValueError("agenda: formato cron, ex.: 0 9,13,18 * * *")
    if not isinstance(f.get("publicar", False), bool):
        raise ValueError("publicar: true ou false")
    voz = str(f.get("voice_id") or "")
    if voz and not re.fullmatch(r"[A-Za-z0-9]{10,40}", voz):
        raise ValueError("voice_id: só letras e números")
    chat = f.get("telegram_chat_id")
    if chat not in (None, "") and not re.fullmatch(r"-?\d{3,20}", str(chat)):
        raise ValueError("telegram_chat_id: número do chat (ex.: -1001234567890)")
    if len(json.dumps(f)) > 60_000:
        raise ValueError("ficha grande demais")


def salvar(cid, f):
    ler(cid)  # confere que é um canal criado pelo painel
    valida(f)
    caminho = C.arquivo_canal(cid)
    C.save_json(caminho, f)
    os.chmod(caminho, 0o644)
    return caminho
