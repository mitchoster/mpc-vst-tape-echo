/* pagetest.mjs — run the companion page's script without a browser.
 *
 *   node vst/web/pagetest.mjs [path/to/index.html]
 *
 * The page is ~700 lines of canvas code that no compiler checks and no unit test runs; the last
 * bug of that class ("reel is not a function") only showed up when a browser rendered it. This
 * harness executes the real script against a recording canvas and a fake DOM, then checks the
 * things that break quietly:
 *
 *   1. draw() runs without throwing, in both layouts, over several frames
 *   2. every control registers a hit region (6 knobs per page, the switch rows, 12 mode cells)
 *   3. a pointerdown inside a knob sends POST /set?k=..., a pointerup sends the final value
 *   4. a lamp that is a switch toggles on tap
 *   5. tapping a mode cell sends that index, and the write carries the X-TEC header
 *   6. no control sits outside the screen or on top of another (all pages, both viewports)
 *
 * No DOM library: the stubs are the dozen things the page actually touches.
 */
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const file = process.argv[2] || new URL('./index.html', import.meta.url).pathname;
const html = readFileSync(file, 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('FAIL: no <script> in ' + file); process.exit(1); }
const code = m[1];

const STATE = {
  instance: 0, count: 1, active: 1, age_ms: 12,
  url: 'http://192.0.2.10:8101/',
  vu: 0.42, peak: 0.6, delay_ms: 190.4, bpm: 120, repeat_rate: 0.414888,
  head_ms: [69.3, 132.5, 191.4], intensity: 0.44, echo_volume: 1, reverb_volume: 0.35, mix: 0.5,
  input_volume: 0.5, bass: 0, treble: 0, wow_flutter: 0.15,
  time_ms: 400, tone_tilt: 0, tape_wear: 0.25,
  mode: 2, tempo_sync: 0, echo_rate_note: 5, tape_age: 1, input_send: 1, ping_pong: 0,
  stereo_width: 0, heads: 4, rev_head: 0
};

let calls = [];
const gradient = { addColorStop() {} };
const ctx = new Proxy({}, {
  get(_, k) {
    if (k === 'measureText') return (t) => ({ width: String(t).length * 7 });
    if (k === 'createLinearGradient' || k === 'createRadialGradient') return () => gradient;
    if (k === 'getImageData') return () => ({ data: new Uint8ClampedArray(4) });
    if (typeof k === 'string' && /^(canvas|fillStyle|strokeStyle|lineWidth|lineCap|lineJoin|font|textAlign|textBaseline|globalAlpha|shadowBlur|shadowColor)$/.test(k)) return ctx[k];
    return (...args) => { if (k === 'fill' || k === 'stroke' || k === 'fillRect') calls.push(k); };
  },
  set(_, k, v) { calls.push('set:' + k); return true; }
});

function el(extra = {}) {
  const listeners = {};
  return Object.assign({
    style: {}, classList: { add() {}, remove() {} }, className: '',
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    removeEventListener() {},
    appendChild() {}, remove() {}, click() {},
    getBoundingClientRect() { return { left: 0, top: 0 }; },
    setPointerCapture() {}, releasePointerCapture() {},
    _fire(t, ev) { (listeners[t] || []).forEach(f => f(ev)); }
  }, extra);
}

const canvas = el({ clientWidth: 1100, clientHeight: 660, width: 1100, height: 660, getContext: () => ctx, toDataURL: () => 'data:,' });
const bar = el();
const link = el({ firstElementChild: el() });
const host = el();
const fsBtn = el();

const document = {
  getElementById: (id) => ({ c: canvas, bar, link, host, fs: fsBtn })[id] || el(),
  createElement: () => el(),
  body: el(),
  documentElement: el({ requestFullscreen: () => Promise.resolve() }),
  addEventListener() {}
};

