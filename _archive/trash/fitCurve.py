import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy.stats import gamma
from scipy.special import gammaln
import pandas


def convert_to_seconds(time_str):
    """
    Converts a time string in the format "minutes:seconds.milliseconds" to total seconds.

    Args:
        time_str (str): The time string (e.g., "1:30.500", "0:05.020", "2:00.000").

    Returns:
        float: The total time in seconds, or None if the input format is invalid.
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError("Invalid format: missing colon.")

        minutes_str = parts[0]
        sec_milisec_str = parts[1]

        seconds_parts = sec_milisec_str.split('.')
        if len(seconds_parts) != 2:
            raise ValueError("Invalid format: missing dot for milliseconds.")

        minutes = int(minutes_str)
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1])

        total_seconds = (minutes * 60) + seconds + (milliseconds / 100)
        return total_seconds
    except:
        return time_str

timesDF = pandas.read_csv('data/NY/m/output1600.csv')

times = [convert_to_seconds(x) for x in timesDF['time'].tolist()]

plt.hist(times, bins=40, density=False)
plt.xticks(np.arange(240, 660, 30))
plt.show()

# --- 2. Your actual data: The fastest 1000 times ---
# Sort the full population to get the fastest (lowest) times
sorted_times = np.sort(times)
num_observed_times = len(times)
fastest_1000_times = sorted_times[:num_observed_times]

# Determine the truncation point (the slowest time among your fastest 1000)
truncation_point_upper = fastest_1000_times[-1] # This is the cutoff for what you observe (all times are <= this)

print(f"Number of observed times: {num_observed_times}")
print(f"Mean of your fastest {num_observed_times} times (biased): {np.mean(fastest_1000_times):.2f}s")
print(f"Std of your fastest {num_observed_times} times (biased): {np.std(fastest_1000_times):.2f}s")
print(f"Truncation point (slowest time in your observed data): {truncation_point_upper:.2f}s")

# --- 3. Define the negative log-likelihood function for a right-truncated normal ---
# We minimize the negative log-likelihood to find the maximum likelihood estimates
def truncated_log_likelihood(params, x, T):
    mu, sigma = params
    if sigma <= 0:
        return np.inf  # avoid invalid sigma
    log_pdf = norm.logpdf(x, loc=mu, scale=sigma)
    log_cdf = np.log(norm.cdf(T, loc=mu, scale=sigma))
    return -np.sum(log_pdf - log_cdf)

# --- 4. Estimate parameters using optimization ---
# Initial guess for mu and sigma.
# Since you have the fastest times, your initial mu should probably be *faster* (lower) than the observed mean,
# and your initial sigma might be slightly *larger* than the observed std.
initial_guess = [130, 20]
# Ensure initial guess for sigma is positive
if initial_guess[1] <= 0:
    initial_guess[1] = 1.0 # default to a small positive value if calculated is non-positive

# Perform the optimization
result = minimize(truncated_log_likelihood, initial_guess,
                  args=(fastest_1000_times, truncation_point_upper),
                  bounds=[(0, None), (0, None)],
                  options={'maxls': 50}) # mu (time) must be positive, sigma strictly positive

estimated_mu, estimated_sigma = result.x
print(f"\nEstimated mean (untruncated): {estimated_mu:.2f}s")
print(f"Estimated std (untruncated): {estimated_sigma:.2f}s")
print(f"Optimization successful: {result.success}")
print(f"Message: {result.message}")

# --- 5. Visualize the results ---
plt.figure(figsize=(12, 7))

# Plot the histogram of observed data based on counts
# Calculate bin edges from the observed data to determine histogram width
bin_counts, bin_edges, _ = plt.hist(fastest_1000_times, bins=50, density=False, alpha=0.6, color='g', label=f'Your Fastest {num_observed_times} Times (Observed Counts)')

# To overlay the normal curve with occurrences, we need to scale the PDF.
# The area under the PDF curve sums to 1. To represent counts, we multiply by total_counts * bin_width.
# The 'total_counts' here is the `num_observed_times`.
bin_width = bin_edges[1] - bin_edges[0]
scaling_factor = num_observed_times * bin_width

# Plot the estimated (untruncated) normal curve, scaled for occurrences
x = np.linspace(estimated_mu - 3*estimated_sigma, estimated_mu + 3*estimated_sigma, 500)
pdf_values_estimated = norm.pdf(x, estimated_mu, estimated_sigma)
plt.plot(x, pdf_values_estimated * scaling_factor, 'r--', label='Extrapolated Full Normal Distribution (Scaled for Counts)')

# Plot the true (untruncated) normal curve (if you had it for comparison), scaled for occurrences
#pdf_values_true = norm.pdf(x, true_mean, true_std)
#plt.plot(x, pdf_values_true * scaling_factor, 'b:', label='True Full Normal Distribution (for comparison, Scaled for Counts)')


# Mark the truncation point
plt.axvline(x=truncation_point_upper, color='purple', linestyle=':',
            label=f'Truncation Point (Slowest of Fastest {num_observed_times} Times): {truncation_point_upper:.2f}s')

plt.title(f'Extrapolation of Normal Distribution from Fastest {num_observed_times} Times (Counts)')
plt.xlabel('Running Time (seconds)')
plt.ylabel('Number of Occurrences') # Changed label
plt.legend()
plt.grid(True)
plt.show()

# --- 6. Estimate total population size (optional) ---
prob_below_truncation = norm.cdf(truncation_point_upper, estimated_mu, estimated_sigma)
print(f"\nEstimated probability of a time being <= {truncation_point_upper:.2f}s (from extrapolated full distribution): {prob_below_truncation:.4f}")

# Estimated total population size = num_observed_times / prob_below_truncation
estimated_total_population = num_observed_times / prob_below_truncation
print(f"Estimated total population size if these are ALL times up to the cutoff: {estimated_total_population:.0f}")

# Example: What's the estimated median time?
estimated_median_time = norm.ppf(0.5, estimated_mu, estimated_sigma)
print(f"Estimated median running time (50th percentile) for the full population: {estimated_median_time:.2f}s")
