import unittest

from media_progress import format_duration, progress_fraction


class ProgressTests(unittest.TestCase):
    def test_formats_track_time(self):
        self.assertEqual(format_duration(84.9), "1:24")
        self.assertEqual(format_duration(0), "0:00")
        self.assertEqual(format_duration(float("inf")), "0:00")
        self.assertEqual(format_duration(float("nan")), "0:00")

    def test_clamps_invalid_progress(self):
        self.assertEqual(progress_fraction(-1, 240), 0)
        self.assertEqual(progress_fraction(480, 240), 1)
        self.assertEqual(progress_fraction("bad", 240), 0)


if __name__ == "__main__":
    unittest.main()
