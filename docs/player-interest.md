# Player interest in FlipFynd

**Ta bort spelaren** hides all identified cards for that player, including new listings in later seller rounds. Exclusions survive checkpoint restoration. The next saved eligible alternative fills the slot without fetching. Resetting the seller search restores excluded players and cards. **Ta bort kortet** excludes only one listing.

## Performance monitoring

The `Player performance monitor` GitHub workflow runs at 07:17 and 19:17 UTC and supports manual dispatch. It collects four days and retains distinct performances for 14 days in `data/player_form.json`.

* NHL: official completed regular-season/playoff boxscores. At least two goals or three points; goalies need a win, at least 30 saves and a save percentage of at least 95%. Full names come from the official player endpoint.
* Football: ESPN completed match scoreboards for Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UEFA Champions League, MLS and Saudi Pro League. At least two individually attributed goals. Own goals and shootout goals are excluded.

A strong match contributes up to 12 ranking points, decaying linearly to zero over 14 days. Several distinct games contribute at most 18. Future, undated, unrelated-sport and duplicate observations contribute nothing. Source outages retain still-recent observations. The UI shows the last check and unsuccessful sources. Coverage is limited to these competitions and measurable match statistics, not all news or national-team matches.

## Legends and ranking

Verified legacy metadata and existing verified career context contribute 20 persistent points. Veteran or retired status alone never implies legend status. Additional legacy records cite NHL's 100 Greatest Players or FIFA. The combined signal is capped at 30.

The signal affects the initial analysis pool, confidence-weighted general ranking, seller deep-analysis priority and seller opportunity ranking. Seller scoring removes the bonus already applied by the general analyser before applying current context, preventing double weighting and allowing old form to expire. Cached reads detect file changes. Saved alternatives are re-ranked when rendered.

These are prioritisation heuristics, not calibrated estimates of resale-price changes. They never directly change valuation, expected profit, max bid or the BUY evidence gate. Verified profitable opportunities retain priority over unsupported hype and known losses.
