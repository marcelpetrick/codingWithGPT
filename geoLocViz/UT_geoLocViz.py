import unittest
from unittest.mock import patch, mock_open, call, MagicMock
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

    @patch('geoLocViz.Photon')
    def test_get_location_coordinates_invalid_location(self, mock_geolocator):
        """Test handling of invalid location queries."""
        mock_geolocator.return_value.geocode.return_value = None
        gc = GeoCache()
        lat, lon = gc.get_location_coordinates("InvalidLocation")
        self.assertEqual((lat, lon), (None, None))

    @patch('geoLocViz.plt')
    @patch('geoLocViz.Basemap')
    def test_plot_locations_on_map(self, mock_basemap, mock_plt):
        """Test plotting locations on the map."""
        mock_basemap.return_value.return_value = ([], [])  # Mock Basemap to return a tuple
        gc = GeoCache()
        gc.cache = {"Location1": [10.0, 20.0], "Location2": [30.0, 40.0]}
        gc.plot_locations_on_map(["Location1", "Location2"])
        mock_basemap.assert_called()
        mock_plt.savefig.assert_called_with("map.png", format='png', dpi=600)

    @patch('geoLocViz.plt')
    @patch('geoLocViz.Basemap')
    def test_plot_locations_on_map_no_valid_locations(self, mock_basemap, mock_plt):
        """Test plot_locations_on_map with no valid locations."""
        gc = GeoCache()
        gc.cache = {"InvalidLocation1": [None, None], "InvalidLocation2": [None, None]}
        gc.plot_locations_on_map(["InvalidLocation1", "InvalidLocation2"])
        mock_basemap.assert_not_called()
        mock_plt.savefig.assert_not_called()

class TestUtilityFunctions(unittest.TestCase):

    @patch('builtins.open', mock_open(read_data="2023-01-01 TestLocation1\n2023-01-02 TestLocation2 (extra)"))
    def test_parse_location_file(self):
        file_path = "dummy_path"
        locations = parse_location_file(file_path)
        self.assertEqual(locations, ["TestLocation1", "TestLocation2"])

    @patch('builtins.open', mock_open(read_data="Invalid format line"))
    def test_parse_location_file_invalid_format(self):
        """Test parse_location_file with a file of invalid format."""
        file_path = "invalid_format_file"
        locations = parse_location_file(file_path)
        self.assertEqual(locations, ['rmat line'])  # Adjust the expectation


if __name__ == '__main__':
    unittest.main()
