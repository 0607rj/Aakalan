"use client";

import * as React from "react";

/**
 * The hero picture: a night sky made of 30,000 possible costs for one project, drawn the way
 * Aakalan's simulation spreads them (skewed: overruns go further than savings), with the low,
 * likely and high marks. A fixed seed draws the same sky every time, as the engine does.
 * Illustration only: no real estimate is drawn.
 */
const SEED = 11;
const SPREAD = 0.32; // log-normal sigma of the illustration
const LO = 0.2; // cost multiples shown, left and right edge
const HI = 2.2;
const Z = { low: -1.2816, likely: 0, high: 1.2816 }; // P10, P50, P90

function rng(seed: number): () => number {
  let t = seed;
  return () => {
    t = (t + 0x6d2b79f5) | 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

/** Position (0..1) of a cost multiple across the sky. */
const across = (multiple: number) => (multiple - LO) / (HI - LO);

/** Log-normal density of a cost multiple. */
function density(multiple: number): number {
  const z = Math.log(multiple) / SPREAD;
  return Math.exp(-0.5 * z * z) / multiple;
}

function draw(canvas: HTMLCanvasElement) {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const w = Math.round(canvas.clientWidth * dpr);
  const h = Math.round(canvas.clientHeight * dpr);
  if (!w || !h) return;
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const rand = rng(SEED);
  const gauss = () => (rand() + rand() + rand() + rand() - 2) / 0.577;
  const k = w / 1000;
  const mode = Math.exp(-SPREAD * SPREAD);
  const peak = density(mode);
  const left = 0.08 * w;
  const span = 0.84 * w;
  const base = 0.8 * h;
  const amp = (w / h < 1.6 ? 0.46 : 0.56) * h; // lower on phones: room for the caption
  const xOf = (m: number) => left + across(m) * span;
  const topOf = (m: number) => base - (density(m) / peak) * amp;

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.globalCompositeOperation = "multiply";
  const blob = (
    x: number,
    y: number,
    r: number,
    a: number,
    rgb = "27,36,51",
  ) => {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, `rgba(${rgb},${a})`);
    g.addColorStop(1, `rgba(${rgb},0)`);
    ctx.fillStyle = g;
    ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
  };

  // the haze along the curve, warm where the likely cost sits
  for (let i = 0; i <= 40; i++) {
    const m = LO + ((HI - LO) * i) / 40;
    blob(xOf(m), topOf(m) + 30 * k, 170 * k, 0.04);
  }
  blob(xOf(1), topOf(1), 260 * k, 0.16, "11,120,184");

  // 30,000 possible costs: most fill the area under the curve, some crowd its edge
  for (let i = 0; i < 30000; i++) {
    const m = Math.exp(SPREAD * gauss());
    if (m < LO || m > HI) continue;
    const x = xOf(m) + (rand() - 0.5) * 6 * k;
    const edge = rand() < 0.45;
    const v = edge ? 1 - Math.abs(gauss()) * 0.05 : Math.sqrt(rand());
    const y = base - (density(m) / peak) * amp * v + (rand() - 0.5) * 8 * k;
    const near = edge ? 0.55 : 0.12 + 0.3 * v;
    ctx.fillStyle = `rgba(11,120,184,${0.03 + near * rand()})`;
    const r =
      (rand() < 0.985 ? 0.35 + 0.45 * rand() : 0.8 + 0.6 * rand()) * 1.3 * k;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.globalCompositeOperation = "source-over";

  // stars behind
  for (let i = 0; i < 900; i++) {
    ctx.fillStyle = `rgba(27,36,51,${0.04 + 0.12 * rand()})`;
    ctx.beginPath();
    ctx.arc(
      rand() * w,
      rand() * h * 0.9,
      (0.35 + 0.6 * rand()) * 1.3 * k,
      0,
      2 * Math.PI,
    );
    ctx.fill();
  }

  // the floor line and the low / likely / high marks
  ctx.strokeStyle = "rgba(27,36,51,0.18)";
  ctx.lineWidth = 1 * dpr;
  ctx.beginPath();
  ctx.moveTo(left, base + 1);
  ctx.lineTo(left + span, base + 1);
  ctx.stroke();
  const mono =
    getComputedStyle(canvas).getPropertyValue("--font-plex-mono").trim() ||
    "monospace";
  ctx.font = `${Math.round(11 * dpr)}px ${mono}`;
  // labels sit beside their line, away from the curve: low to the left, high to the right
  const marks: [string, number, string, CanvasTextAlign, number][] = [
    ["P10 · LOW", Z.low, "27,36,51", "right", -8],
    ["P50 · LIKELY", Z.likely, "217,122,31", "center", 0],
    ["P90 · HIGH", Z.high, "27,36,51", "left", 8],
  ];
  for (const [label, z, rgb, align, dx] of marks) {
    const m = Math.exp(SPREAD * z);
    const x = xOf(m);
    const top = topOf(m) - 70 * k;
    ctx.setLineDash([3 * dpr, 4 * dpr]);
    ctx.strokeStyle = `rgba(${rgb},0.6)`;
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, base + 6 * dpr);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = `rgba(${rgb},0.85)`;
    ctx.textAlign = align;
    ctx.fillText(
      label,
      x + dx * dpr,
      top + (align === "center" ? -8 * dpr : 10 * dpr),
    );
  }

  // film grain
  const img = ctx.getImageData(0, 0, w, h);
  const px = img.data;
  for (let i = 0; i < px.length; i += 4) {
    const n = (rand() - 0.5) * 26;
    px[i] = Math.max(0, Math.min(255, px[i] + n));
    px[i + 1] = Math.max(0, Math.min(255, px[i + 1] + n));
    px[i + 2] = Math.max(0, Math.min(255, px[i + 2] + n));
  }
  ctx.putImageData(img, 0, 0);
}

export function CostSky({ className }: { className?: string }) {
  const ref = React.useRef<HTMLCanvasElement>(null);
  React.useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    let live = true;
    document.fonts.ready.then(() => {
      if (!live) return;
      draw(canvas);
      canvas.dataset.ready = "yes";
    });
    return () => {
      live = false;
    };
  }, []);
  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      className={`cost-sky absolute -inset-[6%] h-[112%] w-[112%] ${className ?? ""}`}
    />
  );
}
