import json
import sys
import re
from pathlib import Path
from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Photon
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

# Global cache file path
CACHE_FILE_PATH = "geocache.json"

def load_cache():
    """
    Load the cache file if it exists, otherwise return an empty dictionary.
    """
    if Path(CACHE_FILE_PATH).is_file():
        with open(CACHE_FILE_PATH, 'r') as file:
            return json.load(file)
    return {}

def save_cache(cache):
    """
    Save the updated cache to the file.
    """
    with open(CACHE_FILE_PATH, 'w') as file:
        json.dump(cache, file, indent=4)

def get_location_coordinates(location_name, cache):
    """
    Get coordinates for a location, using the cache if available,
    otherwise querying the geolocation service.
    """
    if location_name in cache:
        print(f"Cache hit for {location_name}")
        return cache[location_name]

    print(f"Cache miss for {location_name}")
    geolocator = Photon(user_agent="measurements")
    try:
        location = geolocator.geocode(location_name)
        if location:
            cache[location_name] = (location.latitude, location.longitude)
            save_cache(cache)  # Save cache immediately after adding new location
            return cache[location_name]
        else:
            return (None, None)
    except GeocoderTimedOut:
        return (None, None)

def plot_locations_on_map(locations, cache):
    """
    Plot the given locations on a map and save it as a PNG file.
    """
    lats, lons = [], []
    for location in locations:
        lat, lon = get_location_coordinates(location, cache)
        if lat is not None and lon is not None:
            lats.append(lat)
            lons.append(lon)
            print(f"location: {location}, lat: {lat}, lon: {lon}")

    if not lats or not lons:
        print("No valid locations to plot.")
        return

    lat_margin = max(lats) - min(lats)
    lon_margin = max(lons) - min(lons)
    margin_ratio = 1.0

    fig = plt.figure(figsize=(10, 5))
    m = Basemap(projection='merc', llcrnrlat=min(lats) - lat_margin * margin_ratio,
                urcrnrlat=max(lats) + lat_margin * margin_ratio,
                llcrnrlon=min(lons) - lon_margin * margin_ratio,
                urcrnrlon=max(lons) + lon_margin * margin_ratio,
                lat_ts=20, resolution='i')

    m.drawcoastlines()
    m.drawcountries()
    m.fillcontinents(color='lightgray', lake_color='lightblue')
    m.drawmapboundary(fill_color='lightblue')

    x, y = m(lons, lats)
    m.scatter(x, y, marker='^', color='r', zorder=5)

    plt.savefig("map.png", format='png', dpi=600)

def parse_location_file(file_path):
    """
    Parse a file containing dates and locations, returning a list of locations.
    """
    locations = []
    with open(file_path, 'r') as file:
        for line in file:
            # Remove the date and leading characters (first 10 characters)
            location_with_extra = line[10:].strip()

            # Remove additional info in parentheses and other special characters
            location = re.sub(r"\(.*?\)|[/,]", "", location_with_extra).strip()

            locations.append(location)
    return locations

def main(file_path=None):
    """
    Main function to load cache, parse locations from a file (if given),
    plot locations on the map, and save the updated cache.
    """
    # Load cache
    cache = load_cache()

    # Define locations
    locations = parse_location_file(file_path) if file_path else []

    # Plot locations
    plot_locations_on_map(locations, cache)

    # Save cache
    save_cache(cache)

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(file_path)

# call with:
# python geoLocViz.py touristlocations_example.md