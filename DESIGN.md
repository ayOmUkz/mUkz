# TALLGRASS — Design Blueprint

> Codename: **Route Alpha** · A pixel-RPG trading terminal
> _"A Bloomberg Terminal got trapped inside a Game Boy Color cartridge and started hunting rare options flow."_

**Status:** Concept / pre-build. This document is product vision, information architecture, and visual + gameplay design only. No application code.

---

## 0. How To Read This Document

Two vocabularies run in parallel throughout:

- **Game language** — grass, encounter, party, gym, Dex.
- **Trading language** — signal, alert, position, sector, scanner archive.

Every game term resolves to exactly **one** trading meaning. The translation table (§3) and glossary (§11) are the contract. Nothing here is decoration-first: every tile, bar, and color carries data. The brief is "nostalgic but institutional" — treat the pixel art as a _serious information design system_ that happens to be fun.

Sections §1–§10 map 1:1 to the requested deliverables.

---

## 1. Product Concept Summary

### 1.1 What it is

**TALLGRASS** is an active-trading dashboard — scanner, journal, watchlist manager, and execution-decision aid — whose entire interface grammar is borrowed from Game Boy Color-era top-down RPGs. The market is rendered as an explorable overworld. Sectors are towns. Watchlists are routes. Scanner signals are wild encounters hiding in tall grass. Open positions are your party. Your trade history is a Pokédex.

It is **not a game with trading flavor.** It is a professional tool whose UX is reskinned to exploit the single most refined engagement loop in software history — the RPG explore-reward loop — to solve the one problem that actually moves the needle for traders: **consistent, repeatable, low-friction engagement with a disciplined process.**

### 1.2 The core insight

Opportunity detection is fundamentally an _exploration_ problem. Most trading dashboards present it as a spreadsheet problem — dense tables of tables. RPGs solved exploration decades ago: a world you want to walk through, rewards that feel _discovered_ rather than _queried_, and a collection loop that makes returning tomorrow feel natural. TALLGRASS maps `scan → encounter → decide → manage → log` onto `grass → wild encounter → battle → party → Pokédex`, so doing the boring-but-correct thing _feels_ like play.

### 1.3 Target user

Active retail-to-prosumer **options and futures traders** who already run scans, keep watchlists, and (try to) journal. The person currently juggling a broker platform, a flow scanner, a gamma site, a spreadsheet, and a Notion journal. TALLGRASS unifies that stack behind one coherent metaphor.

### 1.4 Differentiators

| Differentiator | Why it matters |
|---|---|
| **Exploration-first IA** | A map you traverse, not a table you sort. Opportunity feels found, not filtered. |
| **Process-reinforcing gamification** | EXP and badges reward _discipline_ (journaling, respecting stops, plan adherence) — never raw P&L. The game cannot be won by gambling. |
| **Journal as a first-class citizen** | The Trainer Journal is a core page, not a settings tab. Missed opportunities are logged automatically as "setups that fled." |
| **Regime-awareness in the core mechanic** | "Type effectiveness" is literally a market-regime fit score. The metaphor _is_ the analysis. |
| **One coherent world** | Stocks, options chains, futures, flow, gamma, volume profile — all live as features of one explorable region instead of five disconnected tabs. |

### 1.5 Functional coverage map

Everything in the functional brief has a home:

| Trading capability | Lives in | Rendered as |
|---|---|---|
| Stocks / equities | World Map, Routes | Town buildings, route tiles |
| Options chains | Battle Screen → "Review Chain" | A scrollable retro sub-menu |
| Futures (ES / NQ) | Premium zone: **Route ES / Route NQ** | High-level routes near "The Exchange" |
| Sector rotation | Gym Leaderboards, World Map weather | Gym strength ranking, money-flow arrows |
| Momentum scans | Tall Grass Scanner | Fire-type grass patches |
| IV Rank scans | Tall Grass Scanner | Volatility "weather" + grass density |
| Unusual options activity | Tall Grass Scanner, Encounter Screen | Psychic-type encounters |
| Gamma exposure | Encounter / Battle data block | Electric-type, "charge" meter |
| Volume Profile | Battle Screen chart panel | Ground-type, value-area tiles |
| Order Flow | Encounter "confirmation" line, NPC dialogue | Liquidity Hunter NPC + confirmation check |
| Wyckoff / AMT classification | Pokédex entry + setup tagging | "Species" classification field |
| Watchlist tracking | Routes on the World Map | Named/numbered routes |
| Trade journaling | Trainer Journal | Daily journal page |
| Missed-opportunity logging | Trainer Journal | "Setups that fled" log |
| Daily review | Trainer Journal + The Rest Stop | End-of-session ritual |
| A+ setup grading | Pokédex + rarity system | Rarity tier + "shiny" flag |

---

## 2. Core Gameplay Metaphor

### 2.1 Who you are

