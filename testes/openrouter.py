"""Teste do provedor OpenRouter contra um servidor falso (sem chave, sem internet):
    docker compose run --rm --entrypoint python worker -m testes.openrouter

Confere o caminho inteiro do LLM_PROVEDOR=openrouter: escolha -> download da matéria pelo script ->
escrita do pacote -> checagem com trecho literal, mais cabeçalhos, id do modelo e soma do custo.
"""
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PEDIDOS = []
MATERIA = ("<html><body><article><h1>Empresa X lança o Produto Y</h1>"
           + "<p>A Empresa X anunciou nesta segunda o Produto Y, que custa R$ 99 por mês no Brasil.</p>" * 30
           + "</article></body></html>")


class Falso(BaseHTTPRequestHandler):
    def do_GET(self):
        corpo = MATERIA.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        PEDIDOS.append({"auth": self.headers.get("Authorization"), **req})
        system = req["messages"][0]["content"]
        if "Escolha a pauta" in system:
            resp = {"escolha": {"link": LINK, "manchete": "Empresa X lança o Produto Y"}}
        elif "checador de fatos" in system:
            resp = {"claims": [{"beat": 0, "claim": "preço", "url": LINK,
                                "quote": "anunciou nesta segunda o Produto Y, que custa R$ 99 por mês no Brasil"}],
                    "problems": []}
        else:
            resp = {"news": {"id": "2026-11-02-produto-y", "style": "vidro", "beats": [], "sources": [{"label": "X", "url": LINK}]},
                    "meta": {"title": "Produto Y"}, "midia": None}
        corpo = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "```json\n" + json.dumps(resp) + "\n```"}}],
                            "usage": {"cost": 0.0123}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), Falso)
PORTA = srv.server_address[1]
LINK = f"http://127.0.0.1:{PORTA}/materia"
threading.Thread(target=srv.serve_forever, daemon=True).start()

os.environ.update({"LLM_PROVEDOR": "openrouter", "OPENROUTER_API_KEY": "chave-de-teste",
                   "OPENROUTER_BASE_URL": f"http://127.0.0.1:{PORTA}", "LLM_MODELO_FORTE": "", "LLM_MODELO_BARATO": ""})

from pipeline import apuracao as ap, checagem as ck, llm  # noqa: E402  (depois do ambiente)


def checa(nome, cond):
    print(("ok   " if cond else "FALHOU ") + nome)
    assert cond, nome


perfil = json.loads(Path("/app/canais/exemplo.json").read_text(encoding="utf-8"))
perfil["dominios"] = ["127.0.0.1"]
perfil["so_pauta"] = []
cands = [{"title": "Empresa X lança o Produto Y", "link": LINK, "outlet": "Falso", "date": "2026-11-02 10:00"},
         {"title": "Fora da lista", "link": "https://blogqualquer.net/a", "outlet": "Outro", "date": "2026-11-02 09:00"}]

with tempfile.TemporaryDirectory() as tmp:
    wd = Path(tmp)
    ap.apuracao(wd, {"items": []}, {"media_enabled": False}, perfil, cands)
    news = json.loads((wd / "news.json").read_text())
    esc = json.loads((wd / "escolha.json").read_text())
    checa("modelos padrão do OpenRouter", llm.MODELO_FORTE == "anthropic/claude-sonnet-5.5"
          and llm.MODELO_BARATO == "anthropic/claude-haiku-5.5")
    checa("duas chamadas na apuração (escolher + escrever)", len(PEDIDOS) == 2)
    checa("chave vai no cabeçalho Bearer", PEDIDOS[0]["auth"] == "Bearer chave-de-teste")
    checa("pede o custo exato (usage.include)", PEDIDOS[0]["usage"] == {"include": True})
    checa("candidato fora da lista nem vai ao modelo", "blogqualquer" not in PEDIDOS[0]["messages"][1]["content"])
    checa("o texto da matéria baixada vai na escrita", "custa R$ 99 por mês" in PEDIDOS[1]["messages"][1]["content"])
    checa("sem ferramentas web na escrita", "tools" not in PEDIDOS[1] and "plugins" not in PEDIDOS[1])
    checa("news.json e escolha.json gravados", news["id"] == "2026-11-02-produto-y" and esc["link"] == LINK)

    news = {"sources": [{"label": "X", "url": LINK}], "beats": [{"voice": {"text": "a"}}]}
    erros, _ = ck.checagem(wd, news)
    checa("checagem pelo modelo barato e trecho literal confere", not erros and PEDIDOS[-1]["model"] == "anthropic/claude-haiku-5.5")
    checa("custo somado das 3 chamadas", abs(llm.CUSTO["llm_usd"] - 0.0369) < 1e-6)
print("openrouter ok")
