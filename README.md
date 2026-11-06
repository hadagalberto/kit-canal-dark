# Canal Dark Kit

Uma **fábrica de reels e shorts de notícia, sem rosto**, rodando inteira no seu PC com Docker. Ela acha a notícia, escreve o roteiro, confere os fatos, grava a voz, monta o vídeo e posta, num canal ou em vários.

```
feeds RSS ─► Bento ─► Ester ─► Caco ─► Íris ─► Vavá ─► Mila ─► Paco ─► YouTube / Instagram
             busca    escreve  confere  acha     grava   monta   posta
             notícias roteiro  os fatos imagens  a voz   o vídeo nas redes

             Tito chama cada canal no turno dele · o painel mostra tudo ao vivo
```

- **Sete robôs**, um por estação da rodada, e o **Tito**, que cuida dos horários. Os nomes estão no [glossário](docs/GLOSSARIO.md).
- **Vários canais no mesmo PC.** Cada canal tem a própria ficha: marca, assunto, feeds, voz, visual, redes e horários.
- **Travas automáticas:** só publica o que tiver um trecho literal da fonte confirmando cada fato. Notícia que não passa vira descarte e não vai ao ar.
- **Painel "Fábrica de reels"** em `http://127.0.0.1:8787`: pixel art, um andar por canal, rodada ao vivo, saldos e gastos.
- **Começa seguro:** sem chave nenhuma, no modo exemplo e em ensaio (gera o vídeo e não posta).

Vai operar o kit com um agente de código (Claude Code, Codex, OpenCode)? As regras dele estão em [AGENTS.md](AGENTS.md).

---

## Sumário

