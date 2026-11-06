# Estilos de reel

O kit vem com **um estilo de exemplo**, o `vidro`. Os outros ficam de fora de propósito: se todo mundo que usa o kit publicar com o mesmo visual, os canais ficam iguais e a plataforma trata como conteúdo repetido. Use o `vidro` para entender a estrutura e crie o visual do seu canal a partir de `DESIGN-TEMPLATE.md`.

Todo estilo lê a mesma notícia (um JSON em `news/`), com a voz medida e a marca do pacote (`news.brand`; sem ela, `src/brand.json`). Muda só o design. A duração sai da voz, então cada notícia tem a sua.

| Estilo | id | Sensação | Documento |
| --- | --- | --- | --- |
| 3D vidro | `vidro` | Cartões de vidro flutuando em profundidade, tom de keynote. | [DESIGN](vidro/DESIGN.md) |

Para ver um estilo, gere stills: `node scripts/stills.mjs <estilo> <newsId>` (dentro do container, em /app/video).

## Criar o seu estilo

1. Copie a pasta `vidro/` para `src/styles/<seu-id>/` e `scripts/cues/vidro.mjs` para `scripts/cues/<seu-id>.mjs`.
2. Troque o nome do componente em `entry.tsx` (`Estilo-<SeuId>`) e registre o estilo em `src/Root.tsx`.
3. Redesenhe `Reel.tsx`: paleta, fontes, layout de cada tipo de cena, transições e efeitos de som. Escreva o `DESIGN.md` seguindo `DESIGN-TEMPLATE.md`.
4. Ponha o id em `"estilos"` na ficha do canal e rode `docker compose run --rm worker --exemplo --estilo <seu-id>`.

## Como um vídeo nasce

```
news/<id>.json            pacote da notícia (escrito pelo pipeline)
   │  node scripts/voice.mjs <id>          voz no Eleven v4, uma fala por beat
   ▼
public/filmes/<id>/voice/*.mp3
   │  node scripts/render-style.mjs <estilo> <id>
   │    1. scripts/story.mjs     valida, mede a voz, calcula fases e eventos
   │    2. scripts/make-audio.mjs <estilo> --story <id>   trilha + efeitos
   │    3. remotion render src/styles/<estilo>/entry.tsx
   │    4. ffprobe               confere 1080×1920, 30 fps, h264 + aac
   ▼
out/filmes/<id>/<estilo>.mp4
```

## Base comum

- **`src/news/types.ts`:** formato da notícia e regras de escrita. Sete tipos de beat: `hero`, `stat`, `compare`, `bars`, `list`, `statement`, `end`. Um beat por fala.
- **`scripts/story.mjs`:** gera `public/filmes/<id>/story.json`, com a notícia, a marca e `timing`:
  - `lines`: início e fim de cada fala, medidos.
  - `beats[].phases[].marks`: momentos de cada fase (quando o título bate, quando o preço é riscado, quando a contagem termina).
  - `events`: cortes, impactos, riscos, tiques, pops e sting, derivados dos marks. Imagem e som usam a mesma fonte, então não saem do compasso.
- **`src/news/story.tsx`:** `StorySound` (voz, trilha e efeitos do estilo), `phasesOf`, `currentAt`, `mark`, `fit`/`glyphs` (tamanho de fonte que cabe), `defaultStory` e `storyMetadata` (duração da composição a partir da história).
- **`src/brand.json`:** marca padrão (nome, handle, marca curta e frase do topo). Na Fábrica, a marca vem da ficha do canal, gravada no pacote (`news.brand`).
- **Som por estilo:** `scripts/cues/<id>.mjs` exporta `(sounds, story) => [{ frame, sound, gain }]`, usando só `story.timing.events`. Sons disponíveis: `click`, `toggle`, `notify`, `check`, `whoosh`, `lid`, `stamp`, `key`, `pop`, `rise`, `sting`, `open`, `tick`.
- **`src/styles/<id>/entry.tsx`:** entrada de render só com aquele estilo, com `defaultProps` e `calculateMetadata`. Um estilo vizinho quebrado não derruba o render. Cada um também entra em `src/Root.tsx` (`Estilo-<Nome>`) para o Studio.
- **`src/styles/DESIGN-TEMPLATE.md`:** seções obrigatórias do `DESIGN.md` de cada estilo.

## Regras

- Nada da notícia no código do estilo. Todo texto, número e data vem da `story`; a marca vem de `story.brand`.
- Só fatos com fonte (`sources` do JSON). Nada de número, data ou nome de produto fora da notícia.
- Sem screenshot e sem grafismo de emissora. Logo da empresa ou do produto da notícia e foto (oficial ou de IA, com crédito) entram só pelo campo `media` do beat, seguindo [MEDIA-SPEC.md](MEDIA-SPEC.md). Sem `media`, o estilo renderiza exatamente como antes.
- Não citar roteamento de modelo.
- Animação só por frame do Remotion (`useCurrentFrame`, `interpolate`, `spring`). Sem `transition` CSS, sem `@keyframes`, sem `Math.random` (use `random(seed)`).
- Safe zone:
  - 60 px nas laterais.
  - Nada essencial abaixo de y=1700 (UI do Instagram).
  - Nada essencial acima de y=90.
- A frase na tela dá o golpe. Ela não transcreve a narração.

## Render

```bash
# dentro do container: docker compose run --rm --entrypoint bash worker
cd /app/video
node scripts/voice.mjs <id>                      # só quando a notícia é nova ou a fala mudou
node scripts/render-style.mjs <estilo> <id>      # gera out/filmes/<id>/<estilo>.mp4
node scripts/render-style.mjs <estilo> <id> --frames=0-90   # trecho rápido para conferir
```

Notícia de teste: a do modo exemplo (`docker compose run --rm worker --exemplo --estilo <id>`). Antes de usar um estilo novo, teste também uma notícia cheia de números e uma com mídia (logo e foto).
