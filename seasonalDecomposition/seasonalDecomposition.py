# mail@marcelpetrick.it
# What is a timeseries of data. Short explanation
#
# A time series is a collection of data points or observations recorded at regular intervals over a period of time. It is a sequence of numerical values where each value represents a specific point in time. Time series data is commonly used in fields like economics, finance, and weather forecasting, where understanding trends, patterns, and seasonality are crucial for making predictions or informed decisions.
# mail@marcelpetrick.it
# I have data over several years, each entry is one month. i want to create a smooth graph over it. what kind of options do i have?
#
# To create a smooth graph from your monthly data, you can use various smoothing techniques to reduce noise and highlight underlying trends. Some popular options include:
#
#     Moving Average: Calculate the average of a fixed number of data points (e.g., 3, 6, or 12 months) and shift the window forward one step at a time. This creates a smoother line by averaging out short-term fluctuations.
#
#     Exponential Smoothing: Apply more weight to recent data points and less weight to older ones by using an exponential decay function. This method produces a smoother line that quickly adapts to changes in the data.
#
#     LOESS (Locally Estimated Scatterplot Smoothing): Fit a low-degree polynomial (e.g., linear or quadratic) to localized subsets of the data using weighted least squares. This method is more flexible and can capture non-linear trends.
#
#     Savitzky-Golay filter: Apply a convolution-based smoothing technique that uses polynomial fitting to preserve higher moments of the data (e.g., peaks and valleys), while still reducing noise.
#
#     Seasonal Decomposition: Decompose the time series into its trend, seasonal, and residual components. You can then analyze the trend component or reconstruct the time series without the residual component to obtain a smoother version of the data.
#
# When choosing a smoothing method, consider factors such as the nature of your data, the presence of seasonality, and the desired level of smoothness. Experiment with different methods and their parameters to find the one that best suits your needs.
# mail@marcelpetrick.it
# write me python code for seasonal decomposition for a list of data with monthly entries.
#
# To perform seasonal decomposition in Python, you can use the statsmodels library. If you don't have it installed, run !pip install statsmodels to install it. Below is an example of how to decompose a list of monthly data using seasonal decomposition:


import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

# Your monthly data as a list
data = [120, 130, 140, 145, 160, 170, 150, 140, 155, 165, 180, 190, 125, 135, 145, 150, 165, 175, 155, 145, 160, 170,
        185, 195, 130, 140, 145, 160, 170, 150, 140, 155, 165, 180, 190, 200  # expanded by me
        ]

# Convert the list into a pandas Series with a DatetimeIndex
date_range = pd.date_range(start='2020-01-01', periods=len(data), freq='M')
monthly_data = pd.Series(data, index=date_range)

# Perform seasonal decomposition
result = seasonal_decompose(monthly_data, model='additive')

# Plot the original data, trend, seasonal, and residual components
fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 8))
result.observed.plot(ax=ax1, title='Original Data')
result.trend.plot(ax=ax2, title='Trend Component')
result.seasonal.plot(ax=ax3, title='Seasonal Component')
result.resid.plot(ax=ax4, title='Residual Component')

plt.tight_layout()
plt.show()

# Explain the trend component, the seasonal component and the residual component to a 15 year old.
#
# Imagine you're observing the sales of ice cream over a year.
#
#     Trend Component: This is the overall pattern or direction in which the ice cream sales are moving. For example, if the ice cream shop is gaining popularity, the trend might show a gradual increase in sales over time. Think of the trend as a line that represents the general direction of the data, ignoring the ups and downs that happen throughout the year.
#
#     Seasonal Component: This is the regular pattern that repeats itself every year, like a cycle. For ice cream sales, you would expect more sales in the warmer months (summer) and fewer sales in the colder months (winter). The seasonal component captures these predictable changes throughout the year.
#
# Residual Component: This is the part of the data that is left over after accounting for the trend and seasonal
# components. It represents random fluctuations, noise, or unexpected events that don't follow the overall pattern or
# seasonality. For instance, if there was a sudden heatwave in winter or a promotional event, it could cause a spike
# in ice cream sales that isn't explained by the trend or seasonal components. Residuals help us identify these
# unusual occurrences in the data.
