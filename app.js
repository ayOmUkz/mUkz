/* ============================================================== *
 * ACTUAL TRADES — rule engine, state model, DOM sync              *
 *                                                                  *
 * Doctrine encoded in code:                                        *
 *   - 1H setup is invalid without a 4H bias direction.             *
 *   - RANGE regime blocks 1H alignment (no trend setups in range). *
 *   - 5M trigger requires momentum OR absorption confirmation.     *
 *   - R:R must be >= 2.0 — non-negotiable.                         *
 *   - News rule is manual; a human must clear it.                  *
 *                                                                  *
 * Trade states (body[data-trade-state]):                           *
 *   WAITING  — 4H bias set, lower TFs incomplete                   *
 *   INVALID  — alignment broken at any layer above 5M              *
 *   ARMED    — alignment ok, missing trigger / risk / news         *
 *   VALID    — every rule passes, EXECUTE button live              *
 * ============================================================== */

const STORAGE_KEY = "actualTrades.entries";

const state = {
  market: "ES",
  regime: "TREND",
  session: "NY",
  h4: {
    bias: null, structure: "", htfLevels: "",
    zones: [], poc: null, vah: null, val: null, last: null,
  },
  h1: {
    liquidity: [], shift: "None", swept: false, poi: [],
  },
  m5: {
    trigger: "None", momentum: false, absorption: false, delta: false,
    entry: null, stop: null, tp: null, size: null,
  },
  notes: "",
  mistakes: {},
  rules: { r_4h: false, r_1h: false, r_5m: false, r_risk: false, r_news: false },
};

/* ---------------------------------------------------------------- *
 * Pure derivation — never mutate, just read                        *
 * ---------------------------------------------------------------- */

const align4H = s =>
  (s.h4.bias === "BULL" || s.h4.bias === "BEAR")
  && s.h4.structure !== ""
  && !(s.h4.bias === "BULL" && s.h4.structure === "LH_LL")
  && !(s.h4.bias === "BEAR" && s.h4.structure === "HH_HL");

const align1H = s =>
  align4H(s)
  && s.h1.shift !== "None"
  && s.h1.swept === true
  && s.h1.liquidity.length > 0
  && s.h1.poi.length > 0
  && s.regime !== "RANGE";

const trigger5M = s =>
  s.m5.trigger !== "None"
  && (s.m5.momentum || s.m5.absorption || s.m5.delta)
  && Number.isFinite(s.m5.entry)
  && Number.isFinite(s.m5.stop)
  && Number.isFinite(s.m5.tp);

const rrRatio = s => {
  if (!Number.isFinite(s.m5.entry) || !Number.isFinite(s.m5.stop) || !Number.isFinite(s.m5.tp)) return null;
  const risk   = Math.abs(s.m5.entry - s.m5.stop);
  const reward = Math.abs(s.m5.tp - s.m5.entry);
  return risk === 0 ? null : reward / risk;
};

const riskOk = s => {
  const r = rrRatio(s);
  return r !== null && r >= 2;
};

/* auction read (4H volume profile hint) */
const auctionHint = s => {
  const { last, vah, val, poc } = s.h4;
  if (!Number.isFinite(last) || !Number.isFinite(vah) || !Number.isFinite(val)) {
    return "Auction read: enter Last + VAH + VAL.";
  }
  if (last > vah)  return `Auction read: price ABOVE value (${last} > ${vah}) — bullish acceptance probable.`;
  if (last < val)  return `Auction read: price BELOW value (${last} < ${val}) — bearish acceptance probable.`;
  if (Number.isFinite(poc)) {
    return `Auction read: inside value area, ${last >= poc ? "above" : "below"} POC ${poc}. Range conditions — favor mean reversion.`;
  }
  return "Auction read: inside value area — range conditions, no trade unless edges break.";
};

/* alignment readout (1H ↔ 4H) */
const alignmentReadout = s => {
  if (!align4H(s))            return { state: "BLOCKED", text: "BLOCKED", sub: "Set a 4H bias and confirm structure." };
  if (s.regime === "RANGE")   return { state: "BLOCKED", text: "BLOCKED", sub: "Regime = RANGE. No trend setups in range." };
  if (!s.h1.swept)            return { state: "PENDING", text: "PENDING", sub: "Liquidity must be swept before structure shift counts." };
  if (s.h1.shift === "None")  return { state: "PENDING", text: "PENDING", sub: "Need BOS or ChoCH after the sweep." };
  if (s.h1.poi.length === 0)  return { state: "PENDING", text: "PENDING", sub: "Tag the OB / FVG you'll trade from." };
  return { state: "OK", text: "ALIGNED", sub: `Setup valid in ${s.h4.bias} direction — wait for 5M trigger.` };
};

