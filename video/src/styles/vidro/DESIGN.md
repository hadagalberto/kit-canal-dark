# Estilo 3D vidro (`vidro`)

Cartões de vidro flutuando num espaço escuro com profundidade, e a câmera passando entre eles. Tom de keynote de lançamento, premium e calmo.


## Quando usar

Funciona melhor em lançamentos de produto, modelo novo, hardware e anúncios de empresa grande. Quando o tom é "novidade bonita", não "escândalo".

Não funciona bem em notícia urgente, polêmica ou de muitos números em sequência rápida, porque o ritmo é lento (um cartão a cada 4 a 7 s). Também sofre com muito texto: o cartão comporta pouco.

## Identidade

| Token | Valor | Uso |
| --- | --- | --- |
| fundo, centro | `#0E2A2E` | centro do gradiente radial (50% 38%) |
| fundo, meio | `#071416` | anel médio; também o texto sobre o selo verde |
| fundo, borda | `#030607` | borda do gradiente |
| `LIME` | `#D6FF3E` | número herói, selo −75%, barra do 5.5, linha quente da frase |
| `ICE` | `#8FDBFF` | cartão do Sonnet, segundo raio de luz, bokeh |
| `PAPER` | `#F4F0E6` | texto principal |
| `MUTED` | `#A39E92` | rótulos secundários, valor "antes", data |
| risco | `#FF5A36` | risco do preço antigo |
| vidro | gradiente 145°: `rgba(255,255,255,0.13)` → `0.03` → acento a 0.06 | corpo do cartão |
| borda do vidro | `1.5px solid rgba(255,255,255,0.22)` | aro claro |

**Tipografia:** tudo em Outfit (`sans` de `../../theme`).

| Peça | Peso | Tamanho | Detalhe |
| --- | --- | --- | --- |
| "5.5" | 700 | 300 px | gradiente branco → verde recortado no texto |
| Preço do Sonnet | 700 | 150 px | — |
| "TECH E IA" final | 800 | 150 px | — |
| Preço | 700 | 112 px | — |
| Frase de impacto | 700 | 92 px | `lineHeight` 1.04 |
| Porcentagem | 700 | 78 px | — |
| Selo −75% | 800 | 64 px | — |
| Chips | 700 | 58 px | — |
| Corpo | 500–600 | 22–34 px | — |
| Rótulo do cartão | 700 | 24 px | `letterSpacing` 0.18em |
| Kicker | 600 | 26 px | `letterSpacing` 0.14em |

**Textura e luz:**
- **Bokeh:** 46 pontos determinísticos (`rnd`) em verde, gelo ou creme. Profundidade de 0.2 a 1, sobem com velocidade proporcional à profundidade e piscam.
- **Raios de luz:** dois raios de 340 px de largura, girados 24°, com 6% de opacidade, cruzando a tela a cada 260 frames.
- **Vinheta:** radial, transparente até 55% e preta a 0.65 na borda.
- **Reflexo do vidro:** uma faixa branca de 16% desliza a cada 120 frames.
- **Flare:** elipse de 1000 × 80 com halo de 440 px nos quadros 0, 300 e 612.

## Layout

```
y=0     ┌──────────────────────────────┐
y=108   │ TECH E IA          07.10.2026│  topo, x 72 → 1008
y=200   │┌────────── palco 3D ────────┐│  perspective 1400, origem 50% 45%
        ││   ┌──────────────────┐     ││
        ││   │ RÓTULO           │     ││  cartão de vidro 820–840 px,
        ││   │ NÚMERO HERÓI     │     ││  centralizado no palco,
        ││   │ chips / barras   │     ││  padding 48/52, raio 40
        ││   └──────────────────┘     ││
y=1260  │└────────────────────────────┘│
y=1330  │ KICKER (26)                  │  frase de impacto, x 72 → 1008
        │ Linha 1 (92)                 │
        │ Linha 2 (92)                 │
~1560   │                              │
y=1700  │                              │  limite da UI do Instagram
y=1920  └──────────────────────────────┘
```

- **Palco:** `top: 200`, altura 1060, largura total.
- **Cartão:** centralizado com flex, largura 820 (modelo, Sonnet) ou 840 (preço, OSWorld, final).
- **Frase de impacto:** `top: 1330`, margens de 72 px. Some no card final.
- **Selo −75%:** absoluto no canto superior direito do cartão de preço (`right: 40, top: 40`).

