# Mídia nos estilos (logo e foto)

Especificação comum para todo estilo. Referência pronta: `src/styles/vidro/Reel.tsx` e `vidro/Media.tsx`.

## O dado

Um beat pode trazer `media` (`src/news/types.ts`):

- `{ kind: "logo", domain, name, src, srcDark }`: logo da empresa ou do produto da notícia (logo.dev, PNG claro e escuro em `public/filmes/<id>/media/`). O estilo escolhe a versão pelo fundo.
- `{ kind: "photo", file, source: "newsroom" | "ai", credit, width, height }`: foto já baixada em `public/filmes/<id>/media/<file>`, vertical na maioria das vezes (768×1376).

No máximo 3 beats por notícia têm mídia. O logo pode estar em qualquer beat, mas normalmente vem no `hero` e no `end`. A foto pode estar em qualquer beat menos o `end`, inclusive em `compare` com várias fases: nesse caso ela fica durante o beat inteiro (todas as fases) ou reaparece em cada fase, como o estilo preferir.

## Componentes prontos (`src/news/media.tsx`)

- `logoOf(beat)`, `photoOf(beat)`: a mídia do beat ou `undefined`.
- `<Logo logo size color outline? strokeWidth? glow? />`: SVG inline em qualquer cor. `outline` desenha só o contorno.
- `<Photo story photo frame from to seed? amount? filter? position? style />`: foto em `object-fit: cover` com movimento Ken Burns. A caixa é sua: dê posição, tamanho, borda e rotação em `style`.
- `<Credit photo color size? style? />`: linha de crédito. **Obrigatória e legível sempre que a foto estiver na tela.**
- `kenBurns`, `reveal`, `beatSpan`, `photoSrc`.

## Regras (não negociáveis)

1. **Sem mídia, nada muda.** Um beat sem `media` tem de renderizar exatamente como antes: mesmas posições, tamanhos e tempos. Use condicionais (`logo ? … : null`, padding diferente só quando há foto).
2. A mídia não cobre o texto do beat, a legenda nem a barra do topo, e fica na área segura: 60 px nas laterais, y de 90 a 1700. Se precisar de espaço, desloque o texto **só nos beats com foto**.
3. Carregar foto e logo só com `<Photo>`/`<Img>` e SVG inline. Nunca como `background-image` ou `mask` em CSS, porque o Remotion não espera essas imagens carregarem e o quadro pode sair em branco. Gradiente CSS (retícula, scanlines) pode.
4. Custo por quadro: o render roda sem GPU (CPU do PC ou de uma VPS) (o vidro já leva 8 min). `transform` e `opacity` são baratos. `filter` fixo na `<Img>` (o mesmo em todo quadro) é aceitável. Nada de `blur`/`backdrop-filter`/`mix-blend-mode` animado sobre a foto inteira a cada quadro. Prefira camadas fixas por cima: uma div com gradiente de scanline ou de retícula.
5. Animação só por quadro (`useCurrentFrame`, `interpolate`, `spring`). Sem `transition`/`@keyframes` em CSS e sem `Math.random` (use `random(seed)` do Remotion).
6. O crédito aparece inteiro, sem corte, em tamanho ≥ 20 px e com contraste.
7. Imagem de IA nunca é apresentada como "o produto anunciado". O crédito já diz que é ilustrativa; não ponha rótulo de produto colado nela.

## Efeito por estilo

Cada estilo trata a mídia na sua própria linguagem. As sugestões abaixo podem ser ajustadas, desde que as regras acima sejam respeitadas e o resultado combine com o `DESIGN.md` do estilo.

| Estilo | Logo | Foto |
| --- | --- | --- |
| vidro | Dentro de um selo de vidro com brilho suave, flutuando | Num cartão de vidro em profundidade, com paralaxe leve e reflexo |

Num estilo novo, decida o efeito do logo e da foto pela linguagem dele (carimbo, adesivo, moldura, filtro fixo...) e registre na seção **Mídia** do `DESIGN.md`.

## Teste

```bash
# dentro do container: docker compose run --rm --entrypoint bash worker
cd /app/video
npx tsc --noEmit
node scripts/stills.mjs <estilo> <id-de-uma-noticia-com-midia>
node scripts/stills.mjs <estilo> <id-de-uma-noticia-sem-midia> 30 250
```

A folha sai em `out/filmes/<id>/stills/<estilo>-sheet.png`. Olhe todas: texto cortado, foto cobrindo texto, crédito ilegível ou quadro vazio são defeitos.

Documente no `DESIGN.md` do estilo uma seção **Mídia** dizendo onde o logo e a foto entram, o efeito, os números (tamanho, posição, quadros) e o que acontece com o texto.
