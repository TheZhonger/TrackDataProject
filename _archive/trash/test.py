import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

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


times = []
with open('data/boys100m.txt', 'r') as file:
    lines = file.readlines()
    for line in lines:
        times.append(float(convert_to_seconds(line)))

times = times[:500]
reflectedTimes = [2*max(times)-x for x in times]

x = np.linspace(min(times), max(reflectedTimes), 1000)
x = np.linspace(min(times), max(times), 1000)

#x = np.linspace(, 1000)
predictedStd = .46
predictedMean = 11.72
y = np.exp(-(x-predictedMean)**2 / (2* predictedStd**2)) / np.sqrt(2 * np.pi * predictedStd**2)

plt.plot(x, y, 'r-', label='Normal Distribution')
plt.xlim(predictedMean-4*predictedStd, predictedMean+4*predictedStd)
sns.histplot(times+reflectedTimes, kde=True, stat='density')
plt.show()