import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SR = 44100;
const FPS = 30;

const here = dirname(fileURLToPath(import.meta.url));

/**
 * Story mode: `node scripts/make-audio.mjs <style> --story <newsId>`.
 * Duration and media folder come from public/filmes/<newsId>/story.json, the
 * bed is rebuilt to that length, and the cue module gets (sounds, story).
 */
const storyFlag = process.argv.indexOf("--story");
const storyId = storyFlag > 0 ? process.argv[storyFlag + 1] : null;
const storyData = storyId
  ? JSON.parse(readFileSync(join(here, "..", "public", "filmes", storyId, "story.json"), "utf8"))
  : null;

const FRAMES = storyData ? storyData.timing.total : 840;
const DURATION = FRAMES / FPS;

const film = storyData ? { id: storyId } : JSON.parse(readFileSync(join(here, "..", "src", "film.json"), "utf8"));
const mediaDir = join(here, "..", "public", "filmes", film.id);
const musicPath = join(mediaDir, "music", "bed.wav");
const cuesPath = join(mediaDir, "sfx", "cues.wav");

let seed = 20261008;
const rand = () => {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
};

const seconds = (n) => Math.floor(SR * n);

const easeInOutCubic = (t) =>
  t < 0.5 ? 4 * t * t * t : 1 - ((-2 * t + 2) ** 3) / 2;

const mixFrame = (frame, from, to, out0, out1) => {
  const t = Math.min(1, Math.max(0, (frame - from) / (to - from)));
  return out0 + (out1 - out0) * easeInOutCubic(t);
};

const env = (t, attack, decay) => {
  if (t < attack) {
    return t / attack;
  }
  return Math.exp(-(t - attack) * decay);
};

const tone = (freq, length, { decay = 8, gain = 0.5, harmonic = 0.2 } = {}) => {
  const out = new Float32Array(seconds(length));
  for (let i = 0; i < out.length; i++) {
    const t = i / SR;
    const amp = env(t, 0.008, decay);
    out[i] =
      (Math.sin(2 * Math.PI * freq * t) +
        harmonic * Math.sin(2 * Math.PI * freq * 2 * t)) *
      amp *
      gain;
  }
  return out;
};

const noiseBurst = (length, { decay = 18, gain = 0.4 } = {}) => {
  const out = new Float32Array(seconds(length));
  let prev = 0;
  for (let i = 0; i < out.length; i++) {
    const white = rand() * 2 - 1;
    const hp = white - prev;
    prev = white;
    const t = i / SR;
    out[i] = hp * Math.exp(-t * decay) * gain;
  }
  return out;
};

const click = () => {
  const body = tone(920, 0.07, { decay: 46, gain: 0.35, harmonic: 0.1 });
  const thump = tone(170, 0.08, { decay: 28, gain: 0.7, harmonic: 0 });
  const tick = noiseBurst(0.04, { decay: 70, gain: 0.25 });
  return sum([body, thump, tick]);
};

const toggle = () => {
  const down = tone(240, 0.09, { decay: 22, gain: 0.45, harmonic: 0 });
  const up = tone(640, 0.07, { decay: 30, gain: 0.28, harmonic: 0.15 });
  const offset = seconds(0.035);
  const out = new Float32Array(Math.max(down.length, up.length + offset));
  add(out, down, 0, 1);
  add(out, up, offset, 1);
  return out;
};

const notify = () => {
  const a = tone(880, 0.12, { decay: 14, gain: 0.4, harmonic: 0.05 });
  const b = tone(1320, 0.18, { decay: 10, gain: 0.38, harmonic: 0.08 });
  const out = new Float32Array(seconds(0.32));
  add(out, a, 0, 1);
  add(out, b, seconds(0.09), 1);
  return out;
};

const check = () => {
  const a = tone(523.25, 0.14, { decay: 12, gain: 0.35, harmonic: 0.12 });
  const b = tone(783.99, 0.2, { decay: 9, gain: 0.32, harmonic: 0.1 });
  const out = new Float32Array(seconds(0.32));
  add(out, a, 0, 1);
  add(out, b, seconds(0.07), 1);
  return out;
};

const whoosh = () => {
  const n = seconds(0.42);
  const out = new Float32Array(n);
  let low = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const p = t / 0.42;
    const white = rand() * 2 - 1;
    low += (white - low) * (0.08 + p * 0.35);
    const window = Math.sin(Math.PI * p) ** 1.4;
    const sweep = Math.sin(2 * Math.PI * (520 - p * 340) * t) * (1 - p);
    out[i] = (low * 0.7 + sweep * 0.25) * window * 0.8;
  }
  return out;
};

const lid = () => {
  const n = seconds(0.55);
  const out = new Float32Array(n);
  let low = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const p = t / 0.55;
    const white = rand() * 2 - 1;
    low += (white - low) * 0.12;
    const window = Math.sin(Math.PI * p);
    const drop = Math.sin(2 * Math.PI * (180 - p * 120) * t);
    out[i] = (low * 0.85 + drop * 0.2) * window * 0.7;
  }
  return out;
};

