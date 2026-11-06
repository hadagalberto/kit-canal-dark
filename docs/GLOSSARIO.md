# Glossário da Fábrica

Um nome para cada coisa, igual no painel, nos logs, nas docs e no curso. Quando o nome no arquivo ou no código é outro (por herança técnica), ele aparece na coluna **No código**. Em caso de dúvida, este arquivo vale.

## Os robôs

Cada estação da rodada tem um robô. O apelido começa com a mesma letra da função, para decorar fácil. Nos logs, a linha vem com o apelido na frente: `[Caco] beat 3: trecho nao esta na pagina` quer dizer que a checagem reprovou a cena 3.

| # | Robô | Função | Estação (no código) | Onde mora |
| --- | --- | --- | --- | --- |
| 1 | **Bento** | busca as notícias | `pauta` | `pipeline/pauta.py` |
| 2 | **Ester** | escreve o roteiro | `apuracao` | `pipeline/apuracao.py`, `pipeline/llm.py` |
| 3 | **Caco** | confere os fatos | `checagem` | `pipeline/checagem.py` |
| 4 | **Íris** | acha as imagens | `midia` | `pipeline/midia.py` |
| 5 | **Vavá** | grava a voz | `narracao` | `pipeline/video.py`, `video/scripts/voice.mjs` |
| 6 | **Mila** | monta o vídeo | `render` | `pipeline/video.py`, `video/` (Remotion) |
| 7 | **Paco** | posta nas redes | `publicacao` | `pipeline/publicar.py`, `publicadores/` |
| — | **Tito** | cuida do turno | agendador | `agendador/agendador.py` |

Os apelidos e as funções ficam num lugar só: `pipeline/robos.py`. A chave da estação (`pauta`, `apuracao`...) está gravada nos dados e não muda.

## As coisas

| Termo | O que é | No código / nos arquivos |
| --- | --- | --- |
| **Fábrica** | O sistema inteiro: robôs, Tito e painel | este repositório |
| **Painel** | A página da Fábrica, em `http://127.0.0.1:8787` | `painel/` |
| **Canal** | Uma marca publicando reels de um nicho | id do canal, pasta `/dados/<canal>` |
| **Ficha do canal** | Configuração do canal: marca, assunto, feeds, fontes aceitas, voz, estilos, redes, turno | `canais/<id>.json` (modelo: `exemplo`) e `/dados/canais/<id>.json` (criados no painel); no código, "perfil" |
| **Turno** | Os horários em que o Tito chama o canal sozinho (formato cron). Sem turno, o canal só roda pelo botão | campo `"agenda"` da ficha |
| **Rodada** | Uma passagem pelas 7 estações, da busca da notícia ao vídeo | `pipeline/rodada.py`, `rodadas.jsonl` |
| **Estação** | Cada etapa da rodada; uma mesa com um robô no painel | `ETAPAS` / `ESTACOES` |
| **Candidato** | Uma manchete que o Bento achou nos feeds | `candidatos.json` |
| **Pacote** | O roteiro estruturado da notícia: cenas, falas, legendas, fontes, estilo | `news/<id>.json` (formato em `video/src/news/types.ts`) |
| **Cena** | Cada bloco do vídeo: uma fala, uma legenda, um visual | `beat` / `beats` |
| **Legenda das redes** | Texto, título e tags que vão com o vídeo nas redes | `meta.json` |
| **Estilo** | O visual do vídeo; o kit traz só o `vidro`, e cada canal cria o seu | pasta `video/src/styles/<estilo>` |
| **Fonte** | Página de onde sai cada fato; precisa estar na lista de fontes aceitas da ficha | `sources`, `dominios` |
| **Travas** | As 4 regras que impedem a publicação: trecho literal da fonte (Caco), fonte aceita, vídeo íntegro (ffprobe), notícia inédita (arquivo) | `checagem.py`, `apuracao.py`, `render-style.mjs`, `banco.py` |
| **Descarte** | Notícia que caiu numa trava, registrada com o motivo para não voltar | status `descartada:<trava>` no arquivo |
| **Arquivo** | Registro de tudo que já saiu ou foi descartado; é a trava contra repetição | `published.json` (`pipeline/banco.py`) |
| **Ensaio** | Rodada que faz o vídeo inteiro e não publica. Acontece com a trava geral fechada ou com a ficha sem permissão | `DRY_RUN=1` no `.env` (trava geral) ou `"publicar": false` na ficha; resultado `dry-run` |
| **Modo exemplo** | Ensaio sem chave nenhuma, com notícia e voz prontas | `MOTOR=exemplo`, `--exemplo` |
| **Teto** | Limite de posts por dia em cada rede (com rampa para conta nova) | `*_max_per_day`, `ramp` no `pipeline.json` |
| **Aviso** | Mensagem no Telegram sobre a rodada: publicado, ensaio, descarte, rede pausada, teto, erro. Sempre no formato "ícone canal · evento" | `pipeline/avisos.py` |
| **Caixa** | Saldos dos fornecedores e gastos da Fábrica | bloco do painel, `painel/caixa.py`, `costs.jsonl` |
| **Saída** | Pasta do Windows onde ficam os MP4 prontos | `./saida` (`/saida` no container) |
| **Dados** | O volume Docker com arquivo, fichas criadas, voz, rascunhos e logins | volume `dados` (`/dados`) |

## Resultados de uma rodada

| No painel | Quer dizer | No arquivo (`rodadas.jsonl`) |
| --- | --- | --- |
| Publicado | Saiu em pelo menos uma rede | `publicado` |
| Ensaio | MP4 pronto, nada publicado | `dry-run` |
| Descarte | Caiu numa trava | `descartado` |
| Pulou | Não havia notícia boa (ou parou de propósito) | `pulou` |
| Teto | Todas as redes no limite do dia | `teto` |
| Erro | Algo quebrou; o motivo vem no log | `erro` |
