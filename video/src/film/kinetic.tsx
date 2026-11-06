import type { CSSProperties } from "react";
import { colors, tint } from "../theme";
import { mix } from "./mix";

/** Decaying jolt after an impact. Returns pixels for x and y. */
export const shake = (frame: number, at: number, amount = 10) => {
  if (frame < at || frame > at + 18) {
    return { x: 0, y: 0 };
  }
  const t = frame - at;
  const decay = Math.exp(-t / 5);
  return {
    x: Math.sin(t * 2.7) * amount * decay,
    y: Math.cos(t * 3.4) * amount * 0.6 * decay,
  };
};

/** Diagonal band of light crossing its parent. The parent needs overflow hidden. */
export const Sheen = ({
  frame,
  at,
  span = 22,
  color = colors.paper,
  strength = 0.22,
}: {
  frame: number;
  at: number;
  span?: number;
  color?: string;
  strength?: number;
}) => {
  const t = mix(frame, [at, at + span], [0, 1]);
  if (t <= 0 || t >= 1) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        top: "-50%",
        bottom: "-50%",
        left: `${-40 + t * 160}%`,
        width: "28%",
        background: `linear-gradient(90deg, transparent, ${tint(color, strength)}, transparent)`,
        transform: "rotate(18deg)",
        pointerEvents: "none",
      }}
    />
  );
};

/** Rings plus short sparks thrown out from one point. */
export const Burst = ({
  frame,
  at,
  x,
  y,
  color = colors.lime,
  radius = 120,
  sparks = 10,
}: {
  frame: number;
  at: number;
  x: number;
  y: number;
  color?: string;
  radius?: number;
  sparks?: number;
}) => {
  const t = mix(frame, [at, at + 20], [0, 1]);
  if (t <= 0 || t >= 1) {
    return null;
  }
  const ease = 1 - (1 - t) ** 3;
  return (
    <svg
      width={radius * 3}
      height={radius * 3}
      viewBox={`${-radius * 1.5} ${-radius * 1.5} ${radius * 3} ${radius * 3}`}
      style={{ position: "absolute", left: x - radius * 1.5, top: y - radius * 1.5, pointerEvents: "none", overflow: "visible", zIndex: 7 }}
    >
      <circle r={radius * 0.25 + ease * radius * 0.85} fill="none" stroke={color} strokeWidth={3 * (1 - t) + 0.5} opacity={1 - t} />
      <circle r={radius * 0.1 + ease * radius * 0.55} fill="none" stroke={colors.paper} strokeWidth={2 * (1 - t)} opacity={(1 - t) * 0.6} />
      {Array.from({ length: sparks }, (_, index) => {
        const angle = (index / sparks) * Math.PI * 2 + index * 0.37;
        const reach = radius * (0.55 + (index % 3) * 0.18);
        const inner = reach * (0.35 + ease * 0.75);
        const outer = inner + 18 * (1 - t) + 4;
        return (
          <line
            key={index}
            x1={Math.cos(angle) * inner}
            y1={Math.sin(angle) * inner}
            x2={Math.cos(angle) * outer}
            y2={Math.sin(angle) * outer}
            stroke={index % 4 === 0 ? colors.paper : color}
            strokeWidth={3}
            strokeLinecap="round"
            opacity={1 - t}
          />
        );
      })}
    </svg>
  );
};

const DIGITS = "0123456789";
/** Taller than 1em so wide display glyphs never bleed into the next cell. */
const CELL = 1.4;

/**
 * Rolls each digit from `from` to `to`, one full turn plus the difference,
 * staggered left to right. Strings must share length and punctuation.
 */
export const Odometer = ({
  frame,
  at,
  from,
  to,
  span = 18,
  style,
}: {
  frame: number;
  at: number;
  from: string;
  to: string;
  span?: number;
  style?: CSSProperties;
}) => {
  return (
    <span style={{ display: "inline-flex", lineHeight: 1, ...style }}>
      {to.split("").map((char, index) => {
        const start = from[index] ?? char;
        if (!DIGITS.includes(char) || !DIGITS.includes(start)) {
          return (
            <span key={index} style={{ whiteSpace: "pre" }}>
              {char}
            </span>
          );
        }
        const a = Number(start);
        const b = Number(char);
        const travel = ((b - a + 10) % 10) + 10;
        const t = mix(frame, [at + index * 2, at + index * 2 + span], [0, 1]);
        const pos = a + travel * t;
        const blur = Math.sin(t * Math.PI);
        return (
          <span
            key={index}
            style={{
              position: "relative",
              display: "inline-block",
              height: `${CELL}em`,
              lineHeight: `${CELL}em`,
              margin: `${(1 - CELL) / 2}em 0`,
              overflow: "hidden",
              WebkitMaskImage: blur > 0.01 ? "linear-gradient(transparent, black 30%, black 70%, transparent)" : undefined,
            }}
          >
            <span style={{ visibility: "hidden" }}>{char}</span>
            <span
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                transform: `translateY(${-pos * CELL}em)`,
                opacity: 1 - blur * 0.35,
              }}
            >
              {Array.from({ length: 30 }, (_, n) => (
                <span key={n} style={{ height: `${CELL}em` }}>
                  {n % 10}
                </span>
              ))}
            </span>
          </span>
        );
      })}
    </span>
  );
};
