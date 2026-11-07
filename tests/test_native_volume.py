import unittest

from web_player import GET_VOLUME_SCRIPT, SET_VOLUME_SCRIPT


class NativeVolumeScriptTests(unittest.TestCase):
    def test_reads_yandex_native_volume_slider(self):
        self.assertIn('aria-label="Управление громкостью"', GET_VOLUME_SCRIPT)
        self.assertIn("slider.value", GET_VOLUME_SCRIPT)

    def test_sets_volume_through_native_slider_events(self):
        self.assertIn('aria-label="Управление громкостью"', SET_VOLUME_SCRIPT)
        self.assertIn("dispatchEvent(new Event('input'", SET_VOLUME_SCRIPT)
        self.assertIn("dispatchEvent(new Event('change'", SET_VOLUME_SCRIPT)
        self.assertNotIn("SetMasterVolume", SET_VOLUME_SCRIPT)


if __name__ == "__main__":
    unittest.main()
