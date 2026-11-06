/**
 * Estilo vidro: subida suave na abertura, whoosh a cada cartão que passa pela
 * câmera, ticks nos odômetros e contagens, pop nos chips e itens, stamp nos
 * impactos fortes, check quando a barra assenta, sting no fecho.
 * Todos os frames vêm de story.timing.events (scripts/story.mjs).
 */
export default (sounds, story) => {
  const e = story.timing.events;
  const strong = e.hits.filter((hit) => hit.power >= 30);
  return [
    { frame: 0, sound: "rise", gain: 0.5 },
    { frame: 2, sound: "sting", gain: 0.55 },
    ...e.cuts.map((frame) => ({ frame: Math.max(0, frame - 6), sound: "whoosh", gain: 0.45 })),
    ...strong.map((hit) => ({ frame: hit.at, sound: "stamp", gain: Math.min(0.9, 0.4 + hit.power / 60) })),
    ...e.strikes.map((frame) => ({ frame, sound: "lid", gain: 0.5 })),
    ...e.strikes.flatMap((frame) => [0, 6, 12, 18].map((d) => ({ frame: frame - 6 + d, sound: "tick", gain: 0.28 }))),
    ...e.ticks.map((frame) => ({ frame, sound: "tick", gain: 0.28 })),
    ...e.pops.map((frame) => ({ frame, sound: "pop", gain: 0.5 })),
    { frame: e.sting, sound: "sting", gain: 0.8 },
  ];
};
