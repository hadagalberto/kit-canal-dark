"""Chamadas ao LLM (motor "api"), pelo SDK oficial da Anthropic.

Portado do reels_api.py do sistema original:
- apurar():   modelo forte com web_search/web_fetch do servidor; contexto fixo (formato, estilos, exemplos,
              domínios) em cache; devolve UM JSON com news, meta, escolha e midia.
- corrigir(): modelo barato, só reescreve o pacote reprovado pela validação.
- revisar():  modelo forte, reescreve os beats que a checagem reprovou, com o texto das fontes.
- checar():   modelo barato SEM web: recebe o texto das páginas que o próprio script baixou, então cita do
              mesmo texto que a conferência literal verifica.
- reparar():  modelo barato, troca os trechos que não bateram.

Os prompts saem do perfil do canal (canais/<nome>.json): nome, nicho, regra de pauta, CTA da legenda.
O custo de cada chamada (usage x preço) soma em CUSTO["llm_usd"], que alimenta o teto diário.

Provedor (LLM_PROVEDOR no .env):
- anthropic   API direta, com web_search/web_fetch do servidor na apuração (como o sistema original).
- openrouter  API compatível com OpenAI (openrouter.ai), qualquer modelo da lista deles. Sem web_fetch:
              a apuração vira duas chamadas (escolher() e escrever()), e quem baixa a matéria é o script.
              O custo vem exato na resposta (usage.cost).
"""
import json
import os
import re
import urllib.error
import urllib.request

from .config import log as _log

PROVEDOR = os.environ.get("LLM_PROVEDOR", "anthropic").strip().lower() or "anthropic"
_PADRAO = {"anthropic": ("claude-sonnet-5-5", "claude-haiku-5-5"),
           "openrouter": ("anthropic/claude-sonnet-5.5", "anthropic/claude-haiku-5.5")}
MODELO_FORTE = os.environ.get("LLM_MODELO_FORTE", "").strip() or _PADRAO.get(PROVEDOR, _PADRAO["anthropic"])[0]
MODELO_BARATO = os.environ.get("LLM_MODELO_BARATO", "").strip() or _PADRAO.get(PROVEDOR, _PADRAO["anthropic"])[1]
OPENROUTER_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
# US$ por milhão de tokens: entrada, saída, leitura de cache, escrita de cache. Confira a tabela de preços atual.
PRECO = {"claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50), "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125)}
PRECO_BUSCA = 0.01  # US$ por web_search

CUSTO = {"llm_usd": 0.0, "llm_chamadas": 0}
_client = None


def chave():
    if PROVEDOR not in _PADRAO:
        raise RuntimeError(f"LLM_PROVEDOR={PROVEDOR!r} desconhecido: use anthropic ou openrouter")
    nome = "OPENROUTER_API_KEY" if PROVEDOR == "openrouter" else "ANTHROPIC_API_KEY"
    k = os.environ.get(nome, "").strip()
    if not k:
        raise RuntimeError(f"MOTOR=api com LLM_PROVEDOR={PROVEDOR} precisa de {nome} no .env (ou use MOTOR=exemplo)")
    return k


def cliente():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=chave(), timeout=600, max_retries=2)
    return _client


def _conta(model, u):
    p_in, p_out, p_read, p_write = PRECO.get(model, PRECO["claude-sonnet-5-5"])
    usd = ((u.input_tokens or 0) * p_in + (u.output_tokens or 0) * p_out
           + (u.cache_read_input_tokens or 0) * p_read + (u.cache_creation_input_tokens or 0) * p_write) / 1e6
    usd += (getattr(getattr(u, "server_tool_use", None), "web_search_requests", 0) or 0) * PRECO_BUSCA
    CUSTO["llm_usd"] = round(CUSTO["llm_usd"] + usd, 4)
    CUSTO["llm_chamadas"] += 1
    return usd


def extrai_json(texto):
    """O último objeto JSON da resposta: bloco ```json ou o maior trecho {...} que faz parse."""
    for b in reversed(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.S)):
        try:
            return json.loads(b)
        except ValueError:
            pass
    ini = texto.find("{")
    while ini != -1:
        fim = texto.rfind("}")
        while fim > ini:
            try:
                return json.loads(texto[ini:fim + 1])
            except ValueError:
                fim = texto.rfind("}", ini, fim)
        ini = texto.find("{", ini + 1)
    return None


