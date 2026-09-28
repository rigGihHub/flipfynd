# FlipFynd v0.14.67

## Seller Top 5 safety

- Separates verified SOLD-backed net profit from active asking-price indication.
- Positive active asking margins can remain research context, but no longer count
  as verified positive net profit.
- Seller UI blocks known negative economics and invalid prices while allowing
  honest research rows to say that net profit cannot be calculated.
- Seller analysis diagnostics now counts positive net only when it is backed by
  verified SOLD evidence.

## Market data map

- Adds `AUTOMATIC_MARKET_DATA_MAP.md` with the current source rules for Tradera,
  eBay, 130 Point, price guides, cached comparisons, manual comps and model
  signals.
- Documents that current `main` has no enabled automatic direct SOLD source;
  active prices are research context only.

## Verification

- Focused regression suite: 41 passed.
