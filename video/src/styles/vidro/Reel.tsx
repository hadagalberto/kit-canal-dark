import { Fragment, type ReactNode } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Odometer } from "../../film/kinetic";
import { mix, pop } from "../../film/mix";
import { logoOf, photoOf } from "../../news/media";
import { PHOTO_CARD_SCALE, PHOTO_CARD_Y, PhotoPane, WithSeal } from "./Media";
import { fit, mark, phasesOf, StorySound } from "../../news/story";
import type { Beat, BeatTiming, Phase, Story, StoryProps } from "../../news/types";
import { sans } from "../../theme";
import { Backdrop, Flare, Glass, ICE, LIME, MUTED, PAPER, Shot, rgba } from "./Space";

/** Outfit 700 average glyph width in em, for `fit`. */
const EM = 0.6;
/** Text column inside a card: 820 wide minus 52 px padding each side. */
const INNER = 716;
const RED = "#FF5A36";

/** Card accent: lime on even beats, ice on odd ones, so neighbors never match. */
const toneOf = (index: number, beat: Beat) => (beat.type === "hero" || beat.type === "end" || index % 2 === 0 ? LIME : ICE);

export const Reel = ({ story }: StoryProps) => {
  const frame = useCurrentFrame();
  const total = story.timing.total;
  const orbitY = Math.sin(frame / 70) * 5;
  const orbitX = 4 + Math.cos(frame / 90) * 3;
  const dolly = 1 + (frame / total) * 0.06;

  return (
    <AbsoluteFill>
      <StorySound story={story} style="vidro" />
      <Backdrop frame={frame} />
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 200,
          height: 1060,
          perspective: 1400,
          perspectiveOrigin: "50% 45%",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            transformStyle: "preserve-3d",
            transform: `rotateX(${orbitX}deg) rotateY(${orbitY}deg) scale(${dolly})`,
          }}
        >
          {story.beats.map((beat, index) => {
            const timing = story.timing.beats[index];
            // The first card is already almost home at frame 0: no dark opening.
            const enter = index === 0 ? -6 : timing.from;
            const leave = index === story.beats.length - 1 ? total + 30 : timing.to - 6;
            const side = index % 2 === 0 ? 1 : -1;
            const logo = logoOf(beat);
            const photo = photoOf(beat);
            const card = <Card frame={frame} story={story} beat={beat} timing={timing} tone={toneOf(index, beat)} />;
            if (!logo && !photo) {
              return (
                <Shot key={beat.voice.id} frame={frame} enter={enter} leave={leave} side={side}>
                  {card}
                </Shot>
              );
            }
            // Media beats only (see Media.tsx). Pane first so it sits behind the card.
            const sealed = logo ? (
              <WithSeal frame={frame} logo={logo} enter={enter} bottom={beat.type === "compare" && Boolean(beat.stamp)}>
                {card}
              </WithSeal>
            ) : (
              card
            );
            return (
              <Fragment key={beat.voice.id}>
                {photo ? (
                  <PhotoPane frame={frame} story={story} photo={photo} enter={enter} leave={leave} from={timing.from} to={timing.to} side={side} seed={index} />
                ) : null}
                <Shot frame={frame} enter={enter} leave={leave} side={side} {...(photo ? { y: PHOTO_CARD_Y } : {})}>
                  {photo ? <div style={{ transform: `scale(${PHOTO_CARD_SCALE})`, transformStyle: "preserve-3d" }}>{sealed}</div> : sealed}
                </Shot>
              </Fragment>
            );
          })}
        </div>
        {story.timing.events.hits
          .filter((hit) => hit.power >= 30)
          .map((hit, i) => (
            <Flare key={hit.at} frame={frame} at={hit.at} x={540} y={i % 2 === 0 ? 520 : 700} tone={i % 3 === 2 ? ICE : LIME} />
          ))}
      </div>
      <Top story={story} />
      <ImpactLine frame={frame} story={story} />
    </AbsoluteFill>
  );
};

