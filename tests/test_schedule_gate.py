import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
from schedule_gate import should_run

class ScheduleGateTests(unittest.TestCase):
    def test_manual_and_push_outside_window(self):
        now=datetime.fromisoformat("2026-11-26T03:00:00+00:00")
        self.assertTrue(should_run("push",now)[0])
        self.assertTrue(should_run("workflow_dispatch",now)[0])
    def test_november_window(self):
        # Invierno: 07:00 UTC = 08:00 Madrid.
        self.assertFalse(should_run("schedule",datetime.fromisoformat("2026-11-26T06:59:00+00:00"))[0])
        self.assertTrue(should_run("schedule",datetime.fromisoformat("2026-11-26T07:07:00+00:00"))[0])
        self.assertTrue(should_run("schedule",datetime.fromisoformat("2026-11-26T20:52:00+00:00"))[0])
        self.assertFalse(should_run("schedule",datetime.fromisoformat("2026-11-26T21:07:00+00:00"))[0])
    def test_summer_window(self):
        # Verano: 06:00 UTC = 08:00 Madrid.
        self.assertFalse(should_run("schedule",datetime.fromisoformat("2027-07-01T05:52:00+00:00"))[0])
        self.assertTrue(should_run("schedule",datetime.fromisoformat("2027-07-01T06:07:00+00:00"))[0])
        self.assertTrue(should_run("schedule",datetime.fromisoformat("2027-07-01T19:52:00+00:00"))[0])
        self.assertFalse(should_run("schedule",datetime.fromisoformat("2027-07-01T20:07:00+00:00"))[0])
    def test_deduplicate_same_hour_only(self):
        now=datetime.fromisoformat("2026-11-26T11:22:00+00:00")
        checked=datetime.fromisoformat("2026-11-26T11:07:00+00:00")
        self.assertFalse(should_run("schedule",now,checked)[0])
        following=datetime.fromisoformat("2026-11-26T12:07:00+00:00")
        self.assertTrue(should_run("schedule",following,checked)[0])
    def test_missing_public_status_fails_open(self):
        now=datetime.fromisoformat("2026-11-26T11:52:00+00:00")
        self.assertTrue(should_run("schedule",now,None)[0])
    def test_autumn_fallback_second_02_hour(self):
        # Horario ambiguo de otoño (02:30 dos veces): la hora Madrid se calcula.
        first=datetime.fromisoformat("2027-10-31T00:30:00+00:00")
        second=datetime.fromisoformat("2027-10-31T01:30:00+00:00")
        self.assertFalse(should_run("schedule",first)[0])
        self.assertFalse(should_run("schedule",second)[0])
