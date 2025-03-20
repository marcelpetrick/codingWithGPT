import pandas as pd

# Read price data (listIcePrices.csv)
prices_df = pd.read_csv('listIcePrices.csv', sep=';', header=None, names=['City', 'Price'])

# Read GPS coordinates (listGeoCoords.csv)
coords_df = pd.read_csv('listGeoCoords.csv', sep=';', header=None, names=['City', 'Latitude', 'Longitude'])

# Handle differences in naming (optional but recommended)
coords_df['City'] = coords_df['City'].replace({'Garmisch-Partenkirchen': 'Garmisch'})

# Merge both DataFrames based on the City name
merged_df = pd.merge(prices_df, coords_df, on='City', how='left')

# Reorder columns for clean output
merged_df = merged_df[['City', 'Latitude', 'Longitude', 'Price']]

# Output merged DataFrame to cleanData.csv
merged_df.to_csv('cleanData.csv', sep=';', index=False, header=False)

# Print confirmation
print("Merged data saved as cleanData.csv")
