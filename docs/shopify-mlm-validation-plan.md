# Shopify ↔ MLM Commission — Attribution-Seam Validation Plan

## Context

The last several sessions built a Shopify proof-of-concept to validate the **seams** between Shopify
and the MLM commission engine Jovonte is porting. The two source documents
(`architecture-big-picture-brief` and `attribution-validation-worksheet`) establish the thesis: in a
four-person, four-bounded-context build, **the seams *are* the product** — the hard part is the
contracts between contexts and the handful of decisions that can't be made independently, not the code
inside any one box. The differentiated, defensible moat is the **Capture & Attribution layer** (durable
referral capture that survives express checkout), *not* the comp-plan math (a commoditized red ocean).

This plan turns that thesis into an executable, multi-session validation. Per the decisions locked with
James (below), this round goes **deep on the attribution layer only** — it empirically settles which
referral carrier actually survives express checkout, builds the Capture context that turns raw Shopify
events into a high-fidelity `AttributedSale` fact, and **freezes the `AttributedSale` contract** (the seam
into Jovonte's engine). It deliberately stops before Commission/Ledger/Payouts are *built*, but it
**documents all five seam contracts** so the three co-founders can pick up their slices in parallel. The
intended outcome: walk into the next architecture review with the carrier-ranking question *answered from
real raw webhook bodies*, a running Capture skeleton, a versioned contract, and an evidence-backed update
to the decision register (D1–D9 + the worksheet's Part-5 open questions).

> **Why a separate repo:** `content-team` (this repo) is INWIGO's *marketing* repo and is the wrong home
> for this work — the Shopify/MLM commission POC is a separate venture. This document is the planning
> deliverable; the code lives in its own standalone monorepo, **`shopify-poc`** (now created at
> `github.com/doleful-creature/shopify-poc`), whose Phase 0 walking skeleton has been scaffolded separately.

---

## Decisions locked (from James, 2026-06-27)

| Decision | Choice | Consequence for this plan |
|---|---|---|
| **Scope** | **Attribution layer only** | Build Capture fully + freeze `AttributedSale`. Downstream seams documented, not built. |
| **POC stack** | **TypeScript / Node** | pnpm workspaces, Ajv for contracts. Flagged throwaway; production stack still deferred. |
| **Repo layout** | **Single monorepo skeleton** | One repo, `contracts/` shared, per-context dirs with CODEOWNERS; split to polyrepo later. |
| **Attribution data** | **Run the matrix fresh** | Worksheet grid is empty; Phase 1 stands up a raw sink and runs it on the `gimlet` dev store. |

**Stack-agnostic guardrail:** the contracts are plain **JSON Schema (draft 2020-12)** — compilable later
by Go/Python/Java/C#. TypeScript is throwaway scaffolding; the schema files are the durable artifact.

---

## What this POC proves — and what it does *not*

**Proves (this round):**
- That the capture carries **everything Jovonte's commission engine needs** — the stable party key
  (`resolved_rep_id` or `customer_id`) + confidence, raw money, context, and reversal anchors — validated
  consumer-driven against the engine's input spec. *(The headline: capture sufficiency for the seam.)*
- Which carrier(s) survive each express-checkout path, from **real raw webhook bodies** — supporting
  evidence for how reliably each engine-required field is populated (express measured via an accepted
  Apple/Google-Pay proxy; real Shop Pay deferred to a logged pre-freeze gate).
- That the Capture context can ingest at-least-once Shopify webhooks **idempotently** (duplicate delivery →
  exactly one `order_attribution` row, asserted *by row count*).
- That the Tier-2 first-party-id (`mlm_aid`) stitch rescues express/guest orders the Tier-1 carrier drops.
- That `AttributedSale` (incl. the `resolved_rep_id: null` / low-confidence cases) is a frozen, validated,
  versioned contract a downstream consumer can parse.

**Does NOT prove this round (deliberately deferred, but *contract-documented* for co-founders):**
- Commission calculation, genealogy/closure-table runs, the double-entry ledger, payout rails, and the
  end-to-end **refund/clawback saga**. These are stage-set as JSON-Schema stubs + an AsyncAPI seam catalog
  so Jovonte/Matt can build against frozen shapes — they are explicitly out of scope for the *build* here.

---

## New CLI tools to install (Phase 0)

| Tool | Install | Purpose |
|---|---|---|
| **Node ≥ 22.12** | `nvm install 22` | Hard requirement for Shopify CLI 4.x; runs the Capture service. |
| **Shopify CLI 4.3** | `npm i -g @shopify/cli@latest` | Scaffold the webhook-sink app, run the dev tunnel (bundled Cloudflare Quick Tunnel), versioned webhook subs in `shopify.app.toml`. |
| **pnpm** (via corepack) | `corepack enable && corepack prepare pnpm@latest --activate` | Monorepo workspace manager; `workspace:*` link to shared `contracts/`. |
| **just** | `cargo install just` / `brew install just` | One-command targets: `just up`, `just smoke`, `just contract-test`. |
| **Docker + Compose v2** | Docker Desktop / `docker-compose-plugin` | Boots Postgres (the event spine) with one command. |
| **Ajv + ajv-formats** | `pnpm add ajv ajv-formats` (in `contracts/`) | Compile draft-2020-12 validators at producer test-time + consumer runtime. |
| **Spectral CLI** | `npm i -g @stoplight/spectral-cli` | Lint schemas against house rules (money = integer, `event_version` present, `resolved_rep_id` nullable). |
| **AsyncAPI CLI** | `npm i -g @asyncapi/cli` | Validate/render the 5-seam catalog doc. |
| **GitHub CLI** | `brew install gh` | Create the repo, set branch protection + CODEOWNERS review gate. |
| **cloudflared / ngrok** | optional | Only if you want a *stable named* tunnel; the CLI bundles an ephemeral one. |
| **webhook.site** | (none — web) | Day-1 zero-code verbatim raw-body capture before the sink exists. |

> **Tunnel reality:** `shopify app dev` opens a public HTTPS Cloudflare Quick Tunnel to localhost and
> auto-registers the webhook URLs. No cloud account needed — exactly the portability we want before the
> cloud/stack is chosen.

---

## Phase 0 — Bootstrap the monorepo + tooling

**Goal:** `git clone && just up` boots the skeleton; CI fails on any seam/schema drift.

Standalone repo `shopify-poc` (already created, private). Layout:

```
shopify-poc/
├── contracts/                      # the 5 seams — SINGLE source of truth (all-hands CODEOWNERS)
│   ├── schemas/
│   │   ├── order_fact.v1.json            # Seam 0 (Shopify→Capture, the money fact)
│   │   ├── attribution_decision.v1.json  # Seam 0 (Shopify→Capture, the who+confidence)
│   │   ├── attributed_sale.v1.json        # Seam 1 (Capture→Commission)  ← THIS ROUND freezes this
│   │   ├── identity_enrichment.v1.json    # Seam 1-rev (Commission→Capture, customer_type)  [stub]
│   │   ├── commission_posted.v1.json      # Seam 2  [stub, documented not built]
│   │   ├── commission_reversed.v1.json    # Seam 2  [stub]
│   │   ├── payout_instruction.v1.json     # Seam 3  [stub]
│   │   └── disbursement_result.v1.json    # Seam 3  [stub]
│   ├── examples/<event>.valid.json + .invalid.json   # negative fixtures MUST fail the build
│   ├── asyncapi.yaml                # 5-seam catalog ($refs the schema files)
│   ├── .spectral.yaml               # house rules
│   ├── CONTRACTS.md                 # versioning discipline the 4 owners sign
│   └── package.json                 # @shopify-poc/contracts — exports validate() + TS types
├── services/
│   ├── capture/                     # ← THE build this round (James)
│   ├── commission/  ledger/  payouts/   # README + consuming-schema stub only (co-founders)
├── fixtures/                        # canned Shopify raw bodies (shop_pay null cart_token, standard, refund)
├── infra/sql/init.sql               # per-context schemas, outbox + processed_events (dedupe) tables
├── docker-compose.yml               # postgres:16 (healthcheck) + capture service
├── justfile                         # up / down / smoke / contract-test / fmt / lint
├── .github/{CODEOWNERS, workflows/ci.yml}
└── README.md                        # "TS + this layout are throwaway POC; prod stack deferred"
```

**Bootstrap commands** (the exact sequence):
```bash
mkdir shopify-poc && cd shopify-poc && git init -b main
corepack enable && corepack prepare pnpm@latest --activate
printf 'packages:\n  - "contracts"\n  - "services/*"\n' > pnpm-workspace.yaml
pnpm init                                 # root: "private": true
mkdir -p contracts/schemas services/capture/src fixtures infra/sql .github/workflows
cd contracts && pnpm init && pnpm add ajv ajv-formats && cd ..
# services/capture/package.json gets:  "@shopify-poc/contracts": "workspace:*"
pnpm install
```

**CODEOWNERS** (gate `contracts/` on all-hands; everything else single-owner):
```
/contracts/            @james @jovonte @matt @matt-payouts
/services/capture/     @james
/services/commission/  @jovonte
/services/ledger/      @matt
/services/payouts/     @matt
```
Then enable branch protection on `main`: require PR + **Require review from Code Owners** + require the
`contract-test` CI check. (Without the branch-protection toggle, CODEOWNERS is just documentation.)

**CI** (`ci.yml`, every PR): `pnpm install --frozen-lockfile && just contract-test && pnpm -r build && pnpm -r test`.
`contract-test` = Spectral lint + AsyncAPI validate + load every schema (`ajv.compile`/`check_schema`),
assert every `.valid.json` passes and **every `.invalid.json` fails** (negative tests prove the schema
actually constrains).

**Gate (Phase 0 → 1):** `just up` boots Postgres + capture healthy; CI green on an empty-but-valid
contracts set; a deliberately-malformed fixture turns CI red.

---

## Phase 1 — Capture sufficiency for the commission engine (matrix as evidence) — run fresh

**Goal (reframed):** Prove the capture produces **everything Jovonte's commission engine needs** from a
sale, under realistic checkout conditions including express-checkout failure modes. The carrier-survival
matrix is **supporting evidence** for how reliably each engine-required field is populated — not the end in
itself. The *seam*, not the carrier ranking, is the priority this round.

**Step 1 — Capture-sufficiency checklist (consumer-driven; the headline deliverable).** From Jovonte's
engine *input spec*, enumerate every field the engine consumes per sale; for each, record (a) which
`AttributedSale` field carries it, (b) where it originates (order-native carrier / Tier-2 `customer.id`
stitch / derived / reverse-seam `customer_type`), (c) reliability + the fallback when absent. Load-bearing
needs: a **stable party key** (`resolved_rep_id` when known, else `customer_id`) **+ `bind_confidence`**, with
`null` first-class; **raw money** (line items + per-line discount + currency — capture must *not* pre-compute
volume; the engine applies its own PV/BV/CV table); `context` (retail vs enrollment); `links` (`customer_id`,
`refund_of`); `occurred_at` + `idempotency_key`; and the persisted `customer→rep` map for rebills. If the
checklist surfaces a missing field, propose the **additive** change to `attributed_sale.v1.json`.

**Step 2 — Run the matrix as evidence** (build the raw sink first; discipline starts *here*, not Phase 2):
```ts
app.post('/webhooks', express.raw({ type: 'application/json' }), (req, res) => {
  const raw = req.body.toString('utf8');          // capture verbatim BEFORE any JSON parse
  // verify HMAC over `raw`; dedupe on req.headers['x-shopify-webhook-id']; 200 within 5s; enqueue async
  res.sendStatus(200);
});
```
- Register **`orders/create` AND `orders/paid`** separately (express/wallet can populate one but not the
  other), plus `refunds/create`. Versioned in `shopify.app.toml`.
- Log the **complete raw body**; **webhook.site** on day 1 for instant archaeology before the sink is solid.
- Tokens `SMOKE_<testid>_<unixts>`, **never reused**; dedupe on order id before grepping (Shopify redelivers).
- Carriers C1–C5 × paths P1–P6. **Decisive cells first:** C1×P2, C1×P3, C1×P4, C1×P5, C4×P2/P3/P4, C1×P6,
  and the time-delayed **rebill** test. Harvest Tier-2 recon (`cart_token` / `checkout_token` / `customer_id`
  presence) **in the same pass**.

> ### Express-checkout policy — proxy accepted this round, real Shop Pay deferred
> Real **Shop Pay / Shop Pay Installments / PayPal Wallet do not render in test mode**; only Apple/Google Pay
> express buttons do. Because the priority is *capture sufficiency for the engine* (not the precise carrier
> ranking), **Apple/Google Pay in test mode is an accepted proxy** this round — their `cart_token`-null /
> dropped-`note_attributes` behavior is exactly the express failure mode that forces the Tier-2 stitch to
> still yield a usable party key. Real Shop Pay is **demoted to a deferred, logged gate**, recorded as an
> **OPEN RISK in the decision register**: *"confirm carrier survival against real Shop Pay before freezing
> `attributed_sale.v1`."* Close it with a paid-month order before Phase 4 — do not silently drop it.

**Record (decision block):** Tier-1 primary carrier · express-checkout backbone (proxy-measured) · Tier-2
role (floor vs co-primary) · rebill-carries-nothing (from a real rebill body) · the open real-Shop-Pay item.

**Gate (Phase 1 → 2):** every engine-required field is reliably captured **or** has an honest, recorded
fallback — including a clean `null`/low-confidence party key on express/guest orders. Every decisive matrix
cell has a ✅/❌ with the exact observed value from a raw body. (Exact carrier ranking is secondary and may
carry the open real-Shop-Pay item into Phase 4.)

---

## Phase 2 — Capture context: idempotent ingest + reconciler

**Goal:** Build the Capture service that turns raw events into a recorded attribution, with idempotency
**load-bearing from the start** (the critics' #1 structural point — do not defer it to a "hardening" phase).

- **Idempotent ingest:** an `inbox`/`processed_events` table keyed on `X-Shopify-Webhook-Id` (and on
  `event_id` for internal events). One Postgres tx does the business effect **+** the processed-row insert,
  then ack **after** commit. (Ack-before-commit loses effects; commit-before-ack is caught by the dedupe
  table on redelivery. Getting this order wrong makes every later exactly-once claim a lie.)
- **`referral_tokens`** (Part 4.1): normalize-at-write, partial unique `(shop_id, token_normalized,
  carrier_type) where status='active'`, validity windows, resolution precedence (specific carrier beats
  `any`; same-specificity collision = **fail loud + alert**).
- **`capture_events`** append-only log + server-assigned monotonic `seq` per `mlm_aid`, allocated inside
  the row-locked critical section (prevents TOCTOU double-apply). Reconciler trusts highest-seq accepted
  event, not the cart attribute.
- **Provenance state machine** (Part 4.3): implement the full transition table
  (`user_overridden > user_confirmed > url_capture > system_default`; `lock_on_confirm` flag; `prior_token`
  on real swaps only). This is the spec to unit-test against.
- **The reconciler** (Part 3.4), 5-step confidence cascade → writes `order_attribution` (Part 3.6) with
  `bind_method` + `bind_confidence` on every row; `resolved_rep_id: null` is a **valid recorded outcome**.

**Gate (Phase 2 → 3):** replay the same `orders/create` webhook **K times** → exactly **one**
`order_attribution` row (asserted by **row count**, not by final-state equality, which can mask
double-apply); the same-specificity token collision raises a loud alert; the transition table passes its
unit suite cell-by-cell.

---

## Phase 3 — Tier-2 first-party-id stitch (the durable floor)

**Goal:** Prove the owned `mlm_aid` correlation id rescues the orders Tier-1 drops — this is "works
regardless," the sturdiest thing in the system.

- **Mint `mlm_aid`** (UUID) at landing: first-party cookie on the storefront domain + localStorage mirror;
  it is the spine of the capture log.
- **Binding cascade** (Part 3.3): **B1** `attributes[mlm_aid]=…` rides Tier-1 (exact join via
  `note_attributes`); **B2** the `mlm_aid ↔ customer.id` server-side map (`aid_identity_map`) — the
  durability layer that **outlives the 7-day ITP cookie cap**; **B3** time-boxed fuzzy fallback recorded as
  `provenance: fuzzy_match`, flagged, never silently authoritative.
- **Validate B2 observation points — the worksheet's Part-5 #1 linchpin.** Empirically determine *where/
  when* the storefront script can reliably observe `customer.id` (account create, login, identified
  checkout) to populate `aid_identity_map`. B2 coverage decides whether the Tier-2 floor actually holds;
  this is the next-session lead item from the worksheet and the honest residual-gap (never-identified guest
  express buyer) must be quantified, not papered over.

**Gate (Phase 3 → 4):** an express order that **dropped** the Tier-1 attribute but carries `customer.id`
is correctly bound via B2 (`bind_method: b2_customer`, `bind_confidence: high`); a never-identified guest
order lands as `resolved_rep_id: null` / `unattributed`, recorded not dropped.

---

## Phase 4 — Freeze the `AttributedSale` contract + seam hardening + decision register

**Goal:** Turn the validated behavior into a frozen, versioned seam, and update the architecture decisions
with evidence — "set the stage for more validations."

- **Freeze the contract** as JSON Schema draft 2020-12: `order_fact.v1`, `attribution_decision.v1`,
  `attributed_sale.v1`. Envelope required on every event: `event_type`, `event_version` (int),
  `event_id` (uuid), `occurred_at`, `idempotency_key`. **Money = integer minor units**
  (`{"type":"integer","minimum":0}`, never `number`), currency travels with every amount.
  **`resolved_rep_id` nullable-AND-required** (`["string","null"]`) so the express-null case is distinct
  from "forgot to set." Producer schemas `additionalProperties:false`; the **consumer read path stays
  lenient** (ignore unknown fields — producers backward-compatible, consumers forward-compatible).
- **Mock consumer** validates every emitted `AttributedSale` against the schema at the seam boundary —
  this is the proof that Capture and a (stub) Commission engine agree on the shape *before* Jovonte builds.
- **Spectral house rules** enforced in CI: `event_version` present, no `type:number` on money paths,
  `idempotency_key` on ledger-bound events, `additionalProperties:false` on event roots. Negative fixtures
  fail the build.
- **AsyncAPI 3.0 seam catalog** (`asyncapi.yaml`) documenting all five seams, `$ref`-ing the schema files —
  the readable map for the four founders. (Defer **Pact/Broker**; reach for it only once the skeleton walks
  and you want machine-checked producer↔consumer proof on `AttributedSale` + `CommissionPosted`.)
- **Webhook subscription health:** Shopify auto-deletes a subscription after sustained failure
  (~19 attempts / ~48h) — add a health-check / re-register check so attribution can't silently go dark.
- **Update the registers with evidence:** the decision register **D1–D9** (esp. D2 money units, D3
  idempotency, D6 `shop_id` RLS — all now demonstrated) and the worksheet's **Part-5 open questions**
  (#1 B2 coverage, #3 rebill map, #8 `orders/create` vs `orders/paid`, #9 lost-guest gap). Hand Jovonte
  the frozen `AttributedSale` + the documented `identity_enrichment` reverse seam.

**Gate (done):** `just contract-test` green; a null-`resolved_rep_id` `AttributedSale` round-trips through
the mock consumer and is queryable as an unattributed record; the decision register and Part-5 answers are
updated with raw-payload evidence; downstream seams exist as documented stubs for co-founders.

---

## Verification (end-to-end, per phase)

- **Phase 0:** `just up` → Postgres + capture healthy; `just contract-test` green; malformed fixture → red CI.
- **Phase 1:** draft the capture-sufficiency checklist from Jovonte's engine inputs first; then fire test
  orders through each matrix cell, inspect **complete raw bodies**, and fill the reliability column. Express
  via the Apple/Google-Pay proxy; log the real-Shop-Pay confirmation as an open pre-freeze gate.
- **Phase 2:** replay a captured webbook K× → assert **one** `order_attribution` row by count; run the
  transition-table unit suite; trigger a same-specificity token collision → assert loud alert.
- **Phase 3:** replay an express-dropped-attribute order with `customer.id` → assert `b2_customer` high-conf
  bind; replay a guest order → assert recorded `null`.
- **Phase 4:** `pnpm -r test` + `just contract-test`; mock consumer validates emitted `AttributedSale`
  (incl. null-rep) against `attributed_sale.v1.json`; Spectral rejects an injected float money field.
- **Shopify MCP** (`get-shop-info`, `list-orders`, `get-order`) is available in this session for
  cross-checking store state and order payloads alongside the CLI/tunnel capture.

---

## What this session produces

Because we're in plan mode in the (wrong) `content-team` repo, the concrete artifact here is **this plan,
committed to branch `claude/shopify-mlm-validation-plan-rsi2nr`** as a portable markdown doc James can take
into the new repo and the co-founder review. No application code is written in `content-team`; all build
work happens in `shopify-poc` per the phases above.
