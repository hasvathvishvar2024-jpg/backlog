
def plan_sprint(items, capacity):
    """
    Select work items for a sprint without exceeding capacity.

    Each item must contain:
    id, title, state, story_points, priority_score, depends_on.

    Dependencies are prerequisite item IDs.
    """

    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("Sprint capacity must be a whole number.")

    if capacity <= 0:
        raise ValueError("Sprint capacity must be greater than zero.")

    item_by_id = {item["id"]: item for item in items}

    if len(item_by_id) != len(items):
        raise ValueError("Work item IDs must be unique.")

    for item in items:
        points = item["story_points"]
        score = item["priority_score"]

        if isinstance(points, bool) or not isinstance(points, int):
            raise ValueError("Story points must be whole numbers.")

        if points <= 0:
            raise ValueError("Story points must be greater than zero.")

        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("Priority scores must be numeric.")

        if not 0 <= score <= 100:
            raise ValueError("Priority scores must be between 0 and 100.")

        for dependency_id in item.get("depends_on", []):
            if dependency_id not in item_by_id:
                raise ValueError(
                    f"Missing dependency {dependency_id}."
                )

            if dependency_id == item["id"]:
                raise ValueError(
                    f"Item {item['id']} cannot depend on itself."
                )

    # Reject circular dependencies before planning
    visiting = set()
    visited = set()

    def visit(item_id):
        if item_id in visiting:
            raise ValueError("Circular dependencies detected.")

        if item_id in visited:
            return

        visiting.add(item_id)

        for dependency_id in item_by_id[item_id].get("depends_on", []):
            visit(dependency_id)

        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in item_by_id:
        visit(item_id)

    # Consider higher-priority items first
    candidates = [
        item for item in items
        if item["state"] != "Done"
    ]

    candidates.sort(
        key=lambda item: (
            -item["priority_score"],
            item["story_points"],
            item["id"],
        )
    )

    selected = {}
    used_capacity = 0

    for item in candidates:
        # Collect unfinished prerequisites recursively
        bundle = set()
        stack = [item["id"]]
        feasible = True

        while stack:
            current_id = stack.pop()

            if current_id in bundle or current_id in selected:
                continue

            current = item_by_id[current_id]

            if current["state"] == "Done":
                continue

            bundle.add(current_id)

            for dependency_id in current.get("depends_on", []):
                dependency = item_by_id[dependency_id]

                if dependency["state"] != "Done":
                    stack.append(dependency_id)

        additional_points = sum(
            item_by_id[item_id]["story_points"]
            for item_id in bundle
        )

        if used_capacity + additional_points > capacity:
            feasible = False

        if not feasible:
            continue

        for item_id in bundle:
            selected[item_id] = item_by_id[item_id]

        used_capacity += additional_points

    chosen = list(selected.values())

    return {
        "stories": chosen,
        "total_points": used_capacity,
        "capacity": capacity,
        "remaining_capacity": capacity - used_capacity,
        "total_priority_score": round(
            sum(item["priority_score"] for item in chosen), 2
        ),
    }
