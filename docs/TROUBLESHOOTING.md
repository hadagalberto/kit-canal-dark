# Troubleshooting

Cada linha de log vem com o robô da estação na frente (`[Bento]`, `[Ester]`, `[Caco]`, `[Íris]`, `[Vavá]`, `[Mila]`, `[Paco]`) e o agendador assina `[Tito]`. Os nomes estão em [GLOSSARIO.md](GLOSSARIO.md).

Primeiro passo de qualquer problema:

```bash
docker compose ps
```

```bash
docker compose logs --tail 100 agendador painel
```

O histórico das rodadas fica em `/dados/<canal>/rodadas.jsonl`:

```bash
docker compose exec painel tail -5 /dados/exemplo/rodadas.jsonl
```

## Instalação

| Sintoma | Causa | Como resolver |
| --- | --- | --- |
| `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine` | Docker Desktop fechado | Abra o Docker Desktop e espere "Engine running" |
| `WSL 2 installation is incomplete` | WSL desatualizado | No PowerShell como administrador: `wsl --update`, depois reinicie |
| Build para em `npm ci` ou `remotion browser ensure` | Internet instável ou proxy da empresa | Rode `docker compose build` de novo. Ele continua do cache |
| `port is already allocated` na 8787 | Outro programa na porta | `PAINEL_PORTA=8788` no `.env` e `docker compose up -d` |
| Script `.sh` com `\r` ou `bad interpreter` | Git converteu as quebras de linha para CRLF | O `.gitattributes` força LF. Clone de novo, ou rode `git config core.autocrlf false` e faça um checkout limpo |

## Render

| Sintoma | Causa | Como resolver |
| --- | --- | --- |
| Render muito lento (mais de 10 min) | CPU fraca ou WSL com poucos núcleos | Suba `processors` no `.wslconfig` e `LIMITE_CPUS`/`RENDER_CONCURRENCY` no `.env`. Estilos com vidro e filtros são os mais pesados |
| `Target closed`, `Page crashed` ou Chrome morre | Pouca memória ou `/dev/shm` pequeno | O compose já usa `shm_size: 1gb`. Suba `LIMITE_MEMORIA` e o `memory` do `.wslconfig` |
| `MP4 fora do padrão` | O ffprobe reprovou o arquivo | Veja o log do render acima da linha. Quase sempre é render interrompido |
| `duracao fora do limite` | A narração passou de 45 s ou ficou abaixo de 15 s | O pacote tem falas demais. A validação pede 350 a 520 caracteres falados |
| Fontes erradas no vídeo | O render baixa as fontes do Google na hora | Precisa de internet no container. Teste `docker compose run --rm --entrypoint curl worker -I https://fonts.gstatic.com` |
| `estilo desconhecido` | O nome não bate com uma pasta de `video/src/styles` | Use o nome da pasta, em minúsculas e sem acento |

## Pipeline