const stamp = () => {
  const thump = tone(78, 0.22, { decay: 10, gain: 0.9, harmonic: 0.4 });
  const slap = noiseBurst(0.08, { decay: 30, gain: 0.35 });
  return sum([thump, slap]);
};

const key = () => tone(1760, 0.028, { decay: 90, gain: 0.22, harmonic: 0.05 });

const pop = () => {
  const n = seconds(0.12);
  const out = new Float32Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const freq = 420 + 380 * (1 - t / 0.12);
    phase += (2 * Math.PI * freq) / SR;
    out[i] = Math.sin(phase) * Math.exp(-t * 18) * 0.55;
  }
  return out;
};

const rise = () => {
  const n = seconds(0.46);
  const out = new Float32Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const p = t / 0.46;
    const freq = 240 + p * p * 520;
    phase += (2 * Math.PI * freq) / SR;
    const window = Math.sin(Math.PI * p);
    out[i] = Math.sin(phase) * window * 0.4;
  }
  return out;
};

const sting = () => {
  const notes = [440, 554.37, 659.25];
  const out = new Float32Array(seconds(0.7));
  notes.forEach((freq, index) => {
    add(out, tone(freq, 0.55, { decay: 3.2, gain: 0.28, harmonic: 0.18 }), seconds(index * 0.035), 1);
  });
  add(out, tone(880, 0.4, { decay: 4, gain: 0.12, harmonic: 0 }), seconds(0.08), 1);
  return out;
};

const open = () => {
  const air = whoosh();
  const paper = tone(310, 0.16, { decay: 14, gain: 0.2, harmonic: 0.3 });
  return sum([air, paper]);
};

function add(target, source, offset, gain) {
  for (let i = 0; i < source.length; i++) {
    const index = i + offset;
    if (index >= 0 && index < target.length) {
      target[index] += source[i] * gain;
    }
  }
}

function sum(parts) {
  const length = Math.max(...parts.map((part) => part.length));
  const out = new Float32Array(length);
  for (const part of parts) {
    add(out, part, 0, 1);
  }
  return out;
}

function place(target, frame, sound, gain) {
  add(target, sound, Math.floor((frame / FPS) * SR), gain);
}

function typingFrames() {
  const phrase = "Organizar a planilha.";
  const frames = [];
  let prev = 0;
  for (let frame = 390; frame <= 448; frame++) {
    const typed = Math.floor(mixFrame(frame, 390, 448, 0, phrase.length));
    if (typed > prev) {
      const char = phrase[typed - 1];
      if (char && char !== " ") {
        frames.push(frame);
      }
      prev = typed;
    }
  }
  return frames;
}

function makeCues() {
  const out = new Float32Array(seconds(DURATION));
  const clickSound = click();
  const tick = tone(1480, 0.045, { decay: 50, gain: 0.3, harmonic: 0 });
  const task = pop();

  place(out, 4, whoosh(), 0.55);
  place(out, 38, task, 0.45);
  place(out, 346, task, 0.6);
  for (const frame of [204, 210, 216, 222, 228, 234, 240, 246, 616, 622, 628, 634]) {
    place(out, frame, tick, 0.22);
  }
  place(out, 30, notify(), 0.7);
  place(out, 82, clickSound, 0.75);
  place(out, 98, open(), 0.4);
  for (const frame of [112, 124, 136]) {
    place(out, frame, tick, 0.28);
  }
  place(out, 166, whoosh(), 0.42);
  for (const frame of [188, 208, 228]) {
    place(out, frame, tick, 0.45);
  }
  place(out, 298, toggle(), 0.8);
  place(out, 318, stamp(), 0.85);
  place(out, 372, whoosh(), 0.28);
  const keySound = key();
  for (const frame of typingFrames()) {
    place(out, frame, keySound, 0.55);
  }
  place(out, 450, clickSound, 0.7);
  place(out, 456, rise(), 0.22);
  for (const frame of [468, 492]) {
    place(out, frame, task, 0.6);
  }
  place(out, 520, check(), 0.55);
  place(out, 586, whoosh(), 0.32);
  place(out, 620, lid(), 0.7);
  place(out, 676, rise(), 0.65);
  place(out, 710, whoosh(), 0.25);
  place(out, 724, sting(), 0.85);
  return normalize(out, 0.9);
}

