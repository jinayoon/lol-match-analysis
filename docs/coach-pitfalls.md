# Common coaching mistakes

**Match fetch:** Never hand-roll long `curl` chains. Run `scripts/fetch_lol_match.py` once with `RIOT_API_KEY` (routing, ranked SR defaults, 429 retries).

**Item names:** Resolve IDs only via `items.json` from the export (or Data Dragon). If missing: `Unknown item (ID: XXXX)` — never guess from memory.

**Smite:** Only the jungler has Smite. If `ELITE_MONSTER_KILL` killer is not jungle, say they **secured** or **last-hit** the objective — not “landed Smite.”

**Counterplay:** Before “dodge this ability,” check whether the analyzed champion’s kit answers it (e.g. Braum **E** vs MF **R** — stand in channel with **E**, don’t only “dodge”).

**Itemization critique:** Before calling an item wrong: (1) Skill Capped guide for champ/role (see `docs/lol-reference.md`), (2) enemy comp (heal → GW, CC → Mikael’s, AoE → Locket). **Grievous Wounds** applies on any damaging hit — do not dismiss anti-heal because the buyer is “low damage”; critique timing/sequencing instead.

**Champion stats:** For ranges/CDs/damage numbers, use wiki or Data Dragon — not training-data recall.
