
CRITERIA = (
    "business_value",
    "urgency",
    "customer_impact",
    "risk_reduction",
    "strategic_alignment",
)

CRITERION_LABELS = {
    "business_value": "Business Value",
    "urgency": "Urgency",
    "customer_impact": "Customer Impact",
    "risk_reduction": "Risk Reduction",
    "strategic_alignment": "Strategic Alignment",
}


def calculate_priority(story, weights):
    if set(weights.keys()) != set(CRITERIA):
        raise ValueError(
            "Configure a weight for all five priority criteria."
        )

    for criterion in CRITERIA:
        weight = weights[criterion]

        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError(f"Invalid weight for {criterion}.")

        if not 0 <= weight <= 100:
            raise ValueError(
                f"Weight for {criterion} must be between 0 and 100."
            )

    if abs(sum(weights.values()) - 100) > 0.01:
        raise ValueError("Priority weights must total 100%.")

    weighted_rating = 0

    for criterion in CRITERIA:
        rating = story[criterion]

        if isinstance(rating, bool) or not isinstance(rating, int):
            raise ValueError(
                f"{criterion} rating must be an integer."
            )

        if not 1 <= rating <= 10:
            raise ValueError(
                f"{criterion} rating must be between 1 and 10."
            )

        weighted_rating += rating * weights[criterion] / 100

    score = ((weighted_rating - 1) / 9) * 100

    return {
        "score": round(score, 2),
        "weighted_rating": round(weighted_rating, 2),
    }


def explain_priority(story, weights):
    """
    Explain how each criterion contributes to a work item's
    overall priority score.
    """

    result = calculate_priority(story, weights)

    contributions = []

    for criterion in CRITERIA:
        rating = story[criterion]
        weight = weights[criterion]

        contributions.append({
            "criterion": criterion,
            "label": CRITERION_LABELS[criterion],
            "rating": rating,
            "weight": round(weight, 2),
            "contribution": round(rating * weight / 100, 2),
        })

    contributions.sort(
        key=lambda item: item["contribution"],
        reverse=True,
    )

    strongest = contributions[0]
    weakest = contributions[-1]

    high_factors = [
        item["label"]
        for item in contributions
        if item["rating"] >= 8
    ]

    low_factors = [
        item["label"]
        for item in contributions
        if item["rating"] <= 3
    ]

    explanation_parts = [
        (
            f"{strongest['label']} is the strongest weighted "
            f"contributor, contributing {strongest['contribution']:.2f} "
            "points to the weighted rating."
        )
    ]

    if high_factors:
        explanation_parts.append(
            "High-rated factors: " + ", ".join(high_factors) + "."
        )

    if low_factors:
        explanation_parts.append(
            "Areas with low ratings: " + ", ".join(low_factors) + "."
        )

    explanation_parts.append(
        f"The overall priority score is {result['score']:.2f}/100."
    )

    return {
        **result,
        "contributions": contributions,
        "strongest_factor": strongest["label"],
        "weakest_factor": weakest["label"],
        "high_factors": high_factors,
        "low_factors": low_factors,
        "explanation": " ".join(explanation_parts),
    }
