from difflib import SequenceMatcher


def thesis_changed(old: str, new: str, threshold: float = 0.85) -> bool:
    old = (old or "").strip()
    new = (new or "").strip()

    if not old or not new:
        return True

    ratio = SequenceMatcher(None, old, new).ratio()
    return ratio < threshold