const Top = ({ story }: { story: Story }) => (
  <div
    style={{
      position: "absolute",
      top: 108,
      left: 72,
      right: 72,
      display: "flex",
      justifyContent: "space-between",
      fontFamily: sans,
      letterSpacing: "0.16em",
    }}
  >
    <span style={{ color: PAPER, fontWeight: 700, fontSize: 24 }}>
      {story.brand.short}
      <span style={{ display: "block", marginTop: 8, color: MUTED, fontWeight: 500, fontSize: 22, letterSpacing: "0.02em" }}>
        {story.brand.tagline}
      </span>
    </span>
    <span style={{ color: MUTED, fontWeight: 500, fontSize: 22 }}>{story.date}</span>
  </div>
);

/** The caption of each beat. Lines with a number glow; otherwise the last line does. */
const ImpactLine = ({ frame, story }: { frame: number; story: Story }) => {
  const index = story.timing.beats.findIndex((t) => frame >= t.from && frame < t.to);
  const beat = story.beats[index];
  if (!beat || beat.type === "end") {
    return null;
  }
  const timing = story.timing.beats[index];
  const from = timing.from + 4;
  const leave = mix(frame, [timing.to - 10, timing.to], [1, 0]);
  const kick = pop(frame, from);
  const rows = beat.caption.text.split("\n");
  const numbered = rows.some((row) => /\d/.test(row));
  return (
    <div style={{ position: "absolute", left: 72, right: 72, top: 1330, opacity: leave }}>
      <div
        style={{
          fontFamily: sans,
          fontWeight: 600,
          fontSize: 26,
          letterSpacing: "0.14em",
          color: LIME,
          opacity: kick,
          textShadow: `0 0 18px ${rgba(LIME, 0.5)}`,
        }}
      >
        {beat.caption.kicker}
      </div>
      <div style={{ marginTop: 18 }}>
        {rows.map((row, i) => {
          const rise = pop(frame, from + 4 + i * 5);
          const hot = numbered ? /\d/.test(row) : i === rows.length - 1;
          return (
            <div key={row} style={{ overflow: "hidden", paddingBottom: 6, filter: hot ? `drop-shadow(0 0 22px ${rgba(LIME, 0.5)})` : undefined }}>
              <div
                style={{
                  fontFamily: sans,
                  fontWeight: 700,
                  fontSize: fit(row, 936, 92, 0.56),
                  lineHeight: 1.04,
                  letterSpacing: "-0.03em",
                  color: hot ? LIME : PAPER,
                  transform: `translateY(${(1 - rise) * 110}%)`,
                }}
              >
                {row}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const Label = ({ children, tone = PAPER }: { children: string; tone?: string }) => (
  <div style={{ fontFamily: sans, fontWeight: 700, fontSize: 24, letterSpacing: "0.18em", color: tone, textTransform: "uppercase" }}>{children}</div>
);

const Sub = ({ children }: { children: ReactNode }) => (
  <div style={{ fontFamily: sans, fontSize: 26, color: MUTED, marginTop: 8 }}>{children}</div>
);

/** Big gradient number or word, the hero of a card. */
const Hero = ({ text, tone, max }: { text: string; tone: string; max: number }) => (
  <div
    style={{
      fontFamily: sans,
      fontWeight: 700,
      fontSize: fit(text, INNER, max, 0.74),
      lineHeight: 0.98,
      letterSpacing: "-0.05em",
      marginTop: 10,
      background: `linear-gradient(180deg, #FFFFFF, ${tone} 70%)`,
      WebkitBackgroundClip: "text",
      color: "transparent",
      filter: `drop-shadow(0 0 40px ${rgba(tone, 0.45)})`,
      whiteSpace: "nowrap",
    }}
  >
    {text}
  </div>
);

const Rise = ({ frame, at, children, x = 0 }: { frame: number; at: number; children: ReactNode; x?: number }) => {
  const s = pop(frame, at);
  return <div style={{ opacity: s, transform: `translate(${(1 - s) * x}px, ${(1 - s) * (x ? 0 : 30)}px)` }}>{children}</div>;
};

/** "72,4%" → same prefix, suffix and decimals as the display string. */
const counter = (display: string, value: number) => {
  const prefix = display.match(/^[^\d]*/)?.[0] ?? "";
  const suffix = display.match(/[^\d]*$/)?.[0] ?? "";
  const decimals = (display.slice(prefix.length, display.length - suffix.length).split(/[.,]/)[1] ?? "").length;
  return `${prefix}${value.toFixed(decimals).replace(".", ",")}${suffix}`;
};

const Card = ({ frame, story, beat, timing, tone }: { frame: number; story: Story; beat: Beat; timing: BeatTiming; tone: string }) => {
  const main = timing.phases[0];
  const m = (name: string) => mark(main, name);
  const shine = timing.from + 10;
  const border = tone === ICE ? { border: `1.5px solid ${rgba(ICE, 0.4)}` } : undefined;

  switch (beat.type) {
    case "hero":
      return (
        <Glass frame={frame} width={820} shineAt={shine} tone={tone}>
          <Label tone={MUTED}>{beat.kicker}</Label>
          {beat.highlight ? (
            <div style={{ fontFamily: sans, fontWeight: 700, fontSize: fit(beat.title, INNER, 96, EM), letterSpacing: "-0.03em", color: PAPER, marginTop: 14, lineHeight: 1 }}>
              {beat.title}
            </div>
          ) : null}
          <Hero text={beat.highlight ?? beat.title} tone={tone} max={300} />
          {beat.chips && beat.chips.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 18, marginTop: 26 }}>
              {beat.chips.map((chip, i) => (
                <Chip key={chip} frame={frame} at={m("chips") + i * 12} text={chip} tone={tone} />
              ))}
            </div>
          ) : null}
        </Glass>
      );
    case "statement":
      return (
        <Glass frame={frame} width={820} shineAt={shine} tone={tone} style={border}>
          <Label tone={MUTED}>{beat.kicker}</Label>
          <Rise frame={frame} at={m("text")}>
            <div
              style={{
                fontFamily: sans,
                fontWeight: 700,
                fontSize: Math.max(64, fit(beat.text, INNER * 2.2, 120, EM)),
                lineHeight: 1.02,
                letterSpacing: "-0.04em",
                marginTop: 18,
                color: PAPER,
                textShadow: `0 0 40px ${rgba(tone, 0.35)}`,
              }}
            >
              {beat.text}
            </div>
          </Rise>
        </Glass>
      );
    case "stat":
      return (
        <Glass frame={frame} width={820} shineAt={shine} tone={tone} style={border}>
          <Rise frame={frame} at={m("value")}>
            <Hero text={beat.value} tone={tone} max={220} />
          </Rise>
          <Rise frame={frame} at={m("label")}>
            <div style={{ fontFamily: sans, fontWeight: 600, fontSize: 38, lineHeight: 1.2, color: PAPER, marginTop: 20 }}>{beat.label}</div>
          </Rise>
          {beat.note ? (
            <Rise frame={frame} at={m("label") + 12}>
              <Sub>{beat.note}</Sub>
            </Rise>
          ) : null}
        </Glass>
      );
    case "compare": {
      const stamp = timing.phases.find((p) => p.kind === "stamp");
      const items = timing.phases.filter((p) => p.kind === "item");
      const badge = stamp ? pop(frame, mark(stamp, "stamp")) : 0;
      const last = items[items.length - 1];
      const noteAt = stamp ? mark(stamp, "label") + 10 : mark(last, "after") + 14;
      return (
        <Glass frame={frame} width={840} shineAt={shine} tone={tone} style={border}>
          <div style={{ maxWidth: beat.stamp ? 520 : INNER }}>
            <Label>{beat.label}</Label>
          </div>
          {items.map((phase) => (
            <PriceRow key={phase.index} frame={frame} phase={phase} item={beat.items[phase.index ?? 0]} tone={tone} count={beat.items.length} />
          ))}
          {beat.stamp && stamp ? (
            <Rise frame={frame} at={mark(stamp, "label")}>
              <Sub>{beat.stamp.label}</Sub>
            </Rise>
          ) : null}
          {beat.note ? (
            <Rise frame={frame} at={noteAt}>
              <div
                style={{
                  display: "inline-block",
                  marginTop: 24,
                  padding: "14px 24px",
                  borderRadius: 99,
                  background: rgba(tone, 0.14),
                  border: `1.5px solid ${rgba(tone, 0.55)}`,
                  fontFamily: sans,
                  fontWeight: 600,
                  fontSize: 28,
                  color: PAPER,
                }}
              >
                {beat.note}
              </div>
            </Rise>
          ) : null}
          {beat.stamp ? (
            <div
              style={{
                position: "absolute",
                right: 40,
                top: 40,
                padding: "14px 26px",
                borderRadius: 999,
                background: tone,
                color: "#071416",
                fontFamily: sans,
                fontWeight: 800,
                fontSize: fit(beat.stamp.value, 220, 64, EM),
                letterSpacing: "-0.03em",
                boxShadow: `0 0 60px ${rgba(tone, 0.6)}`,
                opacity: Math.min(1, badge * 1.3),
                transform: `scale(${0.4 + badge * 0.6}) rotate(${(1 - badge) * 20 + 6}deg)`,
              }}
            >
              {beat.stamp.value}
            </div>
          ) : null}
        </Glass>
      );
    }
    case "bars": {
      const max = beat.max ?? Math.max(...beat.items.map((item) => item.value));
      return (
        <Glass frame={frame} width={840} shineAt={shine} tone={tone} style={border}>
          <Label>{beat.label}</Label>
          {beat.items.map((item, i) => (
            <Bar
              key={item.name}
              frame={frame}
              name={item.name}
              share={item.value / max}
              value={item.value}
              display={item.display}
              enter={m("label") + 4 + i * 8}
              from={m("countFrom")}
              to={m("countTo")}
              tone={item.highlight ? tone : MUTED}
              small={beat.items.length > 2}
            />
          ))}
          {beat.note ? (
            <Rise frame={frame} at={m("countTo") + 10}>
              <Sub>{beat.note}</Sub>
            </Rise>
          ) : null}
        </Glass>
      );
    }
    case "list":
      return (
        <Glass frame={frame} width={820} shineAt={shine} tone={tone} style={border}>
          <Label tone={MUTED}>{beat.label}</Label>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 24 }}>
            {beat.items.map((item, i) => (
              <Rise key={item} frame={frame} at={m(`item${i}`)} x={-40}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 20,
                    padding: "20px 26px",
                    borderRadius: 26,
                    background: "rgba(255,255,255,0.07)",
                    border: `1.5px solid ${rgba(tone, 0.4)}`,
                  }}
                >
                  <span style={{ width: 16, height: 16, borderRadius: 99, background: tone, boxShadow: `0 0 18px ${rgba(tone, 0.7)}`, flexShrink: 0 }} />
                  <span style={{ fontFamily: sans, fontWeight: 700, fontSize: Math.max(36, fit(item, INNER - 90, 56, EM)), lineHeight: 1.1, color: PAPER }}>{item}</span>
                </div>
              </Rise>
            ))}
          </div>
        </Glass>
      );
    case "end": {
      const words = story.brand.name.split(/\s+/);
      const head = words.length > 1 ? words.slice(0, -1).join(" ") : words[0];
      const tail = words.length > 1 ? words[words.length - 1] : "";
      const a = pop(frame, m("brand"));
      const b = pop(frame, m("info"));
      return (
        <Glass frame={frame} width={840} shineAt={shine} tone={tone}>
          <div
            style={{
              fontFamily: sans,
              fontWeight: 800,
              lineHeight: 0.92,
              letterSpacing: "-0.05em",
              color: PAPER,
              opacity: a,
              transform: `translateY(${(1 - a) * 30}px)`,
            }}
          >
            <div style={{ fontSize: fit(head, 736, 150, 0.62) }}>{head}</div>
            {tail ? <div style={{ fontSize: fit(tail, 736, 150, 0.62), color: LIME, textShadow: `0 0 50px ${rgba(LIME, 0.5)}` }}>{tail}</div> : null}
          </div>
          <div style={{ marginTop: 22, fontFamily: sans, fontWeight: 700, fontSize: 30, color: LIME, opacity: a }}>{story.brand.handle}</div>
          <div style={{ marginTop: 14, fontFamily: sans, fontWeight: 600, fontSize: 24, letterSpacing: "0.14em", color: MUTED, opacity: b }}>{story.dateLong}</div>
          <div style={{ marginTop: 30, fontFamily: sans, fontWeight: 600, fontSize: 34, lineHeight: 1.3, color: PAPER, opacity: b }}>{beat.where}</div>
          <div style={{ marginTop: 20, fontFamily: sans, fontSize: 24, color: MUTED, opacity: b }}>{beat.source}</div>
        </Glass>
      );
    }
  }
};