## Estrutura de tempo

Nada de frame fixo. Tudo vem de `story.timing` (calculado por `scripts/story.mjs` a partir da voz medida).

- **Um cartão por beat.** O cartão de cada beat entra em `timing.from` (o primeiro em −6, então já está quase no lugar no frame 0) e sai 6 frames antes do próximo beat. O último fica até o fim. Os cartões alternam o lado (`side`) e o acento: verde nos beats pares, gelo nos ímpares (hero e end sempre verdes).
- **Frase de impacto:** `beat.caption` entra em `from + 4` e some nos 10 frames antes do próximo beat. Linhas com número brilham em verde; se nenhuma tem número, a última brilha. Não aparece no card final.
- **Flares:** em cada impacto de `timing.events.hits` com força ≥ 30.

| Tipo de beat | Cartão | Momentos (`phase.marks`) |
| --- | --- | --- |
| hero | kicker, título, destaque grande em gradiente, chips (número grande + texto quando o chip começa com número) | `chips` (+12 por chip) |
| statement | kicker e a frase grande | `text` |
| stat | valor grande em gradiente, rótulo, nota | `value`, `label` |
| compare | rótulo; uma linha por item com o valor antigo riscado e o odômetro rolando do antigo para o novo; selo no canto; nota em pílula | por item: `name`, `strike` (odômetro começa 6 antes), `after` (fica colorido); fase `stamp`: `stamp`, `label` |
| bars | rótulo e uma barra por item, contando junto até o valor (`display` define casas e símbolo) | `label`, `countFrom`, `countTo` |
| list | rótulo e uma pílula de vidro por item, entrando da esquerda | `item0`, `item1`, … |
| end | nome da marca (última palavra em verde), handle, data longa, onde está disponível, fonte | `brand`, `info` |

Os tamanhos de texto usam `fit` (`src/news/story.tsx`), então valores e títulos longos encolhem para caber.

## Componentes

| Peça | Função |
| --- | --- |
| `src/styles/vidro/Reel.tsx:Reel` | Raiz. Fundo, palco 3D com órbita, cartões, flares, topo, frase. |
| `src/styles/vidro/Reel.tsx:SHOTS` | Janelas de cada cartão. |
| `src/styles/vidro/Reel.tsx:LINES` | Frases de impacto: kicker, duas linhas, índice da linha quente. |
| `src/styles/vidro/Reel.tsx:ImpactLine` | Frase em máscara, linha sobe com `pop`. |
| `src/styles/vidro/Reel.tsx:ModelCard` | Cartão do modelo. |
| `src/styles/vidro/Reel.tsx:PriceCard` | Cartão de preço, usa `PriceRow`. |
| `src/styles/vidro/Reel.tsx:PriceRow` | Linha de preço com risco e odômetro. |
| `src/styles/vidro/Reel.tsx:ScoreCard` | Cartão do OSWorld, usa `Bar`. |
| `src/styles/vidro/Reel.tsx:Bar` | Barra que enche, com contagem. |
| `src/styles/vidro/Reel.tsx:SonnetCard` | Cartão do Sonnet. |
| `src/styles/vidro/Reel.tsx:EndCard` | Card final. |
| `src/styles/vidro/Reel.tsx:Label` | Rótulo do cartão. |
| `src/styles/vidro/Reel.tsx:Top` | Topo com marca e data. |
| `src/styles/vidro/Space.tsx:Backdrop` | Gradiente, bokeh, raios de luz, vinheta. |
| `src/styles/vidro/Space.tsx:Shot` | Vida do cartão em profundidade. Recebe `enter`, `leave`, `side` (1 ou −1 para alternar o lado) e `y`. |
| `src/styles/vidro/Space.tsx:Glass` | Painel de vidro com aro e reflexo. Recebe `width`, `tone`, `shineAt`, `style`. |
| `src/styles/vidro/Space.tsx:Flare` | Clarão de lente. Recebe `at`, `x`, `y`, `tone`. |
| `src/styles/vidro/Space.tsx:rgba` | Hex → rgba. |
| `src/styles/vidro/Media.tsx:Seal`, `WithSeal` | Selo de vidro com o logo, preso no canto do cartão (só em beat com logo). |
| `src/styles/vidro/Media.tsx:PhotoPane` | Painel de vidro com a foto e o crédito, atrás e acima do cartão (só em beat com foto). |
| `src/film/kinetic.tsx:Odometer` | Dígitos que giram. Vem do estilo original. |
| `src/film/mix.ts:mix`, `pop` | Interpolação e spring. Vêm do estilo original. |

