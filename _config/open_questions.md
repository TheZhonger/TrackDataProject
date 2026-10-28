# Open research questions

Layer 3, shared by every stage. These are the live questions for the project; mark one answered here (and
say where) rather than deleting it. Moved out of the root `CONTEXT.md` on 2026-10-08 so the routing file stays short.

1. ~~Is there genuinely no stable GPD regime for the 1600m, or does the grid
   need widening?~~ **Answered: genuine, and not only for the mile.** Pooled,
   ξ slides in 9 of 10 event × sex pools in 2026, and in all 10 in 2025 and
   with both seasons stacked; 2026's 100m boys plateau does not replicate
   (`stages/04_pooled_fit/references/pooled_method.md` §7, §10, §11). Per state, the data
   are consistent with the slide but too noisy to confirm it. **Candidate answer
   (2026-10-09):** the tail is light and unbounded, and a Gompertz tail beats the GPD
   in-sample (22 of 25 pools), across thresholds and out of sample (18 of 20)
   (`pooled_method.md` §12, `_config/evt_theory.md` §3.7). At the top 1% it was
   the best record model on 30 records (§13), but it **failed** the decisive
   out-of-sample test on 180 division records (2026-10-22, §13.1). Real prodigy
   seasons (2025) beat what a 2026-fitted tail allows. Still open: which tail
   (or between-season term) holds at the record, and so whether to score with it.
2. Are exceedance counts comparable across events? This is reported by
   `run_all.py`. Pooled N_u spans 173–5,664 (×33) across the ten pools, so the
   noise floors differ a lot. The girls' 1500m (173) is the thinnest.
3. Unify threshold selection and tail fitting into one pipeline across all five events.
4. Cross-event score aggregation, the actual point, once per-event fits are
   reliable. Today no pool has a stable regime across both seasons, no
   fastest-mark return period is identified, and a fixed benchmark's return
   period differs between seasons by up to 1.7× (`pooled_method.md` §10).
5. ~~The bootstrap wall CI breaks when resampled ξ lands near 0~~. **Fixed
   2026-10-09**: resamples with no finite wall now count as unbounded, and 800m and
   1500m girls 2026 read "unbounded" at the fast end (`pooled_method.md` §7).
6. Extend the pooled analysis beyond the northeast. **Partly done 2026-10-09**: boys and girls
   2026 for all 51 states (`stages/04_pooled_fit/output/national/2026/`, `pooled_method.md` §11); national 2025 is fully scraped (2026-10-22, `scraping.md` §7); national stacked 2025+2026 has a Gompertz fit (`pooled_method.md` §14) but no GPD run yet.