def _pede_openrouter(model, system, user, max_tokens=16000, effort=None, web=False, log=_log):
    """Chat completions do OpenRouter. web=True liga o plugin de busca deles (só para pauta pedida)."""
    texto_system = system if isinstance(system, str) else "\n\n".join(b["text"] for b in system)
    body = {"model": model, "max_tokens": max_tokens, "usage": {"include": True},
            "messages": [{"role": "system", "content": texto_system}, {"role": "user", "content": user}]}
    if effort:
        body["reasoning"] = {"effort": effort}
    if web:
        body["plugins"] = [{"id": "web", "max_results": 5}]
    req = urllib.request.Request(f"{OPENROUTER_URL}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + chave(),
                                          "X-Title": "canal-dark-kit"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e:  # o corpo do erro do OpenRouter diz o motivo (modelo, saldo, chave)
        raise RuntimeError(f"OpenRouter {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None
    if r.get("error"):
        raise RuntimeError(f"OpenRouter: {str(r['error'])[:300]}")
    usd = float((r.get("usage") or {}).get("cost") or 0)
    CUSTO["llm_usd"] = round(CUSTO["llm_usd"] + usd, 4)
    CUSTO["llm_chamadas"] += 1
    escolha = (r.get("choices") or [{}])[0]
    log(f"llm openrouter {model}: {escolha.get('finish_reason')} · US$ {usd:.4f}")
    return (escolha.get("message") or {}).get("content") or ""


def _pede(model, system, user, max_tokens=16000, tools=None, effort=None, log=_log):
    """Uma chamada com loop de pause_turn (ferramentas do servidor podem pausar o turno)."""
    if PROVEDOR == "openrouter":
        return _pede_openrouter(model, system, user, max_tokens, effort, log=log)
    msgs = [{"role": "user", "content": user}]
    kw = {"model": model, "max_tokens": max_tokens, "system": system, "messages": msgs}
    if tools:
        kw["tools"] = tools
    if effort:
        kw["output_config"] = {"effort": effort}
    resp = None
    for volta in range(4):
        resp = cliente().messages.create(**kw)
        usd = _conta(model, resp.usage)
        log(f"llm {model} volta {volta}: {resp.stop_reason} · US$ {usd:.4f}")
        if resp.stop_reason != "pause_turn":
            break
        msgs.append({"role": "assistant", "content": resp.content})
    if resp.stop_reason == "refusal":
        raise RuntimeError("o modelo recusou o pedido")
    return "".join(b.text for b in resp.content if b.type == "text")


def _json_ou_reformata(texto, log):
    d = extrai_json(texto)
    if d is not None:
        return d
    log("llm: resposta sem JSON válido, pedindo só a reformatação")
    t = _pede(MODELO_BARATO, "Voce converte texto em JSON valido.",
              "Devolva SO o objeto JSON contido no texto abaixo, valido, sem comentario:\n\n" + texto[-30000:], log=log)
    return extrai_json(t)


# ---------------------------------------------------------------- apuração

REGRAS_APURACAO = """{perfil}
Os anexos abaixo tem o formato e exemplos: DOMINIOS (unicas fontes aceitas), TYPES.TS (formato e regras de escrita), STYLES.MD (os estilos do canal e quando usar cada um), EXEMPLO-1 (pacote real aprovado), META-EXEMPLO (legenda/titulo das redes).

TAREFA
{regra1}
{passo2}
3. Monte "news" seguindo TYPES.TS a risca:
   - "id": "<data de hoje>-<slug-curto-em-ascii>"; "date": "DD.MM.AAAA" e "dateLong": "DD DE MES DE AAAA" = data do anuncio.
   - "style": um dos ids da tabela de STYLES.MD, o que combina com o tipo da noticia (varie entre os videos).
   - "sources": [{{"label","url"}}] com a URL EXATA da pagina lida (nao a home do site).
   - 5 a 8 beats, um por fala; primeiro "hero", ultimo "end" (end.source = "Fonte: <veiculo> · <dia mes ano>").
   - Fala ("voice.text"): numeros por extenso, "inteligencia artificial" (nunca a sigla), pode usar tags de emocao como [excited] [confident] [measured]. A fala NAO le a legenda; acrescenta fato. TAMANHO: somando todas as falas, 350 a 520 caracteres (sem contar as [tags]); acima de 560 o pacote e reprovado.
   - NAO coloque o campo "media" nos beats: a midia vai SO em "midia", o script baixa e confere.
   - GANCHO (beat 0): a primeira fala tem no maximo 9 palavras e abre com a CONSEQUENCIA ou o NUMERO mais forte da noticia, nao com "A empresa X lancou Y". Continua sendo fato da fonte, sem exagero. O hero (title/highlight) mostra a palavra ou o numero desse gancho.
   - Tela: digitos ("5.5", "US$ 0,10"). caption.text no maximo 2 linhas curtas. items de 1 a 4.
   - NAO GENERALIZE. Cada fala e cada texto de tela tem de estar dito na fonte com o mesmo alcance (so contas gratuitas, so EUA, so parte dos usuarios: diga isso ou nao diga). "Todo mundo", "tudo", "sempre", "ja disponivel" so com a fonte dizendo exatamente isso.
   - NAO AFIRME AUSENCIA. "Valor nao divulgado", "sem data" so se a fonte disser isso com essas palavras.
   - So o que a fonte diz. Preview e preview; sem data de lancamento geral inventada; nada de screenshot.
   - "voice": {{"tempo": 1.12, "stability": 0.5, "similarity": 0.8}}
4. Monte "meta" no formato de META-EXEMPLO: caption (gancho, 2-3 linhas de fato, "Fonte: ... (data)", "{caption_cta}", 4-6 hashtags), title do YouTube (ate 70 caracteres, sem #shorts; COMECA pelo nome do produto ou da empresa e diz a novidade concreta, como {titulo_exemplos}; sem clickbait, sem pergunta), description (fato + fonte + data), tags (4-8).
5. Monte "escolha": {{"link": "<link EXATO do candidato escolhido>", "manchete": "<title EXATO dele>"}}.
6. Se a mensagem pedir midia, monte "midia" como ela descreve; senao "midia": null.

RESPOSTA: no fim, UM objeto JSON, sem texto depois dele:
{{"news": {{...}}, "meta": {{...}}, "escolha": {{...}}, "midia": {{...}} ou null}}
Se NENHUM candidato servir: {{"skip": "<motivo curto>"}}"""

MIDIA_API = """MIDIA (imagens do video, tudo opcional) em "midia":
{"logo": {"dominio": "<dominio oficial da empresa ou produto PROTAGONISTA>", "nome": "<nome da marca>"} ou null,
 "foto": {"beat": <indice do beat, nunca o 0 nem o ultimo>, "tipo": "newsroom", "url": "<URL de IMAGEM (jpg/png/webp) da sala de imprensa OFICIAL>", "empresa": "<nome>"}
         ou {"beat": <indice>, "tipo": "ia", "prompt": "<cena ilustrativa generica em ingles; sem marca, sem texto, sem pessoa real>"}
         ou null}
- Logo so da empresa/produto de que a noticia trata. Na duvida, null.
- Foto oficial so se voce achou a URL da imagem na pagina oficial (nunca foto de veiculo de imprensa). Senao, "ia" com cena generica, nunca o produto anunciado em si.
- No beat da foto, o texto da tela nao pode chamar a imagem de "o novo X": a imagem e ilustrativa."""


def apurar(perfil, anexos, hoje, recentes, candidatos, com_midia, log=_log, tema=None):
    regras = _regras(perfil, PASSO2_WEB)
    fixo = regras + "\n\n" + "\n\n".join(f"===== {nome.upper()} =====\n{txt}" for nome, txt in anexos.items())
    system = [{"type": "text", "text": fixo, "cache_control": {"type": "ephemeral"}}]
    if tema:
        pauta = (f"PAUTA PEDIDA PELO EDITOR (substitui os CANDIDATOS): {tema}\n"
                 "Use web_search para achar a noticia RECENTE (ate 7 dias) sobre esse tema, com fonte em DOMINIOS. "
                 "Se nao houver, responda {\"skip\": \"<motivo>\"}. Em \"escolha\" use a URL e o titulo da fonte principal.\n\n")
    else:
        pauta = f"CANDIDATOS (JSON):\n{json.dumps(candidatos, ensure_ascii=False)}\n\n"
    user = (f"Data de hoje: {hoje} (use no id).\nJA PUBLICADOS OU DESCARTADOS (nao repetir o assunto): {recentes}\n\n"
            + pauta + (MIDIA_API if com_midia else "Nao precisa de midia: \"midia\": null."))
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5},
             {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 8, "max_content_tokens": 18000}]
    return _json_ou_reformata(_pede(MODELO_FORTE, system, user, tools=tools, effort="medium", log=log), log)


