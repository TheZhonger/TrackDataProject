"""
threshold_select.py
===================
Automatic threshold selection for the GPD tail fit in gpd_tail.py.

Two methods, resting on different principles, plus a comparison harness.

WHY NOT JUST MINIMISE A LOSS
----------------------------
Raising the threshold changes WHICH data points are in the fit. So the
likelihood at u = 11.5 and the likelihood at u = 11.0 are computed on
different datasets, and comparing them is meaningless. Goodness-of-fit
statistics don't rescue this: on data where the GPD is exactly right at every
threshold, "pick the best-fitting threshold" chooses essentially at random,
because the differences between thresholds are noise.

The two ways out:

  Method 1 (ForwardStop) reframes it as a sequence of hypothesis tests. You
  don't pick the best fit -- you reject the thresholds that are demonstrably
  too low and take the first survivor. Error rate is controlled explicitly.
  Reference: Bader, Yan & Zhang (2018), Ann. Appl. Stat.

  Method 2 (mixture MLE) models the WHOLE distribution -- a lognormal body
  joined to a GPD tail -- so every data point contributes to the likelihood
  no matter where u sits. Now likelihoods across different u ARE comparable
  and you can honestly maximise over u.
  Reference: Behrens, Lopes & Gamerman (2004), Stat. Modelling.

Neither replaces looking at the stability plot. They give you a defensible
starting point, and when they agree with your eye that's real evidence.

Usage:  python threshold_select.py [csv_path]
"""

from __future__ import annotations

import sys

import numpy as np
from scipy.stats import genpareto, lognorm
from scipy.optimize import minimize

from gpd_tail import load_event, fit_gpd, DEDUPE_ATHLETES, EVENT_FILE
from tail_models import fit_gompertz_excess

# Tail models ForwardStop can test. The procedure itself is model-free: it
# needs a fit, the fitted CDF of the excesses (for A-D), and a way to simulate
# from the fit (for the parametric bootstrap). Each entry supplies those three.
# "gompertz" added 2026-10-22: the Gompertz has no limit theorem behind it, so
# its threshold has to be chosen by evidence like this rather than by theory.
GOF_MODELS = {
    "gpd": {
        "fit": lambda y: tuple(genpareto.fit(y, floc=0)[::2]),       # (xi, sigma)
        "cdf": lambda y, a, b: genpareto.cdf(y, a, loc=0, scale=b),
        "rvs": lambda a, b, n, rng: genpareto.rvs(a, loc=0, scale=b, size=n,
                                                  random_state=rng),
    },
    "gompertz": {
        "fit": fit_gompertz_excess,                                     # (c, b)
        "cdf": lambda y, c, b: -np.expm1(-c * np.expm1(y / b)),
        # inverse of the survival function, applied to uniforms
        "rvs": lambda c, b, n, rng: b * np.log1p(-np.log(rng.random(n)) / c),
    },
}


# ======================================================================
# METHOD 1: SEQUENTIAL GOODNESS-OF-FIT WITH ERROR CONTROL
# ======================================================================

def anderson_darling(excesses: np.ndarray, xi: float, sigma: float,
                     model: str = "gpd") -> float:
    """
    Anderson-Darling statistic: how far the observed excesses sit from the
    fitted GPD.

    The idea: push every observation through the fitted CDF. If the model is
    right, the results should look like a uniform spread between 0 and 1.
    A-D measures the departure from uniform, weighting the two ends heavily --
    which is what we want, since the extreme end is the whole point. (The
    alternative, Kolmogorov-Smirnov, is most sensitive near the middle and
    nearly blind in the tail.)

    (xi, sigma) are the model's two parameters: (c, b) for model="gompertz".
    """
    y = np.sort(excesses)
    N = len(y)
    z = np.clip(GOF_MODELS[model]["cdf"](y, xi, sigma), 1e-12, 1 - 1e-12)
    i = np.arange(1, N + 1)
    return float(-N - np.mean((2 * i - 1) * (np.log(z) + np.log(1 - z[::-1]))))


