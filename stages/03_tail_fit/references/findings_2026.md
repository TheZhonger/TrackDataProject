# Stage 03 findings — 2026 northeast (2026-10-08)

Source: `../output/2026/state_fits.md` (90 per-state fits) and the
single-file run on NY boys 100m. Re-verify after any rescrape.

**Single-file baseline.** NY boys' 100m is unchanged: ForwardStop u = 11.48 s,
N_u = 580, ξ = −0.270 (CI −0.35 to −0.22). It is the same list as the legacy
file. On it, ξ sat at about −0.25 to −0.27 across the candidate range, and the
mixture hit its grid edge (11.95 s, ξ = −0.347). Open wrinkle: the single
fastest time sits above the fitted curve in the log-tail panel.

**Per-state sweep, 90 fits:**
- **Small fields can't carry a tail.** Of the 38 fits on fields under 1,000
  runners, 19 fell back to a fixed N_u and 14 have ξ < −0.5. Those are mostly
  RI, VT and ME: maximum likelihood is non-regular there and the wall sits on
  the record. This is why stage 04 pools.
- **Fields over 2,000 (41 fits):** 25 selected by ForwardStop, 2 by the
  mixture, 14 fallbacks. ξ ranges from about −0.16 to −0.43.
- **Slide or noise?** In 33 of those 41 fits, ξ rises with threshold more
  often than it falls (median rise fraction 0.58). That is the same direction
  as the pooled slide in stage 04, so per-state data is *consistent with* it.
  But no single state shows it clearly. The `xi drift` column is max−min over a
  sweep that runs down to ~15 exceedances, and at the high end it is mostly
  noise (0.12 to 1.3 with no pattern). It cannot separate a slide from noise
  for one state.
- An earlier claim (pooled_method.md, 2026-10-07) that "every state's 1600m
  slides on its own" rested on that same end-to-end range. It is weaker
  evidence than it sounded.

**The old legacy-NY 1600m fit** had no plateau, ξ sliding to −0.66, the wall
~2 s from the record, and both methods at the grid edge (291.45 s). It is
superseded by the 2026 rows: NY boys 1600m 2026 is a fallback at ξ = −0.43.

**Wall CIs (rerun 2026-10-09).** With `gpd_tail.endpoint_interval`, resamples that
have no finite wall count as unbounded instead of being dropped or reported as
negative times. 14 of the 90 state fits now have an "unbounded" fast end, and no
wall interval anywhere sits below 0 s. The selector mix and every ξ are unchanged.
