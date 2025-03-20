import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from shapely.geometry import Point
import contextily as ctx  # optional for basemap tiles

# Step 1: Load Bayern Boundary
bayern_map = gpd.read_file("path_to_bayern_shapefile.shp")

# Step 2: Example data points (lat, lon, value)
data = [
    {'lat': 48.1351, 'lon': 11.5820, 'value': 10},  # Munich
    {'lat': 49.0069, 'lon': 12.0850, 'value': 20},  # Regensburg
    {'lat': 47.5670, 'lon': 10.7019, 'value': 15},  # Kempten
    {'lat': 50.0000, 'lon': 10.2333, 'value': 5},   # Coburg
]

df = pd.DataFrame(data)

# Step 3: Create a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['lon'], df['lat']), crs='EPSG:4326')

# Project to Web Mercator (for plotting with basemaps)
gdf = gdf.to_crs(epsg=3857)
bayern_map = bayern_map.to_crs(epsg=3857)

# Step 4: Interpolation
# Create a grid over Bayern
xmin, ymin, xmax, ymax = bayern_map.total_bounds
xx, yy = np.mgrid[xmin:xmax:500j, ymin:ymax:500j]

# Interpolation: prepare points and values
points = np.vstack((gdf.geometry.x, gdf.geometry.y)).T
values = gdf['value']

# Interpolate
grid_z = griddata(points, values, (xx, yy), method='cubic')

# Step 5: Plot
fig, ax = plt.subplots(figsize=(10, 10))

# Plot interpolated heatmap
plt.imshow(grid_z.T, extent=(xmin, xmax, ymin, ymax), origin='lower', cmap='hot', alpha=0.6)

# Plot the Bayern boundary
bayern_map.boundary.plot(ax=ax, color='black', linewidth=1)

# Plot the points
gdf.plot(ax=ax, color='blue', markersize=50)

# Add a basemap (optional)
ctx.add_basemap(ax, source=ctx.providers.Stamen.Terrain)

plt.title("Heatmap over Bayern")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()
