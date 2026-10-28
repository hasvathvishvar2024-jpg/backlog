
import networkx as nx


def analyze_dependencies(items):
    """
    Analyze backlog item dependencies.

    Each item must be a dictionary containing:
    id, title, state, and depends_on.

    depends_on contains IDs of prerequisite items.
    """

    item_by_id = {item["id"]: item for item in items}

    if len(item_by_id) != len(items):
        raise ValueError("Backlog item IDs must be unique.")

    graph = nx.DiGraph()
    graph.add_nodes_from(item_by_id.keys())

    # Build dependency graph
    for item in items:
        item_id = item["id"]

        for dependency_id in item.get("depends_on", []):
            if dependency_id not in item_by_id:
                raise ValueError(
                    f"Item {item_id} references missing dependency "
                    f"{dependency_id}."
                )

            if dependency_id == item_id:
                raise ValueError(
                    f"Item {item_id} cannot depend on itself."
                )

            # Prerequisite must be completed before this item
            graph.add_edge(dependency_id, item_id)

    # Detect circular dependencies
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError(
            "Circular dependencies detected. Resolve them before planning."
        )

    results = {}

    for item in items:
        blocked_by = []

        for dependency_id in item.get("depends_on", []):
            dependency = item_by_id[dependency_id]

            if dependency["state"] != "Done":
                blocked_by.append(dependency["title"])

        results[item["id"]] = {
            "blocked": bool(blocked_by),
            "blocked_by": blocked_by,
        }

    return results
