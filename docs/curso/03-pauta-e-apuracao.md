# 03 · Bento e Ester: pauta e roteiro com LLM

**Objetivo:** Entender como o LLM escolhe a notícia e escreve o roteiro em JSON.

## Aulas

1. O formato do pacote (video/src/news/types.ts): beats, falas, legendas
2. Prompt de apuração: regra de pauta, gancho, não generalizar
3. web_search e web_fetch do lado do servidor, cache de prompt
4. Validação por código: português, tamanho da fala, dígitos e siglas
5. Custo por rodada e o teto llm_usd_dia
6. Provedor: Anthropic direta (busca web do servidor) ou OpenRouter (apuração em dois passos: o modelo escolhe, o script baixa a matéria, o modelo escreve)

## Exercício

Rodar com MOTOR=api, ainda em ensaio (DRY_RUN=1), e ler o news.json da pasta work/.

## Arquivos do kit

- `pipeline/apuracao.py`
- `pipeline/llm.py`
- `video/src/news/types.ts`

## Roteiro da aula

_A escrever._
