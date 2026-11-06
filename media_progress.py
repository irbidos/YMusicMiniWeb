"""Platform-independent helpers for displaying track progress."""


def format_duration(seconds):
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError, OverflowError):
        total = 0
    minutes, remaining = divmod(total, 60)
    return f"{minutes}:{remaining:02d}"


def progress_fraction(position, duration):
    try:
        position = float(position)
        duration = float(duration)
    except (TypeError, ValueError):
        return 0.0
    if duration <= 0:
        return 0.0
    return max(0.0, min(1.0, position / duration))
