"""
Fit a distribution to scraped track & field times.

Handles two cases:
  IS_TRUNCATED = False -> your data is every recorded performance. Fit directly.
  IS_TRUNCATED = True  -> your data is a top-N cut. Correct for truncation
                          and extrapolate to the full population.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CSV_PATH = "data/NY/m/output1600.csv"     # your scraped data
TIME_COL = "time"          # column holding strings like "4:08.19"
IS_TRUNCATED = False        # <-- set this deliberately; see module docstring
COMPARE_LOGNORMAL = True   # also fit a lognormal for comparison


# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------

def time_to_seconds(value):
    """Parse 'M:SS.hh' or 'SS.hh' into float seconds. Returns NaN on failure."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if not s:
        return np.nan
    try:
        if ":" in s:
            minutes, seconds = s.split(":")
            return int(minutes) * 60 + float(seconds)
        return float(s)
    except (ValueError, TypeError):
        return np.nan


def load_times(csv_path=CSV_PATH, time_col=TIME_COL):
    df = pd.read_csv(csv_path)
    df["seconds"] = df[time_col].map(time_to_seconds)

    n_bad = df["seconds"].isna().sum()
    if n_bad:
        print(f"Dropped {n_bad} rows with unparseable times")
    df = df.dropna(subset=["seconds"])

    # Guard against duplicate scrapes of the same result row
    if "result_id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset="result_id")
        if len(df) < before:
            print(f"Dropped {before - len(df)} duplicate results")

    return df


# ---------------------------------------------------------------------------
# Likelihood
# ---------------------------------------------------------------------------

BIG = 1e10  # finite penalty; np.inf breaks finite-difference gradients


def neg_loglik_truncated(params, x, T):
    """Negative log-likelihood, normal truncated to x <= T."""
    mu, sigma = params
    if sigma <= 0:
        return BIG
    # logcdf, not log(cdf): cdf underflows to 0 deep in the tail
    terms = norm.logpdf(x, loc=mu, scale=sigma) - norm.logcdf(T, loc=mu, scale=sigma)
    if not np.isfinite(terms).all():
        return BIG
    return -terms.sum()


def fit_truncated(x, T, n_starts=6):
    """Multi-start L-BFGS-B fit. Returns (mu, sigma, best_result)."""
    obs_mean, obs_std = np.mean(x), np.std(x, ddof=1)

    # The population mean is slower (higher) and more spread out than the
    # observed tail, so start guesses fan out in that direction.
    starts = [
        (obs_mean, obs_std),
        (T, 2 * obs_std),
        (obs_mean + 2 * obs_std, 2 * obs_std),
        (obs_mean + 4 * obs_std, 4 * obs_std),
        (T + 2 * obs_std, 3 * obs_std),
        (T + 5 * obs_std, 6 * obs_std),
    ][:n_starts]

    results = []
    for guess in starts:
        r = minimize(
            neg_loglik_truncated,
            x0=guess,
            args=(x, T),
            method="L-BFGS-B",
            bounds=[(1e-6, None), (1e-6, None)],  # sigma strictly positive
            options={"maxls": 50, "maxiter": 2000},
        )
        if r.success and np.isfinite(r.fun):
            results.append(r)

    if not results:
        raise RuntimeError("No starting point converged. Inspect the data.")

    best = min(results, key=lambda r: r.fun)

    # Identifiability check: with only the tail visible, mu and sigma are
    # weakly identified. Scattered optima across starts means the answer
    # is start-dependent, not a bug.
    spread = np.ptp([r.x[0] for r in results])
    if spread > 0.05 * abs(best.x[0]):
        print(f"WARNING: mu varies by {spread:.2f}s across starting points.")
        print("         The likelihood surface is flat; treat mu as uncertain.")

    return best.x[0], best.x[1], best


def approx_std_errors(result):
    """Rough standard errors from the L-BFGS-B inverse Hessian."""
    try:
        cov = result.hess_inv.todense()
        return np.sqrt(np.diag(cov))
    except (AttributeError, np.linalg.LinAlgError):
        return np.array([np.nan, np.nan])


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def qq_plot_truncated(x, mu, sigma, T, ax):
    """Q-Q plot against the *truncated* normal, which is what x is drawn from."""
    x_sorted = np.sort(x)
    n = len(x_sorted)
    p = (np.arange(1, n + 1) - 0.5) / n
    # Quantiles of the truncated distribution: invert Phi(q)/Phi(T) = p
    theoretical = norm.ppf(p * norm.cdf(T, mu, sigma), mu, sigma)

    ax.scatter(theoretical, x_sorted, s=6, alpha=0.5)
    lims = [min(theoretical[0], x_sorted[0]), max(theoretical[-1], x_sorted[-1])]
    ax.plot(lims, lims, "r--", lw=1)
    ax.set_xlabel("Theoretical quantile (s)")
    ax.set_ylabel("Observed quantile (s)")
    ax.set_title("Q-Q vs truncated normal")
    ax.grid(True, alpha=0.3)


