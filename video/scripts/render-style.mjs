import { execFileSync, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * One command from news package to MP4. This is what pipeline/video.py calls.
 *
 *   node scripts/render-style.mjs <style> <newsId> [--frames=0-60]
 *
 * 1. story.mjs   validate the package, measure the voice, derive every frame
 * 2. make-audio  bed + this style's cues at the story's length
 * 3. remotion    render through the style's own entry (a broken neighbor style
 *                cannot block it)
 * 4. ffprobe     1080×1920, 30 fps, h264 + aac, duration = timing.total
 *
 * Voice must exist already (scripts/voice.mjs <newsId>), so a re-render never
 * spends ElevenLabs credits. Prints the MP4 path on the last line.
 */

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");

const [style, newsId, ...rest] = process.argv.slice(2);
if (!style || !newsId) {
  console.error("uso: node scripts/render-style.mjs <estilo> <newsId> [--frames=A-B]");
  process.exit(1);
}

const entry = join(root, "src", "styles", style, "entry.tsx");
if (!existsSync(entry)) {
  console.error(`estilo desconhecido: ${style}`);
  process.exit(1);
}
const composition = `Estilo-${style[0].toUpperCase()}${style.slice(1)}`;
const frames = rest.find((arg) => arg.startsWith("--frames="));

const run = (command, args) => {
  const result = spawnSync([command, ...args].join(" "), { cwd: root, stdio: "inherit", shell: true });
  if (result.status !== 0) {
    console.error(`falhou: ${command} ${args.join(" ")}`);
    process.exit(result.status ?? 1);
  }
};

run("node", ["scripts/story.mjs", newsId]);
run("node", ["scripts/make-audio.mjs", style, "--story", newsId]);

const out = join(root, "out", "filmes", newsId, frames ? `${style}-trecho.mp4` : `${style}.mp4`);
const props = join(root, "out", "filmes", newsId, "props.json");
run("npx", [
  "remotion", "render", `"${entry}"`, composition, `"${out}"`,
  `--props="${props}"`, "--codec=h264", "--crf=18", `--concurrency=${process.env.RENDER_CONCURRENCY ?? 4}`, "--log=error",
  ...(frames ? [frames] : []),
]);

const probe = execFileSync("ffprobe", [
  "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height,avg_frame_rate", "-of", "json", out,
]).toString();
const info = JSON.parse(probe);
const video = info.streams.find((s) => s.width);
const audio = info.streams.find((s) => !s.width);
const ok = video?.codec_name === "h264" && video.width === 1080 && video.height === 1920 && video.avg_frame_rate === "30/1" && audio?.codec_name === "aac";
if (!ok) {
  console.error(`MP4 fora do padrão: ${probe}`);
  process.exit(1);
}
console.log(`ok ${Number(info.format.duration).toFixed(2)}s`);
console.log(out);
