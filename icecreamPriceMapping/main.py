import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from shapely.geometry import Point
import contextily as ctx

def load_bayern_shapefile(filepath):
    print("### Loading Bayern shapefile")
    bayern_map = gpd.read_file(filepath)
    if bayern_map.crs is None:
        print("### No CRS found for Bayern shapefile. Setting CRS to EPSG:4326 (WGS84).")
        bayern_map = bayern_map.set_crs(epsg=4326)
    print("### Reprojecting Bayern map to EPSG:3857")
    return bayern_map.to_crs(epsg=3857)

def load_and_clean_data(csv_file):
    print("### Loading input CSV data")
    data_df = pd.read_csv(csv_file, sep=';', header=None, names=['city', 'lat', 'lon', 'price_raw'])
    print("### Cleaning price data")
    data_df['price'] = data_df['price_raw'].str.replace(',', '.').str.replace('€', '').astype(float)
    print("### Dropping rows with missing lat/lon/price")
    data_df = data_df.dropna(subset=['lat', 'lon', 'price'])
    return data_df

def create_geodataframe(data_df):
    print("### Creating GeoDataFrame from data")
    gdf = gpd.GeoDataFrame(
        data_df,
        geometry=gpd.points_from_xy(data_df['lon'], data_df['lat']),
        crs='EPSG:4326'
    )
    print("### Reprojecting GeoDataFrame to EPSG:3857")
    return gdf.to_crs(epsg=3857)

def interpolate_data(gdf, bayern_map):
    print("### Preparing interpolation grid")
    xmin, ymin, xmax, ymax = bayern_map.total_bounds
    xx, yy = np.mgrid[xmin:xmax:500j, ymin:ymax:500j]
    print("### Extracting coordinates and price values")
    points = np.vstack((gdf.geometry.x, gdf.geometry.y)).T
    values = gdf['price']
    print("### Filtering valid data points")
    valid_mask = ~np.isnan(points).any(axis=1) & ~np.isnan(values)
    points = points[valid_mask]
    values = values[valid_mask]
    print("### Performing cubic interpolation")
    grid_z = griddata(points, values, (xx, yy), method='cubic')
    return xx, yy, grid_z

def plot_heatmap(bayern_map, gdf, xx, yy, grid_z):
    print("### Starting plot generation")
    fig, ax = plt.subplots(figsize=(12, 12))
    print("### Plotting heatmap")
    cmap = plt.colormaps.get_cmap('RdYlGn_r')  # Updated per Matplotlib deprecation
    heatmap = ax.imshow(
        grid_z.T,
        extent=(xx.min(), xx.max(), yy.min(), yy.max()),
        origin='lower',
        cmap=cmap,
        alpha=0.6
    )
    print("### Plotting Bayern borders")
    bayern_map.boundary.plot(ax=ax, color='black', linewidth=1.5)
    print("### Plotting original data points")
    gdf.plot(ax=ax, color='black', markersize=50, marker='o', label='Data points')
    print("### Adding basemap tiles")
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)  # Replaced Stamen with OpenStreetMap
    print("### Adding colorbar and labels")
    cbar = plt.colorbar(heatmap, ax=ax, shrink=0.7)
    cbar.set_label('Ice Cream Price (€)')
    plt.title('Ice Cream Prices Heatmap in Bayern')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.legend()
    plt.tight_layout()
    print("### Displaying plot")
    plt.show()

def main():
    bayern_shapefile = "geoBoundaries-DEU-ADM0_simplified.shp"
    csv_file = "cleanData.csv"

    print("### Starting Heatmap Generation Process")
    bayern_map = load_bayern_shapefile(bayern_shapefile)
    data_df = load_and_clean_data(csv_file)
    gdf = create_geodataframe(data_df)
    xx, yy, grid_z = interpolate_data(gdf, bayern_map)
    plot_heatmap(bayern_map, gdf, xx, yy, grid_z)
    print("### Heatmap Generation Completed")

if __name__ == "__main__":
    main()