def plot_fit(x, mu, sigma, T, truncated, ax):
    counts, edges, _ = ax.hist(
        x, bins=50, alpha=0.6, color="g",
        label=f"Observed times (n={len(x)})",
    )
    bin_width = edges[1] - edges[0]

    if truncated:
        # Scale by the ESTIMATED FULL population, not the observed count.
        # Scaling by n makes the curve sit too low by a factor of Phi(T).
        n_total = len(x) / norm.cdf(T, mu, sigma)
    else:
        n_total = len(x)

    grid = np.linspace(mu - 4 * sigma, mu + 4 * sigma, 500)
    ax.plot(
        grid, norm.pdf(grid, mu, sigma) * n_total * bin_width,
        "r--", lw=2,
        label="Fitted full distribution",
    )

    if truncated:
        ax.axvline(T, color="purple", ls=":", lw=2,
                   label=f"Truncation point ({T:.2f}s)")
        ax.axvspan(grid[0], T, alpha=0.07, color="green")

    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Number of performances")
    ax.set_title("Fit vs observed data")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    df = load_times()
    x = df["seconds"].to_numpy()
    x = np.sort(df["seconds"].to_numpy())
    n = len(x)
    T = x[-1]  # slowest observed time

    print(f"n = {n}")
    print(f"Observed mean:  {x.mean():.2f}s")
    print(f"Observed std:   {x.std(ddof=1):.2f}s")
    print(f"Fastest:        {x[0]:.2f}s")
    print(f"Slowest (T):    {T:.2f}s")

    if IS_TRUNCATED:
        mu, sigma, result = fit_truncated(x, T)
        se_mu, se_sigma = approx_std_errors(result)
        print("\n--- Truncated normal fit (extrapolated to full population) ---")
        print(f"mu    = {mu:.2f}s  (SE ~{se_mu:.2f})")
        print(f"sigma = {sigma:.2f}s  (SE ~{se_sigma:.2f})")
        print(f"converged: {result.success} | {result.message}")

        p_below = norm.cdf(T, mu, sigma)
        print(f"\nP(time <= {T:.2f}s) = {p_below:.4f}")
        print(f"Implied total population: {n / p_below:.0f}")
        print(f"Implied population median: {norm.ppf(0.5, mu, sigma):.2f}s")

        if p_below > 0.95:
            print("\nNOTE: nearly the whole distribution is below T. The")
            print("      truncation correction is doing almost nothing --")
            print("      you may not have a truncated sample at all.")
    else:
        mu, sigma = x.mean(), x.std(ddof=1)
        print("\n--- Direct normal fit (no truncation correction) ---")
        print(f"mu    = {mu:.2f}s")
        print(f"sigma = {sigma:.2f}s")

    if COMPARE_LOGNORMAL:
        # A lognormal in x is a normal in log(x); truncation x<=T maps to
        # log(x) <= log(T), so the same fitter applies.
        log_x = np.log(x)
        if IS_TRUNCATED:
            lmu, lsigma, lres = fit_truncated(log_x, np.log(T))
            ll_log = -lres.fun
        else:
            lmu, lsigma = log_x.mean(), log_x.std(ddof=1)
            ll_log = norm.logpdf(log_x, lmu, lsigma).sum()

        # Change of variables: add -sum(log x) to compare on the same scale
        ll_log -= np.log(x).sum()
        ll_norm = (-neg_loglik_truncated([mu, sigma], x, T) if IS_TRUNCATED
                   else norm.logpdf(x, mu, sigma).sum())

        print(f"\nLog-likelihood  normal: {ll_norm:.1f}")
        print(f"Log-likelihood  lognormal: {ll_log:.1f}")
        print(f"Better fit: {'lognormal' if ll_log > ll_norm else 'normal'}")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    plot_fit(x, mu, sigma, T, IS_TRUNCATED, axes[0])
    qq_plot_truncated(x, mu, sigma, T, axes[1])
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()