def gof_pvalue(excesses: np.ndarray, n_sim: int, rng, model: str = "gpd") -> float:
    """
    p-value for "the GPD describes these excesses", by parametric bootstrap.

    We can't read A-D off a standard table here, because we ESTIMATED xi and
    sigma from the same data we're testing. That estimation makes the fit look
    better than it should and shifts the statistic's distribution.

    So we build the correct comparison ourselves: fit the GPD, generate many
    fake datasets from that fitted GPD, and put each through the identical
    fit-then-measure procedure. That gives the distribution of A-D under
    "the model is true, and was fitted the same way." The p-value is the
    fraction of fakes that fit worse than the real data.

    Small p = the real data fits worse than genuine GPD data would = reject.

    model="gompertz" runs the identical procedure with the Gompertz: the real
    data and every fake are fitted by the same function, which is what makes
    the comparison fair.
    """
    m = GOF_MODELS[model]
    xi, sigma = m["fit"](excesses)
    a2_obs = anderson_darling(excesses, xi, sigma, model)
    N = len(excesses)

    worse = 0
    for _ in range(n_sim):
        fake = m["rvs"](xi, sigma, N, rng)
        try:
            xi_b, sig_b = m["fit"](fake)
            if anderson_darling(fake, xi_b, sig_b, model) >= a2_obs:
                worse += 1
        except Exception:
            continue

    # The +1s keep the p-value away from exactly zero, which matters because
    # ForwardStop takes a logarithm of (1 - p) below.
    return (1.0 + worse) / (1.0 + n_sim)


def dequantize(x: np.ndarray, resolution: float, rng) -> np.ndarray:
    """
    Spread each mark uniformly over its rounding interval (+-resolution/2).

    Times are recorded to 0.01 s, so in a big pool almost every excess shares
    its value with others (94-99% of the national sprint excesses). A
    goodness-of-fit test for a CONTINUOUS model reads those ties as misfit:
    the national boys' 100 m rejected the Gompertz at every threshold with
    p = 0.01, and with the times jittered by +-0.005 s the same test gives
    p = 0.13-0.79 (2026-10-22). Jittering removes the artefact and nothing
    else -- a true time of 10.30 is anywhere in [10.295, 10.305) anyway. Use
    it on ForwardStop's input only; the fits themselves are unaffected by ties.
    """
    return np.asarray(x, dtype=float) + rng.uniform(-resolution / 2, resolution / 2,
                                                    size=np.shape(x))


def forwardstop(pvalues: np.ndarray, alpha: float = 0.05) -> int:
    """
    Given p-values ordered from LOWEST threshold to HIGHEST, return how many
    of the leading thresholds to reject.

    Running many tests and stopping at the first pass is a classic multiple-
    comparisons trap: test enough thresholds and one passes by luck. ForwardStop
    guards against this by accumulating evidence:

        q_j = -(1/j) * sum_{i<=j} ln(1 - p_i)

    Each -ln(1 - p_i) is small when p_i is small (strong rejection) and blows
    up as p_i approaches 1. So q_j stays low only while the whole run of
    thresholds so far is being confidently rejected. We reject up through the
    LAST j where q_j is still under alpha, and take the next threshold up.

    This controls the false discovery rate at alpha.
    """
    p = np.clip(np.asarray(pvalues, dtype=float), 1e-12, 1 - 1e-12)
    q = -np.cumsum(np.log1p(-p)) / np.arange(1, len(p) + 1)
    ok = np.flatnonzero(q <= alpha)
    return int(ok[-1] + 1) if ok.size else 0


def select_forwardstop(x, candidate_us, alpha=0.05, n_sim=199,
                       min_exceed=25, rng=None, verbose=True, model="gpd",
                       fallback_u=None):
    """Run the sequential test over candidate thresholds; return the choice.

    fallback_u: what to return when NOTHING is rejected. By default that is the
    lowest candidate, which is a default, not a selection. For the Gompertz the
    A-D test has little power against the mild body misfit at low thresholds,
    so "nothing rejected" happened in 89 of 180 division pools and the
    lowest-candidate fallback (top 20%) gave a tail that was too heavy at the
    record (pooled_method.md section 13.2). Pass a fixed u -- the pools' 95%
    quantile, from 2026-10-22 -- to use instead. None keeps the old behaviour.
    """
    rng = rng or np.random.default_rng(0)

    us, pvals, counts = [], [], []
    for u in candidate_us:
        exc = x[x > u] - u
        if len(exc) < min_exceed:
            continue
        us.append(u)
        counts.append(len(exc))
        pvals.append(gof_pvalue(exc, n_sim, rng, model))

    if not us:
        raise ValueError("No candidate threshold had enough exceedances.")

    us, pvals, counts = np.array(us), np.array(pvals), np.array(counts)
    k_reject = forwardstop(pvals, alpha)

    # Both ends of the grid are fallbacks, not selections. Rejecting nothing
    # returns candidate zero -- the bottom of the grid -- which is exactly how
    # the false 1600 m "agreement" at 291.450 s happened (threshold_select.md):
    # the sequence never turned, so the answer is a default, not evidence.
    if k_reject >= len(us):
        idx = len(us) - 1           # everything rejected: fall back to highest
        note = f"all thresholds rejected -- {model} may be a poor model here"
    elif k_reject == 0 and fallback_u is not None:
        idx = None
        note = "nothing rejected -- fixed fallback u used"
    elif k_reject == 0:
        idx = 0
        note = "nothing rejected -- lowest candidate is a fallback, not a selection"
    else:
        idx = k_reject
        note = "ok"

    if idx is None:
        u_sel, n_sel, p_sel = float(fallback_u), int((x > fallback_u).sum()), np.nan
    else:
        u_sel, n_sel, p_sel = float(us[idx]), int(counts[idx]), float(pvals[idx])

    if verbose:
        print(f"\n  ForwardStop (alpha={alpha}, {n_sim} sims per threshold)")
        print(f"  {'u (s)':>8} {'N_u':>6} {'p-value':>9}")
        for j, (u, n, p) in enumerate(zip(us, counts, pvals)):
            mark = "  <-- selected" if j == idx else ""
            print(f"  {-u:8.3f} {n:6d} {p:9.3f}{mark}")
        print(f"  rejected the first {k_reject} threshold(s); {note}")

    return {"u": u_sel, "u_sec": -u_sel,
            "n_exceed": n_sel, "pvalue": p_sel,
            "note": note, "k_reject": int(k_reject),
            "converged": note == "ok",
            "pvalues": pvals.tolist(), "us": us.tolist(), "counts": counts.tolist()}


