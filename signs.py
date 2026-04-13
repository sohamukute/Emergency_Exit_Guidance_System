# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Sign Logic (delegates to decision.py)
# ─────────────────────────────────────────────

from decision import compute_signs as _compute_signs


def compute_signs(node_states: dict) -> dict:
    """Thin wrapper — delegates entirely to decision.compute_signs()."""
    return _compute_signs(node_states)