PASSO2_WEB = ("2. Leia a FONTE PRIMARIA com web_fetch (anuncio oficial da empresa quando existir; senao a reportagem). "
              "Use web_search so se precisar achar o anuncio oficial. Confirme cada fato. Use no maximo 3 fontes, e TODAS tem "
              "de estar em DOMINIOS (subdominio vale). Fonte fora dessa lista descarta o video inteiro: se a noticia so existir "
              "em sites fora da lista, escolha outra.")
PASSO2_TEXTO = ("2. A noticia ja foi escolhida e o TEXTO DA FONTE vem na mensagem, baixado pelo script. Use SO esse texto: "
                "cada fato do video tem de estar nele. \"sources\" tem exatamente a URL da fonte da mensagem. Se o texto nao "
                "sustentar um video de 5 beats (pagina vazia, paywall, so um paragrafo), responda {\"skip\": \"<motivo>\"}.")


def _regras(perfil, passo2):
    return REGRAS_APURACAO.format(perfil=perfil["perfil"], regra1=perfil["regra1"], passo2=passo2,
                                  caption_cta=perfil["caption_cta"], titulo_exemplos=perfil["titulo_exemplos"])


# ---------------------------------------------------------------- apuração em duas chamadas (openrouter)

ESCOLHE = """{perfil}
Escolha a pauta do proximo reel.
{regra1}
Responda com UM objeto JSON: {{"escolha": {{"link": "<link EXATO do candidato>", "manchete": "<title EXATO dele>"}}}}
Se nenhum servir: {{"skip": "<motivo curto>"}}"""