# ======================================================================
# METHOD 2: WHOLE-DISTRIBUTION MIXTURE, MAXIMISED OVER u
# ======================================================================

def mixture_nll(params, t: np.ndarray, u_t: float) -> float:
    """
    Negative log-likelihood of a lognormal-body / GPD-tail model, in TIME space.

    The density is

        f(t) = f_lognormal(t)                                for t >= u_t
        f(t) = F_lognormal(u_t) * g_GPD(u_t - t; xi, sigma)  for t <  u_t

    Check it's a valid density: the slow side integrates to 1 - F(u_t), the
    fast side to F(u_t) * 1. They sum to 1. So the lognormal decides HOW MUCH
    probability lives in the fast tail, and the GPD decides how that mass is
    SHAPED. That split is exactly the structure the theorem describes.

    The payoff: every observation appears in this likelihood for any u_t, so
    likelihoods at different thresholds are finally comparable.

    Parameters come in logged (log_s, log_scale, log_sigma) so the optimiser
    can roam over the whole real line and still never produce a negative
    scale. xi is unconstrained because it genuinely can be either sign.
    """
    log_s, log_scale, xi, log_sigma = params
    s, scale, sigma = np.exp(log_s), np.exp(log_scale), np.exp(log_sigma)

    if not np.isfinite([s, scale, sigma, xi]).all():
        return np.inf

    body = t >= u_t
    tail = ~body

    ll = float(lognorm.logpdf(t[body], s, loc=0, scale=scale).sum())

    p_tail = float(lognorm.cdf(u_t, s, loc=0, scale=scale))
    if not (0 < p_tail < 1):
        return np.inf

    excess = u_t - t[tail]                       # positive: how far under u_t
    ll += tail.sum() * np.log(p_tail)
    ll += float(genpareto.logpdf(excess, xi, loc=0, scale=sigma).sum())

    return -ll if np.isfinite(ll) else np.inf


