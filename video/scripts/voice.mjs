import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Voice for a news package, on Eleven v4.
 *
 *   node scripts/voice.mjs <newsId> [lineId ...]
 *
 * Reads news/<newsId>.json, writes public/filmes/<newsId>/voice/<line>.mp3.
 * v4 takes audio tags inside the text ("[excited] ...") and only stability and
 * similarity; pace is adjusted afterwards with ffmpeg atempo (news.voice.tempo).
 */

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");

const VOICE_ID = process.env.ELEVENLABS_VOICE_ID; // id da voz do canal (canais/<nome>.json ou .env)
if (!VOICE_ID) {
  console.error("ELEVENLABS_VOICE_ID vazio: escolha uma voz na ElevenLabs e ponha o id no .env");
  process.exit(1);
}
const MODEL_ID = process.env.ELEVENLABS_MODELO || "eleven_v4"; // modelo da ElevenLabs (ELEVENLABS_MODELO no .env)

const [newsId, ...only] = process.argv.slice(2);
if (!newsId) {
  console.error("uso: node scripts/voice.mjs <newsId> [lineId ...]");
  process.exit(1);
}

const news = JSON.parse(readFileSync(join(root, "news", `${newsId}.json`), "utf8"));
const outDir = join(root, "public", "filmes", newsId, "voice");
mkdirSync(outDir, { recursive: true });

const settings = {
  stability: news.voice?.stability ?? 0.5,
  similarity_boost: news.voice?.similarity ?? 0.8,
};
const tempo = news.voice?.tempo ?? 1;

const loadKey = () => {
  const key = (process.env.ELEVENLABS_API_KEY ?? "").trim();
  if (!key) {
    throw new Error("ELEVENLABS_API_KEY vazia no .env");
  }
  return key;
};

/** Credits ElevenLabs charged, from the `character-cost` response header (exact, per request). */
let credits = 0;

const speak = async (key, text) => {
  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}?output_format=mp3_44100_128`,
    {
      method: "POST",
      headers: { "xi-api-key": key, "Content-Type": "application/json", Accept: "audio/mpeg" },
      body: JSON.stringify({ text, model_id: MODEL_ID, language_code: "pt", voice_settings: settings }),
    },
  );
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail.slice(0, 300)}`);
  }
  credits += Number(response.headers.get("character-cost") ?? 0);
  return Buffer.from(await response.arrayBuffer());
};

const duration = (file) =>
  Number(
    execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", file])
      .toString()
      .trim(),
  );

const key = loadKey();
for (const beat of news.beats) {
  const line = beat.voice;
  if (only.length > 0 && !only.includes(line.id)) {
    continue;
  }
  const file = join(outDir, `${line.id}.mp3`);
  writeFileSync(file, await speak(key, line.text));
  if (tempo !== 1) {
    const tmp = join(outDir, `${line.id}.tmp.mp3`);
    execFileSync("ffmpeg", ["-v", "error", "-y", "-i", file, "-filter:a", `atempo=${tempo}`, "-b:a", "128k", tmp]);
    renameSync(tmp, file);
  }
  console.log(`${line.id} ${duration(file).toFixed(2)}s`);
}
console.log(`creditos ${credits}`);