| Sintoma (no log ou no painel) | Significado | O que fazer |
| --- | --- | --- |
| `outra rodada em andamento, saindo` | O lock está preso por uma rodada viva | Normal. Espere a rodada terminar. Se nenhuma estiver rodando, `docker compose restart agendador` |
| `MOTOR=api precisa de ANTHROPIC_API_KEY` | Falta a chave | Preencha no `.env` ou volte para `MOTOR=exemplo` |
| `OpenRouter 401` / `402` | Chave errada / sem saldo no OpenRouter | Confira a chave e os créditos em openrouter.ai/settings |
| `OpenRouter 400 ... model` | Id do modelo errado | Copie o id exato de openrouter.ai/models para `LLM_MODELO_FORTE`/`LLM_MODELO_BARATO` |
| `nenhum candidato com link em dominio aceito` | No OpenRouter a matéria do candidato vira a fonte; os candidatos eram de sites `so_pauta` ou fora da lista | Inclua feeds de sites que estão em `dominios` |
| `ELEVENLABS_VOICE_ID vazio` | Falta o id da voz | Copie o id na Voice Library da ElevenLabs |
| `configuração incompleta: ...` | Falta chave de LLM, `ELEVENLABS_API_KEY` ou a voz do canal. A rodada parou antes de gastar | Preencha o que a mensagem diz no `.env` ou na ficha (`voice_id`) e rode `docker compose up -d` |
| `voz falhou: os créditos do plano da ElevenLabs acabaram` | Plano sem créditos | Renove ou suba o plano. O saldo aparece na Caixa |
| `voz falhou: o voice_id ... não existe nesta conta` | Id da voz errado, ou voz de outra conta | Copie o Voice ID de novo na ElevenLabs e corrija a ficha (Editar ficha) ou o `.env` |
| `voz falhou: ELEVENLABS_API_KEY recusada` | Chave errada ou sem a permissão Text to Speech | Crie a chave de novo com Text to Speech ligado |
| Caixa: "Saldo indisponível: HTTP 401 (a chave precisa da permissão user_read)" | A chave da ElevenLabs não pode ler a conta | Edite a chave e ligue User → Read. A voz funciona mesmo sem isso |
| Telegram não avisa | Falta `TELEGRAM_BOT_TOKEN` ou chat, ou o bot nunca recebeu mensagem sua | Mande uma mensagem ao bot (ou adicione-o ao grupo) e confira o chat id. Erros de envio aparecem no log como `telegram falhou` |
| Editar ficha: "só dá para editar canais criados pelo painel" | Tentou editar o canal `exemplo`, que é a ficha-modelo do kit | Crie o seu canal em + Novo canal |
| `pauta vazia` | Os feeds não trouxeram nada novo em 36 h, ou tudo já está no banco | Confira os feeds com `--until pauta`. Feed quebrado aparece em `feeds com falha` |
| `[Caco] descarte na trava de checagem` | Alguma cena ficou sem trecho literal da fonte | Funcionou como deveria. Os detalhes estão em `/dados/<canal>/work/<rodada>/checagem/checagem.json` |
| `[Ester] descarte na trava de fonte` | Fonte fora da lista do canal, ou notícia repetida (já está no arquivo) | Se a fonte é boa, inclua o domínio em `dominios` na ficha do canal |
| `nao consegui abrir a fonte` | O site bloqueia robôs ou tem paywall | Ponha o domínio em `so_pauta`: ele continua na pauta, mas não serve como fonte |
| `teto diário de LLM atingido` | O gasto do dia passou de `llm_usd_dia` | Suba o valor no `pipeline.json` do canal, se quiser |
| `nenhuma rede livre` | Canal liberado para publicar com `"redes"` vazio na ficha, rede pausada ou teto do dia | Veja `*_paused` e `*_max_per_day` no `pipeline.json` |
| Painel com "Tito (agendador) fora do ar" | O Tito não deu sinal em 60 s | `docker compose logs agendador`; `docker compose up -d` |

Editar o `pipeline.json` do canal:

```bash
docker compose exec painel sh -c "cat /dados/exemplo/pipeline.json"
```

```bash
docker compose cp painel:/dados/exemplo/pipeline.json pipeline.json
```

Edite o arquivo no seu editor e devolva:

```bash
docker compose cp pipeline.json painel:/dados/exemplo/pipeline.json
```

## Publicação

| Erro | Significado | O que fazer |
| --- | --- | --- |
| `login_required: ...` | Sem login ou token vencido | Refaça o login da rede (`docs/curso/07-publicacao.md`) e ponha `"<x>_paused": false` |
| `challenge: ...` | O Instagram pediu confirmação | Confirme no app do celular. Espere pelo menos 1 hora antes de tentar o login de novo |
| `blocked: ...` | Bloqueio temporário ou 3 recusas seguidas | Pare de postar nessa rede por alguns dias. Baixe o teto (`ig_max_per_day` ou a rampa) |
| `HttpError 403 ... quota` | Cota diária da API do YouTube | Espere virar o dia (horário do Pacífico) |

## Zerar tudo

Apaga o banco, os logins e o histórico (os MP4 em `saida/` ficam):

```bash
docker compose down -v
```
