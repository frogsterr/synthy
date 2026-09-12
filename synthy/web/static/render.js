// Falling-notes renderer shared by the player and the style comparison page.

export const FIRST = 21, LAST = 108;
const BLACK = new Set([1, 3, 6, 8, 10]);
const BLACK_SHIFT = { 1: -0.12, 3: 0.12, 6: -0.14, 8: 0, 10: 0.14 };

// fill: bars on white keys (light tint); black: bars on black keys and lit keys (saturated)
export const HAND = {
  1: { fill: "#d3ee7a", black: "#5e9230", edge: "#4a7524", bright: "#f3fdd0", dark: "#31561a" },
  2: { fill: "#a6c8eb", black: "#3f74c9", edge: "#2f5ba3", bright: "#e3effc", dark: "#244b88" },
};
export const COLORS = {
  bg: "#2b2b2b", guide: "rgba(255,255,255,0.09)", measure: "rgba(255,255,255,0.14)",
  measureText: "rgba(255,255,255,0.4)", suspect: "rgba(207,138,31,0.10)",
  hit: "#d8352a", white: "#f7f7f5", whiteGap: "#6f6f6f", black: "#111111", blackLip: "#3a3a3a",
  label: "#9a9a9a",
};
export const FLASH_SECONDS = 0.18;
const MERGE_BEATS = 1 / 8;   // same pitch this close together is one strike, not a re-strike

export function isBlack(pitch) { return BLACK.has(pitch % 12); }

export function mix(a, b, t) {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return "rgb(" + pa.map((v, i) => Math.round(v + (pb[i] - v) * t)).join(",") + ")";
}

export function geometry(W, H, lo = FIRST, hi = LAST) {
  let whites = 0;
  for (let p = lo; p <= hi; p++) if (!isBlack(p)) whites++;
  const whiteW = W / whites;
  const kbH = Math.min(whiteW * 6.2, H * 0.3);
  const kbTop = H - kbH;
  const blackW = whiteW * 0.58, blackH = kbH * 0.62;
  const keys = [];
  let wi = 0;
  for (let p = lo; p <= hi; p++) {
    const pc = p % 12;
    if (BLACK.has(pc)) {
      keys[p] = { black: true, x: wi * whiteW - blackW / 2 + BLACK_SHIFT[pc] * whiteW, w: blackW };
    } else {
      keys[p] = { black: false, x: wi * whiteW, w: whiteW };
      wi++;
    }
  }
  return { W, H, lo, hi, whiteW, kbH, kbTop, blackW, blackH, keys };
}

// ---------- bar styles ----------
// Each receives the bar box (x, y, w, h), the hand palette and whether the key is black.

function classic(ctx, x, y, w, h, c, black) {
  const r = Math.min(5, w / 2, h / 2);
  ctx.fillStyle = black ? c.black : c.fill;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fill();
  ctx.strokeStyle = "rgba(0,0,0,0.28)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.roundRect(x + 0.5, y + 0.5, w - 1, h - 1, r); ctx.stroke();
}

function flat(ctx, x, y, w, h, c, black) {
  const r = Math.min(3, w / 2, h / 2);
  ctx.fillStyle = black ? c.black : c.fill;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fill();
  ctx.strokeStyle = c.edge; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.roundRect(x + 0.5, y + 0.5, w - 1, h - 1, r); ctx.stroke();
}

function bevel(ctx, x, y, w, h, c, black) {
  const base = black ? c.black : c.fill;
  const r = Math.min(4, w / 2, h / 2);
  const grad = ctx.createLinearGradient(x, 0, x + w, 0);
  grad.addColorStop(0, mix(base, c.bright, 0.32));
  grad.addColorStop(0.45, base);
  grad.addColorStop(1, mix(base, c.dark, 0.45));
  ctx.fillStyle = grad;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fill();
  ctx.save();
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.clip();
  ctx.fillStyle = mix(base, c.bright, 0.55);
  ctx.fillRect(x, y, w, 2);                       // lit top edge
  ctx.fillStyle = c.dark;
  ctx.fillRect(x, y + h - 2, w, 2);               // shaded bottom edge
  ctx.restore();
  ctx.strokeStyle = c.dark; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.roundRect(x + 0.5, y + 0.5, w - 1, h - 1, r); ctx.stroke();
}

function strike(ctx, x, y, w, h, c, black) {
  const r = Math.min(2, w / 2, h / 2);
  ctx.strokeStyle = "rgba(0,0,0,0.85)"; ctx.lineWidth = 2;   // dark halo separates neighbours
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.stroke();
  ctx.fillStyle = black ? c.black : c.fill;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fill();
  const band = Math.min(3, Math.max(2, Math.floor(h / 4)));
  ctx.fillStyle = c.bright;                                    // bright landing edge = the hit
  ctx.fillRect(x, y + h - band, w, band);
}

