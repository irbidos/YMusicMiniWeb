import unittest

from web_player import PROGRESS_SCRIPT, SEEK_PROGRESS_SCRIPT


class NativeSeekScriptTests(unittest.TestCase):
    def test_uses_yandex_native_timecode_control(self):
        selector = 'aria-label="Управление таймкодом"'
        self.assertIn(selector, PROGRESS_SCRIPT)
        self.assertIn(selector, SEEK_PROGRESS_SCRIPT)

    def test_does_not_seek_media_element_directly(self):
        self.assertNotIn("currentTime=", SEEK_PROGRESS_SCRIPT)
        self.assertIn("dispatchEvent(new Event('input'", SEEK_PROGRESS_SCRIPT)
        self.assertIn("dispatchEvent(new Event('change'", SEEK_PROGRESS_SCRIPT)

    def test_uses_native_slider_value_as_time_scale(self):
        self.assertIn("Number(slider.value)", PROGRESS_SCRIPT)
        self.assertIn("Number(slider.max)", PROGRESS_SCRIPT)
        self.assertIn("Number(slider.max)*ratio", SEEK_PROGRESS_SCRIPT)


if __name__ == "__main__":
    unittest.main()
