import type { CSSProperties } from "react";
import { Img, interpolate, Loop, OffthreadVideo, staticFile } from "remotion";
import { sans } from "../theme";
import type { Beat, LogoMedia, Media, PhotoMedia, Phase, Story } from "./types";

/**
 * Media shared by the 8 styles. A beat may carry one `media` (see types.ts):
 * a brand logo (logo.dev image, shown as an app-icon tile) or a photo (official
 * press image or AI illustration) with its credit printed next to it.
 *
 * Rules for styles:
 * - A beat without `media` must render exactly as before.
 * - Media never covers the caption block or the top bar, and stays inside the
 *   safe zone (60 px sides, y 90–1700).
 * - Remotion waits for <Img> and inline SVG only: never load a photo or logo as
 *   a CSS background or mask, or the frame can be captured blank.
 * - Keep per-frame cost low: transforms and opacity are cheap; filters
 *   (blur, saturate, drop-shadow) over a big photo on every frame are not.
 */

export const mediaOf = (beat: Beat): Media | undefined => beat.media;
export const logoOf = (beat: Beat): LogoMedia | undefined => (beat.media?.kind === "logo" ? beat.media : undefined);
export const photoOf = (beat: Beat): PhotoMedia | undefined => (beat.media?.kind === "photo" ? beat.media : undefined);

export const photoSrc = (story: Story, photo: PhotoMedia) => staticFile(`filmes/${story.id}/media/${photo.file}`);

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0→1 over `frames` from `at`. */
export const reveal = (frame: number, at: number, frames = 10) => interpolate(frame, [at, at + frames], [0, 1], clamp);

/** Relative luminance 0..1 of a #RRGGBB / #RGB color (anything else counts as dark). */
const luminance = (color: string) => {
  const hex = color.trim().replace("#", "");
  const full = hex.length === 3 ? hex.split("").map((c) => c + c).join("") : hex;
  if (!/^[0-9a-fA-F]{6}$/.test(full)) return 0;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16) / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

/** Static path of the logo image for a foreground of `color`: the dark-theme file when the ink is light. */
export const logoSrc = (logo: LogoMedia, color: string) => staticFile(luminance(color) > 0.5 ? logo.srcDark : logo.src);

/**
 * Brand logo from logo.dev: a square brand icon (often a tile with its own
 * background; sometimes a transparent mark, then the light or dark theme file
 * is picked from `color`, the ink of the spot it sits in). Shown as an app-icon
 * tile with rounded corners and a thin ring in `color`, so it belongs to the
 * style without recoloring the brand. `glow` adds a static drop-shadow;
 * `outline` (neon) drops the ring and lets the glow carry the shape.
 * Same props as the old vector version, so the styles did not change.
 */
export const Logo = ({
  logo,
  size,
  color,
  style,
  outline,
  glow,
}: {
  logo: LogoMedia;
  size: number;
  color: string;
  style?: CSSProperties;
  outline?: boolean;
  strokeWidth?: number;
  glow?: string;
}) => (
  <div
    role="img"
    aria-label={logo.name}
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.22,
      overflow: "hidden",
      flexShrink: 0,
      boxShadow: outline ? undefined : `0 0 0 ${Math.max(1.5, size * 0.025)}px ${color}`,
      filter: glow ? `drop-shadow(0 0 ${size * 0.08}px ${glow})` : undefined,
      ...style,
    }}
  >
    <Img src={logoSrc(logo, color)} style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }} />
  </div>
);

/**
 * Ken Burns move for a photo over a phase: slow zoom and drift. `seed` picks
 * the direction so two photos in one reel do not move the same way.
 */
export const kenBurns = (frame: number, from: number, to: number, seed = 0, amount = 0.08) => {
  const t = interpolate(frame, [from, Math.max(from + 1, to)], [0, 1], clamp);
  const dir = seed % 2 === 0 ? 1 : -1;
  return `scale(${1 + amount * (seed % 3 === 2 ? 1 - t : t)}) translate(${dir * t * 2.2}%, ${-t * 1.4}%)`;
};

/**
 * Photo filling its box (object-fit cover) with a Ken Burns move. The box is
 * the caller's: give it position, size, border, rotation. `filter` is applied
 * once on the <Img> (static, so the browser can cache it).
 */
export const Photo = ({
  story,
  photo,
  frame,
  from,
  to,
  seed = 0,
  amount,
  filter,
  position = "center",
  style,
}: {
  story: Story;
  photo: PhotoMedia;
  frame: number;
  from: number;
  to: number;
  seed?: number;
  amount?: number;
  filter?: string;
  position?: string;
  style?: CSSProperties;
}) => {
  const fill: CSSProperties = {
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    objectFit: "cover",
    objectPosition: position,
    transform: kenBurns(frame, from, to, seed, amount),
    filter,
  };
  return (
    <div style={{ position: "relative", overflow: "hidden", ...style }}>
      {photo.video && photo.videoFrames ? (
        // trailer clip, muted, looping over the whole reel so it always has a frame (styles fade it in before `from`)
        <Loop durationInFrames={photo.videoFrames} layout="none">
          <OffthreadVideo src={staticFile(`filmes/${story.id}/media/${photo.video}`)} muted style={fill} />
        </Loop>
      ) : (
        <Img src={photoSrc(story, photo)} style={fill} />
      )}
    </div>
  );
};

/** Credit line ("Imagem: Google", "Imagem ilustrativa gerada por IA"). Always visible with the photo. */
export const Credit = ({ photo, color, size = 20, style }: { photo: PhotoMedia; color: string; size?: number; style?: CSSProperties }) => (
  <div
    style={{
      fontFamily: sans,
      fontWeight: 600,
      fontSize: size,
      letterSpacing: "0.04em",
      color,
      textShadow: "0 1px 3px rgba(0,0,0,0.55)",
      whiteSpace: "nowrap",
      ...style,
    }}
  >
    {photo.credit}
  </div>
);

/** Frames of the beat (first phase start to last phase end), for media that spans a multi-phase beat. */
export const beatSpan = (phases: Phase[]) => ({ from: phases[0].from, to: phases[phases.length - 1].to });
