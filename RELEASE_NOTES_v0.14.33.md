# v0.14.33 — possible finds from asking prices

User-approved policy: small positive margins count, and active seller asking
prices may support suggestions without SOLD data. Asking prices remain clearly
separate from realized sale values and verified BUY recommendations.

- Full analyses in ordinary and seller searches now compare matching eBay Browse
  fixed-price listings when API credentials and a searchable card identity exist.
- The lowest eligible retrieved asking price, rather than the median or maximum,
  supplies an explicit hypothetical resale scenario. Every positive net margin
  qualifies as a possible find. Identity/grade/variant conflicts, bids, lots and
  reprints cannot supply that scenario.
- Costs include purchase, inbound shipping (known or labeled assumption), the
  existing private Tradera fee assumption, and 3 SEK packaging. Resale postage is
  assumed paid separately by the buyer. 10 + 22 SEK acquisition versus a 50 SEK
  asking price yields 10 SEK possible net margin after 5 SEK fee and packaging.
- Convert foreign asks using dated ECB daily reference rates, cached hourly.
  Missing/stale FX never silently becomes a SEK value. International price
  differences and condition still need review; an ask does not prove demand.
- Show the arithmetic and links in both search views. Asking-price opportunities
  rank ahead of collector-only research while verified finds remain first.
- Reserve up to four of the existing maximum 20 seller deep-analysis slots for
  inexpensive identifiable cards, even without collector merit or SOLD evidence.
- Reuse the eBay OAuth token; cache searches for 15-minute periods; expire
  analysis/search cache entries containing stale active-price snapshots. Failed
  API requests or missing credentials cannot create suggestions or fake prices.

Validation: 1,460 tests passed, including 39 new cases for small margins, cost
arithmetic, cheapest-price selection, malformed prices, FX, identity mismatches,
API token reuse, stale caches, full-vs-fast analysis, seller routing and actual
Streamlit rendering. Full source compilation passed. Production API credentials,
live deployment and real-world search latency were not verified locally.

Primary references checked 2026-09-16:
- eBay Browse API: https://developer.ebay.com/api-docs/buy/static/api-browse.html
- eBay fixed-price search filter: https://developer.ebay.com/
- Tradera fees: https://www.tradera.com/support/gb/posts/vad-kostar-det-att-saelja-pa-tradera/
- ECB reference rates: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html

Not changed: SOLD ingestion, verified market values, verified BUY gates and
evidence-based maximum bids. Asking-price margins are a distinct scenario.