def escolher(perfil, recentes, candidatos, tema=None, log=_log):
    """Passo 1 sem ferramentas: escolhe um candidato (ou, com tema, acha a materia pela busca web do OpenRouter)."""
    system = ESCOLHE.format(perfil=perfil["perfil"], regra1=perfil["regra1"])
    if tema:
        dominios = ", ".join(sorted(set(perfil["dominios"]) - set(perfil.get("so_pauta", []))))
        user = (f"PAUTA PEDIDA PELO EDITOR: {tema}\n"
                f"Ache a noticia RECENTE (ate 7 dias) sobre esse tema numa fonte destes dominios: {dominios}.\n"
                "Em \"link\" a URL exata da materia, em \"manchete\" o titulo dela.\n"
                f"JA PUBLICADOS OU DESCARTADOS: {recentes}")
        texto = _pede_openrouter(MODELO_FORTE, system, user, max_tokens=4000, web=True, log=log)
    else:
        user = (f"JA PUBLICADOS OU DESCARTADOS (nao repetir o assunto): {recentes}\n\n"
                f"CANDIDATOS (JSON):\n{json.dumps(candidatos, ensure_ascii=False)}")
        texto = _pede(MODELO_FORTE, system, user, max_tokens=4000, effort="low", log=log)
    return _json_ou_reformata(texto, log)


def escrever(perfil, anexos, hoje, escolha, url, texto_fonte, com_midia, log=_log):
    """Passo 2 sem ferramentas: escreve news/meta/midia so com o texto da fonte baixado pelo script."""
    fixo = _regras(perfil, PASSO2_TEXTO) + "\n\n" + "\n\n".join(f"===== {n.upper()} =====\n{t}" for n, t in anexos.items())
    user = (f"Data de hoje: {hoje} (use no id).\nESCOLHA: {json.dumps(escolha, ensure_ascii=False)}\n\n"
            f"===== TEXTO DA FONTE: {url} =====\n{texto_fonte}\n\n"
            + (MIDIA_API if com_midia else "Nao precisa de midia: \"midia\": null."))
    return _json_ou_reformata(_pede(MODELO_FORTE, fixo, user, effort="medium", log=log), log)


# ---------------------------------------------------------------- correção, revisão, checagem

REVISA = """Voce e o editor do reel e a checagem de fatos reprovou o roteiro abaixo. Reescreva SO o que os PROBLEMAS apontam, usando apenas o que esta no TEXTO DAS FONTES:
- Exagero ou generalizacao: reduza a frase ao alcance exato da fonte ("por precaucao", "so nos EUA", "pode", "segundo a empresa").
- Fato sem trecho literal: troque por um fato que o texto da fonte diga claramente, ou remova a afirmacao do beat.
- Mantenha o resto igual: mesmos beats, tipos, ids das falas, estilo e fontes. Gancho com no maximo 9 palavras, fala com numeros por extenso, tela com digitos.
- Ajuste meta (caption, title, description) se ela repetir o exagero.
Responda com UM objeto JSON: {"news": {...}, "meta": {...}}"""

