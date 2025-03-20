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

# Initialize geolocator with a valid, descriptive user agent
geolocator = Nominatim(user_agent="icecream_price_mapper_example@gmail.com")

# RateLimiter to ensure requests don't exceed API limits
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, error_wait_seconds=10)

# Get and immediately print GPS coordinates for each town
for town in towns:
    location = geocode(f"{town}, Germany")
    if location:
        print(f"{town};{location.latitude};{location.longitude}")
    else:
        print(f"{town};None;None")
