# Estilo <Nome> (`<id>`)

Uma linha: o que este estilo é e a sensação que passa.


## Quando usar

Tipo de notícia em que funciona melhor. Tipo em que não funciona.

## Identidade

| Token | Valor | Uso |
| --- | --- | --- |
| fundo | `#......` | ... |
| texto | `#......` | ... |
| acento | `#......` | ... |

Tipografia: fonte, peso, tamanhos usados (título, número herói, rótulo, corpo, rodapé), de onde vem (`@remotion/google-fonts/...` ou `../../theme`).

Textura e luz: grão, scanlines, partículas, vinheta, etc.

## Layout

Coordenadas no quadro 1080×1920. Desenhe o esqueleto em ASCII.

```
y=0     ┌──────────────────────┐
y=90    │ TECH E IA   07.10.26 │  topo
        │                      │
        │  ...                 │
y=1700  │                      │  limite da UI do Instagram
y=1920  └──────────────────────┘
```

Margens laterais, zona do herói, zona da frase de impacto, onde fica o rodapé.

## Estrutura de tempo

Tabela de blocos, frame de entrada/saída e fala de `VOICE` que cada um cobre.

| Bloco | Frames | Fala | O que mostra |
| --- | --- | --- | --- |

## Componentes

`arquivo:símbolo` de cada peça reutilizável e o que ela recebe.

## Movimento

Entradas, saídas, transição entre blocos, impactos (tremor, flash), câmera. Com números: duração em frames, escala, deslocamento, easing/spring.

## Som

O que `scripts/cues/<id>.mjs` toca e em quais ações.

## Adaptar para outra notícia

Passo a passo do que trocar (textos, números, blocos, tempos, cues) e o que não mexer.

## Render

```bash
# dentro do container: docker compose run --rm --entrypoint bash worker
cd /app/video
node scripts/make-audio.mjs <id>
npx remotion render src/styles/<id>/entry.tsx Estilo-<Nome> out/filmes/<film-id>/estilo-<id>.mp4 --codec=h264 --crf=18
```

## Pontos fracos conhecidos

O que ainda não está bom e como melhorar.
