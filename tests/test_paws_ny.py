"""Run: python -m unittest discover tests"""
import json
import unittest
from pathlib import Path
from unittest import mock

from refresh import tagging
from refresh.sources import paws_ny, rescuegroups

FIX = Path(__file__).parent / "fixtures"
ZIPS = {"11106": (40.7609, -73.9295), "11363": (40.7722, -73.7454)}


@mock.patch("refresh.geo.zip_to_latlon", side_effect=lambda z: ZIPS.get(z))
class PawsNyTest(unittest.TestCase):
    def test_index_lists_each_listing_once(self, _):
        urls = paws_ny.parse_index((FIX / "index.html").read_text())
        self.assertEqual(len(urls), 18)
        self.assertEqual(len(set(urls)), 18)

    def test_dog_listing(self, _):
        x = paws_ny.parse_listing((FIX / "listing_dogs.html").read_text(), "https://example.org/opportunities/68-abc-def")
        self.assertEqual(x["petName"], "Storm and Kaylee")
        self.assertEqual(x["species"], ["dog"])
        self.assertEqual(x["size"], ["large"])
        self.assertIn("Siberian husky", x["breed"])
        self.assertTrue({"energetic", "affectionate", "calm"} <= set(x["temper"]))
        self.assertEqual(x["hood"], "Crescent St, Astoria")
        self.assertEqual(x["borough"], "Queens")
        self.assertEqual(x["activity"], ["walk"])
        self.assertEqual(x["daypart"], ["morning", "midday", "evening"])
        self.assertIn("10am to 7pm", x["when"])
        self.assertEqual(x["sourceUpdated"], "2025-09-09")
        self.assertEqual((x["lat"], x["lon"]), ZIPS["11106"])

    def test_cat_listing(self, _):
        x = paws_ny.parse_listing((FIX / "listing_cat.html").read_text(), "https://example.org/opportunities/68-abc-cat")
        self.assertEqual(x["petName"], "Lightfoot")
        self.assertEqual(x["species"], ["cat"])
        self.assertEqual(x["activity"], ["visit"])
        self.assertEqual(x["daypart"], ["morning"])
        self.assertTrue({"gentle", "affectionate"} <= set(x["temper"]))

    def test_closed_listing_is_dropped(self, _):
        page = (FIX / "listing_cat.html").read_text().replace("Recruiting now", "Closed")
        self.assertIsNone(paws_ny.parse_listing(page, "https://example.org/x"))


class TaggingTest(unittest.TestCase):
    def test_schedule(self):
        self.assertEqual(tagging.schedule_tags("Mon, Wed, Fri - 1 shift: 11:30 to 14:00 EST"), (["weekday"], ["midday"]))
        self.assertEqual(tagging.schedule_tags("")[1], ["any"])

    def test_breed_sizes(self):
        self.assertEqual(tagging.breeds_in("Walk a chihuahua for a neighbor")[1], ["small"])
        self.assertEqual(tagging.breeds_in("an adorable golden lab mix service dog")[0], "Golden lab mix")


class RescueGroupsTest(unittest.TestCase):
    @mock.patch("refresh.geo.zip_to_latlon", return_value=(40.76, -73.93))
    def test_maps_api_fields(self, _):
        payload = {"data": [{"type": "animals", "id": "42", "attributes": {
            "name": "Biscuit", "breedString": "Beagle / Mixed", "sizeGroup": "Medium", "ageGroup": "Senior",
            "energyLevel": "Low", "newPeopleReaction": "Friendly", "isHousetrained": True,
            "descriptionText": "A mellow old soul.", "url": "https://example.org/biscuit", "updatedDate": "2026-11-01T10:00:00Z"},
            "relationships": {"orgs": {"data": [{"type": "orgs", "id": "7"}]}}}],
            "included": [{"type": "orgs", "id": "7", "attributes": {"name": "Queens Rescue", "city": "Astoria", "postalcode": "11106"}}]}
        (x,) = rescuegroups.parse_response(payload, "dog")
        self.assertEqual((x["id"], x["size"], x["age"]), ("rescue-42", ["medium"], ["senior"]))
        self.assertEqual(x["temper"], ["calm", "friendly"])
        self.assertEqual((x["org"], x["borough"], x["activity"]), ("Queens Rescue", "Queens", ["foster"]))

    def test_spread_caps_each_rescue(self):
        pets = [{"org": "A"}] * 5 + [{"org": "B"}] * 2
        self.assertEqual([p["org"] for p in rescuegroups.spread(pets, 2, 10)], ["A", "A", "B", "B"])

    def test_skipped_without_key(self):
        with mock.patch.dict("os.environ", {"RESCUEGROUPS_API_KEY": ""}):
            self.assertIsNone(rescuegroups.fetch({}))


if __name__ == "__main__":
    unittest.main()