1. [O que você precisa](#1-o-que-você-precisa)
2. [Instalação (Windows)](#2-instalação-windows)
3. [Primeiro vídeo, sem chave](#3-primeiro-vídeo-sem-chave)
4. [O painel](#4-o-painel)
5. [Criar o seu canal](#5-criar-o-seu-canal)
6. [Conectar as contas](#6-conectar-as-contas)
7. [Do ensaio à publicação](#7-do-ensaio-à-publicação)
8. [Turnos e operação diária](#8-turnos-e-operação-diária)
9. [Vários canais](#9-vários-canais)
10. [Avisos no Telegram](#10-avisos-no-telegram)
11. [Quanto custa](#11-quanto-custa)
12. [Comandos](#12-comandos)
13. [Onde fica cada coisa](#13-onde-fica-cada-coisa)
14. [As travas](#14-as-travas)
15. [Regras das plataformas e segurança](#15-regras-das-plataformas-e-segurança)
16. [Ajuda](#16-ajuda)

---

## 1. O que você precisa

| Item | Para quê | Obrigatório? |
| --- | --- | --- |
| PC com Windows 10/11, 8 GB de RAM (16 GB é melhor), 4 núcleos, 10 GB livres | Rodar a Fábrica. O render usa CPU, não GPU | sim |
| Docker Desktop e Git | Instalar e rodar | sim |
| Conta na Anthropic **ou** no OpenRouter, com créditos | O LLM que escolhe a notícia, escreve e confere | para o canal de verdade |
| Conta na ElevenLabs, em plano pago se o canal for monetizado | A voz | para o canal de verdade |
| Canal no YouTube e um projeto no Google Cloud (grátis) | Postar Shorts | para publicar |
| Conta no Instagram | Postar Reels (API não oficial, com risco) | opcional |
| Bot no Telegram | Avisos de cada rodada | opcional |

Sem nenhuma conta, você já instala, vê o painel e gera um vídeo de exemplo.

## 2. Instalação (Windows)

**1. Programas**

1. Instale o **Docker Desktop** ([docker.com](https://www.docker.com/products/docker-desktop/)) com a opção **"Use WSL 2"** marcada. Reinicie o PC se ele pedir.
2. Instale o **Git** ([git-scm.com](https://git-scm.com/download/win)) com as opções padrão.
3. Abra o Docker Desktop e espere o ícone da baleia ficar verde ("Engine running").

**2. Memória do Docker (recomendado)**

O Docker Desktop roda dentro do WSL 2. Para o render ter memória, crie o arquivo `C:\Users\<seu-usuario>\.wslconfig` com:

```ini
[wsl2]
memory=8GB
processors=4
```

Depois rode no PowerShell e abra o Docker Desktop de novo:

```bash
wsl --shutdown
```

**3. Baixar o kit e criar o `.env`**

```bash
git clone https://github.com/hadagalberto/kit-canal-dark.git
```

```bash
cd kit-canal-dark
```

```bash
copy .env.example .env
```

No Git Bash, o último comando é `cp .env.example .env`. O `.env` guarda as configurações da máquina e as suas chaves. Ele nunca vai para o git.

**4. Subir a Fábrica**

```bash
docker compose up -d --build
```

O primeiro build leva de 5 a 10 minutos e baixa uns 2 GB (Node, Chrome, ffmpeg e Python). Os próximos levam segundos. Quando terminar, abra **http://127.0.0.1:8787**.

## 3. Primeiro vídeo, sem chave

```bash
docker compose run --rm worker --exemplo
```

Ou clique duas vezes em **▶ Rodar agora** no painel. Em um ou dois minutos aparece em `saida/` o arquivo `exemplo-<data>-vidro.mp4` (1080×1920, 30 fps), com a legenda das redes ao lado (`.json`).

O modo exemplo usa uma notícia e uma voz já prontas, então não gasta nada e nunca publica. Ele serve para ver a Fábrica funcionando antes de pôr dinheiro em API.

## 4. O painel

`http://127.0.0.1:8787`, aberto só no seu PC.

- **Caixa**, no topo:
  - saldo da ElevenLabs e do OpenRouter, lido com as chaves do `.env`;
  - saldo estimado da Anthropic (veja a [seção 11](#11-quanto-custa));
  - gasto de hoje, 7 dias e mês por canal, em US$ e R$, com os créditos de voz;
  - views e custo por mil views, quando houver estatísticas.
- **Um andar por canal**, com as 7 mesas, uma por robô. A mesa ativa pisca durante a rodada. Embaixo de cada andar: a última rodada (resultado, motivo, caminho do MP4), o histórico, os publicados do dia e os tetos de cada rede.
- **▶ Rodar agora:** pede uma rodada ao Tito. Precisa de dois cliques, e o botão diz se a rodada será ensaio ou publicação de verdade.
- **Editar ficha:** abre a ficha do canal para mudar marca, feeds, voz, turno etc. O painel valida antes de salvar.
- **+ Novo canal**, embaixo: o formulário de criação.

## 5. Criar o seu canal

O kit traz só uma ficha-modelo (`canais/exemplo.json`) e um estilo de vídeo (`vidro`), de propósito. Se todo mundo publicar com o mesmo nicho, as mesmas fontes e o mesmo visual, os canais ficam iguais. As plataformas tratam isso como conteúdo repetido, e o público também.

**Pelo painel (+ Novo canal)**

| Campo | O que é |
| --- | --- |
| Id | Nome curto do canal, em minúsculas (`futebol`, `carros-br`). Vira a pasta de dados |
| Nome no vídeo, @ e frase do topo | A marca que aparece no vídeo e no card final |
| Assunto | O nicho, por extenso. Entra no prompt: "reels de notícia de …" |
| O que priorizar na pauta | Sua regra editorial: o que entra primeiro, o que evitar |
| Feeds RSS | De onde o Bento tira as manchetes. Uma por linha: `Nome \| URL` |
| Domínios aceitos como fonte | **Só sites confiáveis.** A trava de fonte descarta qualquer notícia cuja fonte esteja fora desta lista |
| Id da voz | A voz da ElevenLabs do canal. Vazio = a voz padrão do `.env` |
| Turno | Horários em que o Tito roda o canal sozinho (formato cron). Vazio = só pelo botão |
| Redes | Onde o canal posta |
| Estilos | O visual do vídeo |
| Publicar de verdade | Desmarcado = ensaio. Mesmo marcado, nada sai com `DRY_RUN=1` |

O canal nasce em ensaio e sem turno. Confira se os feeds trazem notícia, sem gastar API:

```bash
docker compose run --rm -e CANAL=<id> worker --until pauta
```

Para mudar algo depois, use **Editar ficha** no painel. A ficha fica em `/dados/canais/<id>.json`.

**O seu visual**

Crie o estilo do canal a partir do `vidro`, seguindo `video/src/styles/README.md` ("Criar o seu estilo"), e ponha o id dele em "Estilos" na ficha. Para ver o resultado sem gastar nada:

```bash
docker compose run --rm -e CANAL=<id> worker --exemplo --estilo <seu-estilo>
```

## 6. Conectar as contas

Comece pelas chaves de API. Conecte as redes só quando o ensaio estiver bom. Depois de mudar o `.env`, rode `docker compose up -d` para os containers lerem o arquivo novo.

### 6.1 LLM (no `.env`)

Escolha um provedor:

- **Anthropic (padrão):** crie a chave em [console.anthropic.com](https://console.anthropic.com) → API Keys e ponha créditos em Billing. No `.env`: `ANTHROPIC_API_KEY=...`. A apuração usa a busca e a leitura de páginas do próprio servidor da Anthropic.
- **OpenRouter:** crie a chave em [openrouter.ai](https://openrouter.ai) → Keys e ponha créditos. No `.env`: `LLM_PROVEDOR=openrouter` e `OPENROUTER_API_KEY=...`. Dá para usar qualquer modelo da lista deles em `LLM_MODELO_FORTE` e `LLM_MODELO_BARATO`. A apuração vira dois passos: o modelo escolhe a notícia, o script baixa a matéria e o modelo escreve com ela.

### 6.2 Voz: ElevenLabs (no `.env` e na ficha)

1. Em [elevenlabs.io](https://elevenlabs.io) → **Developers → API Keys**, crie uma chave com a permissão **Text to Speech**. Ligue também **User → Read** para o saldo de créditos aparecer na Caixa. Ponha em `ELEVENLABS_API_KEY`.
2. Em **Voices**, escolha uma voz em português e copie o **Voice ID**. Ponha em `ELEVENLABS_VOICE_ID`, a voz padrão. Para um canal ter voz própria, use o campo "Id da voz" da ficha.
3. `ELEVENLABS_MODELO` vem como `eleven_v4`, que entende as tags de emoção que o roteiro usa (`[excited]`, `[measured]`).

Como a voz entra na rodada:
- **Ordem:** a voz só é gerada depois que o Caco aprova a notícia. Notícia barrada antes disso (pauta, fonte, checagem) não gasta crédito de voz.
- **Créditos:** cada vídeo gasta algo como 200 a 300 créditos. O painel mostra os créditos gastos por canal, e a Caixa mostra o saldo da conta.
- **Conta compartilhada:** uma conta ElevenLabs serve todos os canais, e os créditos do plano são divididos entre eles.
- **Antes de gastar:** a rodada confere a chave e a voz logo no começo. Se faltar alguma, ela para antes de pagar o LLM.
- **Erros:** créditos acabados, voz que não existe e chave sem permissão aparecem em português no painel e no Telegram.

### 6.3 YouTube (API oficial)

**Uma vez por máquina: o "app" no Google Cloud**

1. Em [console.cloud.google.com](https://console.cloud.google.com), crie um projeto, por exemplo "fabrica-reels".
2. Em **APIs e serviços → Biblioteca**, ative a **YouTube Data API v3**.
3. Em **Tela de permissão OAuth**, escolha **Externo** e preencha nome e e-mail.
   - Em **Usuários de teste**, adicione a conta Google de cada canal.
   - Enquanto o app estiver em "Teste", o login vence a cada 7 dias. Para não vencer, clique em **Publicar app**. O Google mostra o aviso "app não verificado"; para uso próprio, é só continuar.
4. Em **Credenciais → Criar credenciais → ID do cliente OAuth**, escolha **App para computador** e baixe o JSON.
5. Renomeie o arquivo para `client_secret.json`, coloque na pasta do kit e copie para dentro da Fábrica:

```bash
docker compose exec painel mkdir -p /dados/segredos/youtube
```

```bash
docker compose cp client_secret.json painel:/dados/segredos/youtube/client_secret.json
```

Depois apague o `client_secret.json` da pasta do kit.

**Uma vez por canal: autorizar a conta**

```bash
docker compose run --rm --service-ports -e CANAL=<canal> --entrypoint python worker -m publicadores.youtube autorizar
```

1. Abra no navegador do Windows o link que aparece.
2. Entre com a conta Google **dona do canal do YouTube** desse canal e aceite.
3. O comando termina mostrando o nome do canal conectado.

Para conferir depois, sem postar nada:

```bash
docker compose run --rm -e CANAL=<canal> --entrypoint python worker -m publicadores.youtube verificar
```

Todo vídeo sobe marcado como conteúdo sintético, por causa da voz de IA. A cota de upload da API é do **projeto** do Google Cloud: canais no mesmo projeto dividem a mesma cota diária, que aparece em **APIs e serviços → Cotas**.

### 6.4 Instagram (API não oficial: leia antes)

A instagrapi entra como se fosse o app do celular, com usuário e senha. Isso **fere os termos do Instagram** e pode levar a conta a bloqueio ou banimento. Use uma conta que você aceite perder. A alternativa oficial é a Graph API da Meta (conta profissional e app aprovado), que o kit ainda não traz.

1. No `.env`, ponha `INSTALAR_INSTAGRAM=1` e rode `docker compose up -d --build`.
2. Faça o login **uma vez** por canal. O comando pergunta usuário, senha e um proxy opcional. A senha não é gravada; fica só a sessão, em `/dados/segredos/<canal>/instagram/`.

```bash
docker compose run --rm -e CANAL=<canal> --entrypoint python worker -m publicadores.instagram login
```

3. Se o Instagram pedir confirmação, aprove no app do celular e digite o código. Se der erro de limite, espere pelo menos 1 hora antes de tentar de novo: login repetido é o que mais leva bloqueio.
4. Para conferir depois:

```bash
docker compose run --rm -e CANAL=<canal> --entrypoint python worker -m publicadores.instagram verificar
```

O teto do Instagram começa em 2 posts por dia e sobe com as semanas (a rampa). Se a rede pausar por desafio ou bloqueio, o teto desce um degrau por 7 dias.

### 6.5 TikTok

Fora do kit por enquanto. A API oficial só publica como privado até o app passar por uma auditoria do TikTok. Veja `publicadores/tiktok.py`.

### 6.6 Opcionais

| Serviço | Para quê | No `.env` |
| --- | --- | --- |
| [logo.dev](https://logo.dev) | Logo da empresa da notícia no vídeo (ligue `"media_enabled": true` no `pipeline.json` do canal) | `LOGODEV_TOKEN` |
| OpenRouter | Imagem ilustrativa gerada por IA, com crédito na tela | `OPENROUTER_API_KEY`, `IMAGEM_IA_MODELO` |
| Telegram | Avisos (veja a [seção 10](#10-avisos-no-telegram)) | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |

## 7. Do ensaio à publicação

Para um canal postar de verdade, **duas chaves** precisam estar abertas:

1. `DRY_RUN=0` no `.env`. É a trava geral da máquina.
2. `"publicar": true` na ficha do canal.

Com qualquer uma fechada, a rodada é um **ensaio**: faz tudo, deixa o MP4 em `saida/` e não posta.

Caminho recomendado:

1. **Ensaio com a pauta real.** Com `MOTOR=api` no `.env` e as chaves de LLM e voz, rode algumas vezes e assista aos vídeos em `saida/`:

   ```bash
   docker compose run --rm -e CANAL=<canal> worker
   ```

2. **Conecte as redes** (seção 6) e confira cada uma com `verificar`.
3. **Primeiro post discreto.** Ponha `YOUTUBE_PRIVACIDADE=unlisted` no `.env` (o vídeo sai, mas não aparece no canal). Ponha `"publicar": true` na ficha e `DRY_RUN=0` no `.env`, rode `docker compose up -d` e clique em **Rodar agora**. O link aparece na última rodada do painel.
4. **Abra o canal.** Volte `YOUTUBE_PRIVACIDADE=public` e preencha o turno (seção 8).

**Parar tudo na hora:** volte `DRY_RUN=1` no `.env` e rode `docker compose up -d`. Para parar um canal só, desmarque `"publicar"` ou apague o turno dele em **Editar ficha**.

## 8. Turnos e operação diária

O turno é o campo `"agenda"` da ficha, no formato cron: `minuto hora dia mês dia-da-semana`, no fuso de `FUSO_HORAS`.

| Turno | Quando roda |
| --- | --- |
| `0 9,12,15,18,21 * * *` | 5 vezes por dia, de 3 em 3 horas, das 9h às 21h |
| `0 7-23 * * *` | De hora em hora, das 7h às 23h |
| `30 8,13,19 * * 1-5` | 3 vezes por dia, de segunda a sexta |
| vazio | Nunca sozinho: só pelo botão do painel |

Nem toda rodada vira vídeo. Se não houver notícia boa ou ela cair numa trava, a rodada pula ou descarta. Por isso, rodar mais vezes do que o número de posts que você quer é normal. O teto de cada rede segura o excesso.

**Rotina sugerida:** uma vez por dia, abra o painel e confira:
- os descartes e o motivo de cada um;
- o gasto na Caixa;
- se alguma rede está pausada.

Os avisos do Telegram (seção 10) cobrem o resto.

## 9. Vários canais

Um container serve todos os canais. Cada canal é uma ficha em `/dados/canais/<id>.json`, com a própria pasta de dados em `/dados/<id>/`: arquivo de notícias, custos, histórico e logins.

| Fica por canal | Fica para a máquina (dividido entre os canais) |
| --- | --- |
| Marca, assunto, regra de pauta, feeds, fontes aceitas | Chave do LLM e o teto total `LLM_USD_DIA_TOTAL` |
| Voz (`voice_id`) | Conta e créditos da ElevenLabs |
| Estilos, redes, turno, `publicar` | Trava geral `DRY_RUN` e `MOTOR` |
| Login do YouTube e do Instagram | Projeto do Google Cloud e a cota de upload dele |
| Teto de LLM do dia (`llm_usd_dia`), tetos de cada rede, pausas | O render: **uma rodada por vez no PC inteiro** |
| Chat do Telegram (`telegram_chat_id`, opcional) | O bot do Telegram |

**Quantos canais cabem:** cada rodada leva de alguns minutos (pauta, LLM, voz) a mais uns minutos de render, conforme a CPU e o estilo. Com uma rodada por vez, some os turnos de todos os canais e deixe folga. Se dois horários coincidirem, a segunda rodada espera a primeira terminar.

**Para desligar um canal:** apague o turno e desmarque `"publicar"` em **Editar ficha**. Para tirar o canal do painel, apague o arquivo da ficha:

```bash
docker compose exec painel rm /dados/canais/<id>.json
```

Isso apaga só a ficha. Os dados do canal em `/dados/<id>/` continuam lá.

## 10. Avisos no Telegram

1. Fale com o [@BotFather](https://t.me/BotFather), crie um bot e ponha o token em `TELEGRAM_BOT_TOKEN`.
2. Mande uma mensagem para o bot, ou adicione o bot a um grupo, e pegue o id do chat (o [@userinfobot](https://t.me/userinfobot) mostra o seu). Ponha em `TELEGRAM_CHAT_ID`.
3. Para mandar cada canal a um grupo diferente, ponha `"telegram_chat_id"` na ficha.

Todas as mensagens têm o mesmo formato: ícone, canal e evento na primeira linha, a notícia na segunda, os detalhes embaixo.

```
🎬 Canal Futebol · publicado
Flamengo renova com técnico até 2027
YouTube: https://youtube.com/shorts/abc
Estilo vidro · 31 s · Fonte: ge
```

| Ícone | Evento |
| --- | --- |
| 🎬 | Publicado (ou "não publicado", com o erro de cada rede) |
| 🗑️ | Descarte: qual trava e qual robô barrou, com os motivos |
| ⏸️ | Rede pausada (desafio, login ou bloqueio) e como religar |
| 💸 | Teto de gasto do dia atingido (um aviso por dia) |
| 🚨 | Erro na rodada: em qual estação e onde ver o log |
| 🧪 | Ensaio pronto, com o caminho do MP4 (só com `TELEGRAM_AVISAR_ENSAIO=1`) |

## 11. Quanto custa

Valores aproximados, medidos no sistema que deu origem ao kit. Confira sempre a tabela de preços atual de cada fornecedor.

| Item | Custo |
| --- | --- |
| LLM por rodada, com Claude Sonnet na apuração e Haiku na checagem | ~US$ 0,16 a 0,25. Rodada descartada também gasta |
| LLM por rodada, com um modelo barato no OpenRouter | uma fração disso. Teste a qualidade da pauta antes de trocar |
| Voz por vídeo | ~200 a 300 créditos da ElevenLabs |
| Imagem de IA (opcional) | ~US$ 0,03 por imagem, com teto diário `ai_images_per_day` |
| Docker, Remotion, painel | grátis (veja a licença do Remotion na seção 15) |

**Freios de gasto:**
- `llm_usd_dia` no `pipeline.json` de cada canal (padrão: US$ 5);
- `LLM_USD_DIA_TOTAL` no `.env`, para a soma de todos os canais;
- o teto diário de imagens de IA.

Passou do teto, as rodadas do dia pulam e o Telegram avisa.

**Saldo da Anthropic na Caixa:** a API não informa saldo. Para ter uma estimativa, ponha no `pipeline.json` do primeiro canal:

```json
"custos": {"anthropic_saldo": {"usd": 100, "em": "2026-11-05"}}
```

Use o saldo e a data do console. O painel desconta o que os canais gastaram desde esse dia.

## 12. Comandos

Rode na pasta do kit. `-e CANAL=<id>` escolhe o canal; sem ele, vale o primeiro.

| Comando | O que faz |
| --- | --- |
| `docker compose up -d --build` | Sobe ou atualiza a Fábrica. Mudou código ou `.env`? Rode de novo |
| `docker compose ps` | Mostra o que está de pé |
| `docker compose logs -f agendador` | Acompanha as rodadas ao vivo. Cada linha traz o robô: `[Caco] ...` |
| `docker compose run --rm worker --exemplo` | Vídeo de exemplo, sem chave e sem custo |
| `docker compose run --rm -e CANAL=<id> worker --until pauta` | Mostra os candidatos dos feeds, sem custo |
| `docker compose run --rm -e CANAL=<id> worker` | Rodada completa (ensaio ou publicação, conforme as duas chaves) |
| `docker compose run --rm -e CANAL=<id> worker --tema "assunto"` | Rodada com pauta pedida, no lugar dos feeds |
| `docker compose run --rm -e CANAL=<id> worker --estilo <estilo>` | Força um estilo |
| `docker compose run --rm --entrypoint python worker -m testes.travas` | Testes das travas, offline |
| `docker compose down` | Para tudo. Os dados ficam no volume |

## 13. Onde fica cada coisa

```
docker compose
 ├─ agendador   Tito: chama cada canal no turno dele
 ├─ painel      http://127.0.0.1:8787
 └─ worker      rodada avulsa (docker compose run)

.env                         configurações da máquina e chaves (fora do git)
saida/                       os MP4 prontos + legenda das redes (.json)
volume "dados" (/dados)
 ├─ canais/<id>.json         ficha de cada canal
 ├─ <id>/published.json      o arquivo: tudo que saiu ou foi descartado
 ├─ <id>/pipeline.json       tetos, pausas das redes, rampa, teto de LLM
 ├─ <id>/rodadas.jsonl       histórico das rodadas (o painel lê)
 ├─ <id>/costs.jsonl         custo de cada rodada
 ├─ <id>/work/<rodada>/      rascunhos: candidatos, roteiro, checagem
 ├─ segredos/                client_secret do Google e logins de cada canal
 └─ estado.json              rodada em andamento
```

| Pasta do kit | O que tem |
| --- | --- |
| `pipeline/` | As estações em Python. `robos.py` tem os nomes; `rodada.py` orquestra |
| `publicadores/` | Um arquivo por rede |
| `video/` | Projeto Remotion: estilos, validação do roteiro, trilha e efeitos, render |
| `canais/` | A ficha-modelo |
| `painel/` | O painel e a Caixa |
| `agendador/` | O Tito |
| `docs/` | [Glossário](docs/GLOSSARIO.md), [problemas e soluções](docs/TROUBLESHOOTING.md) e o [curso](docs/curso/README.md) |

## 14. As travas

Não há aprovação humana. Um vídeo só sai se passar em todas as travas:

1. **Checagem literal (Caco):** cada cena precisa de um trecho da fonte que sustente o que o vídeo diz. O código confere esse trecho, caractere por caractere, na página que ele mesmo baixou.
2. **Fonte confiável:** toda fonte está na lista de domínios aceitos da ficha.
3. **Vídeo íntegro:** o MP4 passa no ffprobe (1080×1920, 30 fps, h264 e aac) e dura entre 15 e 45 s.
4. **Sem repetição:** a notícia não está no arquivo do canal, por URL nem por título parecido.

Se falhar alguma, a notícia vira **descarte**, fica registrada com o motivo e a rodada termina. Nunca sai nada "meio certo". Não afrouxe uma trava para "destravar" um vídeo: elas são o que permite rodar sem ninguém olhando.

## 15. Regras das plataformas e segurança

- **Conteúdo de IA:** o YouTube recebe todo vídeo marcado como conteúdo sintético. Mantenha o rótulo de IA nas outras redes também.
- **ElevenLabs:** confira nos termos do seu plano se o uso comercial é permitido. Canal monetizado pede plano pago.
- **Instagram pela instagrapi:** fere os termos do Instagram e pode levar a conta a bloqueio.
- **Imagens:** só logo da empresa da notícia, foto da sala de imprensa oficial ou imagem de IA com crédito na tela. Nada de screenshot ou foto de veículo de imprensa.
- **Remotion:** gratuito para pessoa física e empresa de até 3 pessoas. Acima disso, a empresa precisa de licença.
- **Seus dados:**
  - o `.env`, a pasta `segredos/` e os arquivos `client_secret*.json` nunca vão para o git;
  - a senha do Instagram não é gravada em lugar nenhum;
  - o painel só abre em `127.0.0.1`, e as ações dele exigem um cabeçalho próprio e o endereço local, contra sites maliciosos.

## 16. Ajuda

- **Algo deu errado:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) explica cada mensagem de log e de painel.
- **Um nome que você não entendeu:** [docs/GLOSSARIO.md](docs/GLOSSARIO.md).
- **Mudar ou operar com um agente de código:** [AGENTS.md](AGENTS.md).
- **Aprender em ordem:** [docs/curso/](docs/curso/README.md).

Licença: [MIT](LICENSE). O Remotion, usado no vídeo, tem licença própria (seção 15).