function capsule(ctx, x, y, w, h, c, black) {
  const base = black ? c.black : c.fill;
  const r = Math.min(w / 2, h / 2);
  ctx.strokeStyle = "rgba(0,0,0,0.7)"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.stroke();
  ctx.fillStyle = base;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fill();
  if (h > 10 && w > 6) {                                       // lighter core reads at any size
    const cw = Math.max(2, Math.round(w * 0.36)), cx = x + Math.round((w - cw) / 2);
    const ch = h - 8, cy = y + 4;
    ctx.fillStyle = mix(base, c.bright, 0.5);
    ctx.beginPath(); ctx.roundRect(cx, cy, cw, ch, cw / 2); ctx.fill();
  }
}

export const STYLES = {
  classic: { name: "Classic", blurb: "The Synthesia look: light bars on white keys, saturated bars on black keys, soft corners.", bar: classic },
  flat: { name: "Matte", blurb: "Same fills with tighter corners and a coloured outline.", bar: flat },
  bevel: { name: "Bevel", blurb: "Side-lit cylinder with a lit top and shaded bottom edge, so bars read as solid objects.", bar: bevel },
  strike: { name: "Strike edge", blurb: "Square corners, dark halo between neighbours, and a bright bottom band marking the exact hit.", bar: strike },
  capsule: { name: "Capsule", blurb: "Fully rounded ends with a lighter core stripe; chords stay separable and short notes still show.", bar: capsule },
};

function lowerBound(arr, value) {
  let lo = 0, hi = arr.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (arr[mid].onset < value) lo = mid + 1; else hi = mid; }
  return lo;
}

