"""
test_milestone_counter.py — server-side mutation logic for the stack-based
milestone counter (v1.7.4). The binary D&D 5e `inspiration` boolean handler
remains in place and is unaffected; these tests cover the new `_milestone_inc`
and `_milestone_dec` mutation ops.

Run from repo root:
    python3 -m unittest tests.test_milestone_counter -v
"""
import importlib.util
import json
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "display"))


def _import_app():
    spec = importlib.util.spec_from_file_location(
        "dnd_display_app", str(REPO / "display" / "dnd-display-app.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class MilestoneCounterTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_app()
        cls.mod._token_ok = lambda: True
        cls.client = cls.mod.app.test_client()

    def setUp(self):
        self.mod._current_stats = {
            "players": [{"name": "Aldric", "milestones": {}}]
        }

    def _post(self, body):
        return self.client.post(
            "/stats", data=json.dumps(body), content_type="application/json"
        )

    def _player(self, name="Aldric"):
        for p in self.mod._current_stats.get("players", []):
            if p["name"] == name:
                return p
        return None

    def test_milestone_inc_creates_label(self):
        r = self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bardic Inspiration"}]})
        self.assertIn(r.status_code, (200, 204), msg=r.data)
        self.assertEqual(self._player()["milestones"], {"Bardic Inspiration": 1})

    def test_repeated_inc_accumulates(self):
        for _ in range(3):
            self._post({"players": [{"name": "Aldric", "_milestone_inc": "Hero Coin"}]})
        self.assertEqual(self._player()["milestones"], {"Hero Coin": 3})

    def test_dec_removes_label_at_zero(self):
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Fate Token"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_dec": "Fate Token"}]})
        self.assertNotIn("Fate Token", self._player().get("milestones", {}))

    def test_dec_below_zero_clamps(self):
        self._post({"players": [{"name": "Aldric", "_milestone_dec": "Fate Token"}]})
        self.assertEqual(self._player().get("milestones", {}).get("Fate Token", 0), 0)

    def test_milestone_caps_respected(self):
        self._player()["milestone_caps"] = {"Bardic Inspiration": 1}
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bardic Inspiration"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bardic Inspiration"}]})
        self.assertEqual(self._player()["milestones"]["Bardic Inspiration"], 1)

    def test_inspiration_field_independent_of_milestones(self):
        """Existing binary `inspiration` field stays separate from milestones dict."""
        self._post({"players": [{"name": "Aldric", "inspiration": True}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Hero Coin"}]})
        p = self._player()
        self.assertEqual(p.get("inspiration"), True)
        self.assertEqual(p.get("milestones"), {"Hero Coin": 1})

    def test_multiple_labels_coexist(self):
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Bardic Inspiration"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Hero Coin"}]})
        self._post({"players": [{"name": "Aldric", "_milestone_inc": "Hero Coin"}]})
        self.assertEqual(self._player()["milestones"],
                         {"Bardic Inspiration": 1, "Hero Coin": 2})


if __name__ == "__main__":
    unittest.main()
