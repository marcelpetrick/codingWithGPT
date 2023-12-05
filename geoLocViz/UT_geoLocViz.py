import unittest
from unittest.mock import patch, mock_open, call
from geoLocViz import GeoCache, parse_location_file

class TestGeoCache(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open, read_data='{"TestLocation": [1.0, 2.0]}')
    def test_load_cache(self, mock_file):
        gc = GeoCache()
        self.assertEqual(gc.cache, {"TestLocation": [1.0, 2.0]})

    @patch('json.dump')
    @patch('builtins.open', new_callable=mock_open, read_data='{}')
    def test_save_cache(self, mock_file, mock_json_dump):
        gc = GeoCache()
        gc.cache = {"NewLocation": [3.0, 4.0]}
        gc.save_cache()
        write_call = call('geocache.json', 'w')
        mock_file.assert_has_calls([write_call], any_order=True)
        mock_json_dump.assert_called_once_with(gc.cache, mock_file(), indent=4)

    @patch('geoLocViz.Photon')
    def test_get_location_coordinates_cache_hit(self, mock_geolocator):
        gc = GeoCache()
        gc.cache = {"CachedLocation": [5.0, 6.0]}
        lat, lon = gc.get_location_coordinates("CachedLocation")
        self.assertEqual((lat, lon), (5.0, 6.0))
        mock_geolocator.assert_not_called()

    @patch('geoLocViz.Photon')
    def test_get_location_coordinates_cache_miss(self, mock_geolocator):
        mock_geolocator.return_value.geocode.return_value = type('Location', (object,), {'latitude': 7.0, 'longitude': 8.0})
        gc = GeoCache()
        gc.cache = {}
        lat, lon = gc.get_location_coordinates("NewLocation")
        self.assertEqual((lat, lon), (7.0, 8.0))
        self.assertTrue("NewLocation" in gc.cache)

    # You can add more tests for plot_locations_on_map here, mocking plt and Basemap accordingly

class TestUtilityFunctions(unittest.TestCase):

    @patch('builtins.open', mock_open(read_data="2023-01-01 TestLocation1\n2023-01-02 TestLocation2 (extra)"))
    def test_parse_location_file(self):
        file_path = "dummy_path"
        locations = parse_location_file(file_path)
        self.assertEqual(locations, ["TestLocation1", "TestLocation2"])

# More tests can be added as needed

if __name__ == '__main__':
    unittest.main()
