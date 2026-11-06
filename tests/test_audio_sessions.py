import unittest

from audio_sessions import find_matching_audio_session


class _Control:
    def __init__(self, pid):
        self.pid = pid

    def GetProcessId(self):
        return self.pid


class _Session:
    def __init__(self, pid):
        self._ctl = _Control(pid)


class AudioSessionMatchingTests(unittest.TestCase):
    def test_returns_only_session_owned_by_music_process_tree(self):
        sessions = [_Session(111), _Session(222)]

        result = find_matching_audio_session(sessions, {222})

        self.assertIs(result, sessions[1])

    def test_does_not_fall_back_to_unrelated_webview_session(self):
        sessions = [_Session(111), _Session(222)]

        result = find_matching_audio_session(sessions, set())

        self.assertIsNone(result)

    def test_rejects_ambiguous_matching_sessions(self):
        sessions = [_Session(222), _Session(333)]

        result = find_matching_audio_session(sessions, {222, 333})

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
