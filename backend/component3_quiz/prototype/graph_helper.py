import json
from pathlib import Path
from collections import defaultdict, deque

BASE = Path(__file__).parent
GRAPH_FILE = BASE / "java_concept_graph.json"


def load_graph():
    with GRAPH_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_concept_node(graph, module_no, concept_tag):
    """Find a concept belonging to the specified Java module."""
    for node in graph["nodes"]:
        if (
            node.get("node_type") == "concept"
            and node.get("module_no") == module_no
            and node.get("concept_tag") == concept_tag
        ):
            return node
    return None


def expand_weak_concepts(module_no, weak_tags, max_related=5):
    """
    Return weak concepts first, followed by connected concepts
    in the same module. Does not modify the graph.
    """
    graph = load_graph()
    nodes = {
        node["id"]: node
        for node in graph["nodes"]
    }

    # Build concept-to-concept connections.
    adjacency = defaultdict(list)

    for edge in graph["edges"]:
        source = edge.get("from")
        target = edge.get("to")
        relation = edge.get("relation")

        if relation not in ("prerequisite", "related"):
            continue

        source_node = nodes.get(source, {})
        target_node = nodes.get(target, {})

        if (
            source_node.get("node_type") != "concept"
            or target_node.get("node_type") != "concept"
        ):
            continue

        if (
            source_node.get("module_no") != module_no
            or target_node.get("module_no") != module_no
        ):
            continue

        adjacency[source].append(target)
        adjacency[target].append(source)

    # Keep the original weak concepts in their input order.
    results = []
    seen_tags = set()

    for tag in weak_tags:
        if tag not in seen_tags:
            results.append(tag)
            seen_tags.add(tag)

    # Expand one connection at a time, preserving weak concepts first.
    queue = deque()
    visited_nodes = set()

    for tag in results:
        node = find_concept_node(graph, module_no, tag)
        if node:
            visited_nodes.add(node["id"])
            queue.append(node["id"])

    added = 0

    while queue and added < max_related:
        current = queue.popleft()

        for neighbour_id in adjacency[current]:
            if neighbour_id in visited_nodes:
                continue

            visited_nodes.add(neighbour_id)
            queue.append(neighbour_id)

            neighbour = nodes[neighbour_id]
            tag = neighbour.get("concept_tag")

            if tag and tag not in seen_tags:
                results.append(tag)
                seen_tags.add(tag)
                added += 1

                if added >= max_related:
                    break

    return results


if __name__ == "__main__":
    graph = load_graph()
    print("Graph loaded successfully.")
    print("Nodes:", len(graph["nodes"]))
    print("Edges:", len(graph["edges"]))

    test_tags = expand_weak_concepts(
        module_no=1,
        weak_tags=["declaration"],
        max_related=5,
    )

    print("\nTest: Module 1, weak concept = declaration")
    print("Concepts returned:", test_tags)