/** "1M de contexto" → big "1M" over small "de contexto"; plain text otherwise. */
const Chip = ({ frame, at, text, tone }: { frame: number; at: number; text: string; tone: string }) => {
  const s = pop(frame, at);
  const [head, ...rest] = text.split(" ");
  const split = /\d/.test(head) && rest.length > 0;
  return (
    <div
      style={{
        flex: "1 1 300px",
        borderRadius: 26,
        padding: "22px 24px",
        background: "rgba(255,255,255,0.07)",
        border: `1.5px solid ${rgba(tone, 0.4)}`,
        opacity: s,
        transform: `translateY(${(1 - s) * 30}px) scale(${0.9 + s * 0.1})`,
      }}
    >
      {split ? (
        <>
          <div style={{ fontFamily: sans, fontWeight: 700, fontSize: 58, color: tone, lineHeight: 1 }}>{head}</div>
          <div style={{ fontFamily: sans, fontWeight: 500, fontSize: 24, color: PAPER, marginTop: 8 }}>{rest.join(" ")}</div>
        </>
      ) : (
        <div style={{ fontFamily: sans, fontWeight: 600, fontSize: 30, lineHeight: 1.2, color: PAPER }}>{text}</div>
      )}
    </div>
  );
};

/** One before → after line. The odometer rolls from the old value to the new one. */
const PriceRow = ({ frame, phase, item, tone, count }: { frame: number; phase: Phase; item: { name: string; before: string; after: string }; tone: string; count: number }) => {
  const enter = pop(frame, mark(phase, "name"));
  const strikeAt = mark(phase, "strike");
  const strike = mix(frame, [strikeAt, strikeAt + 10], [0, 1]);
  const settled = frame >= mark(phase, "after");
  return (
    <div style={{ marginTop: 30, opacity: enter, transform: `translateX(${(1 - enter) * -40}px)` }}>
      <div style={{ display: "flex", gap: 22, alignItems: "baseline", fontFamily: sans, flexWrap: "wrap" }}>
        <span style={{ fontSize: 32, fontWeight: 600, color: PAPER }}>{item.name}</span>
        <span style={{ position: "relative", fontSize: 28, color: MUTED }}>
          {item.before}
          <span style={{ position: "absolute", left: -4, right: -4, top: "55%", height: 3, background: RED, transform: `scaleX(${strike})`, transformOrigin: "left" }} />
        </span>
      </div>
      <div
        style={{
          fontFamily: sans,
          fontWeight: 700,
          fontSize: fit(item.after, INNER, count > 1 ? 112 : 150, EM),
          lineHeight: 1.05,
          letterSpacing: "-0.04em",
          color: settled ? tone : PAPER,
          filter: settled ? `drop-shadow(0 0 22px ${rgba(tone, 0.5)})` : undefined,
        }}
      >
        <Odometer frame={frame} at={strikeAt - 6} from={item.before} to={item.after} span={22} />
      </div>
    </div>
  );
};

