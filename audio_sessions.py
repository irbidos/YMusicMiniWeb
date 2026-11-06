"""Helpers for selecting the audio session owned by the music WebView2."""


def find_matching_audio_session(sessions, process_ids):
    """Return an unambiguous session whose process belongs to ``process_ids``.

    Never falls back to an arbitrary WebView2 session: another WebView2 app may
    be playing audio at the same time.
    """
    matches = []
    wanted = set(process_ids)
    for session in sessions:
        try:
            pid = int(session._ctl.GetProcessId())
        except (AttributeError, TypeError, ValueError):
            continue
        if pid in wanted:
            matches.append(session)
    return matches[0] if len(matches) == 1 else None
