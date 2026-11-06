import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Stills of one style for one news, to check layout without a full render.
 *
 *   node scripts/stills.mjs <style> <newsId> [frame ...]
 *
 * Without frames: for every beat that has `media`, a frame 8 frames into each
 * phase and one in the middle; plus the first frame of the end card. Writes
 * out/filmes/<id>/stills/<style>-<frame>.png and a contact sheet
 * out/filmes/<id>/stills/<style>-sheet.png (labelled by frame). Runs
 * scripts/story.mjs first so props.json is fresh. Voice must exist.
 */

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const [style, newsId, ...given] = process.argv.slice(2);
if (!style || !newsId) {
  console.error("uso: node scripts/stills.mjs <estilo> <newsId> [frame ...]");
  process.exit(1);
}

execFileSync("node", [join(root, "scripts", "story.mjs"), newsId], { stdio: "ignore" });
const story = JSON.parse(readFileSync(join(root, "public", "filmes", newsId, "story.json"), "utf8"));

let frames = given.map(Number).filter((n) => Number.isFinite(n));
if (frames.length === 0) {
  story.beats.forEach((beat, i) => {
    const timing = story.timing.beats[i];
    if (beat.media) {
      for (const phase of timing.phases) {
        frames.push(phase.from + 8, Math.round((phase.from + phase.to) / 2));
      }
    }
  });
  const end = story.timing.beats.at(-1);
  frames.push(end.from + 30);
}
frames = [...new Set(frames)].sort((a, b) => a - b).filter((f) => f < story.timing.total);

const entry = join(root, "src", "styles", style, "entry.tsx");
if (!existsSync(entry)) {
  console.error(`estilo desconhecido: ${style}`);
  process.exit(1);
}
const composition = `Estilo-${style[0].toUpperCase()}${style.slice(1)}`;
const props = join(root, "out", "filmes", newsId, "props.json");
const dir = join(root, "out", "filmes", newsId, "stills");
mkdirSync(dir, { recursive: true });

const files = [];
for (const frame of frames) {
  const file = join(dir, `${style}-${frame}.png`);
  const r = spawnSync(
    ["npx", "remotion", "still", `"${entry}"`, composition, `"${file}"`, `--props="${props}"`, `--frame=${frame}`, "--log=error"].join(" "),
    { cwd: root, stdio: "inherit", shell: true },
  );
  if (r.status !== 0) {
    console.error(`falhou no frame ${frame}`);
    process.exit(1);
  }
  files.push({ file, frame });
}

// Contact sheet: up to 6 per row, 270×480 each, frame number burned in.
const cols = Math.min(6, files.length);
const inputs = files.flatMap(({ file }) => ["-i", file]);
const scaled = files
  .map(({ frame }, i) => `[${i}]scale=270:480,drawtext=text='${frame}':x=8:y=8:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[s${i}]`)
  .join(";");
const rows = [];
for (let i = 0; i < files.length; i += cols) {
  const group = files.slice(i, i + cols).map((_, j) => `[s${i + j}]`);
  while (group.length < cols) {
    group.push(`[pad${i}_${group.length}]`);
  }
  rows.push(group);
}
const pads = rows
  .flatMap((group) => group.filter((g) => g.startsWith("[pad")).map((g) => `color=black:s=270x480:d=1${g}`))
  .join(";");
const stacked = rows
  .map((group, r) => (cols === 1 ? `${group[0]}null[r${r}]` : `${group.join("")}hstack=inputs=${cols}[r${r}]`))
  .join(";");
const final = rows.length > 1 ? `;${rows.map((_, r) => `[r${r}]`).join("")}vstack=inputs=${rows.length}[out]` : "";
const graph = [scaled, pads, stacked].filter(Boolean).join(";") + final;
const sheet = join(dir, `${style}-sheet.png`);
try {
  execFileSync("ffmpeg", ["-v", "error", "-y", ...inputs, "-filter_complex", graph, "-map", rows.length > 1 ? "[out]" : "[r0]", "-frames:v", "1", sheet], { stdio: "ignore" });
  console.log(sheet);
} catch {
  // The sheet is a convenience: drawtext can crash when Fontconfig is broken. The PNGs above are already written.
  console.error("folha de contato não gerada (ffmpeg/drawtext); os PNGs individuais estão em " + dir);
}
