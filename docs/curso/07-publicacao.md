# 07 · Paco: publicação no YouTube, Instagram e TikTok

**Objetivo:** Publicar com segurança, sem perder a conta.

## Aulas

1. YouTube (oficial): o app no Google Cloud (YouTube Data API v3, tela de permissão, "App para computador", publicar o app para o login não vencer em 7 dias) e a autorização de cada canal com CANAL=<canal>. Passo a passo no README, "Conectar as contas"
2. Instagram (não oficial, instagrapi): riscos (termos, bloqueio), INSTALAR_INSTAGRAM=1, login único por canal (pergunta usuário, senha e proxy; a senha não é gravada), sessão presa ao IP, aquecimento da conta com a rampa
3. Conferir o login sem postar (verificar) e um login por canal em /dados/segredos/<canal>/
4. Alternativa oficial do Instagram: Graph API da Meta (conta profissional + app aprovado)
5. TikTok: por que está fora (API oficial só publica privado sem auditoria)
6. Tetos por dia, rampa de aquecimento, pausa automática em challenge/login/bloqueio
7. As duas chaves: trava geral DRY_RUN no .env e "publicar" + "redes" na ficha do canal

## Exercício

Autorizar o YouTube e publicar 1 vídeo como não listado (YOUTUBE_PRIVACIDADE=unlisted).

## Arquivos do kit

- `publicadores/`
- `pipeline/publicar.py`

## Roteiro da aula

_A escrever._
