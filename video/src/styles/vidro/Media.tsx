import type { ReactNode } from "react";
import { interpolate } from "remotion";
import { mix, pop } from "../../film/mix";
import { Credit, Logo, Photo } from "../../news/media";
import type { LogoMedia, PhotoMedia, Story } from "../../news/types";
import { ICE, LIME, PAPER, rgba } from "./Space";

/**
 * Media in the glass style. Everything here only renders on beats that carry
 * `media`; a beat without it never touches this file.
 *
 * - Logo: a round glass seal pinned to a corner of the card, floating in front.
 * - Photo: a glass pane above the card, a little deeper in z, with its own
 *   (unblurred) copy of the Shot motion, slow parallax and a sliding reflection.
 *
 * Cost: no blur, no backdrop-filter, no animated filter. Only transform and
 * opacity move; the glass, sheen and scrim are fixed gradient layers.
 */

/** Photo beats: the card drops by this much (stage px) and shrinks to make room for the pane. */
export const PHOTO_CARD_Y = 262;
export const PHOTO_CARD_SCALE = 0.84;

/** Pane box, in stage coordinates (the stage starts at screen y 200). */
const PANE_TOP = 6;
const PANE_W = 700;
const PANE_H = 500;
const PANE_Z = -140;
const FRAME = 12;

/**
 * Seal size and corner. A compare beat with a stamp already uses the top-right
 * corner, so there the seal goes to the bottom-right.
 */
const SEAL = 146;

