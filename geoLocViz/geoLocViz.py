import json
from pathlib import Path
from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Photon
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import re
import sys

class GeoCache:
    """
    A class for handling geolocation caching and plotting.

    Attributes:
        cache_file (str): Path to the cache file.
        cache (dict): Cache storage for geolocations.
    """

    def __init__(self, cache_file="geocache.json"):
        """
        Initializes the GeoCache object with a specified cache file.

        Args:
            cache_file (str): Path to the cache file. Defaults to 'geocache.json'.
        """
        self.cache_file = cache_file
        self.cache = self.load_cache()

    def load_cache(self):
        """
        Load the cache file if it exists, otherwise return an empty dictionary.

        Returns:
            dict: The loaded cache.
        """
        if Path(self.cache_file).is_file():
            with open(self.cache_file, 'r') as file:
                return json.load(file)
        return {}

    def save_cache(self):
        """
        Save the updated cache to the file.
        """
        with open(self.cache_file, 'w') as file:
            json.dump(self.cache, file, indent=4)

    def get_location_coordinates(self, location_name):
        """
        Get coordinates for a location, using the cache if available,
        otherwise querying the geolocation service.

        Args:
            location_name (str): The name of the location to find coordinates for.

        Returns:
            tuple: A tuple of latitude and longitude.
        """
        if location_name in self.cache:
            print(f"Cache hit for {location_name}")
            return self.cache[location_name]

        print(f"Cache miss for {location_name}")
        geolocator = Photon(user_agent="measurements")
        try:
            location = geolocator.geocode(location_name)
            if location:
                self.cache[location_name] = (location.latitude, location.longitude)
                self.save_cache()  # Save cache immediately after adding new location
                return self.cache[location_name]
            else:
                return (None, None)
        except GeocoderTimedOut:
            return (None, None)

    def plot_locations_on_map(self, locations):
        """
        Plot the given locations on a map and save it as a PNG file.

        Args:
            locations (list): A list of location names to be plotted.
        """
        lats, lons = [], []
        for location in locations:
            lat, lon = self.get_location_coordinates(location)
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

    Args:
        file_path (str): Path to the file containing dates and locations.

    Returns:
        list: A list of parsed locations.
    """
    locations = []
    with open(file_path, 'r') as file:
        for line in file:
            # Remove the date and leading characters (first 10 characters)
            location_with_extra = line[10:].strip()

            # Remove additional info in parentheses and other special characters
            location = re.sub(r"\(.*?\)|[/,]", "", location_with_extra).strip()

            if len(location) > 0:
                locations.append(location)
    return locations

def main(file_path=None):
    """
    Main function to create a GeoCache object, parse locations from a file,
    plot locations on the map, and save the updated cache.

    Args:
        file_path (str): Optional path to a file containing dates and locations.
    """
    geo_cache = GeoCache()

    locations = parse_location_file(file_path) if file_path else []
    geo_cache.plot_locations_on_map(locations)
    geo_cache.save_cache()

if __name__ == "__main__":
    file_path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(file_path_arg)

# call with:
# python geoLocViz.py touristlocations_example.md
