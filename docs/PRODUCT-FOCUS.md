# Product focus: what to invest in, and what to leave alone

**Decided 2026-08-02, from `/demand` rather than from opinion.** Read this before
building anything new on a paid endpoint.

## The measurement

`app/demand.py` counts 402 challenges served per resource against sales settled,
keyed to the revenue ledger's `product_id`. It exists precisely because "nobody
has ever seen this listing" and "agents priced it and walked away" look
identical from outside and imply opposite next moves. It had never been read.

Read on 2026-08-02:

| Resource | Challenges | Qualified | Sales | Conversion | Revenue |
|---|---:|---:|---:|---:|---:|
| Pulse composite | 5,133 | 1,840 | 3 | **0.02%** | $0.35 |
| `/base/tx-decision` | 4,780 | 1,783 | 3 | **0.06%** | $0.03 |
| `/mn/property-check` | 25 | 15 | 2 | **4.0%** | $0.02 |

`mn-property-check` converts **66-200x better** than the other two, on traffic
roughly 200x smaller.

## What that means

The two high-traffic products do not have a discovery problem. They have been
seen thousands of times and converted at ~0.03%. Read the raw user agents in
`/demand` and most of that traffic is `x402-census-probe`, `AgentReeve`,
`x402-liveness-directory` and friends — a good number self-labelled
*"no payment sent"* / *"never pays"*. So do not read "1,900 qualified views" as
1,900 buyers who declined. Read it as: **this traffic was never demand, and more
listings produce more of it.**

The shape difference is the likely cause, and it was predicted independently
from the product alone before these numbers were read:

- `/base/tx-decision` sells `max_fee = 2 x base_fee + tip` over a free RPC call.
  A capable agent developer inlines that in five lines for $0.
- `/base/finality-check` reads block tags a buyer can read themselves for free.
- The Pulse composite is a synthesis of the same public inputs.
- `/mn/property-check` resells something with a real access barrier: three City
  of Minneapolis ArcGIS datasets, joined, normalised, and kept current.

Every seller on these rails that actually earns is reselling a real cost basis
or a real access barrier. We have exactly one product with that shape.

## The decision

**Invest in `/mn/property-check`.** It is the only endpoint that converts and
the only one no catalog has ever indexed — because until 2026-08-02 it answered
a parameterless crawler probe with `422` instead of `402`, which is on
x402scan's published list of registration failures. That is now fixed, its
catalog description has been rewritten for buyers rather than engineers, and it
is registered on x402scan and submitted to the gold-402 directory.

**Stop investing in the Pulse composite and `/base/tx-decision`.** Specifically:

- No new features, tiers, or repositioning.
- No further re-index settles to refresh their catalog entries.
- No outreach or directory submissions that lead with them.
- They stay deployed and listed. They cost nothing to serve, they are already
  cataloged, and they hold the only external sales this project has made. This
  is a decision to stop *spending* on them, not to delete them.

**Not a conclusion about x402.** The rail works: payments settle, the catalog
indexes, strangers have paid. The conclusion is about what we chose to sell on
it.

## What would reverse this

- `/mn/property-check` gets cataloged and still converts near zero at >200
  challenges — then the problem is the market, not the product shape, and the
  honest move is to stop selling data products here entirely.
- Either de-prioritised endpoint reaches ~1% conversion on its own — then the
  read was wrong and it deserves attention again.
- A buyer asks for a feature on one of them and is willing to pay for it. Real
  demand beats this table.

## Method note

`/demand` was built on 2026-07-24 and first read on 2026-08-02. Nine days of
building happened in between, some of it on the endpoints this table says to
stop building. Instruments only help if someone reads them; check this table
before the next product decision, not after.
