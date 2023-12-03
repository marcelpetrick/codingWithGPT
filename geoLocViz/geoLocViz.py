from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Photon

def get_location_coordinates(location_name):
    geolocator = Photon(user_agent="measurements")

    try:
        # Get location data
        location = geolocator.geocode(location_name)

        # Check if location is found
        if location:
            return (location.latitude, location.longitude)
        else:
            return ("Location not found", "Location not found")
    except GeocoderTimedOut:
        return ("Geocoder service timed out", "Geocoder service timed out")

def evaluateLocations(input):
    for location in input:
        print(f"location: {location}")
        lat, lon = get_location_coordinates(location)
        print(f"lat: {lat}, lon: {lon})")

locations = ["Eiffel Tower", "Eibsee", "Zorneding"]
evaluateLocations(locations)