def select_mixture_mle(t: np.ndarray, candidate_u_secs, min_exceed=25,
                       verbose=True):
    """
    Profile the mixture likelihood over u: for each candidate threshold,
    optimise the other four parameters, record the best log-likelihood, then
    take the u that scored highest.
    """
    log_t = np.log(t)
    s0, scale0 = float(log_t.std(ddof=1)), float(np.exp(log_t.mean()))

    rows = []
    for u_t in candidate_u_secs:
        n_tail = int((t < u_t).sum())
        if n_tail < min_exceed:
            continue

        # Warm-start xi and sigma from the plain fixed-threshold fit, so the
        # optimiser begins somewhere sensible rather than at an arbitrary point.
        try:
            warm = fit_gpd(-t, -u_t)
            xi0, sig0 = warm.xi, warm.sigma
        except Exception:
            xi0, sig0 = -0.1, float((u_t - t[t < u_t]).mean())

        x0 = [np.log(s0), np.log(scale0), xi0, np.log(max(sig0, 1e-3))]
        res = minimize(mixture_nll, x0, args=(t, u_t), method="Nelder-Mead",
                       options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-6})
        if not np.isfinite(res.fun):
            continue

        rows.append({"u_sec": float(u_t), "n_tail": n_tail,
                     "loglik": float(-res.fun),
                     "xi": float(res.x[2]),
                     "sigma": float(np.exp(res.x[3]))})

    if not rows:
        raise ValueError("Mixture fit failed at every candidate threshold.")

    best = max(rows, key=lambda r: r["loglik"])
    at_edge = (rows.index(best) in (0, len(rows) - 1)) and len(rows) > 2

    if verbose:
        print("\n  Mixture profile likelihood (lognormal body + GPD tail)")
        print(f"  {'u (s)':>8} {'N_tail':>7} {'log-lik':>12} {'xi':>8}")
        top = max(r["loglik"] for r in rows)
        for r in rows:
            mark = "  <-- selected" if r is best else ""
            print(f"  {r['u_sec']:8.3f} {r['n_tail']:7d} "
                  f"{r['loglik']:12.2f} {r['xi']:+8.3f}{mark}")
        print(f"  (log-lik is comparable across rows: all {len(t):,} points "
              f"used every time)")
        # Within ~2 log-likelihood units is conventionally "not meaningfully
        # worse" -- report the plateau, not just the peak.
        near = [r["u_sec"] for r in rows if r["loglik"] >= top - 2.0]
        if len(near) > 1:
            print(f"  within 2 log-lik of the best: "
                  f"{min(near):.2f}s to {max(near):.2f}s")
        if at_edge:
            print("  !! The best value sits at the EDGE of the candidate grid,")
            print("     so the likelihood never turned around -- this is not a")
            print("     real optimum. Usually it means the lognormal body is")
            print("     wrong for your data, and the more flexible GPD is")
            print("     expanding to cover the misfit. Widen the grid to check,")
            print("     and lean on the ForwardStop answer instead.")

    best = dict(best)
    best["at_edge"] = at_edge
    return best


# ======================================================================
# COMPARISON HARNESS
# ======================================================================

def compare(t: np.ndarray, q_lo=0.80, q_hi=0.995, n_cand=18,
            alpha=0.05, n_sim=199, seed=0):
    """Run both methods on the same candidate grid and show them side by side."""
    rng = np.random.default_rng(seed)
    x = -t

    us = np.quantile(x, np.linspace(q_lo, q_hi, n_cand))
    u_secs = -us

    fs = select_forwardstop(x, us, alpha=alpha, n_sim=n_sim, rng=rng)
    mx = select_mixture_mle(t, u_secs)

    print("\n" + "=" * 62)
    print("  SELECTED THRESHOLDS")
    print("=" * 62)
    for name, u_sec in (("ForwardStop GoF test", fs["u_sec"]),
                        ("Mixture profile MLE ", mx["u_sec"])):
        f = fit_gpd(x, -u_sec)
        print(f"  {name}   u = {u_sec:7.3f} s   N_u = {f.n_exceed:5d}   "
              f"xi = {f.xi:+.3f}")

    # Agreement tolerance is 10% of the candidate grid's span, so it scales
    # with the event: 0.15 s (the old hardcoded value) is meaningful on a
    # 100 m grid and meaningless on a 1600 m grid spanning ninety seconds.
    # Same rule as stage 04's select_threshold.
    spread = abs(fs["u_sec"] - mx["u_sec"])
    tol = 0.10 * float(abs(u_secs.max() - u_secs.min()))
    mx_ok = not mx.get("at_edge", False)
    both_ok = fs["converged"] and mx_ok
    print(f"\n  The two methods differ by {spread:.3f} s "
          f"(tolerance {tol:.3f} s = 10% of the grid span).")
    if not both_ok:
        # Two fallbacks landing together are not corroboration.
        bad = [n for n, ok in (("ForwardStop", fs["converged"]),
                               ("mixture MLE", mx_ok)) if not ok]
        print(f"  No agreement to report: {' and '.join(bad)} did not converge "
              f"({fs['note'] if not fs['converged'] else 'hit the grid edge'}).")
    elif spread < tol:
        print("  Close agreement -- treat this region as a solid choice.")
    else:
        print("  Wide disagreement. That gap IS your threshold uncertainty;")
        print("  fit at both and see how much your answer actually moves.")

    return {"forwardstop": fs, "mixture": mx, "spread_s": spread,
            "tolerance_s": tol, "both_converged": both_ok,
            "agree": bool(both_ok and spread < tol)}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else EVENT_FILE
    df, stats = load_event(path, dedupe=DEDUPE_ATHLETES)
    times = df["seconds"].to_numpy(dtype=float)
    print(f"Loaded {path}: {stats['n_final']:,} athletes "
          f"(from {stats['n_raw']:,} rows)")
    compare(times)
