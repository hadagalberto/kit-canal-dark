"""Testes offline das travas (sem chave, sem internet):
    docker compose run --rm --entrypoint python worker -m testes.travas
"""
from pipeline.apuracao import em_portugues, travas_fonte, validate
from pipeline.checagem import confere
from pipeline.fontes import flat

URL = "https://techcrunch.com/2026/10/08/x"
NEWS = {"sources": [{"label": "TechCrunch", "url": URL}], "beats": [{}, {}]}
PAGINA = flat("<p>The agent gets its <a href='#'>own account</a>, with email, calendar and Drive.</p>")


def checa(nome, cond):
    print(("ok   " if cond else "FALHOU ") + nome)
    assert cond, nome


# (a) trecho literal: precisa estar caractere por caractere na página
p, falhas, cob = confere({"claims": [{"beat": 0, "url": URL, "quote": "The agent gets its own account, with email"}]}, NEWS, {URL: PAGINA})
checa("trecho literal com link no meio passa", cob == {0} and not falhas)
p, falhas, cob = confere({"claims": [{"beat": 0, "url": URL, "quote": "The agent gets an account for everyone"}]}, NEWS, {URL: PAGINA})
checa("trecho inventado cai", not cob and len(falhas) == 1)
p, falhas, cob = confere({"claims": [{"beat": 0, "url": "https://outro.com/a", "quote": "The agent gets its own account"}]}, NEWS, {URL: PAGINA})
checa("url fora das fontes vira problema", p and not cob)

# (b) fonte fora da lista
perfil = {"dominios": ["techcrunch.com"], "so_pauta": []}
db = {"items": []}
ident = {"titles": [], "urls": []}
checa("fonte da lista passa", travas_fonte(NEWS, db, perfil, ident) == [])
ruim = {"sources": [{"label": "blog", "url": "https://blogqualquer.net/a"}]}
checa("fonte fora da lista cai", travas_fonte(ruim, db, perfil, ident))

# (d) notícia repetida
db = {"items": [{"titles": ["Gemini ganha conta propria no Workspace"], "urls": []}]}
checa("tema repetido cai", travas_fonte(NEWS, db, perfil, {"titles": ["Gemini ganha conta propria no Workspace hoje"], "urls": []}))

# validação do pacote
checa("português passa", em_portugues("O agente ganhou uma conta no diretório da empresa, com e-mail e calendário para o time"))
checa("inglês cai", not em_portugues("The agent gets its own account and it is available for the team now"))
erros = validate({"id": "x", "style": "nada", "beats": []}, {}, ["vidro"])
checa("pacote quebrado lista vários erros", len(erros) >= 4)
print("todas as travas ok")
