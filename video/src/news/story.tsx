import { Audio, Sequence, staticFile, type CalculateMetadataFunction } from "remotion";
import haiku from "./fixtures/haiku.story.json";
import type { Beat, BeatTiming, Phase, Story, StoryProps } from "./types";

/**
 * Default story so `remotion still` and the Studio work without --props.
 * A copy kept in src/, so the bundle never depends on the public/filmes volume.
 */
export const defaultStory = haiku as unknown as Story;
export const defaultProps: StoryProps = { story: defaultStory };

/** Duration comes from the measured voice, never from a constant. */
export const storyMetadata: CalculateMetadataFunction<StoryProps> = ({ props }) => ({
  durationInFrames: props.story.timing.total,
});

const media = (story: Story, kind: "voice" | "music" | "sfx", name: string) =>
  staticFile(`filmes/${story.id}/${kind}/${name}`);

/** Voice lines at their measured frames, the bed, and this style's cue stem. */
export const StorySound = ({ story, style }: { story: Story; style: string }) => (
  <>
    {story.timing.lines.map((line) => (
      <Sequence key={line.id} from={line.at} layout="none">
        <Audio src={media(story, "voice", `${line.id}.mp3`)} />
      </Sequence>
    ))}
    <Audio src={media(story, "music", "bed.wav")} volume={0.1} />
    <Audio src={media(story, "sfx", `cues-${style}.wav`)} volume={0.42} />
  </>
);

export type Current = {
  beat: Beat;
  timing: BeatTiming;
  index: number;
  phase: Phase;
  phaseIndex: number;
};

/** All phases in order, each with its beat. Handy for "one screen per phase" styles. */
export const phasesOf = (story: Story) =>
  story.timing.beats.flatMap((timing, index) =>
    timing.phases.map((phase, phaseIndex) => ({ beat: story.beats[index], timing, index, phase, phaseIndex })),
  );

/** Beat and phase on screen at `frame`. */
export const currentAt = (story: Story, frame: number): Current => {
  const all = phasesOf(story);
  return [...all].reverse().find((item) => frame >= item.phase.from) ?? all[0];
};

/** Mark of the current phase, or Infinity when the mark does not exist. */
export const mark = (phase: Phase, name: string) => phase.marks[name] ?? Number.POSITIVE_INFINITY;

/**
 * Font size that fits `text` in `width` px. `em` is the average glyph width
 * of the font in em (Anton ~0.42, Syne 800 ~0.78, Outfit 700 ~0.56).
 */
export const fit = (text: string, width: number, max: number, em: number) =>
  Math.min(max, Math.floor(width / Math.max(1, glyphs(text) * em)));

/** Wide and narrow glyphs, relative to an average letter. */
const WEIGHT: Record<string, number> = { "%": 1.9, M: 1.35, W: 1.45, "÷": 1.3, "−": 1.1, " ": 0.45, ",": 0.45, ".": 0.45, I: 0.55, "1": 0.8 };

/** Text length in "average glyphs", so "−75%" counts wider than "ABCD". */
export const glyphs = (text: string) => [...text].reduce((sum, char) => sum + (WEIGHT[char.toUpperCase()] ?? 1), 0);