function makeBed() {
  const total = seconds(DURATION);
  const out = new Float32Array(total);
  const bpm = 96;
  const beat = 60 / bpm;
  const beats = Math.floor(DURATION / beat);

  const kick = (() => {
    const n = seconds(0.24);
    const buffer = new Float32Array(n);
    let phase = 0;
    for (let i = 0; i < n; i++) {
      const t = i / SR;
      const freq = 130 * Math.exp(-t * 18) + 46;
      phase += (2 * Math.PI * freq) / SR;
      buffer[i] = Math.sin(phase) * Math.exp(-t * 9);
    }
    return buffer;
  })();

  const hat = noiseBurst(0.045, { decay: 48, gain: 0.18 });
  const bass = tone(55, 0.34, { decay: 5, gain: 0.7, harmonic: 0.15 });
  const motif = [440, 523.25, 659.25, 783.99, 659.25, 523.25, 440, 392];

  for (let i = 0; i < beats; i++) {
    const start = Math.floor(i * beat * SR);
    if (i % 2 === 0) {
      add(out, kick, start, 0.55);
    } else {
      add(out, hat, start, 0.18);
    }
    if (i % 4 === 0) {
      add(out, bass, start, 0.62);
    }
  }

  motif.forEach((freq, index) => {
    const first = 4 * beat + index * beat;
    const second = 18 * beat + index * beat;
    if (first < DURATION - 1) {
      add(out, tone(freq, 0.26, { decay: 7, gain: 0.22, harmonic: 0.25 }), Math.floor(first * SR), 1);
    }
    if (second < 23) {
      add(out, tone(freq, 0.22, { decay: 8, gain: 0.14, harmonic: 0.2 }), Math.floor(second * SR), 1);
    }
  });

  let low = 0;
  for (let i = 0; i < total; i++) {
    const t = i / SR;
    const chord = [220, 261.63, 329.63]
      .map((freq, index) => Math.sin(2 * Math.PI * freq * t + index))
      .reduce((summed, value) => summed + value, 0);
    low += (chord - low) * 0.02;
    const fadeIn = Math.min(1, t / 0.6);
    const fadeOut = Math.min(1, (DURATION - t) / 1.5);
    const swell = 0.72 + 0.28 * Math.sin(2 * Math.PI * 0.07 * t);
    out[i] += low * 0.16 * fadeIn * fadeOut * swell;
    out[i] *= fadeIn * fadeOut;
  }

  const clipped = new Float32Array(total);
  for (let i = 0; i < total; i++) {
    clipped[i] = Math.tanh(out[i] * 1.35);
  }
  return normalize(clipped, 0.85);
}

function normalize(samples, peak) {
  let max = 0;
  for (let i = 0; i < samples.length; i++) {
    max = Math.max(max, Math.abs(samples[i]));
  }
  const gain = max > 0 ? peak / max : 1;
  const out = new Float32Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    out[i] = samples[i] * gain;
  }
  return out;
}

function wavMono(samples) {
  const dataSize = samples.length * 2;
  const buffer = Buffer.alloc(44 + dataSize);
  buffer.write("RIFF", 0);
  buffer.writeUInt32LE(36 + dataSize, 4);
  buffer.write("WAVE", 8);
  buffer.write("fmt ", 12);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(SR, 24);
  buffer.writeUInt32LE(SR * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write("data", 36);
  buffer.writeUInt32LE(dataSize, 40);
  for (let i = 0; i < samples.length; i++) {
    const value = Math.max(-1, Math.min(1, samples[i]));
    buffer.writeInt16LE((value * 32767) | 0, 44 + i * 2);
  }
  return buffer;
}

function rms(samples) {
  let acc = 0;
  for (let i = 0; i < samples.length; i++) {
    acc += samples[i] * samples[i];
  }
  return Math.sqrt(acc / samples.length);
}

mkdirSync(dirname(musicPath), { recursive: true });
mkdirSync(dirname(cuesPath), { recursive: true });

/**
 * Style tests: `node scripts/make-audio.mjs <style>` reads scripts/cues/<style>.mjs
 * (default export: (sounds) => [{ frame, sound, gain }]) and writes only
 * sfx/cues-<style>.wav. The bed and the main cues stay untouched.
 */
const style = process.argv[2] && !process.argv[2].startsWith("--") ? process.argv[2] : null;
if (style) {
  const sounds = {
    click, toggle, notify, check, whoosh, lid, stamp, key, pop, rise, sting, open,
    tick: () => tone(1480, 0.045, { decay: 50, gain: 0.3, harmonic: 0 }),
  };
  const { default: list } = await import(`./cues/${style}.mjs`);
  const out = new Float32Array(seconds(DURATION));
  // The bed is the same for every style of a story: build it once, so styles
  // rendering in parallel never rewrite a file another render is reading.
  if (storyData && !existsSync(musicPath)) {
    mkdirSync(dirname(musicPath), { recursive: true });
    writeFileSync(musicPath, wavMono(makeBed()));
  }
  for (const cue of list(sounds, storyData)) {
    place(out, cue.frame, sounds[cue.sound](), cue.gain ?? 0.6);
  }
  const target = join(mediaDir, "sfx", `cues-${style}.wav`);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, wavMono(normalize(out, 0.9)));
  console.log(`cues-${style} ${(out.length / SR).toFixed(2)}s rms ${rms(out).toFixed(3)}`);
  process.exit(0);
}

const bed = makeBed();
const cues = makeCues();
writeFileSync(musicPath, wavMono(bed));
writeFileSync(cuesPath, wavMono(cues));

console.log(
  `bed ${(bed.length / SR).toFixed(2)}s rms ${rms(bed).toFixed(3)}`,
);
console.log(
  `cues ${(cues.length / SR).toFixed(2)}s rms ${rms(cues).toFixed(3)} keys ${typingFrames().length}`,
);