const fetched = [];
const sandbox = {
  console,
  document,
  window: null,
  location: { host: '192.0.2.10:8101', href: 'http://192.0.2.10:8101/' },
  navigator: {},
  performance: { now: () => Date.now() },
  devicePixelRatio: 2,
  addEventListener() {},
  setInterval: () => 1, clearInterval() {}, setTimeout: () => 1, clearTimeout() {},
  requestAnimationFrame: () => 1,
  fetch: (url, opts) => { fetched.push({ url, opts }); return Promise.resolve({ ok: true, json: () => Promise.resolve(STATE), text: () => Promise.resolve('') }); },
  Math, Date, JSON, Uint8Array, Float32Array, Object, Array, String, Number, Boolean, isNaN, parseInt, parseFloat, encodeURIComponent
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

vm.createContext(sandbox);
vm.runInContext(code, sandbox, { filename: 'index.html' });

const P = sandbox.__tecPanel;
let fails = 0;
const check = (ok, name, detail = '') => {
  console.log((ok ? 'PASS' : 'FAIL') + ': ' + name + (detail ? ' = ' + detail : ''));
  if (!ok) fails++;
};

check(!!P, 'the page exposes its test hook', P ? 'ok' : 'missing');
if (!P) process.exit(1);

/* 1 — the drawing runs, in both layouts */
function render(w, h, frames) {
  canvas.clientWidth = w; canvas.clientHeight = h;
  P.fit();
  /* timestamps come from the same clock the page uses; synthetic ones from the past made
   * the ripple maths run backwards (a real bug, found here) */
  const t0 = performance.now();
  for (let i = 0; i < frames; i++) P.draw(t0 + i * 130);
}
try {
  render(1100, 660, 12);
  check(true, 'wide layout draws', 'no exception');
  render(430, 850, 8);
  check(true, 'portrait layout draws', 'no exception');
} catch (e) {
  check(false, 'drawing runs', String(e && e.stack ? e.stack.split('\n')[0] : e));
  process.exit(1);
}

/* 2 — every control registered a region */
render(1100, 660, 2);
const hits = P.hits();
const keys = hits.filter(h => h.t === 'knob').map(h => h.key);
for (const k of ['time_ms', 'repeat_rate', 'intensity', 'echo_volume', 'reverb_volume', 'mix']) {
  check(keys.includes(k), 'knob region: ' + k, keys.join(','));
}
const toggles = hits.filter(h => h.t === 'toggle').map(h => h.key);
for (const k of ['tempo_sync', 'input_send', 'ping_pong']) {
  check(toggles.includes(k), 'footer lamp switch: ' + k, toggles.join(','));
}
const modes = hits.filter(h => h.t === 'mode');
check(modes.length === 12, 'twelve mode cells', String(modes.length));

/* pages: three faces, reachable by swipe and by the dots */
for (let i = 0; i < 3; i++) {
  P.goPage(i);
  render(1100, 660, 3);
  check(P.page().target === i, 'page ' + i + ' is reachable', String(P.page().at));
}

/* page 1 and 2 expose their own controls */
P.goPage(1); render(1100, 660, 2);
const tapeKeys = P.hits().filter(h => h.t === 'knob' || h.t === 'seg').map(h => h.key);
for (const k of ['input_volume', 'bass', 'treble', 'wow_flutter', 'stereo_width', 'echo_rate_note',
                 'tape_age', 'input_send', 'ping_pong', 'tempo_sync']) {
  check(tapeKeys.includes(k), 'TAPE page control: ' + k, tapeKeys.join(','));
}
P.goPage(2); render(1100, 660, 2);
const macroKeys = P.hits().filter(h => h.t === 'knob' || h.t === 'seg').map(h => h.key);
for (const k of ['time_ms', 'tone_tilt', 'tape_wear', 'intensity', 'mix', 'tempo_sync']) {
  check(macroKeys.includes(k), 'MACRO page control: ' + k, macroKeys.join(','));
}

/* geometry: every control inside the screen, no two touching. The pages are hand-placed;
 * a 10 px mistake is invisible in a JSON diff and obvious to a thumb. */
function box(h) {
  if (h.t === 'knob' || h.t === 'toggle') return { x: h.x - h.r, y: h.y - h.r, w: h.r * 2, h: h.r * 2, id: h.t + ':' + h.key };
  return { x: h.x, y: h.y, w: h.w, h: h.h, id: h.t + ':' + (h.key !== undefined ? h.key : h.i) };
}
for (let i = 0; i < 3; i++) {
  for (const [w, h] of [[1100, 660], [430, 850]]) {
    P.goPage(i); render(w, h, 2);
    const boxes = P.hits().filter(x => x.t !== 'page').map(box);
    const outside = boxes.filter(b => b.x < 0 || b.y < 0 || b.x + b.w > w || b.y + b.h > h);
    check(outside.length === 0, `page ${i} ${w}x${h}: controls inside the screen`,
          outside.map(b => b.id).slice(0, 3).join(' ') || 'ok');
    let overlaps = [];
    for (let a = 0; a < boxes.length; a++)
      for (let b = a + 1; b < boxes.length; b++) {
        const A = boxes[a], B = boxes[b];
        if (A.x < B.x + B.w && B.x < A.x + A.w && A.y < B.y + B.h && B.y < A.y + A.h) overlaps.push(A.id + ' x ' + B.id);
      }
    check(overlaps.length === 0, `page ${i} ${w}x${h}: no overlapping controls`, overlaps.slice(0, 3).join(' | ') || 'ok');
  }
}

/* a segment tap sends its index */
P.goPage(1); render(1100, 660, 2);
const ageSeg = P.hits().find(h => h.t === 'seg' && h.key === 'tape_age' && h.i === 2);
fetched.length = 0;
canvas._fire('pointerdown', { clientX: ageSeg.x + 3, clientY: ageSeg.y + 3, pointerId: 9, preventDefault() {} });
check(fetched.some(f => f.url.includes('k=tape_age') && f.url.includes('v=2')), 'a segment tap sends its index',
      fetched.map(f => f.url).join(' '));

/* a swipe on the bare panel moves to the next page */
P.goPage(0); render(1100, 660, 2);
/* the finger moves left (700 -> 40): the next page comes in, as on a phone */
canvas._fire('pointerdown', { clientX: 700, clientY: 300, pointerId: 10, preventDefault() {} });
canvas._fire('pointermove', { clientX: 40, clientY: 300, pointerId: 10 });
canvas._fire('pointerup', { clientX: 40, clientY: 300, pointerId: 10 });
check(P.page().target === 1, 'a leftward swipe turns to the next page', JSON.stringify(P.page()));
/* and back again */
render(1100, 660, 20);
canvas._fire('pointerdown', { clientX: 60, clientY: 300, pointerId: 11, preventDefault() {} });
canvas._fire('pointermove', { clientX: 720, clientY: 300, pointerId: 11 });
canvas._fire('pointerup', { clientX: 720, clientY: 300, pointerId: 11 });
check(P.page().target === 0, 'a rightward swipe goes back', JSON.stringify(P.page()));

/* 3 — a knob drag writes, and the mapped value is the plugin's unit (ms here) */
P.goPage(0); render(1100, 660, 2);
const timeKnob = P.hits().find(h => h.t === 'knob' && h.key === 'time_ms');
fetched.length = 0;
canvas._fire('pointerdown', { clientX: timeKnob.x, clientY: timeKnob.y, pointerId: 1, preventDefault() {} });
canvas._fire('pointermove', { clientX: timeKnob.x, clientY: timeKnob.y - 90, pointerId: 1, preventDefault() {} });
canvas._fire('pointerup', { clientX: timeKnob.x, clientY: timeKnob.y - 90, pointerId: 1 });
const timeUrls = fetched.map(f => f.url).filter(u => u.includes('k=time_ms'));
check(timeUrls.length > 0, 'turning the TIME knob sends /set?k=time_ms', timeUrls[timeUrls.length - 1] || 'none');
const timeVal = timeUrls.length ? parseFloat(timeUrls[timeUrls.length - 1].split('v=')[1]) : -1;
check(timeVal > 400 && timeVal <= 490, 'the value went up, in milliseconds (69..490)', String(timeVal));
const timeCall = fetched.find(f => f.url === timeUrls[0]);
check(timeCall.opts && timeCall.opts.method === 'POST', 'writes are POST', 'ok');
check(timeCall.opts.headers && timeCall.opts.headers['X-TEC'] === '1',
      'writes carry the X-TEC header (no cross-site form can set one)', JSON.stringify(timeCall.opts.headers || {}));

/* 4 — a lamp that is also a switch toggles on tap */
P.goPage(0); render(1100, 660, 2);
const armLamp = P.hits().find(h => h.t === 'toggle' && h.key === 'input_send');
fetched.length = 0;
canvas._fire('pointerdown', { clientX: armLamp.x, clientY: armLamp.y, pointerId: 2, preventDefault() {} });
canvas._fire('pointerup', { clientX: armLamp.x, clientY: armLamp.y, pointerId: 2 });
const armVals = fetched.map(f => f.url).filter(u => u.includes('k=input_send')).map(u => u.split('v=')[1]);
check(armVals.length === 1 && armVals[0] === '0', 'ARM (on) sends exactly one 0', armVals.join(' -> '));

/* the pairing address: /state's `url` when present, this page's own host otherwise */
P.setState({ url: 'http://192.0.2.5:8101/' });
P.refreshPair();
check(P.pair() === 'http://192.0.2.5:8101/', 'the bar shows the address /state publishes', P.pair());
P.setState({ url: '' });
P.refreshPair();
check(P.pair() === '192.0.2.10:8101', 'without it the bar falls back to this page\'s host', P.pair());

/* 5 — the mode grid */
P.goPage(0); render(1100, 660, 2);
const cell = P.hits().find(h => h.t === 'mode' && h.i === 10);
fetched.length = 0;
canvas._fire('pointerdown', { clientX: cell.x + 2, clientY: cell.y + 2, pointerId: 3, preventDefault() {} });
check(fetched.some(f => f.url.includes('k=mode') && f.url.includes('v=10')), 'a mode cell sends its index',
      fetched.map(f => f.url).join(' '));

console.log(fails ? 'FAILED' : 'PASSED');
process.exit(fails ? 1 : 0);
