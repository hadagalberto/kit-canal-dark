import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { mix } from "../../film/mix";

export const LIME = "#D6FF3E";
export const ICE = "#8FDBFF";
export const PAPER = "#F4F0E6";
export const MUTED = "#A39E92";

export const rgba = (hex: string, a: number) => {
  const v = hex.replace("#", "");
  return `rgba(${parseInt(v.slice(0, 2), 16)},${parseInt(v.slice(2, 4), 16)},${parseInt(v.slice(4, 6), 16)},${a})`;
};

/** Deterministic noise so every render matches. */
const rnd = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

const BOKEH = Array.from({ length: 46 }, (_, i) => ({
  x: rnd(i) * 1080,
  y: rnd(i + 100) * 1920,
  depth: 0.2 + rnd(i + 200) * 0.8,
  size: 6 + rnd(i + 300) * 34,
  tone: rnd(i + 400) > 0.72 ? LIME : rnd(i + 500) > 0.5 ? ICE : PAPER,
}));

/** Dark teal void, drifting bokeh in depth, sweeping light shafts. */
export const Backdrop = ({ frame }: { frame: number }) => {
  const sweep = (frame % 260) / 260;
  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(ellipse at 50% 38%, #0E2A2E 0%, #071416 42%, #030607 78%)",
        overflow: "hidden",
      }}
    >
      {BOKEH.map((b, i) => {
        const drift = frame * (0.4 + b.depth * 1.6);
        const y = ((b.y - drift) % 1920 + 1920) % 1920;
        const x = b.x + Math.sin(frame / 40 + i) * 18 * b.depth;
        const size = b.size * (0.5 + b.depth);
        const twinkle = 0.5 + 0.5 * Math.sin(frame / 14 + i * 1.7);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background: `radial-gradient(circle, ${rgba(b.tone, 0.55 * b.depth)}, transparent 70%)`,
              opacity: 0.35 + twinkle * 0.5,
            }}
          />
        );
      })}
      {[0, 1].map((k) => {
        const t = (sweep + k * 0.5) % 1;
        return (
          <div
            key={k}
            style={{
              position: "absolute",
              left: interpolate(t, [0, 1], [-900, 1300]),
              top: -400,
              width: 340,
              height: 2800,
              transform: "rotate(24deg)",
              background: `linear-gradient(90deg, transparent, ${rgba(k ? ICE : LIME, 0.06)}, transparent)`,
            }}
          />
        );
      })}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(0,0,0,0.65) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * A card's life in depth: rises from far back (blurred), holds at z 0,
 * then flies past the camera. Frames are absolute film frames.
 */
export const Shot = ({
  frame,
  enter,
  leave,
  children,
  y = 0,
  side = 1,
}: {
  frame: number;
  enter: number;
  leave: number;
  children: ReactNode;
  y?: number;
  side?: 1 | -1;
}) => {
  if (frame < enter - 30 || frame > leave + 20) {
    return null;
  }
  const arrive = mix(frame, [enter - 30, enter + 10], [0, 1]);
  const go = mix(frame, [leave, leave + 18], [0, 1]);
  const z = interpolate(arrive, [0, 1], [-1800, 0]) + go * go * 900;
  const rotY = (1 - arrive) * -28 * side + go * 34 * side + Math.sin(frame / 50) * 4;
  const rotX = (1 - arrive) * 12 + Math.cos(frame / 60) * 3;
  const x = (1 - arrive) * 160 * side - go * 420 * side;
  const opacity = Math.min(arrive * 1.4, 1) * (1 - go);
  const blur = Math.max(0, (1 - arrive) * 10) + go * 6;
  const style: CSSProperties = {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transform: `translate3d(${x}px, ${y}px, ${z}px) rotateY(${rotY}deg) rotateX(${rotX}deg)`,
    opacity,
    filter: blur > 0.4 ? `blur(${blur.toFixed(1)}px)` : undefined,
    transformStyle: "preserve-3d",
  };
  return <div style={style}>{children}</div>;
};

/** Translucent pane with a thin bright rim and a specular band sliding across. */
export const Glass = ({
  frame,
  width,
  children,
  tone = LIME,
  shineAt = 0,
  style,
}: {
  frame: number;
  width: number;
  children: ReactNode;
  tone?: string;
  shineAt?: number;
  style?: CSSProperties;
}) => {
  const shine = ((frame - shineAt) % 120) / 120;
  return (
    <div
      style={{
        width,
        position: "relative",
        borderRadius: 40,
        padding: "48px 52px",
        background: `linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.03) 45%, ${rgba(tone, 0.06)})`,
        border: "1.5px solid rgba(255,255,255,0.22)",
        boxShadow: `0 60px 120px rgba(0,0,0,0.55), 0 0 80px ${rgba(tone, 0.12)}, inset 0 1px 0 rgba(255,255,255,0.35)`,
        overflow: "hidden",
        ...style,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: -200,
          bottom: -200,
          left: `${-60 + shine * 220}%`,
          width: "22%",
          transform: "rotate(20deg)",
          background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.16), transparent)",
          pointerEvents: "none",
        }}
      />
      <div style={{ position: "relative" }}>{children}</div>
    </div>
  );
};

/** Lens flare burst, used for the hook and the big numbers. */
export const Flare = ({ frame, at, x, y, tone = LIME }: { frame: number; at: number; x: number; y: number; tone?: string }) => {
  const t = mix(frame, [at, at + 6, at + 40], [0, 1, 0]);
  if (t <= 0.01) {
    return null;
  }
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: x - 500,
          top: y - 40,
          width: 1000,
          height: 80,
          borderRadius: "50%",
          background: `radial-gradient(ellipse, ${rgba(tone, 0.7 * t)}, transparent 70%)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: x - 220,
          top: y - 220,
          width: 440,
          height: 440,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${rgba("#FFFFFF", 0.5 * t)}, ${rgba(tone, 0.25 * t)} 30%, transparent 68%)`,
        }}
      />
    </>
  );
};
