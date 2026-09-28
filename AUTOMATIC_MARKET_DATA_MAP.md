# FlipFynd automatic market data map

This document describes the market data sources currently represented in `main`
and how each source is allowed to affect valuation decisions.

Product rule: FlipFynd may show active prices as research context, but BUY/FYND
requires exact identity, verified SOLD evidence and conservative positive net
profit. When automatic evidence is missing, the value must remain uncertain.

| Source | SOLD or active | Price verified | Shipping | Date | Currency | Identity verification | Automatic use | Stability / cost | Decision impact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tradera active listings | Active | Current listing price only | Buyer shipping may be parsed or conservatively assumed | Listing/update date when available | SEK | Listing title/category only until exact analysis parses identity | Yes, for inventory and purchase cost | Existing fetch path, unstable pagination/timeout risk | Can create candidates and total acquisition cost. Never creates resale value or SOLD quorum. |
| Tradera sold | SOLD only when explicitly imported/verified | Yes if row passes SOLD import gates | Stored when provided | Required by sold-comp normalizer | SEK | Structured identity plus explicit confirmation required for exact comps | No general automatic sold feed in current code | Research/import only; no added infra cost | Strong local evidence when exact-ready. Can support KÖP after normal gates. |
| eBay Browse / active context | Active | Current asking price only | May be included by source/context; otherwise not SOLD-safe | Fetch timestamp/context date | Source currency converted when ECB FX is available | Exact identity query plus comparison eligibility | Yes, where credentials exist | Official active API; credential-dependent | Research-only price indication. Positive active margin can show UNDERSÖK, never KÖP/FYND. |
| eBay Marketplace Insights | SOLD | Would be verified realised sales | API-dependent | API-dependent | API-dependent | API-dependent | No, blocked/restricted in current registry | Official but limited-release access | Correct future target if access is approved; currently cannot power automatic Top 5. |
| eBay Sold / Product Research | SOLD | Verified manually | May be visible per sale | Visible manually | Source currency | Manual exact-card verification | No | Manual/in-login research | Optional research source; not required for automatic Top 5. |
| 130 Point | SOLD aggregator plus active results | Only if underlying sale and origin marketplace are recorded | Depends on underlying marketplace | Depends on result | Depends on result | Exact identity plus origin marketplace required | No | Cloudflare/human verification; no stable public API verified | Optional manual cross-check. Cannot create independent source diversity without origin. |
| Card Ladder | SOLD database / guide | Depends on access/export | Depends on export | Depends on export | Depends on export | Exact row verification required | No | Licensed/manual research | Optional secondary evidence only. |
| SportsCardsPro | Aggregated guide | Aggregated guide value, not a single sale | Not decision-grade per comp | Current guide date | Source currency/guide | Product-level matching risk | No | Research/guide access | Sanity check only; cannot create exact SOLD comps by itself. |
| COMC / Fanatics Collect | Marketplace sales/history | Only if individual realised sale is captured | Depends on row | Depends on row | Depends on row | Structured exact identity required | No | Research/import only | Can support valuation only after strict external adapter and sold intake. |
| Manual sold comps | SOLD when explicit fields pass normalizer | Yes after import validation | Stored when provided | Required | Required or converted before import | Structured identity plus confirmation required | Yes, as explicit import rows | Free but manual; not central product path | Strong evidence only for exact-ready rows; rejected/uncertain rows go to review/quarantine. |
| Model values / collector signals | Neither SOLD nor active market price | Not a realised price | Not applicable | Not applicable | Not applicable | Signal only | Yes, internally | Stable but non-market evidence | May route research. Must never create value, profit, max bid or KÖP alone. |
| Cached comparisons | Same as original source | Same as original source | Same as original source | Must respect freshness/staleness | Same as original source | Same as original source | Yes, if fresh and source-safe | Low cost; stale risk | Cannot upgrade source quality. Stale or unsafe cache must fail closed. |

## Current automatic SOLD status

`src/sold_source_registry.py` currently reports zero automatic direct SOLD
sources. The safe automatic path today is therefore:

1. Fetch active Tradera inventory and active eBay price context where allowed.
2. Use these only for purchase cost, candidate routing and research indication.
3. Require explicit sold-comp import or verified future API access before a
   row can become decision-grade SOLD evidence.
4. Leave valuation uncertain when exact SOLD evidence is missing.

## Decision rules

- KÖP/FYND: exact identity, verified SOLD comps, display-safe positive net
  profit and acceptable risk.
- UNDERSÖK: a card-specific opportunity exists but a decisive part is missing,
  such as verified SOLD value, source diversity or confidence.
- EJ FYND / hidden from list: missing/zero purchase price, known negative net
  profit, invalid identity, active prices with no margin, stale/unsafe evidence
  or generic signal-only filler.