export const Seal = ({ frame, logo, enter, bottom }: { frame: number; logo: LogoMedia; enter: number; bottom?: boolean }) => {
  const s = pop(frame, enter + 4);
  const bob = Math.sin(frame / 30) * 6;
  const tilt = Math.sin(frame / 46) * 4;
  const breathe = 0.55 + 0.45 * (0.5 + 0.5 * Math.sin(frame / 22));
  const shine = (((frame - enter) % 150) + 150) % 150 / 150;
  const corner = bottom ? { bottom: -SEAL * 0.32 } : { top: -SEAL * 0.36 };
  return (
    <div
      style={{
        position: "absolute",
        right: -SEAL * 0.1,
        ...corner,
        width: SEAL,
        height: SEAL,
        opacity: Math.min(1, s * 1.4),
        transform: `translate3d(0, ${bob + (1 - s) * 30}px, 60px) scale(${0.6 + s * 0.4}) rotate(${tilt + (1 - s) * -20}deg)`,
      }}
    >
      {/* Soft glow: a fixed radial halo, only its opacity breathes. */}
      <div
        style={{
          position: "absolute",
          inset: -SEAL * 0.45,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${rgba(LIME, 0.32)} 0%, ${rgba(LIME, 0.1)} 38%, transparent 68%)`,
          opacity: breathe,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          overflow: "hidden",
          // Glass over a dark tinted base, so the card rim behind never shows through.
          background: `linear-gradient(145deg, rgba(255,255,255,0.24), rgba(255,255,255,0.05) 52%, ${rgba(LIME, 0.12)}), radial-gradient(circle at 50% 40%, #12343A, #081719)`,
          border: "1.5px solid rgba(255,255,255,0.42)",
          boxShadow: `0 24px 50px rgba(0,0,0,0.5), 0 0 40px ${rgba(LIME, 0.22)}, inset 0 2px 0 rgba(255,255,255,0.45), inset 0 -10px 24px ${rgba(LIME, 0.1)}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: -SEAL,
            bottom: -SEAL,
            left: 0,
            width: SEAL * 0.32,
            background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.28), transparent)",
            transform: `translateX(${-SEAL * 0.6 + shine * SEAL * 2.2}px) rotate(24deg)`,
          }}
        />
        <Logo logo={logo} size={Math.round(SEAL * 0.5)} color={PAPER} glow={rgba(LIME, 0.8)} />
      </div>
    </div>
  );
};

/** Card with a seal on its corner. The wrapper only exists on logo beats. */
export const WithSeal = ({ children, frame, logo, enter, bottom }: { children: ReactNode; frame: number; logo: LogoMedia; enter: number; bottom?: boolean }) => (
  <div style={{ position: "relative", transformStyle: "preserve-3d" }}>
    {children}
    <Seal frame={frame} logo={logo} enter={enter} bottom={bottom ?? false} />
  </div>
);

/**
 * The photo pane's life: same arrive/leave curve as `Shot` (so it travels with
 * its card), but no blur, a little deeper, and a slower counter-float that
 * reads as parallax against the card in front.
 */
export const PhotoPane = ({
  frame,
  story,
  photo,
  enter,
  leave,
  from,
  to,
  side,
  seed,
}: {
  frame: number;
  story: Story;
  photo: PhotoMedia;
  enter: number;
  leave: number;
  from: number;
  to: number;
  side: 1 | -1;
  seed: number;
}) => {
  if (frame < enter - 30 || frame > leave + 20) {
    return null;
  }
  const arrive = mix(frame, [enter - 30, enter + 10], [0, 1]);
  const go = mix(frame, [leave, leave + 18], [0, 1]);
  const z = interpolate(arrive, [0, 1], [-1800, 0]) + go * go * 900 + PANE_Z;
  const rotY = (1 - arrive) * -28 * side + go * 34 * side - Math.sin(frame / 50) * 2.5;
  const rotX = (1 - arrive) * 12 - Math.cos(frame / 60) * 2;
  const x = (1 - arrive) * 160 * side - go * 420 * side + Math.sin(frame / 64) * 10;
  const y = Math.cos(frame / 72) * 6;
  // A sharp photo would show through the previous (translucent) card while it
  // is still leaving, so the pane fades in only once that card is on its way out.
  const fadeIn = enter <= 0 ? Math.min(arrive * 1.4, 1) : mix(frame, [enter - 4, enter + 12], [0, 1]);
  const opacity = fadeIn * (1 - go);
  const shine = (((frame - enter) % 180) + 180) % 180 / 180;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: PANE_TOP,
        height: PANE_H,
        display: "flex",
        justifyContent: "center",
        transform: `translate3d(${x}px, ${y}px, ${z}px) rotateY(${rotY}deg) rotateX(${rotX}deg)`,
        opacity,
      }}
    >
      <div
        style={{
          position: "relative",
          width: PANE_W,
          height: PANE_H,
          borderRadius: 38,
          overflow: "hidden",
          background: `linear-gradient(145deg, rgba(255,255,255,0.2), rgba(255,255,255,0.04) 45%, ${rgba(ICE, 0.1)})`,
          border: "1.5px solid rgba(255,255,255,0.3)",
          boxShadow: `0 60px 110px rgba(0,0,0,0.6), 0 0 70px ${rgba(ICE, 0.14)}, inset 0 1px 0 rgba(255,255,255,0.4)`,
        }}
      >
        <Photo
          story={story}
          photo={photo}
          frame={frame}
          from={from}
          to={to}
          seed={seed}
          amount={0.07}
          style={{ position: "absolute", left: FRAME, top: FRAME, right: FRAME, bottom: FRAME, borderRadius: 28 }}
        />
        {/* Glass over the photo: a fixed diagonal sheen, an edge tint and a scrim for the credit. */}
        <div
          style={{
            position: "absolute",
            left: FRAME,
            top: FRAME,
            right: FRAME,
            bottom: FRAME,
            borderRadius: 28,
            background: `linear-gradient(155deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.04) 26%, transparent 42%), linear-gradient(180deg, transparent 58%, rgba(3,6,7,0.72) 100%)`,
            boxShadow: `inset 0 0 0 1px rgba(255,255,255,0.18), inset 0 0 50px ${rgba("#030607", 0.45)}`,
          }}
        />
        <div
          style={{
            position: "absolute",
            top: -200,
            bottom: -200,
            left: 0,
            width: PANE_W * 0.16,
            background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.13), transparent)",
            transform: `translateX(${-PANE_W * 0.3 + shine * PANE_W * 1.6}px) rotate(20deg)`,
          }}
        />
        <Credit photo={photo} color={PAPER} size={22} style={{ position: "absolute", left: FRAME + 24, bottom: FRAME + 18 }} />
      </div>
    </div>
  );
};
