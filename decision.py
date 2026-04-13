# ─────────────────────────────────────────────
#  Emergency Exit Guidance System — Decision Logic
#
#  Centralises all cross-node, cross-floor sign routing.
#  Input:  dict of {node_id: {"risk": float, "status": str}}
#  Output: {"signs": {sign_id: state}, "alerts": [str]}
#
#  Sign states: "safe" | "caution" | "blocked" | "stairs"
# ─────────────────────────────────────────────

# Map each sign to the primary exit it points toward
SIGN_TARGETS: dict[str, str] = {
    # Floor 2
    "1L": "exit_A",   "1R": "mid_F2",
    "2L": "mid_F2",   "2R": "exit_B",
    # Floor 1
    "3L": "exit_C",   "3R": "mid_F1",
    "4L": "mid_F1",   "4R": "exit_D",
    # Ground
    "5L": "exit_E",   "5R": "main_exit",
    "6L": "main_exit","6R": "exit_F",
}

_UNSAFE  = {"DANGER", "CRITICAL", "SENSOR_ERROR"}
_CAUTION = {"CAUTION"}


def compute_signs(node_states: dict) -> dict:
    """
    Parameters
    ----------
    node_states : dict of {node_id: {"risk": float|None, "status": str}}

    Returns
    -------
    {"signs": dict[sign_id, state], "alerts": list[str]}
    """
    signs:  dict[str, str] = {}
    alerts: list[str]      = []

    def st(nid: str) -> str:
        return node_states.get(nid, {}).get("status", "SENSOR_ERROR")

    def bad(nid: str) -> bool:
        return st(nid) in _UNSAFE

    def caut(nid: str) -> bool:
        return st(nid) in _CAUTION

    # ── Base rule ─────────────────────────────────────────
    for sign, target in SIGN_TARGETS.items():
        if bad(target):
            signs[sign] = "blocked"
        elif caut(target):
            signs[sign] = "caution"
        else:
            signs[sign] = "safe"

    # ── Scenario 2: mid-corridor bad → block traversal ────
    if bad("mid_F2"):
        signs["1R"] = "blocked"
        signs["2L"] = "blocked"
    elif caut("mid_F2"):
        if signs["1R"] == "safe":
            signs["1R"] = "caution"
        if signs["2L"] == "safe":
            signs["2L"] = "caution"

    if bad("mid_F1"):
        signs["3R"] = "blocked"
        signs["4L"] = "blocked"
    elif caut("mid_F1"):
        if signs["3R"] == "safe":
            signs["3R"] = "caution"
        if signs["4L"] == "safe":
            signs["4L"] = "caution"

    # ── Scenario 3: one exit bad + mid caution → warn centre ──
    if bad("exit_A") and caut("mid_F2") and not bad("exit_B"):
        signs["1R"] = "caution"
        signs["2L"] = "caution"

    if bad("exit_B") and caut("mid_F2") and not bad("exit_A"):
        signs["1R"] = "caution"
        signs["2L"] = "caution"

    # ── Scenario 1: both floor exits bad → stairs ─────────
    if bad("exit_A") and bad("exit_B"):
        for s in ("1L", "1R", "2L", "2R"):
            signs[s] = "stairs"
        alerts.append("Floor 2: Both exits critical — USE STAIRS to Floor 1")

    if bad("exit_C") and bad("exit_D"):
        for s in ("3L", "3R", "4L", "4R"):
            signs[s] = "stairs"
        alerts.append("Floor 1: Both exits critical — USE STAIRS to Ground Floor")

    # ── Scenario 4: exit_D + exit_E both bad ──────────────
    if bad("exit_D") and bad("exit_E"):
        signs["4R"] = "blocked"
        signs["5L"] = "blocked"
        signs["5R"] = "safe"   if not bad("main_exit") else "blocked"
        signs["6L"] = "safe"   if not bad("main_exit") else "blocked"
        signs["6R"] = "safe"   if not bad("exit_F")    else "blocked"
        alerts.append(
            "Exit D (F1 right) + Exit E (GF left) blocked — use Main Exit or Exit F"
        )

    # ── Scenario 6: Main Exit bad ─────────────────────────
    if bad("main_exit"):
        signs["5R"] = "blocked"
        signs["6L"] = "blocked"
        signs["5L"] = "safe" if not bad("exit_E") else "blocked"
        signs["6R"] = "safe" if not bad("exit_F") else "blocked"
        if bad("exit_E") and bad("exit_F"):
            alerts.append(
                "CRITICAL: ALL GROUND EXITS COMPROMISED — shelter in place or ascend stairs"
            )

    # ── Scenario 5: full column failure ───────────────────
    if bad("exit_A") and bad("exit_C") and bad("exit_E"):
        for s in ("1L", "2L", "3L", "4L", "5L"):
            signs[s] = "blocked"
        alerts.append("Left evacuation column compromised — use RIGHT-side exits only")

    if bad("exit_B") and bad("exit_D") and bad("exit_F"):
        for s in ("1R", "2R", "3R", "4R", "6R"):
            signs[s] = "blocked"
        alerts.append("Right evacuation column compromised — use LEFT-side exits only")

    return {"signs": signs, "alerts": alerts}