CHECA = """Voce e checador de fatos, independente de quem escreveu o reel. Voce recebe o PACOTE (textos de tela e falas) e o TEXTO de cada fonte, ja baixado.
Para CADA beat (indice 0 a {n}), liste as afirmacoes de fato que ele faz (numeros, nomes, datas, disponibilidade, comparacoes), na tela ou na fala.
Para cada afirmacao, copie do TEXTO DA FONTE o trecho LITERAL que a sustenta: copia exata e continua, caractere por caractere, no idioma original, de 30 a 500 caracteres. Nao traduza, nao resuma, nao junte pedacos e NUNCA tire nada do meio: se a frase tiver algo no meio, copie um pedaco continuo mais curto.
Basta que QUALQUER uma das fontes sustente a afirmacao.
"problems" e so para: afirmacao sem nenhum trecho que a sustente, ou que uma fonte contradiz (numero diferente, preview tratado como lancamento geral, data errada, exagero). Na duvida sobre o fato, e problema.
A data do topo e do card final ja foi conferida contra a data do feed: NAO marque problema so porque o texto nao mostra data.
A frase final de chamada para seguir o canal nao e afirmacao de fato.
Todo beat precisa de pelo menos uma claim. Responda com UM objeto JSON:
{{"claims": [{{"beat": 0, "claim": "...", "url": "<a url da fonte>", "quote": "<trecho literal>"}}], "problems": ["beat X: ..."]}}"""


def _fontes(textos):
    return "\n\n".join(f"===== FONTE: {url} =====\n{txt}" for url, txt in textos.items())


def corrigir(types_ts, news, meta, erros, log=_log):
    system = [{"type": "text", "text": "Voce corrige pacotes de reel reprovados pela validacao automatica, sem mudar os fatos.\n\n"
               "===== TYPES.TS =====\n" + types_ts, "cache_control": {"type": "ephemeral"}}]
    user = ("O pacote abaixo foi reprovado:\n" + "\n".join(f"- {e}" for e in erros)
            + "\n\nCorrija SO esses problemas, sem mudar os fatos. Responda com UM objeto JSON: {\"news\": {...}, \"meta\": {...}}\n\n"
            + json.dumps({"news": news, "meta": meta}, ensure_ascii=False))
    return _json_ou_reformata(_pede(MODELO_BARATO, system, user, effort="medium", log=log), log)


def revisar(news, meta, textos, problemas, log=_log):
    user = ("PROBLEMAS DA CHECAGEM:\n" + "\n".join(f"- {p}" for p in problemas)
            + "\n\nROTEIRO:\n" + json.dumps({"news": news, "meta": meta}, ensure_ascii=False) + "\n\n" + _fontes(textos))
    return _json_ou_reformata(_pede(MODELO_FORTE, [{"type": "text", "text": REVISA}], user, effort="medium", log=log), log)


def checar(news, textos, log=_log):
    system = [{"type": "text", "text": CHECA.format(n=len(news["beats"]) - 1)}]
    user = "PACOTE:\n" + json.dumps(news, ensure_ascii=False) + "\n\n" + _fontes(textos)
    return _json_ou_reformata(_pede(MODELO_BARATO, system, user, effort="medium", log=log), log)


def reparar(news, textos, rep, falhas, log=_log):
    system = [{"type": "text", "text": CHECA.format(n=len(news["beats"]) - 1)}]
    lista = "\n".join(f'- beat {c.get("beat")} ({c.get("url")}): "{c.get("quote", "")}"' for c in falhas)
    user = ("PACOTE:\n" + json.dumps(news, ensure_ascii=False) + "\n\n" + _fontes(textos)
            + "\n\nSua checagem anterior:\n" + json.dumps(rep, ensure_ascii=False)
            + "\n\nEstes trechos NAO estao literalmente no texto da fonte (o script conferiu caractere por caractere):\n" + lista
            + "\nTroque cada um por um pedaco CONTINUO e mais curto do mesmo texto. Se nenhum pedaco sustentar a afirmacao, "
              "apague a claim e registre em \"problems\". Devolva a checagem COMPLETA no mesmo formato JSON.")
    return _json_ou_reformata(_pede(MODELO_BARATO, system, user, effort="medium", log=log), log)
