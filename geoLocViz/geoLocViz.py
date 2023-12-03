from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Photon
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np

def get_location_coordinates(location_name):
    geolocator = Photon(user_agent="measurements")

    try:
        location = geolocator.geocode(location_name)
        if location:
            return (location.latitude, location.longitude)
        else:
            return (None, None)
    except GeocoderTimedOut:
        return (None, None)

def plot_locations_on_map(locations):
    # Initialize lists to store latitude and longitude
    lats, lons = [], []

    # Geocode each location and add to lists
    for location in locations:
        lat, lon = get_location_coordinates(location)
        if lat is not None and lon is not None:
            lats.append(lat)
            lons.append(lon)
            print(f"location: {location}, lat: {lat}, lon: {lon}")

    # Calculate margins dynamically
    lat_margin = max(lats) - min(lats)
    lon_margin = max(lons) - min(lons)
    margin_ratio = 1.0  # 200% margin

    # Create a new map
    fig = plt.figure(figsize=(10, 5))
    m = Basemap(projection='merc',
                llcrnrlat=min(lats) - lat_margin * margin_ratio,
                urcrnrlat=max(lats) + lat_margin * margin_ratio,
                llcrnrlon=min(lons) - lon_margin * margin_ratio,
                urcrnrlon=max(lons) + lon_margin * margin_ratio,
                lat_ts=20, resolution='i')

    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='lightgray', lake_color='lightblue')
    m.drawmapboundary(fill_color='lightblue')

    # Convert latitude and longitude to x and y coordinates
    x, y = m(lons, lats)

    # Plot each location on the map
    #m.scatter(x, y, marker='x', color='r', zorder=5)
    m.scatter(x, y, marker='^', color='r', zorder=5)

    plt.savefig("map.png", format='png', dpi=600)
    #plt.show()

# Locations to plot
locations = ["Regensburg", "München", "Eibsee", "Zorneding"]
plot_locations_on_map(locations)
