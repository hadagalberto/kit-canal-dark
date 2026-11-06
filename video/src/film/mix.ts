import { Easing, interpolate, spring } from "remotion";
import { FPS } from "../timing";

const ease = Easing.inOut(Easing.cubic);

export const mix = (
  frame: number,
  range: number[],
  output: number[] = [0, 1],
) =>
  interpolate(frame, range, output, {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: range.length === 2 ? ease : undefined,
  });

export const pop = (frame: number, at: number) => {
  if (frame < at) {
    return 0;
  }
  return spring({
    frame: frame - at,
    fps: FPS,
    config: { damping: 13, mass: 0.55, stiffness: 150 },
  });
};

const pageSpring = { damping: 18, mass: 0.48, stiffness: 170 };

/** Page change. The next card swings in from the right while the last one slides off to the left. */
export const presence = (frame: number, enterAt: number, leaveAt: number) => {
  const enter =
    frame < enterAt
      ? 0
      : spring({
          frame: frame - enterAt,
          fps: FPS,
          config: pageSpring,
        });
  const leave = mix(frame, [leaveAt, leaveAt + 16], [0, 1]);
  const x = interpolate(enter, [0, 1], [86, 0]) + interpolate(leave, [0, 1], [0, -104]);
  const y = interpolate(enter, [0, 1], [18, 0]) + interpolate(leave, [0, 1], [0, -14]);
  const rotate = interpolate(enter, [0, 1], [2.2, 0]) + interpolate(leave, [0, 1], [0, -2.8]);
  const rotateY = interpolate(enter, [0, 1], [18, 0]) + interpolate(leave, [0, 1], [0, -22]);
  const scale = interpolate(enter, [0, 1], [0.9, 1]) * interpolate(leave, [0, 1], [1, 0.86]);
  const leaveFade = interpolate(leave, [0, 0.62, 1], [1, 0.8, 0]);
  return {
    opacity: Math.min(enter, leaveFade),
    x,
    y,
    rotate,
    rotateY,
    scale,
    moving: enter < 0.985 || leave > 0.02,
  };
};

export const floatOf = (frame: number, amount = 7) =>
  Math.sin(frame / 16) * amount;