## Movimento

- **Câmera global:**
  - Órbita com `rotateX(4 + cos(f/90)·3)°` e `rotateY(sen(f/70)·5)°`.
  - Dolly de `scale` 1 → 1.06 ao longo dos 840 frames.
- **`Shot` (cada cartão):**
  - **Chegada:** de `enter − 30` a `enter + 10` (40 frames).
    - z vai de −1800 a 0.
    - `rotateY` de −28°·side a 0; `rotateX` de 12° a 0.
    - x de 160·side a 0.
    - Blur de 10 px a 0.
    - Opacidade cheia em ~70% da chegada.
  - **Flutuação parada:** `rotateY` ±4° (sen f/50) e `rotateX` ±3° (cos f/60).
  - **Saída:** de `leave` a `leave + 18`.
    - z sobe +900 (quadrático, passa pela câmera).
    - `rotateY` +34°·side, x −420·side.
    - Blur até 6 px; opacidade a 0.
  - Os cartões alternam o lado (`side`): modelo +1, preço −1, OSWorld +1, Sonnet −1, final +1.
- **Odômetro:** 22 frames por dígito, com atraso de 2 frames entre dígitos.
- **Risco do preço:** de `at + 18` a `at + 28`. A cor do número muda para verde no meio do risco.
- **Selo −75%:**
  - Spring `pop`.
  - Escala 0.4 → 1, rotação 26° → 6°.
  - Glow `0 0 60px` verde a 0.6.
- **Barras:** enchem em 32 frames (`at + 4` a `at + 36`), com contagem do número.
- **Frase de impacto:**
  - O kicker aparece com `pop`.
  - Cada linha sobe 110% de dentro da máscara, com 5 frames de atraso entre elas.
  - Some em 10 frames antes do `to`.
- **Flare:** sobe em 6 frames e apaga até o +40.

## Mídia

Logo e foto vêm de `beat.media` (regras em `src/styles/MEDIA-SPEC.md`). Código em `src/styles/vidro/Media.tsx`; o `Reel` só chama esse código quando `logoOf(beat)` ou `photoOf(beat)` existe. **Beat sem mídia renderiza exatamente como antes** (`python scripts/compare-baseline.py vidro` → "SEM MUDANÇA").

**Logo (`Seal`, `WithSeal`):** selo redondo de vidro preso no canto do cartão, flutuando à frente.
- Círculo de 146 px, centro no canto superior direito do cartão, puxado para fora (`right −15`, `top −53`), em `translateZ(60px)`. Num `compare` com `stamp` (o selo de preço ocupa esse canto) vai para o canto inferior direito (`bottom −47`).
- Vidro: gradiente 145° branco 0.24 → 0.05 → verde 0.12 sobre base escura (`#12343A` → `#081719`), para o aro do cartão não aparecer através; borda 1.5 px branca 0.42; brilho interno no topo.
- Logo em `PAPER`, 73 px, com `drop-shadow` verde (filtro num SVG pequeno).
- Brilho suave: halo radial verde fixo atrás do selo; só a opacidade respira (0.55 → 1, `sen f/22`).
- Reflexo: faixa branca 0.28 cruzando o selo a cada 150 quadros (só `transform`).
- Entrada: `pop` em `enter + 4` (escala 0.6 → 1, sobe 30 px, gira −20° → 0). Flutua com `translateY(sen(f/30)·6)` e `rotate(sen(f/46)·4°)`.
- O texto do cartão não muda; o selo fica quase todo fora do cartão, longe do título.