// o: { scale, width, measureLines, suspects, rate, style }
// data: { notes (sorted by onset), measures, maxDuration }
export function draw(ctx, g, beat, o, data) {
  const { W, H, kbTop } = g;
  const { notes, measures, maxDuration } = data;
  const pxb = o.scale;
  const laneBeats = kbTop / pxb;
  const style = STYLES[o.style] || STYLES.classic;

  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = COLORS.guide;
  for (let p = g.lo + 1; p <= g.hi; p++) {
    if (p % 12 === 0) ctx.fillRect(Math.round(g.keys[p].x), 0, 1, kbTop);
  }

  if (o.suspects || o.measureLines) {
    for (const m of measures) {
      const yBottom = kbTop - (m.start - beat) * pxb;
      const yTop = yBottom - m.length * pxb;
      if (yBottom < 0 || yTop > kbTop) continue;
      if (o.suspects && m.suspect) {
        ctx.fillStyle = COLORS.suspect;
        ctx.fillRect(0, Math.max(0, yTop), W, Math.min(kbTop, yBottom) - Math.max(0, yTop));
      }
      if (o.measureLines && yBottom <= kbTop) {
        ctx.fillStyle = COLORS.measure;
        ctx.fillRect(0, Math.round(yBottom), W, 1);
        ctx.fillStyle = COLORS.measureText;
        ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
        ctx.textBaseline = "bottom";
        ctx.fillText(String(m.index + 1), 6, Math.round(yBottom) - 3);
      }
    }
  }

  // collect visible bars; a re-strike cuts the note still sounding on that key
  const lastEnd = new Map(), lastRec = new Map();
  const passes = [[], []];
  const from = lowerBound(notes, beat - maxDuration);
  const to = lowerBound(notes, beat + laneBeats);
  for (let i = from; i < to; i++) {
    const n = notes[i];
    const end = n.onset + n.duration;
    const key = g.keys[n.pitch];
    if (!key) continue;
    const prevEnd = lastEnd.get(n.pitch);
    const prev = lastRec.get(n.pitch);
    if (prevEnd !== undefined && n.onset < prevEnd - 1e-6 && prev) {
      if (n.onset - prev.n.onset < MERGE_BEATS) {      // same key press written twice
        prev.end = Math.max(prev.end, end);
        prev.yTop = kbTop - (prev.end - beat) * pxb;
        lastEnd.set(n.pitch, Math.max(prevEnd, end));
        continue;
      }
      prev.end = Math.min(prev.end, n.onset);
      prev.yTop = kbTop - (prev.end - beat) * pxb;
    }
    lastEnd.set(n.pitch, Math.max(prevEnd ?? 0, end));
    const yBottom = kbTop - (n.onset - beat) * pxb;
    const yTop = kbTop - (end - beat) * pxb;
    if (yTop > kbTop || yBottom < 0) continue;
    const rec = { n, key, end, yTop, yBottom };
    lastRec.set(n.pitch, rec);
    passes[key.black ? 1 : 0].push(rec);
  }

  const active = new Map();
  for (const pass of passes) {
    for (const rec of pass) {
      if (rec.n.onset <= beat && beat < rec.end) {
        const age = (beat - rec.n.onset) / o.rate;
        const cur = active.get(rec.n.pitch);
        if (!cur || age < cur.age) active.set(rec.n.pitch, { hand: rec.n.hand, age });
      }
    }
  }

  ctx.save();
  ctx.beginPath(); ctx.rect(0, 0, W, kbTop); ctx.clip();
  for (const pass of passes) {
    for (const { n, key, yTop, yBottom } of pass) {
      const c = HAND[n.hand];
      const inset = key.w * (1 - o.width) / 2;
      const x = Math.round(key.x + inset), w = Math.max(2, Math.round(key.w - 2 * inset));
      const y0 = Math.round(yTop);
      let h = Math.round(yBottom) - y0;
      if (h > 6) h -= 2;           // gap between consecutive notes on one key
      h = Math.max(h, 4);
      style.bar(ctx, x, y0, w, h, c, key.black);
    }
  }
  ctx.restore();

  // keyboard: lit keys take the hand's saturated colour, brighter for a moment after the strike
  const keyColor = (a) => {
    const c = HAND[a.hand];
    const t = Math.max(0, 1 - a.age / FLASH_SECONDS);
    return t > 0 ? mix(c.black, c.bright, t * 0.5) : c.black;
  };
  const kb = Math.round(kbTop);
  ctx.fillStyle = COLORS.whiteGap;
  ctx.fillRect(0, kb, W, g.kbH);
  const labels = g.whiteW >= 14;
  if (labels) { ctx.font = Math.round(Math.min(11, g.whiteW * 0.55)) + "px ui-sans-serif, system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "bottom"; }
  for (let p = g.lo; p <= g.hi; p++) {
    const key = g.keys[p];
    if (key.black) continue;
    const a = active.get(p);
    const x = Math.round(key.x) + 1, w = Math.round(key.x + key.w) - x - 1;
    ctx.fillStyle = a ? keyColor(a) : COLORS.white;
    ctx.beginPath(); ctx.roundRect(x, kb, w, g.kbH - 1, [0, 0, 3, 3]); ctx.fill();
    if (labels && p % 12 === 0) {
      ctx.fillStyle = a ? "rgba(255,255,255,0.8)" : COLORS.label;
      ctx.fillText("C" + (p / 12 - 1), x + w / 2, kb + g.kbH - 4);
    }
  }
  ctx.textAlign = "start";
  for (let p = g.lo; p <= g.hi; p++) {
    const key = g.keys[p];
    if (!key.black) continue;
    const a = active.get(p);
    const x = Math.round(key.x), w = Math.round(key.w), bh = Math.round(g.blackH);
    ctx.fillStyle = COLORS.whiteGap;
    ctx.beginPath(); ctx.roundRect(x - 1, kb, w + 2, bh + 1, [0, 0, 3, 3]); ctx.fill();
    if (a) {
      ctx.fillStyle = keyColor(a);
    } else {
      const grad = ctx.createLinearGradient(0, kb, 0, kb + bh);
      grad.addColorStop(0, COLORS.black); grad.addColorStop(1, "#1e1e1e");
      ctx.fillStyle = grad;
    }
    ctx.beginPath(); ctx.roundRect(x, kb, w, bh, [0, 0, 2, 2]); ctx.fill();
    const lip = Math.max(2, Math.round(bh * 0.06));
    ctx.fillStyle = a ? "rgba(255,255,255,0.35)" : COLORS.blackLip;    // lower face catches light
    ctx.beginPath(); ctx.roundRect(x + 1, kb + bh - lip - 1, w - 2, lip, [0, 0, 2, 2]); ctx.fill();
  }

  // white flare where a lit key meets the hit line
  for (const [p, a] of active) {
    const key = g.keys[p];
    const cx = key.x + key.w / 2;
    const t = Math.max(0, 1 - a.age / FLASH_SECONDS);
    const strength = 0.6 + 0.4 * t;
    const radius = g.whiteW * (1.2 + 0.7 * t);
    const grad = ctx.createRadialGradient(cx, kb, 0, cx, kb, radius);
    grad.addColorStop(0, "rgba(255,255,255," + strength.toFixed(3) + ")");
    grad.addColorStop(0.3, "rgba(255,255,255," + (0.6 * strength).toFixed(3) + ")");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(cx - radius, kb - radius, radius * 2, radius * 2);
  }

  ctx.fillStyle = COLORS.hit;
  ctx.fillRect(0, kb - 1, W, 2);
}
