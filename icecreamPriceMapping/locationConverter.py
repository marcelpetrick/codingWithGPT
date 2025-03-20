import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# List of towns
towns = [
    "München", "Wolfratshausen", "Garmisch-Partenkirchen", "Starnberg", "Herrsching",
    "Nürnberg", "Schwabach", "Ansbach", "Treuchtlingen", "Neustadt an der Aisch",
    "Gunzenhausen", "Fürth", "Bayreuth", "Kulmbach", "Bamberg", "Lichtenfels", "Coburg",
    "Hof", "Bad Staffelstein", "Münchberg", "Würzburg", "Schweinfurt", "Aschaffenburg",
    "Kitzingen", "Miltenberg", "Ochsenfurt", "Werneck", "Passau", "Landshut", "Straubing",
    "Deggendorf", "Dingolfing", "Ergoldsbach", "Reisbach", "Regen", "Geiselhöring",
    "Massing", "Metten", "Regensburg", "Neumarkt in der Oberpfalz", "Auerbach in der Oberpfalz",
    "Nittenau", "Amberg", "Nittendorf", "Regenstauf", "Parsberg", "Kaufbeuren", "Sonthofen",
    "Kempten (Allgäu)", "Isny im Allgäu", "Wangen im Allgäu", "Marktoberdorf", "Oberstaufen",
    "Augsburg", "Günzburg", "Friedberg", "Memmingen", "Aichach", "Lindau", "Neu-Ulm", "Lauingen"
]

# Initialize geolocator with valid user agent
geolocator = Nominatim(user_agent="your_unique_user_agent_here")

# RateLimiter to avoid hitting the server too quickly (1 second delay)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, error_wait_seconds=10)

# Function to get GPS coordinates safely
def get_gps_location(city):
    location = geocode(f"{city}, Germany")
    return (location.latitude, location.longitude) if location else (None, None)

# Fetch GPS locations with error handling
gps_locations = [get_gps_location(city) for city in towns]

# Create DataFrame
df_locations = pd.DataFrame({
    "City": towns,
    "Latitude": [loc[0] for loc in gps_locations],
    "Longitude": [loc[1] for loc in gps_locations]
})

# Display DataFrame
print(df_locations)

# Optional: save to CSV
df_locations.to_csv("city_gps_coordinates.csv", index=False)
