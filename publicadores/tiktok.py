"""TikTok: fora do kit por enquanto.

No sistema original o TikTok ia por uma ferramenta não oficial de upload pela web, e desde 12 out 2026 todo
upload passou a ser recusado ("Invalid parameters"). A API oficial (Content Posting API) só publica como
privado até o app passar por uma auditoria do TikTok.

Para ligar: implemente publicar() com a API oficial depois da auditoria, ou com um serviço que já tenha app
auditado. O contrato é o mesmo dos outros publicadores (veja publicadores/youtube.py).
"""


def publicar(mp4, meta, dry):
    return {"ok": False, "error": "tiktok sem publicador no kit (veja publicadores/tiktok.py)"}