You are a **Scout** (the brief's "trainer," but institutional). The market is your **region** to explore. Your job is not to catch everything — it's to recognize what's worth catching, capture it cleanly, and keep a meticulous field journal.

### 2.2 The world

| Game element | Is the trading concept | Notes |
|---|---|---|
| The overworld / region | The whole market | Persistent, with weather + day/night |
| Towns / cities | Market sectors | Each has a Gym |
| Routes | Watchlists | "Route Alpha" = your primary watchlist |
| Tall grass patches | Opportunity zones | Where hidden setups live |
| Weather | Volatility regime | Clear / Rain / Storm / Fog / Harsh Sun |
| Time of day | Trading session | Dawn=pre-market, Day=RTH, Dusk=AH, Night=Globex |
| Gyms | Sector strength challenges | Has a "boss ticker" = sector leader |
| The Exchange (capital district) | Index futures hub | Route ES / Route NQ branch from here |
| The Rest Stop (Poké Center analog) | Risk reset + end-of-day flatten | "Heal" = review heat, flatten, journal |
| The Outfitter (Mart analog) | Scanner + strategy-tool config | Where you tune the Bag |
| The Lab (Professor analog) | Research / backtest / Pokédex analytics | Run by the Quant NPC |
| Elite Four | Recurring macro bosses | FOMC · CPI · NFP · OPEX |

### 2.3 The core loop

```
   EXPLORE            ENCOUNTER           DECIDE              MANAGE             LOG
  ┌────────┐         ┌──────────┐       ┌──────────┐       ┌────────┐        ┌────────┐
  │  walk  │  grass  │  "Wild   │       │  Battle  │  cap- │ Party  │  exit  │ Pokédex│
  │  the   │ rustles │  setup   │ ───▶  │  Screen  │ ture  │ (open  │ ─────▶ │   +    │
  │  map / │ ──────▶ │ appeared!│       │  Enter / │ ────▶ │ posi-  │        │ Journal│
  │  grass │         │   "      │       │  Pass    │       │ tions) │        │        │
  └────────┘         └──────────┘       └──────────┘       └────────┘        └────────┘
       ▲                                      │ pass / fled                      │
       └──────────────────────────────────────┴──────────────────────────────────┘
                          loop back — every outcome enriches the Dex
```

### 2.4 Capture, HP, and outcomes

- **Capture attempt** = placing the entry order. The "ball wobble" animation = your limit order working.
- **Capture success** = filled at an acceptable price. The setup becomes a **party member** (open position).
- **Capture difficulty** = execution friction (spread width, option liquidity, book depth, session liquidity, slippage estimate). Easy → Expert.
- **"It broke free"** = order didn't fill at your price.
- **"The setup fled"** = it triggered and ran without you → auto-logged to the Journal as a missed opportunity.
- **Party-member HP** = the position's _risk budget_. HP drains as price moves toward your stop. **HP = 0 → "fainted"** = stopped out.
- **EXP** = earned for _process_, never P&L: logging the trade, respecting the stop, following the written plan, completing the daily review. You cannot grind EXP by gambling.
- **Evolution** = a position reaching its profit target / thesis maturing — you choose to take profit or "let it grow."
- **Badges** = discipline + competence milestones (e.g., "Risk Discipline Badge: 20 trades within max-risk rules"; "Tech Gym Badge: demonstrated edge in the sector").

### 2.5 Trainer condition (the psychology layer)

The Scout has **status conditions** — trading psychology rendered as RPG status effects. Surfaced on the Trainer Card and as warnings on the Battle Screen:

| Condition | Trading meaning | Dashboard behavior |
|---|---|---|
| **Focused** (normal) | On-plan, even-keeled | No restriction |
| **Tilted** (Confusion) | Revenge-trade risk after a loss/streak | Battle Screen shows a cool-down warning |
| **Burned** | Just took a loss; confidence + capital chipped | Suggests smaller size on next capture |
| **Paralyzed** | Hesitation — missing valid entries | Journal nudges: "3 A-grade setups fled today" |
| **Asleep** | Disengaged — not scanning | Map dims; gentle re-engagement prompt |
| **Poisoned** | Holding a slow bleeder past its thesis | Party card flashes "thesis stale" |

---

## 3. Trading-to-Game Mechanic Translation Table

The master contract. **Game mechanic → Trading meaning → How it shows up in the UI.**

| Game mechanic | Trading meaning | UX manifestation |
|---|---|---|
| Tall grass | Opportunity zone (a scan/filter is "live") | Animated grass tiles; **rustle** = something hiding |
| Grass density | Number / strength of candidates in that scan | Sparse vs. thick grass |
| Wild encounter | A scanner alert fired | Screen-wipe → encounter popup |
| "Wild ___ appeared!" | The setup's name + type | Dialogue box headline |
| Pokémon species | A specific setup archetype (Wyckoff spring, gamma squeeze…) | Sprite + Dex species name |
| Pokémon type | Market setup category (see §7) | Color-coded type badge |
| Shiny variant | A+ / textbook-perfect confluence setup | Sparkle FX + special Dex flag |
| Rarity | Setup grade / frequency (Common→Legendary) | Star tier on the encounter card |
| Battle screen | Pre-trade decision interface | Modal: stats left, menu right |
| FIGHT / BAG / POKéMON / RUN | **ENTER TRADE / REVIEW CHAIN / CHECK RISK / PASS SETUP** | 2×2 retro command menu |
| Catching / Poké Ball wobble | Order working; fill quality | Capture animation tied to fill status |
| Capture difficulty | Execution friction (spread, liquidity, slippage) | Easy / Moderate / Hard / Expert gauge |
| Party (6 slots) | Open positions (configurable cap) | Party page + persistent party strip |
| Party member HP bar | Position risk budget (distance to stop) | Green→Yellow→Red HP bar |
| Fainting | Getting stopped out | Card greys out; "fainted" log entry |
| EXP / leveling | Process discipline score | Trainer Card XP bar |
| Evolution | Thesis matured / target reached | "Ready to evolve" prompt on party card |
| Pokédex | Discovered-setup archive / intelligence DB | Dex page (grid + entry detail) |
| Pokédex entry | One setup species' dossier + your history with it | Entry sheet (template in §4.4) |
| Bag / inventory | Strategy tools & order presets | Bag page; usable from Battle Screen |
| Items (Poké Balls, Repels, Potions) | Order types, alert mutes, hedges/adjustments | Item list with retro icons |
| Towns / cities | Market sectors | Map nodes |
| Gym | Sector strength challenge | Gym Leaderboards page |
| Gym Leader / boss ticker | Current sector-leading ticker | Boss sprite at top of gym board |
| Gym badge | Demonstrated edge in that sector | Badge case on Trainer Card |
| Routes | Watchlists | Map paths between towns |
| NPCs | Market participants / flow archetypes | Sprites that emit dialogue + signals |
| Weather | Volatility regime | Map overlay + status bar |
| Time of day | Session (pre/RTH/AH/overnight) | Lighting + clock |
| Map markers / flags | Market regime tags | Planted flag icons |
| Minimap | Portfolio + market at-a-glance | Corner widget |
| Elite Four / Champion | Macro events (FOMC, CPI, NFP, OPEX) | Countdown "challenges" on the map |
| Save point | Snapshotting journal / EOD state | The Rest Stop |
| Trainer Card | Account stats, badges, condition, settings | Trainer Card page |
| Starter Pokémon | Your core / signature strategy | Companion that levels with you |

---

## 4. Dashboard Page-by-Page Blueprint

### Global navigation — the START Menu

Press **START** anywhere to open the classic pause menu. This is the entire IA in one list:

```
┌─ START ─────────┐
│  ▶ MAP          │  → Page 1  World Map Dashboard
│    GRASS        │  → Page 2  Tall Grass Scanner
│    DEX          │  → Page 4  Pokédex Opportunity Archive
│    PARTY        │  → Page 6  Party / Active Positions
│    GYMS         │  → Page 7  Gym Leaderboards
│    JOURNAL      │  → Page 8  Trainer Journal
│    BAG          │  → Strategy tools / order presets
│    CARD         │  → Trainer Card (account, badges, condition)
│    OPTIONS      │  → Settings, palette, data feeds
└─────────────────┘
```

**Encounter (Page 3)** and **Battle (Page 5)** are not in the menu — they are _modal interrupts_ triggered by the world, exactly like wild encounters in the source material.

A persistent **party strip** (3–6 mini HP bars) and a **dialogue box** (latest NPC/system message) are docked on every page so the trader never loses positions or context.

---

### Page 1 — World Map Dashboard

**Purpose:** The home screen. A single top-down pixel map answering "what does the market look like right now, and where should I walk?"

```
┌──────────────────────────────────────────────────────────┐
│ ☀ CLEAR  │ REGIME: TRENDING │ ◷ 10:42 RTH │ HEAT ▓▓▓░░ 38%│  ← status bar
├──────────────────────────────────────────────────────────┤
│   ┌─────────┐        ~ ~ ~ grass ~ ~ ~      ┌──────────┐  │
│   │ SILICON │═══ Route Alpha ═══════════════│  VAULT   │  │
│   │  CITY   │         ░░grass░░             │   CITY   │  │
│   │ [TECH]  │                               │  [FINS]  │  │
│   └────┬────┘      ┌───────────────┐        └────┬─────┘  │
│        │           │ THE EXCHANGE  │             │        │
│   ~grass~          │  ▶ Route ES   │        ~ ~ grass ~ ~ │
│        │           │  ▶ Route NQ   │             │        │
│   ┌────┴────┐      └───────────────┘        ┌────┴─────┐  │
│   │ DERRICK │                               │ MENDWELL │  │
│   │  TOWN   │  ░░░░ thick grass ░░░░         │  [HLTH]  │  │
│   │[ENERGY] │   (UOA scan is hot)            └──────────┘  │
│   └─────────┘                                              │
├──────────────────────────────────────────────────────────┤
│ ▣ minimap   │ ♪ PROF. OAK-style NPC: "Storm building on   │
│ ▣ ▣ ▣ party │  Route NQ — mind your size, Scout."         │
└──────────────────────────────────────────────────────────┘
```

**Key components**
- **Towns** = the 11 GICS sectors; six headline towns (Silicon City/Tech, Derrick Town/Energy, Vault City/Financials, Mendwell/Healthcare, Smallcap Village/Russell, Highbeta Badlands/crypto + meme). Town size/glow = sector strength.
- **Routes** = watchlists connecting towns. **Route Alpha** = primary watchlist.
- **The Exchange** = central district; **Route ES / Route NQ** branch from it.
- **Tall grass patches** = active scans. Patch thickness = candidate count; **rustling** = a live signal.
- **Weather overlay** = vol regime. **Lighting** = session.
- **Money-flow arrows** between towns = sector rotation.
- **Minimap** + **regime flags** planted on the terrain.

**Interactions:** walk/click into a town → Gym board; click a route → that watchlist; click rustling grass → jump to Scanner focused on that patch; hover a town → sector tooltip card.

**Game feel:** calm exploration. The map _breathes_ — grass sways, weather drifts, NPCs patrol.

---

### Page 2 — Tall Grass Scanner

**Purpose:** The working surface. Hidden opportunities surface from active filters. This is where the Scout spends real screen time.

```
┌──────────────────────────────────────────────────────────┐
│ FILTERS (the "Repels & Lures")                            │
│ [Momentum]✓ [IV Rank]✓ [UOA]✓ [Gamma]□ [Vol Profile]□    │
├───────────────────────────┬──────────────────────────────┤
│   THE FIELD               │  CANDIDATE LIST              │
│                           │  ┌────────────────────────┐  │
│   ░░░░  ░rustle!░  ░░░    │  │🔥 NVDA  Momentum  ★★★☆ │  │
│   ░░grass░░  ░░░░░░░░░    │  │⚡ SMCI  Gamma     ★★★★ │  │
│        ░░░░░░░  ░░░░      │  │👻 XYZ   Trap      ★★☆☆ │  │
│   ░░░░░  ░rustle!░ ░░░    │  │🔮 AAPL  Flow      ★★★☆ │  │
│                           │  └────────────────────────┘  │
│  (patches = scan groups;  │  sort: rarity ▼ │ type │ age │
│   sprites peek out)       │                              │
├───────────────────────────┴──────────────────────────────┤
│ ♪ "Two patches rustling on Route Alpha. Walk carefully."  │
└──────────────────────────────────────────────────────────┘
```

**Key components**
- **Filter toggles** styled as in-game items ("Repels" suppress noise, "Lures" boost a scan's sensitivity).
- **The Field** — grass organized into patches, one per scan category. Sprites _peek_ from grass as candidates qualify; full **rustle** = alert-grade.
- **Candidate list** — the same data as a sortable retro list for power users (the table never disappears — it's just _also_ a field).
- **Encounter rate** indicator per patch = how active that scan is.

**Interactions:** click a rustling patch or a list row → **Encounter Screen**. Toggle filters → grass redraws. "Walk" continuously → ambient auto-scan.

**Game feel:** the hunt. Tension between "keep walking" and "investigate that rustle."

---

### Page 3 — Encounter Screen (modal interrupt)

**Purpose:** The alert. A detected setup demands a look — _now_.

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│        ⚡  Wild  GAMMA SQUEEZE  appeared!                 │
│            ┌──────────┐                                  │
│            │  SPRITE  │   SMCI · Technology              │
│            │  (peeks  │   Type: ELECTRIC   Rarity: ★★★★  │
│            │  from    │   Regime fit: SUPER EFFECTIVE    │
│            │  grass)  │   Capture difficulty: MODERATE   │
│            └──────────┘                                  │
│   ──────────────────────────────────────────────────     │
│   Momentum 82 │ IV Rank 19 │ Gamma ▓▓▓▓░ │ RVOL 3.1x     │
│   ──────────────────────────────────────────────────     │
│            ▶ INVESTIGATE        FLEE (dismiss)            │
└──────────────────────────────────────────────────────────┘
```

**Key components:** the headline ("Wild ___ appeared!"), the sprite (species art), the four-stat quick block, **type + rarity + regime-fit + capture difficulty** badges, and two choices: **INVESTIGATE** → Battle Screen, or **FLEE** → dismiss (logged).

**Alert tiers (how aggressively the world interrupts):**
- **Common** — sprite quietly peeks; no modal. Passive.
- **Uncommon / Rare** — full screen-wipe + encounter modal.
- **Legendary / Shiny** — screen flash, distinct chime, the modal _holds_ until acknowledged. (User-configurable; respects Trainer condition — a Tilted Scout gets calmer alerts.)

**Game feel:** the jolt of a wild encounter — but every interruption is _earned_ by signal quality.

---

### Page 4 — Pokédex Opportunity Archive

**Purpose:** A collectible intelligence archive. Every setup _species_ you've ever encountered, plus your personal history with it.

```
┌── POKéDEX ───────────────┬───────────────────────────────┐
│ #001 🔥 Momentum Break ✔ │  #014  ⚡ GAMMA SQUEEZE        │
│ #002 💧 Mean Revert    ✔ │  ┌────────┐                   │
│ #003 ⚡ Gamma Squeeze  ✔ │  │ SPRITE │  Caught: 11×       │
│ #004 👻 Liquidity Trap ✔ │  └────────┘  Win rate: 64%     │
│ #005 🛡 Defensive Rot. ✔ │                                │
│ #006 🔮 Unusual Flow   ✔ │  Type: ELECTRIC               │
│ #007 🌍 Value Area     ◐ │  Sector bias: Tech / Highbeta  │
│ #008 🐉 A+ Institut'l  ─ │  Best regime: HIGH VOL         │
│  ...                     │  Worst regime: LOW VOL         │
│ ▣▣▣ party  │ caught 6/8  │  Avg R: +1.7R  │ Hold: 1–3d    │
│            │             │  Field notes: "Fails when IV   │
│            │             │   rank > 50. Best off opening   │
│            │             │   drive." — last 3 encounters   │
└──────────────────────────┴───────────────────────────────┘
```

**Pokédex entry template** (per the brief, every field present):

```
SPECIES        Gamma Squeeze
DEX #          014
TYPE           Electric
CLASSIFICATION Wyckoff/AMT: "Spring → Markup"
─────────────────────────────────────────────
LAST ENCOUNTER Ticker: SMCI    Sector: Technology
               Momentum score: 82
               IV Rank: 19
               Options volume: 3.1× avg
               Gamma exposure: high / dealer short
               Risk/Reward: 1 : 2.4
─────────────────────────────────────────────
YOUR HISTORY   Encounters: 11   Captured: 7   Fled: 3   Passed: 1
               Historical win rate: 64%   Avg result: +1.7R
─────────────────────────────────────────────
NOTES          Free-text from previous encounters (auto-stamped
               with date + ticker + outcome).
─────────────────────────────────────────────
STATUS         ● Watching   ○ Entered   ○ Avoided   ○ Completed
```

**Two views:** the **species archive** (the dossier above — the _type_ of setup) and the **encounter log** (every individual instance: ticker, date, outcome). Filterable by type, sector, status, win rate. Completion % drives a collection meter.

**Game feel:** the satisfaction of a filling Dex — but the "collectible" is _earned pattern knowledge_.

---

### Page 5 — Battle Decision Screen (modal)

**Purpose:** The trade decision. Reached from "INVESTIGATE." Everything needed to commit or pass, on one screen.

```
┌── BATTLE ────────────────────────────────────────────────┐
│  ⚡ GAMMA SQUEEZE          Lv.★★★★    │  CAPTURE          │
│  ┌────────┐  SMCI                     │  DIFFICULTY       │
│  │ SPRITE │  Target HP ▓▓▓▓▓▓▓░░░     │  ▓▓▓░░ MODERATE   │
│  └────────┘  (room to profit target)  │  spread 0.6%      │
│                                       │  OI 12k · liquid  │
│  ── SETUP DOSSIER ──────────────────  ├───────────────────┤
│  Entry zone   42.10 – 42.60           │  ▶ ENTER TRADE    │
│  Stop level   40.80   (HP floor)      │    REVIEW CHAIN   │
│  Profit tgt   47.50 / 51.00           │    CHECK RISK     │
│  IV condition IV Rank 19 — cheap ✔    │    PASS SETUP     │
│  Liquidity    tight, deep book ✔      │                   │
│  Order flow   buyers lifting ✔        │  ── PROBABILITY ──│
│  R / R        1 : 2.4                 │  Score: 71/100    │
│  Regime fit   SUPER EFFECTIVE         │  Grade: A         │
└──────────────────────────────────────┴───────────────────┘
```

**The command menu** (replacing FIGHT / BAG / POKéMON / RUN):

| Menu item | Does |
|---|---|
| **ENTER TRADE** | Opens the order ticket (size from risk rules) → capture animation |
| **REVIEW CHAIN** | Retro sub-menu: the options chain, strikes/expiries, greeks |
| **CHECK RISK** | Position-sizing calc, portfolio heat impact, correlation w/ open party |
| **PASS SETUP** | Decline; logs reasoning to Journal (a _good_ pass earns EXP too) |

**Required data blocks** (all from the brief): entry zone, stop level, profit target(s), IV condition, liquidity condition, order-flow confirmation, probability score, R/R, and **capture difficulty** (clean-execution feasibility). The target's "HP bar" visualizes room-to-target; the difficulty gauge visualizes execution friction.

**Game feel:** a turn-based battle's deliberateness — _you have time to think,_ and the screen rewards thinking over reacting.

---

### Page 6 — Party / Active Positions

**Purpose:** Live management of open trades. Each position is a party member with stats.

```
┌── PARTY ─────────────────────────────────────────────────┐
│ ┌──────────────────────┐  ┌──────────────────────┐       │
│ │🔥 NVDA   Lv.A         │  │⚡ SMCI   Lv.A        │       │
│ │ Call debit spread     │  │ Long calls           │       │
│ │ HP ▓▓▓▓▓▓▓░░░  +1.2R  │  │ HP ▓▓▓░░░░░░░ -0.4R  │       │
│ │ Δ.42 Θ-.08 V.11 Γ.03  │  │ Δ.55 Θ-.14 V.20      │       │
│ │ DTE 9   ● healthy     │  │ DTE 4   ▲ near stop  │       │
│ │ Exit: trail / 47.50   │  │ Exit: hard 40.80     │       │
│ └──────────────────────┘  └──────────────────────┘       │
│ ┌──────────────────────┐  [ + empty slot ]               │
│ │👻 XYZ   Lv.B          │                                │
│ │ ...POISONED (stale)   │  Portfolio heat ▓▓▓▓░ 41%       │
│ └──────────────────────┘  Open R at risk: 2.3R            │
└──────────────────────────────────────────────────────────┘
```

**Each position card** (all brief fields present): ticker, strategy, entry, current P/L (as **R**), full greeks, DTE, **risk status** (HP bar + health icon), confidence level (its Lv. grade), and the **exit rule** written at entry. Cards show **Trainer-condition-style flags** (Poisoned = stale thesis, near-stop warnings).

**Aggregate footer:** portfolio heat, total open R-at-risk, correlation clusters ("3 party members are Fire-type — you're long one bet").

**Interactions:** tap a card → manage (scale, roll, hedge from the Bag, close); "ready to evolve" prompt at target.

**Game feel:** your team. You _care_ about these characters; that emotional attachment is redirected into _disciplined management_ instead of neglect.

---

### Page 7 — Gym Leaderboards

**Purpose:** Sector ranking + top-ticker strength board. "Which gyms are worth challenging today?"

```
┌── GYM LEADERBOARDS ──────────────────────────────────────┐
│  RANK  GYM            STRENGTH   MOMENTUM   BOSS TICKER   │
│  ─────────────────────────────────────────────────────   │
│   1    ⚡ TECH GYM     ▓▓▓▓▓ 91   ▲ +2.3%   NVDA  👑      │
│   2    🛡 ENERGY GYM   ▓▓▓▓░ 74   ▲ +1.1%   XOM           │
│   3    💧 FINS GYM     ▓▓▓░░ 58   ▼ -0.4%   JPM           │
│   4    🔮 HEALTH GYM   ▓▓░░░ 41   ▼ -0.9%   LLY           │
│   ...                                                    │
│  ── selected: TECH GYM ───────────────────────────────   │
│  Leadership: NVDA, AVGO, SMCI    Macro sensitivity: HIGH  │
│  Options activity: ELEVATED      Relative momentum: +2.3% │
│  Badge: ◇ not yet earned (need edge proof: 5 trades >0R)  │
└──────────────────────────────────────────────────────────┘
```

**Per gym:** sector strength score, leadership tickers, relative momentum, options activity level, macro sensitivity, and the **current boss ticker** (sector leader, wears a crown). Earning a gym **badge** = proving an edge there (tracked from your Journal).

**Game feel:** a ladder to climb; sectors you "main" vs. sectors you avoid.

---

### Page 8 — Trainer Journal

**Purpose:** Daily review — trades, lessons, missed opportunities, emotional state. The page that actually compounds skill.

```
┌── TRAINER JOURNAL ──────────────  Thu 2026-05-14 ────────┐
│  CONDITION TODAY:  ● Focused → ▲ Tilted (after 14:10)    │
│  EXP earned: +120 (journaled all trades, 1 clean pass)   │
│  ─────────────────────────────────────────────────────  │
│  CAPTURED                                                │
│   🔥 NVDA  +1.2R   plan-adherence ✔   "good entry"       │
│   ⚡ SMCI  -0.4R   plan-adherence ✔   "stop respected"    │
│  ─────────────────────────────────────────────────────  │
│  SETUPS THAT FLED  (auto-logged)                         │
│   🐉 META  A+ Institutional — hesitated, Paralyzed       │
│   🌍 CL    Value Area — wasn't scanning Energy patch     │
│  ─────────────────────────────────────────────────────  │
│  LESSON OF THE DAY  (free text)                          │
│   "Tilt started after the SMCI stop. Should have walked  │
│    to the Rest Stop instead of forcing the META entry."  │
│  ─────────────────────────────────────────────────────  │
│  ▶ COMPLETE DAILY REVIEW   (saves at the Rest Stop)      │
└──────────────────────────────────────────────────────────┘
```

**Sections:** condition timeline (psychology across the session), trades captured (with plan-adherence flags + R), **"setups that fled"** (missed opportunities, auto-logged from Encounter dismissals and un-acted Scanner alerts), free-text lesson, and the **Complete Daily Review** ritual (the "save point" — done at The Rest Stop, awards EXP).

**Game feel:** the end-of-session campfire. Reflective, low-stimulus, _rewarding_ — the opposite energy of the Scanner.

---

## 5. Pixel Art UI Component Library

### 5.1 Foundations

**Grid & scale.** 8×8 px base tile. UI built on a 4 px sub-grid. Sprites 16×16 (small NPC/items) and 32×32 (encounter species). Render at integer scale only (2×, 3×, 4×) — never fractional, never anti-aliased.

**Palettes.** Limited, named, swappable (Options page):

| Palette | Use | Hex set |
|---|---|---|
| **DMG Green** | "Nostalgia mode" world layer | `#0f380f` `#306230` `#8bac0f` `#9bbc0f` |
| **Crystal Terminal** (primary) | UI chrome — institutional, cool | bg `#0b0f14` · panel `#14202b` / `#1f2e3d` · ink `#c3d1d9` · frame `#5a7a8c` |
| **Phosphor accents** | Data semantics | up `#3fe06b` · down `#ff5d5d` · caution `#ffc23f` · info `#4fd6e0` |

**Type accent colors** (one per setup type): Fire `#ff6a3d` · Water `#4f9dde` · Electric `#ffd23f` · Ghost `#8a6fd6` · Steel `#9aa7b0` · Psychic `#ff6fae` · Ground `#c9a25e` · Dragon `#6a5cff`.

**Typography.** Two pixel fonts: a chunky display face (e.g. _Press Start 2P_) for headers/labels/menu items; a **readable pixel mono** (e.g. _Departure Mono_ / _Pixel Operator Mono_) for all numbers and dense data — display faces are too wide for a trading grid. Hard rule: no number is ever shown in the display face.

### 5.2 Component list

| Component | Description | Carries |
|---|---|---|
| **Chunky window frame** | 2–4 px double-line border, hard corners, drop "shadow" of one dark tile | Every panel |
| **Dialogue box** | Bottom-docked, typewriter text reveal, ▼ continue arrow | NPC + system messages |
| **Command menu** | 2×2 or list, blinking ▶ cursor | Battle actions, START menu |
| **HP / risk bar** | Segmented bar, green→yellow→red | Position risk, target room |
| **Charge / strength meter** | Filled-block gauge `▓▓▓░░` | Gamma, sector strength, heat, capture difficulty |
| **Type badge** | Color chip + 1-glyph icon | Setup type everywhere |
| **Rarity stars** | `★★★★` 1–4 + shiny sparkle | Setup grade |
| **Species sprite** | 32×32, 2–4 frame idle anim ("peek from grass") | Encounter / Battle / Dex |
| **NPC sprite** | 16×16, walk cycle, "!" / "?" thought bubble | Market participants |
| **Grass tile set** | Static + 3-frame rustle animation | Scanner field, map |
| **Tile-based map** | Towns, routes, water, buildings, gym doors | World Map |
| **Minimap widget** | Compressed map + party/heat dots | Corner of every page |
| **Weather overlay** | Particle layer: rain, storm, fog, sun rays | Regime |
| **Day/night lighting** | Palette shift over the map | Session |
| **Map flag / marker** | Planted pennant icon | Regime tags |
| **Badge icons** | 16×16 minted-metal style | Trainer Card badge case |
| **Encounter popup** | Screen-wipe transition + framed modal | Alerts |
| **Capture animation** | Ball-wobble (1/2/3 wobble → click / break) | Order fill status |
| **Item icons** | 16×16 — balls, potions, repels, lures | Bag / order presets |
| **Pokédex grid cell** | Number + sprite + caught-state glyph | Dex archive |
| **Stat block** | Label-value rows in pixel mono, hairline rules | Dossiers, cards |
| **Tab / page header** | Banner with page name + page glyph | Every page |
| **Cursor / selection** | Blinking ▶ + 1-tile highlight box | Navigation |
| **Toast / chime** | Small corner card + 8-bit SFX | Background events |
| **Transition wipes** | Door-fade, spiral, curtain | Page → page, world → battle |

### 5.3 Motion principles

- **Snappy, not smooth.** Stepped animation (8–12 fps), no easing curves — movement happens in tile/pixel jumps.
- **Idle life everywhere.** Grass sways, water shimmers, NPCs breathe, the cursor blinks. A static screen feels broken.
- **Sound is data.** Distinct 8-bit cues for: Common peek, Rare encounter, Legendary/Shiny, fill confirmed, stop hit, EXP gained, daily-review saved.
- **Restraint = institutional.** Animation is _ambient_, never carnival. When real money is on screen, the motion calms down.

---

## 6. Scanner Alert Examples

Format: **the encounter line** · _trigger logic_ · type · rarity · what the card shows.

1. **"⚡ A Wild GAMMA SQUEEZE appeared!"**
   _Dealer gamma negative + price near a high-OI strike + RVOL > 2.5× + float/short conditions._ Electric · ★★★★ · shows gamma "charge" meter, strike wall map, RVOL.

2. **"🔮 An Unusual OPTIONS FLOW emerged from the grass!"**
   _Sweep/block prints > X notional, aggressive (lifting offers), DTE/strike outside normal._ Psychic · ★★★☆ · shows trade tape, premium spent, call/put skew.

3. **"🔥 A Wild MOMENTUM BREAKOUT candidate emerged!"**
   _Price clears N-day range high on RVOL > 2× with trend regime confirmed._ Fire · ★★★☆ · shows range-break level, RVOL, ADX.

4. **"💧 A Wild MEAN-REVERSION setup appeared!"**
   _Stretched from VWAP/band by ≥ 2σ in a range regime, momentum diverging._ Water · ★★☆☆ · shows σ-distance, regime tag, divergence.

5. **"🔥 A Rare IV-CRUSH play is hiding here!"**
   _IV Rank > 80 into a known catalyst (earnings) — premium-selling candidate._ Fire (volatility variant) · ★★★★ · shows IV Rank, catalyst date, expected move.

6. **"🌍 A Wild VALUE-AREA setup appeared!"**
   _Price testing prior-session VAH/VAL or a naked POC with order-flow rejection._ Ground · ★★★☆ · shows volume profile, VA levels, delta.

7. **"🛡 A Wild SECTOR ROTATION appeared!"**
   _Defensive sector relative strength flips positive while index momentum fades._ Steel · ★★★☆ · shows relative-strength curve, money-flow arrow.

8. **"👻 Something feels off in the grass…"** → **"It was a LIQUIDITY TRAP!"**
   _Breakout on weak/declining volume + thin book + prior failed breaks — a fake-out._ Ghost · ★★☆☆ · shows the warning explicitly; this encounter teaches you to PASS.

9. **"⚡ A Wild ES LIQUIDITY SWEEP setup appeared on Route ES!"**
   _Stop-run beyond a session extreme + immediate reclaim + delta flip._ Electric/Ground · ★★★★ · shows swept level, reclaim, footprint delta.

10. **"🐉 ✨ A SHINY A+ INSTITUTIONAL setup appeared!"**
    _Multi-factor confluence: regime fit + flow + gamma + level + relative strength all aligned._ Dragon · ★★★★ + shiny · the rare "hold-until-acknowledged" alert; auto-flagged in the Dex.

**Alert logic summary**
- Every alert has a **trigger spec** (objective, backtestable conditions) — the metaphor never replaces the math.
- **Rarity = strictness.** More conditions + better regime fit + cleaner liquidity → higher tier → louder interrupt.
- **Trainer-condition aware.** A Tilted/Burned Scout gets de-escalated alerts (peek instead of modal) to reduce reactive trading.
- **Fled tracking.** If an alert isn't acted on and the setup runs, it's auto-logged to the Journal as a "setup that fled."

---

## 7. Trade Setup "Creature Type" Taxonomy

### 7.1 The eight types

| Type | Trading meaning | Primary trigger signals | Typical hold |
|---|---|---|---|
| 🔥 **Fire** | Momentum / breakout (incl. volatility-expansion plays) | Range break, RVOL spike, ADX, trend regime | Intraday – days |
| 💧 **Water** | Mean reversion | σ-stretch from VWAP/bands, exhaustion, range regime | Hours – days |
| ⚡ **Electric** | Gamma squeeze | Dealer gamma, OI walls, float/short, RVOL | Intraday – days |
| 👻 **Ghost** | Hidden liquidity / trap / fake-out | Weak-volume breaks, thin book, prior failed breaks | Avoid / fade |
| 🛡 **Steel** | Defensive sector rotation | Defensive relative strength, money flow, risk-off | Days – weeks |
| 🔮 **Psychic** | Unusual options flow / predictive signal | Sweeps, blocks, skew shifts, aggressive prints | Varies (leads) |
| 🌍 **Ground** | Value area / volume profile | VAH/VAL/POC tests, delta rejection, AMT structure | Intraday – days |
| 🐉 **Dragon** | Rare A+ institutional setup | Multi-factor confluence of the above | The "keepers" |

### 7.2 Type effectiveness = regime fit

The "type chart" is a literal **regime-fit score.** Market regime is the battle's _terrain/weather_; a type is **Super Effective**, **Neutral**, or **Not Very Effective** depending on it. This is shown on every Encounter/Battle screen.

| Type \ Regime | TRENDING | RANGE / CHOP | HIGH VOL | LOW VOL / COMP. | ROTATIONAL |
|---|---|---|---|---|---|
| 🔥 Fire | **Super** | Weak | Neutral | Neutral | Neutral |
| 💧 Water | Weak | **Super** | Neutral | Neutral | Neutral |
| ⚡ Electric | Neutral | Neutral | **Super** | Weak | Neutral |
| 👻 Ghost | Neutral | Neutral | Neutral | **Appears most** ⚠ | Neutral |
| 🛡 Steel | Weak | Neutral | **Super** | Neutral | **Super** |
| 🔮 Psychic | Neutral | Neutral | Neutral | Neutral | **Super** (leads shifts) |
| 🌍 Ground | Neutral | **Super** | Neutral | Neutral | **Super** |
| 🐉 Dragon | **Super** | **Super** | **Super** | **Super** | **Super** |

> **Ghost is the teaching type.** It doesn't get a "good regime" — it shows up most in compression/at range extremes and exists to be _recognized and passed_. Passing a Ghost cleanly earns EXP.
> **Dragon is legendary** — effective everywhere, but its _encounter rate_ is intentionally tiny.

### 7.3 Rarity tiers

| Tier | Stars | Setup grade | Meaning |
|---|---|---|---|
| Common | ★ | C | Frequent, low conviction (e.g. routine high-RVOL) |
| Uncommon | ★★ | B | Decent confluence, tradeable |
| Rare | ★★★ | A | Strong multi-factor setup |
| Legendary | ★★★★ | A+ | Best-in-class confluence; loud alert |
| **Shiny** (overlay) | ✨ | A+ "textbook" | Perfect confluence — cosmetic sparkle + special Dex flag, any type |

### 7.4 Capture difficulty (execution friction — separate from rarity)

A great setup can still be **Expert** to capture. Rendered as its own gauge:

| Difficulty | Conditions |
|---|---|
| **Easy** | Tight spread, deep liquidity, prime session |
| **Moderate** | Some spread, adequate OI/book |
| **Hard** | Wide spread, thin OI, fast tape |
| **Expert** | Illiquid, large slippage risk — capture may "break free" |

Rarity tells you _how good the prize is._ Capture difficulty tells you _whether you can actually get it cleanly._ A wise Scout passes Expert-difficulty Commons and hunts Easy Rares.

---

## 8. Example User Flow — Scanner Signal → Trade Decision

A concrete walkthrough, start to finish.

1. **Morning, on the map.** Scout opens TALLGRASS. Status bar: ☀ → 🌧 _Rain_, regime **HIGH VOL**, session **RTH**. The **Market Maker NPC** on Route Alpha says: _"Spreads are wide on Route NQ today, Scout — mind your fills."_

2. **Walking the Scanner.** Scout opens **Tall Grass** (Page 2). The **UOA** and **Gamma** filter-items are active. A patch on the Tech sub-field starts **rustling hard** — a sprite peeks out.

3. **Encounter.** Click the rustle → screen-wipe → **"⚡ A Wild GAMMA SQUEEZE appeared!"** Card: **SMCI**, Electric, ★★★★, **Regime fit: SUPER EFFECTIVE** (Electric loves HIGH VOL), **Capture difficulty: MODERATE**. Quick stats: Momentum 82, IV Rank 19, Gamma ▓▓▓▓░, RVOL 3.1×.

4. **Investigate → Battle Screen.** Scout hits **INVESTIGATE**. The Battle Screen lays out the dossier: entry 42.10–42.60, stop 40.80, targets 47.50 / 51.00, IV Rank 19 (cheap ✔), liquidity deep ✔, order flow buyers lifting ✔, R/R 1:2.4, probability **71/100 — Grade A**.

5. **Check the chain & risk.** **REVIEW CHAIN** → scans strikes, picks the 45C two weeks out (OI healthy). **CHECK RISK** → sizing calc says 1.0R fits within max-risk rules; portfolio heat would go 38% → 47%; warns that **NVDA (Fire) is already in the party** — note the directional correlation.

6. **Decide.** Regime fit is Super Effective, R/R is clean, risk fits. Scout chooses **ENTER TRADE**. Order ticket pre-fills size from the risk rule.

7. **Capture.** Ball-wobble animation as the limit order works… _wobble, wobble, click_ — **filled at 42.40.** SFX confirms. SMCI joins the **party** as a Level-A Electric member with a full green HP bar; exit rule "hard stop 40.80" is written onto the card.

8. **Manage.** Through the session the **party strip** stays docked. SMCI's HP holds green, then dips to yellow on a pullback — no action needed, stop intact. Later it pushes toward 47.50; the card shows **"ready to evolve."** Scout scales half, trails the rest.

9. **Log.** End of day at **The Rest Stop**, the Scout opens the **Journal**. SMCI auto-appears under **Captured** (+1.6R, plan-adherence ✔). One **🐉 Dragon on META "fled"** — the Scout hesitated (condition went **Paralyzed** mid-day). Scout writes the lesson, hits **Complete Daily Review** → **+EXP**.

10. **Archive.** The **Pokédex** entry for _Gamma Squeeze_ updates: Encounters 11→12, Captured 7→8, win rate recalculated, a dated field note appended. The pattern knowledge compounds for next time.

> One loop: `map → grass → encounter → battle → capture → party → journal → dex`. Every page in the product was touched, and the only "game" was doing the process correctly.

---

## 9. Future Feature Ideas — Sims-Like Production Gameplay

The long-term vision: the world stops being a static skin and becomes a **living, persistent simulation** that rewards tending it.

**A living overworld.** Grass grows and withers with scan activity; towns light up by session; weather drifts in real time. Leave for a day, come back, and the world has _changed_.

**Cultivation (the "production" core).** "Plant" watchlist tickers like crops in plots you own. **Tending them = doing your homework** — marking levels, reading filings, setting alerts. Well-tended plots mature into higher-rarity encounters; neglected plots wither. Prep work becomes visible, compounding progress.

**NPC routines & ambient simulation.** Market-participant NPCs walk patrol routes and _react_ to real conditions. Even when you're not looking, the world simulates — return to a **"While you were away…"** digest: _"A Wild Breakout fled on Route NQ. The Whale NPC printed a block in XLE."_

**Buildings you upgrade.** Spend earned **Research Points** (from journaling/reviews) to upgrade structures: a better **Lab** unlocks deeper backtest analytics; a bigger **Bag** unlocks more strategy-tool slots; an upgraded **Rest Stop** unlocks richer review templates. Progression gates _capability_, never _safety_.

**Resource economy that fights overtrading.** A daily **Focus** meter caps quality encounters/captures — running out nudges you to stop, by design. **Research Points** are the "currency of patience," earned only by reflection.

**Seasons & festivals.** The calendar becomes seasons: **earnings season** as a literal in-game season with more (and more volatile) grass; **OPEX** as a recurring festival event; the **Elite Four** (FOMC/CPI/NFP/OPEX) as scheduled boss challenges that change the weather.

**The starter / companion.** Pick a **starter** = your signature strategy. It levels with you, gains "moves" (variations) as your Dex win rate proves them, and is the emotional through-line of the save file.

**Breeding hypotheses.** Combine two Dex observations into a **hypothesis egg** — a setup variant to forward-test. Hatches into a provisional new species if it earns its win rate.

**Co-op & guilds (later, optional).** Trainer guilds with a shared Dex; cross-user **Gym leaderboards**; trade-review "raids" where members critique each other's Journals. Strictly process-and-pattern sharing — never copy-trading.

**Persistence & save file.** One long-running save: your Dex, badges, trainer level, and the state of your cultivated world _are_ your trading track record, made tangible.

---

## 10. First MVP — One-Page HTML Dashboard

**Goal:** the smallest build that makes a stranger _feel_ the whole vision in 30 seconds. One screen, mock data, the complete core loop visible.

> No code in this document — this is the build spec for that first page.

### 10.1 What it is

A single self-contained `index.html` page: **a stripped "Tall Grass Scanner + Encounter + Battle + Party" on one screen.** It demonstrates `explore → encounter → decide → manage` end-to-end. Driven entirely by a small **mock data object** (~6 watchlist items, each hiding a setup) — no live feeds, no backend, no persistence.

### 10.2 Layout (single viewport, no scrolling)

```
┌──────────────────────────────────────────────────────────┐
│ ☀ CLEAR │ REGIME: TRENDING │ ◷ 10:42 RTH │ HEAT ▓▓▓░░    │  status bar
├───────────────────────────────────┬──────────────────────┤
│  THE FIELD                        │  PARTY               │
│   ░░░░  ░rustle!░  ░░░░░░░        │  ┌────────────────┐  │
│   ░░grass░░   ░░░░   ░░░░         │  │🔥 NVDA  +1.2R  │  │
│   ░░░  ░rustle!░  ░░░░░░░░        │  │ HP ▓▓▓▓▓▓░░    │  │
│   (6 patches = 6 watchlist names; │  └────────────────┘  │
│    they rustle on mock signals)   │  ┌────────────────┐  │
│                                   │  │⚡ SMCI  -0.4R  │  │
│  [ click a rustling patch ]       │  │ HP ▓▓▓░░░░░    │  │
│                                   │  └────────────────┘  │
├───────────────────────────────────┴──────────────────────┤
│ ♪ "Two patches rustling on Route Alpha. Walk carefully."  │  dialogue box
└──────────────────────────────────────────────────────────┘
```

Clicking a rustling patch opens the **Encounter → Battle modal** over this screen.

### 10.3 Core interactions (the MVP must do exactly these)

1. **Ambient rustle.** On load + on a timer, mock signals fire; 1–2 grass patches animate a rustle.
2. **Encounter.** Click a rustling patch → modal: _"Wild ⚡ Gamma Squeeze appeared!"_ with type badge, rarity stars, regime-fit tag, capture-difficulty gauge, and the 4-stat quick block.
3. **Battle.** "Investigate" → the dossier (entry/stop/target, IV, liquidity, flow, R/R, probability) + the 4-command menu: **ENTER TRADE / REVIEW CHAIN / CHECK RISK / PASS SETUP**.
4. **Capture.** "Enter Trade" → ball-wobble animation → on success the setup is appended to the **Party strip** with a fresh HP bar.
5. **Pass / Flee.** "Pass Setup" or dismiss → a line is written to the **dialogue box** (the seed of the Journal).
6. **Dialogue box** narrates every event in typewriter text.

### 10.4 Visual requirements

- **Crystal Terminal** palette for chrome; **type accent colors** for badges; phosphor green/red for P/L.
- One display pixel font (headers/menus) + one readable pixel mono (numbers) via webfont.
- Chunky 4 px double-line borders; hard corners; one-tile drop shadows.
- Stepped animation only (grass rustle = 3 frames; ball wobble = 3 states). Integer scaling.
- Fits a 1280×720 viewport with no scroll.

### 10.5 Explicitly OUT of scope for the MVP

Live/real data · World Map page · full Pokédex · full Journal · Gym Leaderboards · the START-menu navigation · multi-page routing · persistence/save · sound (nice-to-have, not required) · the Sims/production layer.

### 10.6 Why this is the right MVP

- It renders the **entire core loop** (`explore → encounter → decide → manage`) on **one screen** — the fastest possible proof of the concept's _feel_.
- Every element is a **seed of a full page**: The Field → Page 2, the modal → Pages 3 & 5, the Party strip → Page 6, the dialogue box → Page 8.
- Mock-data-driven means **zero infra** — pure front-end, instantly shareable, trivially iterable on visual feel.
- It forces the hardest design question early: _does pixel-RPG framing make trading data clearer or just cuter?_ One honest screen answers that before we build eight pages.

**Build order after MVP:** World Map (Page 1) → real Scanner data (Page 2) → Pokédex (Page 4) → Party deepening (Page 6) → Journal (Page 8) → Gyms (Page 7) → START-menu IA wiring → production/Sims layer.

---

## 11. Glossary — The Two-Vocabulary Contract

| Game term | Trading term |
|---|---|
| Scout / Trainer | The user / trader |
| Region / overworld | The market |
| Town / city | Market sector |
| Gym | Sector strength challenge |
| Boss ticker / Gym Leader | Sector-leading ticker |
| Route | Watchlist |
| Tall grass / patch | Opportunity zone (a live scan) |
| Rustle | A signal qualifying within a scan |
| Wild encounter | A scanner alert |
| Species | A setup archetype |
| Type | Setup category (regime-fit class) |
| Shiny | A+ "textbook" confluence setup |
| Rarity / stars | Setup grade (C/B/A/A+) |
| Capture | Placing/filling the entry order |
| Capture difficulty | Execution friction |
| "It fled" | A missed opportunity |
| Party | Open positions |
| HP bar | Position risk budget (distance to stop) |
| Fainted | Stopped out |
| Evolution | Thesis matured / target reached |
| EXP | Process-discipline score |
| Badge | Discipline / sector-edge milestone |
| Pokédex | Discovered-setup archive |
| Bag / items | Strategy tools & order presets |
| Weather | Volatility regime |
| Time of day | Trading session |
| Elite Four | Recurring macro events |
| The Rest Stop | End-of-day flatten + review ritual |
| The Lab | Research / backtest / Dex analytics |
| The Outfitter | Scanner & strategy-tool configuration |
| Trainer condition | Trading-psychology state |

---

## 12. Decisions To Lock Before Build

Open questions worth resolving early — they shape the architecture:

1. **Data sources.** Which feeds for quotes, options chains, flow, and gamma? (Affects everything past MVP.)
2. **Execution scope.** Is "Enter Trade" a real broker order, a paper ticket, or a hand-off to the user's broker? MVP assumes none — decide for v2.
3. **Party cap.** Fixed at 6 (canon) or configurable to real position counts? Recommendation: soft-cap at 6 visible, "PC box" overflow for the rest.
4. **Regime engine.** What objectively classifies TRENDING / RANGE / HIGH VOL / etc.? The whole type-effectiveness mechanic depends on this being credible.
5. **EXP formula.** Exact process behaviors that grant EXP — must be impossible to farm by gambling.
6. **Alert delivery.** In-app only, or push/desktop notifications for Legendary/Shiny?
7. **Platform.** Web-first (recommended for MVP), with desktop/mobile later? Mobile changes the pixel-density math.
8. **Accessibility.** Pixel fonts + limited palettes need a deliberate high-contrast/large-text mode — plan it in, don't bolt it on.

---

_End of blueprint. Next deliverable on request: the MVP build (§10) as a single self-contained HTML page._
