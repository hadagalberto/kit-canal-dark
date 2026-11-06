import { loadFont as loadOutfit } from "@remotion/google-fonts/Outfit";
import { loadFont as loadSyne } from "@remotion/google-fonts/Syne";

const syne = loadSyne("normal", {
  weights: ["700", "800"],
  subsets: ["latin"],
});

const outfit = loadOutfit("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

export const display = syne.fontFamily;
export const sans = outfit.fontFamily;

export type PaletteId = "lima" | "ciano" | "ambar" | "rosa";

const shared = {
  ink: "#090A0C",
  paper: "#F4F0E6",
  muted: "#A39E92",
  line: "rgba(244,240,230,0.16)",
};

/** Same ink, paper and type. Only the accent pair changes. */
export const palettes: Record<PaletteId, { lime: string; ice: string; coral: string }> = {
  lima: { lime: "#D6FF3E", ice: "#8FDBFF", coral: "#FF5A36" },
  ciano: { lime: "#3EFFF1", ice: "#9EB6FF", coral: "#FF5A36" },
  ambar: { lime: "#FFC53D", ice: "#FF8B6B", coral: "#FF5A36" },
  rosa: { lime: "#FF6AD5", ice: "#8FD4FF", coral: "#FF5A36" },
};

export const colors = {
  ...shared,
  ...palettes.lima,
};

export const applyPalette = (id: PaletteId = "lima") => {
  const next = palettes[id] ?? palettes.lima;
  colors.lime = next.lime;
  colors.ice = next.ice;
  colors.coral = next.coral;
};

export const tint = (hex: string, alpha: number) => {
  const value = hex.replace("#", "");
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
};