/* ---------------------------------------------------------------- *
 * Master evaluation                                                *
 * ---------------------------------------------------------------- */

function evaluate() {
  state.rules.r_4h   = align4H(state);
  state.rules.r_1h   = align1H(state);
  state.rules.r_5m   = trigger5M(state);
  state.rules.r_risk = riskOk(state);
  /* r_news stays whatever the human set */

  const allPass = Object.values(state.rules).every(Boolean);
  let tradeState;
  if (allPass)                                            tradeState = "VALID";
  else if (state.rules.r_4h && state.rules.r_1h)          tradeState = "ARMED";
  else if (state.rules.r_4h)                              tradeState = "WAITING";
  else                                                    tradeState = "INVALID";

  document.body.dataset.tradeState = tradeState;
  render();
}

/* ---------------------------------------------------------------- *
 * Rendering — sync DOM from state                                  *
 * ---------------------------------------------------------------- */

function render() {
  /* trade state badge + status pill */
  const badge = document.getElementById("tradeStateBadge");
  const pill  = document.getElementById("statusPill");
  const ts    = document.body.dataset.tradeState;
  badge.dataset.state = ts;
  badge.querySelector(".label").textContent = ts;
  pill.dataset.state  = ts;
  pill.textContent    = ts;

  /* rule checklist */
  Object.entries(state.rules).forEach(([key, val]) => {
    const cb = document.querySelector(`input[data-rule="${key}"]`);
    if (cb) cb.checked = val;
  });

  /* execute button */
  const btn = document.getElementById("executeBtn");
  const sub = document.getElementById("executeSub");
  const allPass = ts === "VALID";
  btn.disabled = !allPass;
  sub.textContent = allPass
    ? "all rules clear — log this trade"
    : `${Object.values(state.rules).filter(Boolean).length}/5 rules clear`;

  /* RR box */
  const r = rrRatio(state);
  const rrEl  = document.getElementById("rrValue");
  const rrBox = document.getElementById("rrBox");
  const rrNote= document.getElementById("rrNote");
  if (r === null) {
    rrEl.textContent = "—"; rrBox.dataset.state = "empty";
    rrNote.textContent = "enter prices to compute";
  } else {
    rrEl.textContent = r.toFixed(2) + "R";
    rrBox.dataset.state = r >= 2 ? "ok" : "bad";
    rrNote.textContent  = r >= 2
      ? "risk acceptable — minimum 2R cleared"
      : "below 2R — refuse this trade";
  }

  /* alignment readout */
  const ar = alignmentReadout(state);
  const arEl = document.getElementById("alignmentReadout");
  arEl.dataset.state = ar.state;
  document.getElementById("alignText").textContent = ar.text;
  document.getElementById("alignSub").textContent  = ar.sub;

  /* 4H auction hint */
  document.getElementById("h4Hint").textContent = auctionHint(state);
}

/* ---------------------------------------------------------------- *
 * State mutation helpers                                           *
 * ---------------------------------------------------------------- */

function setPath(obj, path, value) {
  const keys = path.split(".");
  const last = keys.pop();
  const target = keys.reduce((o, k) => o[k], obj);
  target[last] = value;
}

function getPath(obj, path) {
  return path.split(".").reduce((o, k) => o?.[k], obj);
}

function coerce(el, raw) {
  if (el.type === "checkbox")           return el.checked;
  if (el.type === "number")             return raw === "" ? null : Number(raw);
  if (el.tagName === "SELECT" && (raw === "true" || raw === "false")) return raw === "true";
  return raw;
}

/* ---------------------------------------------------------------- *
 * Wiring                                                           *
 * ---------------------------------------------------------------- */

function wireBiasSelector() {
  document.querySelectorAll(".bias-selector button[data-bias]").forEach(b => {
    b.addEventListener("click", () => {
      const next = b.dataset.bias;
      state.h4.bias = state.h4.bias === next ? null : next;
      document.querySelectorAll(".bias-selector button[data-bias]").forEach(x =>
        x.setAttribute("aria-pressed", String(x.dataset.bias === state.h4.bias))
      );
      evaluate();
    });
  });
}

function wireRegimeToggle() {
  document.querySelectorAll(".regime-toggle button[data-regime]").forEach(b => {
    b.addEventListener("click", () => {
      state.regime = b.dataset.regime;
      document.body.dataset.regime = state.regime;
      document.querySelectorAll(".regime-toggle button[data-regime]").forEach(x =>
        x.setAttribute("aria-pressed", String(x.dataset.regime === state.regime))
      );
      evaluate();
    });
  });
}