**Foto (`PhotoPane`):** cartão de vidro em profundidade, acima do cartão de texto.
- Painel 700 × 500, raio 38, no topo do palco (`top 6` do palco, tela ≈ 230–690), z −140 (fica atrás do cartão de texto e encolhe ~9% na projeção).
- Moldura de vidro de 12 px (gradiente branco 0.2 → 0.04 → gelo 0.1, borda branca 0.3, sombra profunda); foto `<Photo>` dentro, raio 28, Ken Burns de 7% ao longo do beat inteiro (todas as fases do `compare`), sem filtro.
- Por cima da foto, camadas fixas: reflexo diagonal (branco 0.18 → 0 até 42%), escurecimento embaixo (transparente até 58% → `#030607` a 0.72) e aro interno. Faixa de reflexo branca 0.13 desliza a cada 180 quadros (só `transform`).
- Crédito `<Credit>` 22 px `PAPER`, canto inferior esquerdo da foto (x +36, y −30), sobre o escurecimento.
- Movimento: mesma curva de chegada e saída do `Shot` (anda junto com o cartão), **sem blur**. Paralaxe: flutua em sentido oposto ao cartão (`rotateY −sen(f/50)·2.5°`, `rotateX −cos(f/60)·2°`, x `sen(f/64)·10`, y `cos(f/72)·6`). Aparece de `enter − 4` a `enter + 12` (para não ser vista através do cartão anterior, que ainda está saindo); no primeiro beat usa a opacidade do `Shot`.
- Texto: só nos beats com foto, o cartão desce 262 px (`Shot y`) e fica em escala 0.84. O cartão mais alto testado (compare com selo e nota, lista de 4 itens) termina em y ≈ 1260, antes da frase de impacto (1330), que não muda.

**Custo:** nada de `blur`, `backdrop-filter`, `mix-blend-mode` nem filtro animado sobre a foto; só `transform` e `opacity` mudam por quadro.

**Teste:** `node scripts/stills.mjs vidro 2026-10-09-haiku-midia` e `... 2026-10-09-gemini-midia`; folhas em `out/filmes/<id>/stills/vidro-sheet.png`.

## Som

`scripts/cues/vidro.mjs`:

| Som | Quadros | Ganho |
| --- | --- | --- |
| `rise` + `sting` | 0 e 2 (abertura) | — |
| `pop` | 106, 118 (chips do modelo) | — |
| `whoosh` | 172, 362, 580, 706 (saída de cada cartão) | — |
| `tick` | 204–222 e 236–254 a cada 6 frames (odômetros de preço) | 0.3 |
| `tick` | 608–626 (odômetro do Sonnet) | — |
| `stamp` | 300 (selo −75%) | 0.85 |
| `pop` | 462 (barra 4.5) | — |
| `rise` | 494 (barra 5.5) | — |
| `check` | 530 (fim da barra) | — |
| `lid` | 632 ("antes 0,20") | — |
| `pop` | 650 (chip ~20%) | — |
| `sting` | 722 (card final) | — |

## Adaptar para outra notícia

Não mexa no código. A notícia é um JSON:

1. Escreva `news/<id>.json` seguindo `src/news/types.ts` (beats hero → … → end, fala por extenso com tags do v4, legenda curta).
2. `node scripts/voice.mjs <id>` gera a voz (gasta crédito da ElevenLabs).
3. `node scripts/render-style.mjs vidro <id>` valida, mede, gera o som e renderiza `out/filmes/<id>/vidro.mp4`.

Para mudar o visual do estilo, os pontos são `Card` (um caso por tipo de beat) em `Reel.tsx` e `Space.tsx` (`Backdrop`, `Shot`, `Glass`, `Flare`). **Não mexa:** a perspectiva (1400), a curva do `Shot` e o tamanho do palco (200 → 1260), que alinham a frase de impacto.

## Render

```bash
# dentro do container: docker compose run --rm --entrypoint bash worker
cd /app/video
node scripts/render-style.mjs vidro <id>
```

Quadro solto: `npx remotion still src/styles/vidro/entry.tsx Estilo-Vidro out/filmes/<id>/vidro-N.png --frame=N --props=out/filmes/<id>/props.json` (rode antes `node scripts/story.mjs <id>`).

## Pontos fracos conhecidos

- **Abertura** (resolvido na versão por dados): o primeiro cartão entra em −6 e já está quase no lugar no frame 0.
- **Ritmo lento.** Um cartão por beat; beats longos (como o de preço) ficam parados vários segundos. Correção: mudar o enquadramento da câmera por fase.
- **Odômetro sujo.** Durante o giro aparecem dígitos cortados. É do efeito, mas fica sujo em tamanho grande.
- **Render mais lento que os outros estilos**, por causa do blur em cartões grandes e dos 46 gradientes de bokeh por quadro.
- **Frase repete o cartão.** A frase de impacto às vezes repete o número do cartão ("De US$ 1,00 para US$ 0,10"). Prefira uma consequência na frase.
