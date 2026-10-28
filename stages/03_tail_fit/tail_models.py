"""
tail_models.py
==============
Three models for the fast tail, fitted the same way so they can be compared.

All work on x = -seconds (the fast tail is the upper tail), above a threshold u,
on the excesses y = x - u >= 0. Each fit returns a TailFit that knows its own
survival function S(t) (unconditional: P(an athlete-season is t or faster)),
its density of excesses, and its local shape xi(x).

WHY THESE THREE
---------------
Pooled GPD fits slide: xi rises toward 0 as u rises, in every pool, in both
seasons (stages/04_pooled_fit/references/pooled_method.md section 10). That is
the textbook signature of a tail that is light but UNBOUNDED -- the Gumbel
domain, xi = 0 -- seen at finite thresholds. There, the GPD that best fits the
excesses over u has the "penultimate" shape

    xi_u = r'(u),     r(u) = S(u) / f(u)   (the reciprocal hazard),

which is negative for a normal-like tail and creeps to 0 as u grows. For a
normal tail, xi_u = u*M(u) - 1 with M the Mills ratio; that zero-parameter
prediction already tracks the 30 pooled fits (correlation 0.83).

  gpd          the current model: S(u+y)/S(u) = (1 + xi*y/sigma)^(-1/xi).
               With xi < 0 it has a hard wall at u - sigma/xi.
  exponential  the GPD with xi fixed at 0: S(u+y)/S(u) = exp(-y/sigma).
               The Gumbel-domain LIMIT. No wall, but too heavy at reachable
               thresholds if the penultimate xi is still negative there.
  weibull      a Weibull-type ("generalized normal") tail:
                   S(x)/S(u) = exp( -((x-mu)/s)^theta + ((u-mu)/s)^theta ),
               theta = tail weight: 2 behaves like a normal tail, 1 is the
               exponential (so `exponential` is nested in it). No wall, and its
               local shape r'(x) = (1-theta)/theta * ((x-mu)/s)^(-theta) slides
               toward 0 by construction -- the model has the slide built in
               instead of fighting it.
  gompertz     S(u+y)/S(u) = exp(-c*(exp(y/b) - 1)): the Weibull-type family's
               theta -> infinity edge, and the classic human-mortality tail.
               Lighter than any finite theta, still unbounded; local shape
               -exp(-y/b)/c, so it also slides to 0. Added 2026-10-09 because at
               low thresholds the Weibull fits ran off to that edge.

The base rate zeta = N_u / n is counted, not modelled, exactly as in gpd_tail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize
from scipy.stats import genpareto

MODELS = ("gpd", "exponential", "weibull", "gompertz")

# Above this tail weight a Weibull-type fit has effectively become a Gompertz
# tail (its theta -> infinity limit); the optimiser is stopped there rather
# than chasing theta to 20,000 along a flat ridge.
THETA_MAX = 50.0


@dataclass
class TailFit:
    model: str
    u: float                  # threshold, x-space (= -seconds)
    zeta: float               # N_u / n
    n_exceed: int
    n_total: int
    params: dict = field(default_factory=dict)
    loglik: float = np.nan

    @property
    def u_seconds(self) -> float:
        return -self.u

    @property
    def k(self) -> int:
        """Number of fitted parameters (zeta is counted, not fitted)."""
        return {"gpd": 2, "exponential": 1, "weibull": 3, "gompertz": 2}[self.model]

    # ---- conditional pieces, on excesses y = x - u ------------------------
    def logpdf_excess(self, y: np.ndarray) -> np.ndarray:
        y = np.asarray(y, dtype=float)
        p = self.params
        if self.model == "gpd":
            return genpareto.logpdf(y, p["xi"], loc=0, scale=p["sigma"])
        if self.model == "exponential":
            return np.where(y >= 0, -np.log(p["sigma"]) - y / p["sigma"], -np.inf)
        if self.model == "gompertz":
            c, b = p["c"], p["b"]
            out = np.log(c) - np.log(b) + y / b - c * np.expm1(y / b)
            return np.where(y >= 0, out, -np.inf)
        s, z, th = p["s"], p["z"], p["theta"]
        w = z + y / s
        out = (np.log(th) - np.log(s) + (th - 1) * np.log(w) - w ** th + z ** th)
        return np.where(y >= 0, out, -np.inf)

    def sf_excess(self, y: np.ndarray) -> np.ndarray:
        """P(excess > y | exceedance)."""
        y = np.asarray(y, dtype=float)
        p = self.params
        if self.model == "gpd":
            return genpareto.sf(y, p["xi"], loc=0, scale=p["sigma"])
        if self.model == "exponential":
            return np.exp(-np.maximum(y, 0) / p["sigma"])
        if self.model == "gompertz":
            return np.exp(-p["c"] * np.expm1(np.maximum(y, 0) / p["b"]))
        s, z, th = p["s"], p["z"], p["theta"]
        return np.exp(-(z + np.maximum(y, 0) / s) ** th + z ** th)

    def isf_excess(self, q: np.ndarray) -> np.ndarray:
        """Inverse of sf_excess: the excess y with P(excess > y) = q."""
        q = np.asarray(q, dtype=float)
        p = self.params
        if self.model == "gpd":
            return genpareto.isf(q, p["xi"], loc=0, scale=p["sigma"])
        if self.model == "exponential":
            return -p["sigma"] * np.log(q)
        if self.model == "gompertz":
            return p["b"] * np.log1p(-np.log(q) / p["c"])
        s, z, th = p["s"], p["z"], p["theta"]
        return s * ((z ** th - np.log(q)) ** (1 / th) - z)

    def implied_gpd_xi(self, x_new: float, m: int = 4000) -> float:
        """The xi a GPD would return if fitted above x_new (>= u) to data from
        THIS model: fit it to m evenly spaced quantiles of the model's excess
        distribution above x_new. This, not local_xi, is the curve to lay over
        an observed threshold sweep -- a fitted GPD averages the shape over the
        whole excess range, so it sits well above the local shape at u."""
        y0 = x_new - self.u
        q = self.sf_excess(np.array([y0]))[0] * (np.arange(m) + 0.5) / m
        exc = self.isf_excess(q) - y0
        return float(genpareto.fit(exc[exc > 0], floc=0)[0])

    # ---- unconditional, in seconds ---------------------------------------
    def prob(self, t_seconds) -> np.ndarray:
        """P(an athlete-season runs t or faster). Only valid for t at or
        faster than the threshold; slower times return nan."""
        y = -np.asarray(t_seconds, dtype=float) - self.u
        return np.where(y >= 0, self.zeta * self.sf_excess(y), np.nan)

    def return_period(self, t_seconds) -> np.ndarray:
        with np.errstate(divide="ignore"):
            return 1.0 / self.prob(t_seconds)

    def local_xi(self, x: np.ndarray) -> np.ndarray:
        """Penultimate shape r'(x), r = S/f, at points x >= u (x-space).

        This is the xi a GPD fitted at threshold x would be expected to find
        if this model were the truth. Constant for the GPD; 0 for the
        exponential; sliding toward 0 for the Weibull-type tail.
        """
        x = np.asarray(x, dtype=float)
        p = self.params
        if self.model == "gpd":
            return np.full_like(x, p["xi"])
        if self.model == "exponential":
            return np.zeros_like(x)
        if self.model == "gompertz":
            return -np.exp(-(x - self.u) / p["b"]) / p["c"]
        w = p["z"] + (x - self.u) / p["s"]
        return (1 - p["theta"]) / p["theta"] * w ** (-p["theta"])

    @property
    def endpoint_seconds(self) -> float | None:
        if self.model == "gpd" and self.params["xi"] < 0:
            return -(self.u - self.params["sigma"] / self.params["xi"])
        return None


def _gompertz_nll(v, y):
    c, b = np.exp(v)
    ll = np.log(c) - np.log(b) + y / b - c * np.expm1(y / b)
    out = -ll.sum()
    return out if np.isfinite(out) else 1e300


def fit_gompertz_excess(y: np.ndarray) -> tuple[float, float]:
    """
    Gompertz MLE on excesses y >= 0, by profile likelihood -> (c, b).

    For a fixed scale b, the best c has a closed form: setting d(loglik)/dc = 0
    in  N log c - N log b + sum(y)/b - c * sum(expm1(y/b))  gives
    c = N / sum(expm1(y/b)). Substituting it back leaves a function of b
    alone, so the fit is a 1-D bounded search instead of a 2-D Nelder-Mead.
    Same answer as fit_tail(..., "gompertz") to optimiser precision, about
    5x faster -- which matters for ForwardStop's parametric bootstrap
    (18 thresholds x 199 refits per pool).
    """
    from scipy.optimize import minimize_scalar
    y = np.asarray(y, dtype=float)
    N, sy, m = y.size, y.sum(), y.mean()

    def neg_profile(log_b):
        b = np.exp(log_b)
        s = np.expm1(y / b).sum()
        if not np.isfinite(s) or s <= 0:
            return 1e300
        return -(N * np.log(N / s) - N * np.log(b) + sy / b - N)

    r = minimize_scalar(neg_profile, bounds=(np.log(m) - 9, np.log(m) + 9),
                        method="bounded", options={"xatol": 1e-10})
    b = float(np.exp(r.x))
    return float(N / np.expm1(y / b).sum()), b


def _weibull_nll(theta_vec, y):
    log_s, log_z, log_th = theta_vec
    if log_th > np.log(THETA_MAX):
        return 1e300
    s, z, th = np.exp(log_s), np.exp(log_z), np.exp(log_th)
    w = z + y / s
    ll = np.log(th) - np.log(s) + (th - 1) * np.log(w) - w ** th + z ** th
    v = -ll.sum()
    return v if np.isfinite(v) else 1e300


def fit_tail(x: np.ndarray, u: float, model: str,
             n_total: int | None = None) -> TailFit:
    """Maximum-likelihood fit of one tail model to the excesses of x over u."""
    x = np.asarray(x, dtype=float)
    y = x[x > u] - u
    if y.size < 10:
        raise ValueError(f"only {y.size} exceedances above u")
    n = int(n_total) if n_total else x.size
    fit = TailFit(model=model, u=float(u), zeta=y.size / n,
                  n_exceed=int(y.size), n_total=n)

    if model == "gpd":
        xi, _, sigma = genpareto.fit(y, floc=0)       # floc=0: non-negotiable
        fit.params = {"xi": float(xi), "sigma": float(sigma)}
    elif model == "exponential":
        fit.params = {"sigma": float(y.mean())}        # closed-form MLE
    elif model == "weibull":
        # Reparametrised on logs so every parameter is unconstrained, with
        # z = (u - mu)/s > 0 in place of mu (mu < u is then automatic).
        # Several starts: the likelihood is ridge-shaped along (s, z) for a
        # given theta, and one start can stall on it.
        m = y.mean()
        best = None
        for th0, z0 in ((2.0, 2.0), (1.3, 1.0), (3.0, 3.0), (1.05, 0.5)):
            s0 = th0 * z0 ** (th0 - 1) * m   # matches the hazard at u to 1/mean
            r = minimize(_weibull_nll, np.log([s0, z0, th0]), args=(y,),
                         method="Nelder-Mead",
                         options={"maxiter": 4000, "xatol": 1e-7, "fatol": 1e-9})
            if best is None or r.fun < best.fun:
                best = r
        s, z, th = np.exp(best.x)
        fit.params = {"s": float(s), "z": float(z), "theta": float(th),
                      "mu_seconds": float(-(u - s * z)),
                      "at_theta_max": bool(th > 0.99 * THETA_MAX)}
    elif model == "gompertz":
        m = y.mean()
        best = None
        for c0, b0 in ((1.0, m), (0.3, 2 * m), (3.0, 0.5 * m)):
            r = minimize(_gompertz_nll, np.log([c0, b0]), args=(y,),
                         method="Nelder-Mead",
                         options={"maxiter": 2000, "xatol": 1e-8, "fatol": 1e-9})
            if best is None or r.fun < best.fun:
                best = r
        c, b = np.exp(best.x)
        fit.params = {"c": float(c), "b": float(b)}
    else:
        raise ValueError(f"unknown model {model!r}; known: {MODELS}")

    fit.loglik = float(fit.logpdf_excess(y).sum())
    return fit


def rank_pit(fit: TailFit, t_sorted: np.ndarray, ranks=(1,)) -> dict:
    """
    How surprising is the k-th fastest mark of a season, under `fit`?

    The k-th best of n marks t_k satisfies: z_k = n * S(t_k), the number of
    athletes the model expects at or beyond t_k, is approximately Gamma(k, 1)
    when the model is right (exactly so as n grows; for the record, k = 1, it
    is Exp(1): median 0.69, central 95% range 0.025-3.69). So one record can
    sit anywhere from "1/40 of an athlete expected" to "3.7 expected" without
    the model being wrong, and record accuracy can only be judged over many
    records.

    Returns {k: (z_k, p_k)} with p_k = GammaCDF(z_k; k), which is Uniform(0, 1)
    under a correct model. Small p: the model calls the mark too rare (the GPD
    near its wall). Large p: the model expects more athletes that fast than
    there were (too heavy). n is the length of `t_sorted` (the whole season, in
    seconds, fastest first); ranks below the threshold return nan.
    """
    from scipy.stats import gamma
    t_sorted = np.asarray(t_sorted, dtype=float)
    n = t_sorted.size
    out = {}
    for k in ranks:
        if k > n:
            continue
        z = float(n * fit.prob(t_sorted[k - 1]))
        out[k] = (z, float(gamma.cdf(z, k)) if np.isfinite(z) else np.nan)
    return out
