/**
 * News package: the single input of the pipeline.
 *
 * The pipeline (pipeline/rodada.py) writes `news/<id>.json` (a `News`). `scripts/story.mjs` measures the
 * voice and adds `timing`, merges `src/brand.json`, and writes
 * `public/filmes/<id>/story.json` (a `Story`). Every style renders a `Story`.
 *
 * Rules a writer of this file must follow (also checked by `scripts/story.mjs`):
 * - One beat per voice line, in order. First beat is `hero`, last is `end`.
 * - Voice text spells numbers out ("cinco ponto cinco", "dez centavos de dólar").
 *   Screen fields use digits ("5.5", "US$ 0,10").
 * - Voice says "inteligência artificial", never the acronym.
 * - Voice never reads the caption. Caption is the punch, voice adds the fact.
 * - Every number or claim on screen must come from `sources`.
 * - v4 audio tags go in square brackets inside voice text: "[excited] ...".
 */

export type BeatType = "hero" | "stat" | "compare" | "bars" | "list" | "statement" | "end";

export type Voice = {
  /** File name without extension: public/filmes/<id>/voice/<voice.id>.mp3 */
  id: string;
  /** Text sent to ElevenLabs, with v4 tags. */
  text: string;
};

export type Caption = {
  kicker: string;
  /** Two short lines max, "\n" separated. */
  text: string;
};

/**
 * Logo of the company or product the news is about, from logo.dev (free plan:
 * the description credits "Logos: logo.dev"). Square brand icon, 512 px PNG,
 * already downloaded under public/. Two files: `src` for a light background,
 * `srcDark` (logo.dev theme=dark) for a dark one; `Logo` picks by the ink color.
 */
export type LogoMedia = {
  kind: "logo";
  /** Company domain the logo came from, e.g. "anthropic.com". */
  domain: string;
  /** Brand name as written, e.g. "Anthropic". */
  name: string;
  /** staticFile path, e.g. "filmes/<id>/media/logo.png". */
  src: string;
  /** staticFile path of the dark-background version. */
  srcDark: string;
};

/**
 * A photo, already downloaded to public/filmes/<id>/media/<file>.
 * - newsroom: official press image of the product (editorial use). Credit "Imagem: <empresa>".
 * - ai: generated illustration. Never shows the real product; credit must say it is AI.
 * - game: official screenshot or trailer clip from a publisher's media kit.
 *   With `video` the beat plays that muted clip (looping every `videoFrames`); `file` is its poster.
 * The credit is always printed on screen next to the photo.
 */
export type PhotoMedia = {
  kind: "photo";
  file: string;
  source: "newsroom" | "ai" | "game";
  credit: string;
  width: number;
  height: number;
  video?: string;
  videoFrames?: number;
};

export type Media = LogoMedia | PhotoMedia;

type BeatBase = {
  voice: Voice;
  caption: Caption;
  /** Optional. At most 3 beats per news carry media; a beat without it renders exactly as before. */
  media?: Media;
};

/** Opening. Brand-new thing, big. */
export type HeroBeat = BeatBase & {
  type: "hero";
  kicker: string;
  title: string;
  /** The part that gets the accent color, e.g. a version number. */
  highlight?: string;
  chips?: string[];
};

/** One number or short phrase that fills the screen. */
export type StatBeat = BeatBase & {
  type: "stat";
  value: string;
  label: string;
  note?: string;
};

/** Before and after. Prices, versions, limits. */
export type CompareBeat = BeatBase & {
  type: "compare";
  label: string;
  items: { name: string; before: string; after: string }[];
  /** Optional verdict stamp, e.g. { value: "−75%", label: "em média" }. */
  stamp?: { value: string; label: string };
  note?: string;
};

/** Benchmarks or shares. `value` is 0..max, `display` is what is printed. */
export type BarsBeat = BeatBase & {
  type: "bars";
  label: string;
  max?: number;
  items: { name: string; value: number; display: string; highlight?: boolean }[];
  note?: string;
};

/** Features or steps, 2 to 4 short items. */
export type ListBeat = BeatBase & {
  type: "list";
  label: string;
  items: string[];
};

/** A sentence that carries the beat on its own. */
export type StatementBeat = BeatBase & {
  type: "statement";
  kicker: string;
  text: string;
};

/** Closing card: where it is available and the source. */
export type EndBeat = BeatBase & {
  type: "end";
  where: string;
  source: string;
};

export type Beat = HeroBeat | StatBeat | CompareBeat | BarsBeat | ListBeat | StatementBeat | EndBeat;

export type News = {
  id: string;
  /** Top bar date, "07.10.2026". */
  date: string;
  /** End card date, "07 DE OUTUBRO DE 2026". */
  dateLong: string;
  /** Suggested style id (see src/styles/README.md). */
  style: string;
  sources: { label: string; url: string }[];
  voice?: {
    /** ffmpeg atempo applied after generation. 1 = untouched. */
    tempo?: number;
    stability?: number;
    similarity?: number;
  };
  beats: Beat[];
};

export type Brand = {
  name: string;
  handle: string;
  /** Short mark for tight spots, e.g. the top bar. */
  short: string;
  /** One line under the brand at the top of every video. */
  tagline: string;
};

export type LineTiming = { id: string; at: number; end: number };

/**
 * A beat is cut into phases. Styles may show each phase as its own screen.
 * `marks` are absolute frames of the moments inside the phase. Sound cues use
 * the same marks, so picture and sound never drift apart.
 *
 * Marks by beat type (all absolute frames):
 * - hero      main:  title, highlight, chips
 * - statement main:  text
 * - stat      main:  value, label
 * - compare   item:  name, before, strike, after     (one phase per item, `index`)
 *             stamp: stamp, label                     (only when beat.stamp exists)
 * - bars      main:  label, countFrom, countTo
 * - list      main:  label, item0, item1, …
 * - end       main:  brand, info
 */
export type Phase = {
  kind: "main" | "item" | "stamp";
  index?: number;
  from: number;
  to: number;
  marks: Record<string, number>;
};

export type BeatTiming = { from: number; to: number; phases: Phase[] };

/** Every sound-worthy moment, derived from the marks. */
export type Events = {
  /** Impacts with strength 0–40: drive shake, flash and the "stamp" sound. */
  hits: { at: number; power: number }[];
  strikes: number[];
  ticks: number[];
  pops: number[];
  /** Start of every phase except frame 0. */
  cuts: number[];
  sting: number;
};

export type Timing = {
  fps: number;
  total: number;
  lines: LineTiming[];
  beats: BeatTiming[];
  events: Events;
};

export type Story = News & { brand: Brand; timing: Timing };

export type StoryProps = { story: Story };
