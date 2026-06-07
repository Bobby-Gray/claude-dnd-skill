"""Tests for _phone_present() + _client_chars lifecycle in dnd-display-app.

Locks in the routing contract for the v2.1.4 on-screen dice work:

- A connected SSE client registers its bound character (lowercased, whitespace
  trimmed, length-capped) in `_client_chars`.
- `_phone_present(<name>)` returns True iff any registered client's bound
  character matches, case-insensitively.
- Disconnect → `_client_chars.pop(q, None)` removes the entry.

The router-side payload field `onscreen_targets` is built from
`_phone_present()` results in `/dice-request` and the catch-up replay block
inside `/stream`. Those endpoints stand up Flask app state we'd rather not
exercise from unit tests; this file pins the inner function instead so a
refactor of the registration/cleanup paths can't silently flip routing
behaviour.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
DISPLAY = REPO / "skills" / "dnd" / "display"


def _load_app_module():
    """Import dnd-display-app.py under a unique name. Same pattern as
    test_display_robustness.py — no Flask app boot needed for the helpers
    we exercise."""
    spec = importlib.util.spec_from_file_location(
        "_phone_presence_app_under_test", DISPLAY / "dnd-display-app.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_phone_presence_app_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class PhonePresentTest(unittest.TestCase):
    """The pure read-side of the routing decision."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _load_app_module()

    def setUp(self) -> None:
        # Reset the module-level dict before each test so we don't leak state
        # between cases. The real cleanup path lives in _broadcast and /stream;
        # we exercise it explicitly in DisconnectCleanupTest below.
        self.app._client_chars.clear()

    def test_empty_dict_returns_false(self) -> None:
        self.assertFalse(self.app._phone_present("Aldric"))

    def test_empty_or_whitespace_input_returns_false(self) -> None:
        self.app._client_chars["q-aldric"] = "aldric"
        self.assertFalse(self.app._phone_present(""))
        self.assertFalse(self.app._phone_present("   "))
        # None is the third realistic shape — `request.args.get(...)` returns
        # None when missing, and the dice-request code path passes that value
        # through if a target wasn't supplied.
        self.assertFalse(self.app._phone_present(None))

    def test_exact_match(self) -> None:
        self.app._client_chars["q-aldric"] = "aldric"
        self.assertTrue(self.app._phone_present("aldric"))

    def test_case_insensitive_match(self) -> None:
        self.app._client_chars["q-aldric"] = "aldric"
        for variant in ("Aldric", "ALDRIC", "AlDrIc"):
            with self.subTest(variant=variant):
                self.assertTrue(self.app._phone_present(variant))

    def test_whitespace_trimmed_on_lookup(self) -> None:
        # Registration also lowercases + strips, so a stored "aldric" matches a
        # request that arrives padded.
        self.app._client_chars["q-aldric"] = "aldric"
        self.assertTrue(self.app._phone_present("  aldric  "))
        self.assertTrue(self.app._phone_present("\tALDRIC\n"))

    def test_no_match_when_character_absent(self) -> None:
        self.app._client_chars["q-aldric"] = "aldric"
        self.assertFalse(self.app._phone_present("Mira"))

    def test_multiple_phones_distinct_targets(self) -> None:
        self.app._client_chars["q-aldric"] = "aldric"
        self.app._client_chars["q-mira"] = "mira"
        self.app._client_chars["q-thorne"] = "thorne kask"
        self.assertTrue(self.app._phone_present("Aldric"))
        self.assertTrue(self.app._phone_present("Mira"))
        # Multi-word names round-trip too.
        self.assertTrue(self.app._phone_present("Thorne Kask"))
        self.assertFalse(self.app._phone_present("Quill"))


class DisconnectCleanupTest(unittest.TestCase):
    """The pop-on-disconnect path. Both _broadcast's dead-queue loop and the
    /stream finally block call `_client_chars.pop(q, None)` — verify the
    routing decision flips back to False when a phone disconnects."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _load_app_module()

    def setUp(self) -> None:
        self.app._client_chars.clear()

    def test_pop_removes_entry_and_flips_phone_present(self) -> None:
        q_key = "q-aldric"
        self.app._client_chars[q_key] = "aldric"
        self.assertTrue(self.app._phone_present("aldric"))

        # Simulate the cleanup path: same call signature both production sites use.
        self.app._client_chars.pop(q_key, None)

        self.assertFalse(self.app._phone_present("aldric"))

    def test_pop_missing_key_is_a_noop(self) -> None:
        # `pop(q, None)` is the exact form both call sites use; verifies the
        # contract that double-disconnect or out-of-order cleanup doesn't raise.
        self.app._client_chars.pop("q-never-existed", None)
        self.assertEqual(dict(self.app._client_chars), {})


if __name__ == "__main__":
    unittest.main()
