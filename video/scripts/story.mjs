import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * news/<id>.json + measured voice + src/brand.json → public/filmes/<id>/story.json
 *
 *   node scripts/story.mjs <newsId>
 *
 * Validates the package (rules in src/news/types.ts), measures every voice
 * line and derives all frames. Nothing downstream hardcodes a frame.
 * Exit code 1 with a list of problems if the package is invalid.
 */

const FPS = 30;
const GAP = 14; // frames between two voice lines (~0.47 s)
const FIRST_LINE = 4; // the hero is on screen a few frames before the voice
const LEAD = 4; // a beat starts this many frames before its line
const TAIL = 45; // frames after the last line
const END_MIN = 105; // the end card stays at least 3.5 s

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");

const newsId = process.argv[2];
if (!newsId) {
  console.error("uso: node scripts/story.mjs <newsId>");
  process.exit(1);
}

const news = JSON.parse(readFileSync(join(root, "news", `${newsId}.json`), "utf8"));
// news.brand: outro canal (pipeline/rodada.py grava a marca do perfil do canal no pacote)
const brand = news.brand ?? JSON.parse(readFileSync(join(root, "src", "brand.json"), "utf8"));
const voiceDir = join(root, "public", "filmes", newsId, "voice");
const mediaDir = join(root, "public", "filmes", newsId, "media");

const problems = [];
const need = (cond, msg) => {
  if (!cond) {
    problems.push(msg);
  }
};

const REQUIRED = {
  hero: ["kicker", "title"],
  stat: ["value", "label"],
  compare: ["label", "items"],
  bars: ["label", "items"],
  list: ["label", "items"],
  statement: ["kicker", "text"],
  end: ["where", "source"],
};

need(news.id === newsId, `id "${news.id}" diferente do arquivo "${newsId}"`);
need(Array.isArray(news.sources) && news.sources.length > 0, "sem sources");
need(Array.isArray(news.beats) && news.beats.length >= 3, "precisa de pelo menos 3 beats");
need(news.beats?.[0]?.type === "hero", "o primeiro beat tem de ser hero");
need(news.beats?.at(-1)?.type === "end", "o último beat tem de ser end");

const ids = new Set();
news.beats?.forEach((beat, i) => {
  const at = `beat ${i} (${beat.type})`;
  need(REQUIRED[beat.type], `${at}: tipo desconhecido`);
  for (const field of REQUIRED[beat.type] ?? []) {
    need(beat[field] !== undefined && beat[field] !== "", `${at}: falta ${field}`);
  }
  need(beat.voice?.id && beat.voice?.text, `${at}: falta voice.id ou voice.text`);
  need(!ids.has(beat.voice?.id), `${at}: voice.id repetido "${beat.voice?.id}"`);
  ids.add(beat.voice?.id);
  const spoken = (beat.voice?.text ?? "").replace(/\[[^\]]*\]/g, "");
  need(!/\d/.test(spoken), `${at}: a fala tem dígitos, escreva por extenso: "${spoken.trim()}"`);
  need(!/\bIA\b/.test(spoken), `${at}: a fala usa a sigla IA, diga "inteligência artificial"`);
  need(beat.caption?.kicker && beat.caption?.text, `${at}: falta caption.kicker ou caption.text`);
  need((beat.caption?.text ?? "").split("\n").length <= 2, `${at}: caption com mais de 2 linhas`);
  if (Array.isArray(beat.items)) {
    need(beat.items.length >= 1 && beat.items.length <= 4, `${at}: items precisa ter de 1 a 4 itens`);
  }
  need(existsSync(join(voiceDir, `${beat.voice?.id}.mp3`)), `${at}: falta o áudio voice/${beat.voice?.id}.mp3 (rode scripts/voice.mjs)`);
  const media = beat.media;
  if (media) {
    if (media.kind === "logo") {
      need(/^[a-z0-9.-]+\.[a-z]{2,}$/.test(media.domain ?? ""), `${at}: media.domain inválido`);
      need(media.name, `${at}: media.name vazio`);
      for (const key of ["src", "srcDark"]) {
        need(existsSync(join(root, "public", media[key] ?? "")), `${at}: falta o logo ${media[key]}`);
      }
    } else if (media.kind === "photo") {
      need(["newsroom", "ai", "game"].includes(media.source), `${at}: media.source tem de ser newsroom, ai ou game`);
      if (media.video) {
        need(existsSync(join(mediaDir, media.video)), `${at}: falta o clipe media/${media.video}`);
        need(media.videoFrames > 0, `${at}: media.videoFrames`);
      }
      need(media.credit, `${at}: foto sem crédito na tela`);
      need(media.source !== "ai" || /\bIA\b/.test(media.credit ?? ""), `${at}: imagem de IA tem de dizer que é IA no crédito`);
      need(existsSync(join(mediaDir, media.file ?? "")), `${at}: falta a imagem media/${media.file}`);
      need(media.width > 0 && media.height > 0, `${at}: media.width/height`);
    } else {
      need(false, `${at}: media.kind desconhecido`);
    }
  }
});
need((news.beats ?? []).filter((beat) => beat.media).length <= 3, "mais de 3 beats com mídia");

