"""Offline payload regressions: python scripts/test_calendar_writer_description.py."""

import unittest

from personal_os_calendar_writer import TASK_URL_BASE, event_body


class DescriptionTests(unittest.TestCase):
    def body(self, description=None):
        return event_body(
            {
                "task_id": "abc-123",
                "title": "Test Kalendář",
                "description": description,
                "starts_at": "2026-10-25T09:00:00+01:00",
                "ends_at": "2026-10-25T10:00:00+01:00",
            }
        )

    def test_empty_description_only_has_one_named_link(self):
        description = self.body()["description"]
        self.assertEqual(
            description,
            f'<a href="{TASK_URL_BASE}?task=abc-123">Otevřít úkol v Personal OS</a>',
        )

    def test_legacy_duplicate_links_are_removed(self):
        body = self.body(
            "Domluvit dopravu.\n\nPersonal OS task: /tasks?task=abc-123\n\nPersonal OS task: "
            + TASK_URL_BASE
            + "?task=abc-123"
        )
        self.assertNotIn("Personal OS task:", body["description"])
        self.assertEqual(body["description"].count("href="), 1)
        self.assertTrue(body["description"].startswith("Domluvit dopravu.<br><br>"))
        self.assertEqual(body["summary"], "Test Kalendář")
        self.assertEqual(body["start"]["dateTime"], "2026-10-25T09:00:00+01:00")

    def test_user_text_is_escaped_and_linebreaks_preserved(self):
        text = self.body("Rozměry <okna> & dveře\nDruhý řádek")["description"]
        self.assertIn("Rozměry &lt;okna&gt; &amp; dveře<br>Druhý řádek", text)

    def test_other_task_reference_is_preserved(self):
        self.assertIn(
            "Personal OS task: /tasks?task=other",
            self.body("Personal OS task: /tasks?task=other")["description"],
        )


if __name__ == "__main__":
    unittest.main()
