
from priority_engine import explain_priority

story = {
    "business_value": 9,
    "urgency": 8,
    "customer_impact": 10,
    "risk_reduction": 6,
    "strategic_alignment": 7,
}

weights = {
    "business_value": 30,
    "urgency": 20,
    "customer_impact": 25,
    "risk_reduction": 15,
    "strategic_alignment": 10,
}

result = explain_priority(story, weights)

print("Priority Score:", result["score"])
print("Strongest Factor:", result["strongest_factor"])
print("Explanation:", result["explanation"])

print("\nCriterion Contributions:")

for item in result["contributions"]:
    print(
        item["label"],
        "| Rating:", item["rating"],
        "| Weight:", item["weight"], "%",
        "| Contribution:", item["contribution"],
    )
