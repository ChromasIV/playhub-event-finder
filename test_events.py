import unittest
import math
from datetime import datetime
from unittest.mock import patch, mock_open

# Import functions from find_events
from find_events import haversine, filter_and_format_events, load_config

class TestPlayhubEventFinder(unittest.TestCase):
    
    def test_haversine_distance(self):
        # Coordinates of Tampa, FL: 27.9506, -82.4572
        # Coordinates of Orlando, FL: 28.5383, -81.3792
        # The distance is roughly 77-80 miles.
        dist = haversine(27.9506, -82.4572, 28.5383, -81.3792)
        self.assertAlmostEqual(dist, 77.4, delta=2.0)
        
        # Test identical coordinates distance is 0
        self.assertEqual(haversine(27.9506, -82.4572, 27.9506, -82.4572), 0.0)
        
        # Test None inputs return 9999.0
        self.assertEqual(haversine(None, -82.4572, 28.5383, -81.3792), 9999.0)
        self.assertEqual(haversine(27.9506, None, 28.5383, -81.3792), 9999.0)
        
    def test_filter_and_format_events_keywords(self):
        # Sample raw events from Playhub API
        raw_events = [
            {
                "id": "event-1",
                "name": "Disney Lorcana Store Championship",
                "description": "Weekly play championship event",
                "start_datetime": "2026-06-10T18:00:00Z",
                "cost_in_cents": 1000,
                "registered_user_count": 5,
                "capacity": 32,
                "store": {
                    "name": "Cool Stuff Games",
                    "full_address": "Tampa, FL",
                    "latitude": 27.9506,
                    "longitude": -82.4572
                }
            },
            {
                "id": "event-2",
                "name": "Regular Weekly Play",
                "description": "Casual Lorcana games, no prizes",
                "start_datetime": "2026-06-12T18:00:00Z",
                "cost_in_cents": 0,
                "registered_user_count": 2,
                "store": {
                    "name": "Cool Stuff Games",
                    "full_address": "Tampa, FL",
                    "latitude": 27.9506,
                    "longitude": -82.4572
                }
            }
        ]
        
        # Test filtering with keyword "championship"
        keywords = ["championship"]
        filtered = filter_and_format_events(raw_events, "Lorcana", keywords, user_lat=27.9506, user_lon=-82.4572)
        
        # Should only match event-1
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "event-1")
        self.assertEqual(filtered[0]["cost"], "$10.00")
        self.assertEqual(filtered[0]["spots"], "5 registered / 32 max")
        self.assertEqual(filtered[0]["distance"], 0.0)
        self.assertEqual(filtered[0]["lat"], 27.9506)
        self.assertEqual(filtered[0]["lon"], -82.4572)
        
    def test_filter_and_format_events_timezone(self):
        raw_events = [
            {
                "id": "event-tz",
                "name": "Disney Lorcana Championship NY Time",
                "description": "Weekly play championship event",
                "start_datetime": "2026-06-10T18:00:00Z",
                "timezone": "America/New_York",
                "cost_in_cents": 1000,
                "store": {
                    "name": "NY Store"
                }
            }
        ]
        filtered = filter_and_format_events(raw_events, "Lorcana", ["championship"])
        self.assertEqual(len(filtered), 1)
        # 18:00 UTC = 14:00 (2:00 PM) EDT in America/New_York (June is daylight saving)
        self.assertEqual(filtered[0]["date"], "Wednesday, June 10, 2026")
        self.assertTrue(filtered[0]["time"].startswith("02:00 PM"))
        
    @patch("os.path.exists")
    def test_load_config_default(self, mock_exists):
        mock_exists.return_value = False
        config = load_config()
        self.assertEqual(config, {})

if __name__ == "__main__":
    unittest.main()
