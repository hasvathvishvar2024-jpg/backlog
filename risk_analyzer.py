
def analyze_sprint_risk(selected_items, capacity):
    """
    Assess sprint risk using transparent rules.

    Each selected item should contain:
    story_points and optionally blocked.
    """

    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("Capacity must be a whole number.")

    if capacity <= 0:
        raise ValueError("Capacity must be greater than zero.")

    total_points = 0

    for item in selected_items:
        points = item["story_points"]

        if isinstance(points, bool) or not isinstance(points, int):
            raise ValueError("Story points must be whole numbers.")

        if points <= 0:
            raise ValueError("Story points must be greater than zero.")

        total_points += points

    utilization = total_points / capacity
    reasons = []
    score = 0

    # Capacity utilization risk
    if total_points > capacity:
        score += 60
        reasons.append("Selected work exceeds sprint capacity.")
    elif utilization > 0.90:
        score += 30
        reasons.append("Sprint utilization exceeds 90%.")
    elif utilization > 0.75:
        score += 15
        reasons.append("Sprint utilization is relatively high.")

    # Blocked work risk
    blocked_count = sum(
        bool(item.get("blocked", False))
        for item in selected_items
    )

    if blocked_count:
        score += min(40, blocked_count * 20)
        reasons.append(
            f"{blocked_count} selected item(s) are marked blocked."
        )

    score = min(score, 100)

    if score >= 60:
        level = "High"
    elif score >= 30:
        level = "Medium"
    else:
        level = "Low"

    if not reasons:
        reasons.append(
            "No major risk indicators were detected by these rules."
        )

    return {
        "risk_score": score,
        "risk_level": level,
        "reasons": reasons,
        "total_points": total_points,
        "utilization_percent": round(utilization * 100, 2),
    }