function wireMarket() {
  const sel = document.getElementById("market");
  sel.addEventListener("change", () => {
    state.market = sel.value;
    document.body.dataset.market = state.market;
  });
}

function wireFields() {
  document.querySelectorAll("[data-field]").forEach(el => {
    const path = el.dataset.field;
    const evt  = (el.tagName === "SELECT" || el.type === "checkbox") ? "change" : "input";
    el.addEventListener(evt, () => {
      setPath(state, path, coerce(el, el.value));
      evaluate();
    });
  });
}

function wireMistakes() {
  document.querySelectorAll("[data-mistake]").forEach(el => {
    el.addEventListener("change", () => {
      state.mistakes[el.dataset.mistake] = el.checked;
    });
  });
}

function wireTagLists() {
  /* Add via Enter key or button click */
  document.querySelectorAll("[data-add]").forEach(input => {
    const path = input.dataset.add;
    const commit = () => {
      const text = input.value.trim();
      if (!text) return;
      const arr = getPath(state, path);
      arr.push(text);
      input.value = "";
      renderTagList(path);
      evaluate();
    };
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") { e.preventDefault(); commit(); }
    });
    const btn = document.querySelector(`[data-add-btn="${path}"]`);
    if (btn) btn.addEventListener("click", commit);
  });
  /* initial paint */
  document.querySelectorAll("[data-list]").forEach(ul => renderTagList(ul.dataset.list));
}

function renderTagList(path) {
  const ul = document.querySelector(`[data-list="${path}"]`);
  if (!ul) return;
  const arr = getPath(state, path);
  ul.innerHTML = "";
  arr.forEach((text, idx) => {
    const li = document.createElement("li");
    li.className = "tag";
    li.innerHTML = `<span></span><button type="button" aria-label="remove">×</button>`;
    li.querySelector("span").textContent = text;
    li.querySelector("button").addEventListener("click", () => {
      arr.splice(idx, 1);
      renderTagList(path);
      evaluate();
    });
    ul.appendChild(li);
  });
}

function wireScreenshot() {
  const input = document.getElementById("screenshot");
  const preview = document.getElementById("screenshotPreview");
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (!file) { preview.hidden = true; preview.innerHTML = ""; return; }
    const url = URL.createObjectURL(file);
    preview.innerHTML = `<img alt="trade screenshot"/>`;
    preview.querySelector("img").src = url;
    preview.hidden = false;
  });
}

function wireSession() {
  const label = document.getElementById("sessionLabel");
  const dateEl = document.getElementById("dateLabel");
  const now = new Date();
  const utcHour = now.getUTCHours();
  let session = "ASIA";
  if (utcHour >= 7  && utcHour < 12) session = "LONDON";
  if (utcHour >= 12 && utcHour < 21) session = "NY";
  state.session = session;
  label.dataset.session = session;
  label.textContent = session;
  dateEl.textContent = now.toISOString().slice(0, 10);
}

function wireExecute() {
  const btn = document.getElementById("executeBtn");
  btn.addEventListener("click", () => {
    if (btn.disabled) return;
    const entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    entries.push({
      ts: Date.now(),
      market: state.market,
      session: state.session,
      regime: state.regime,
      snapshot: structuredClone(state),
      rr: rrRatio(state),
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    refreshJournalCount();
    flashExecuted();
  });

  document.getElementById("clearJournalBtn").addEventListener("click", () => {
    if (!confirm("Clear the journal? This cannot be undone.")) return;
    localStorage.removeItem(STORAGE_KEY);
    refreshJournalCount();
  });
}

function refreshJournalCount() {
  const entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  document.getElementById("journalCount").textContent = entries.length;
}

function flashExecuted() {
  const btn = document.getElementById("executeBtn");
  const prev = btn.querySelector(".execute-label").textContent;
  btn.querySelector(".execute-label").textContent = "TRADE LOGGED";
  setTimeout(() => { btn.querySelector(".execute-label").textContent = prev; }, 1400);
}

/* ---------------------------------------------------------------- *
 * Boot                                                             *
 * ---------------------------------------------------------------- */

function init() {
  wireSession();
  wireBiasSelector();
  wireRegimeToggle();
  wireMarket();
  wireFields();
  wireMistakes();
  wireTagLists();
  wireScreenshot();
  wireExecute();
  refreshJournalCount();
  evaluate();
}

document.addEventListener("DOMContentLoaded", init);