const Bar = ({
  frame,
  name,
  share,
  value,
  display,
  enter,
  from,
  to,
  tone,
  small,
}: {
  frame: number;
  name: string;
  share: number;
  value: number;
  display: string;
  enter: number;
  from: number;
  to: number;
  tone: string;
  small: boolean;
}) => {
  const s = pop(frame, enter);
  const fill = mix(frame, [from, to], [0, 1]);
  const hot = tone !== MUTED;
  return (
    <div style={{ marginTop: small ? 24 : 36, opacity: s }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontFamily: sans, gap: 20 }}>
        <span style={{ fontSize: 32, fontWeight: 600, color: hot ? PAPER : MUTED }}>{name}</span>
        <span style={{ fontSize: small ? 60 : 78, fontWeight: 700, letterSpacing: "-0.03em", color: tone, filter: hot ? `drop-shadow(0 0 20px ${rgba(tone, 0.5)})` : undefined }}>
          {fill >= 1 ? display : counter(display, value * fill)}
        </span>
      </div>
      <div style={{ height: 26, borderRadius: 99, background: "rgba(255,255,255,0.08)", marginTop: 10, overflow: "hidden" }}>
        <div
          style={{
            width: `${share * fill * 100}%`,
            height: "100%",
            borderRadius: 99,
            background: hot ? `linear-gradient(90deg, ${rgba(tone, 0.6)}, ${tone})` : "rgba(244,240,230,0.4)",
            boxShadow: hot ? `0 0 26px ${rgba(tone, 0.6)}` : undefined,
          }}
        />
      </div>
    </div>
  );
};