if (problems.length > 0) {
  console.error(`news/${newsId}.json inválido:\n- ${problems.join("\n- ")}`);
  process.exit(1);
}

const seconds = (file) =>
  Number(
    execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", file])
      .toString()
      .trim(),
  );

const lines = [];
let cursor = FIRST_LINE;
for (const beat of news.beats) {
  const length = Math.ceil(seconds(join(voiceDir, `${beat.voice.id}.mp3`)) * FPS);
  lines.push({ id: beat.voice.id, at: cursor, end: cursor + length });
  cursor += length + GAP;
}

const starts = lines.map((line, i) => (i === 0 ? 0 : line.at - LEAD));
const lastEnd = lines.at(-1).end;
const total = Math.max(lastEnd + TAIL, starts.at(-1) + END_MIN);

/** Moments inside a span: `at(0.3, 18)` = 30% in, but never later than 18 frames. */
const inside = (from, to) => (share, cap = Infinity) => from + Math.round(Math.min((to - from) * share, cap));

const phasesOf = (beat, from, to) => {
  const main = (marks) => [{ kind: "main", from, to, marks }];
  const at = inside(from, to);
  switch (beat.type) {
    case "hero":
      return main({ title: from + 2, highlight: at(0.12, 14), chips: at(0.45, 40) });
    case "statement":
      return main({ text: at(0.06, 6) });
    case "stat":
      return main({ value: at(0.06, 6), label: at(0.2, 18) });
    case "bars": {
      const countFrom = at(0.1, 10);
      return main({ label: from + 2, countFrom, countTo: countFrom + Math.round(Math.min((to - from) * 0.4, 36)) });
    }
    case "list": {
      const step = Math.min(24, Math.floor(((to - from) * 0.6) / beat.items.length));
      return main({ label: from + 2, ...Object.fromEntries(beat.items.map((_, i) => [`item${i}`, from + 8 + i * step])) });
    }
    case "end":
      return main({ brand: from + 2, info: at(0.2, 24) });
    case "compare": {
      const count = beat.items.length + (beat.stamp ? 1 : 0);
      const size = (to - from) / count;
      const phases = beat.items.map((_, i) => {
        const a = Math.round(from + i * size);
        const b = Math.round(from + (i + 1) * size);
        const p = inside(a, b);
        return { kind: "item", index: i, from: a, to: b, marks: { name: a + 2, before: p(0.08, 6), strike: p(0.3, 18), after: p(0.45, 26) } };
      });
      if (beat.stamp) {
        const a = Math.round(from + beat.items.length * size);
        phases.push({ kind: "stamp", from: a, to, marks: { stamp: a + 4, label: inside(a, to)(0.3, 16) } });
      }
      return phases;
    }
    default:
      return main({});
  }
};

const beats = starts.map((from, i) => {
  const to = i + 1 < starts.length ? starts[i + 1] : total;
  return { from, to, phases: phasesOf(news.beats[i], from, to) };
});

const POWER = { title: 22, highlight: 30, text: 12, value: 30, after: 22, stamp: 34, countTo: 30, brand: 16 };
const events = { hits: [], strikes: [], ticks: [], pops: [], cuts: [], sting: 0 };
for (const [i, beat] of beats.entries()) {
  for (const phase of beat.phases) {
    if (phase.from > 0) {
      events.cuts.push(phase.from);
    }
    for (const [name, frame] of Object.entries(phase.marks)) {
      if (POWER[name]) {
        events.hits.push({ at: frame, power: POWER[name] });
      }
      if (name === "strike") {
        events.strikes.push(frame);
      }
      if (name.startsWith("item") || name === "chips") {
        events.pops.push(frame);
      }
    }
    if (phase.marks.countFrom !== undefined) {
      for (let f = phase.marks.countFrom; f < phase.marks.countTo; f += 3) {
        events.ticks.push(f);
      }
    }
  }
  if (news.beats[i].type === "end") {
    events.sting = beat.phases[0].marks.brand;
  }
}

const story = { ...news, brand, timing: { fps: FPS, total, lines, beats, events } };
const file = join(root, "public", "filmes", newsId, "story.json");
mkdirSync(dirname(file), { recursive: true });
writeFileSync(file, JSON.stringify(story, null, 2));

const propsDir = join(root, "out", "filmes", newsId);
mkdirSync(propsDir, { recursive: true });
writeFileSync(join(propsDir, "props.json"), JSON.stringify({ story }));

console.log(`${newsId}: ${news.beats.length} beats, ${total} frames (${(total / FPS).toFixed(1)} s)`);
for (const [i, beat] of news.beats.entries()) {
  console.log(`  ${String(beats[i].from).padStart(4)}–${String(beats[i].to).padEnd(4)} ${beat.type.padEnd(9)} ${beat.voice.id} (fala ${lines[i].at}–${lines[i].end})`);
}
