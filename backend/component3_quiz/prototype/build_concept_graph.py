import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
QUESTIONS_FILE = BASE / "static_questions.json"
MODULE_GRAPH_FILE = BASE / "java_knowledge_graph.json"
OUTPUT_FILE = BASE / "java_concept_graph.json"

REL = {"P": "prerequisite", "R": "related"}

# Relationships within each module:
# (module_number, source_concept, target_concept, relationship)
WITHIN = [
    (1, "declaration", "initialization", "P"),
    (1, "initialization", "assignment", "P"),
    (1, "assignment", "reassignment", "P"),
    (1, "declaration", "naming", "P"),
    (1, "naming", "naming_convention", "P"),
    (1, "initialization", "constants", "P"),
    (1, "declaration", "default_values", "P"),
    (1, "declaration", "variable_types", "P"),
    (1, "variable_types", "type_inference", "P"),
    (1, "declaration", "scope", "P"),
    (1, "scope", "shadowing", "P"),

    (2, "primitive_types", "integer_types", "P"),
    (2, "primitive_types", "floating_point", "P"),
    (2, "primitive_types", "char_type", "P"),
    (2, "primitive_types", "boolean_type", "P"),
    (2, "integer_types", "overflow", "P"),
    (2, "floating_point", "precision", "P"),
    (2, "primitive_types", "literals", "P"),
    (2, "primitive_types", "casting", "P"),
    (2, "casting", "promotion", "P"),
    (2, "primitive_types", "wrappers", "P"),
    (2, "char_type", "string_type", "R"),

    (3, "arithmetic", "increment", "P"),
    (3, "arithmetic", "compound", "P"),
    (3, "arithmetic", "precedence", "P"),
    (3, "relational", "logical", "P"),
    (3, "relational", "ternary", "P"),
    (3, "arithmetic", "concat", "R"),
    (3, "logical", "bitwise", "R"),

    (4, "conditions", "if_else", "P"),
    (4, "if_else", "else_if", "P"),
    (4, "if_else", "nested_if", "P"),
    (4, "conditions", "switch", "P"),
    (4, "switch", "fallthrough", "P"),
    (4, "switch", "modern_switch", "P"),

    (5, "while_loop", "do_while", "P"),
    (5, "for_loop", "enhanced_for", "P"),
    (5, "for_loop", "nested_loops", "P"),
    (5, "nested_loops", "patterns", "P"),
    (5, "while_loop", "infinite_loop", "P"),
    (5, "for_loop", "off_by_one", "P"),
    (5, "for_loop", "break_continue", "R"),
    (5, "for_loop", "string_loop", "R"),

    (6, "array_declaration", "initializer", "P"),
    (6, "array_declaration", "indexing", "P"),
    (6, "indexing", "array_length", "P"),
    (6, "array_length", "traversal", "P"),
    (6, "traversal", "array_algorithms", "P"),
    (6, "array_declaration", "array_reference", "P"),
    (6, "array_declaration", "array_2d", "P"),
    (6, "array_declaration", "default_values", "P"),
    (6, "traversal", "arrays_class", "R"),
    (6, "array_reference", "array_methods", "R"),

    (7, "method_basics", "parameters", "P"),
    (7, "parameters", "return", "P"),
    (7, "parameters", "pass_by_value", "P"),
    (7, "method_basics", "method_scope", "P"),
    (7, "method_basics", "overloading", "P"),
    (7, "method_basics", "static_methods", "P"),
    (7, "parameters", "varargs", "P"),
    (7, "return", "recursion", "P"),

    (8, "class_basics", "fields_methods", "P"),
    (8, "class_basics", "constructors", "P"),
    (8, "constructors", "object_creation", "P"),
    (8, "class_basics", "this_keyword", "P"),
    (8, "class_basics", "encapsulation", "P"),
    (8, "object_creation", "references", "P"),
    (8, "class_basics", "static_members", "P"),
    (8, "object_creation", "object_methods", "P"),

    (9, "extends", "inheritance_types", "P"),
    (9, "extends", "is_a", "P"),
    (9, "extends", "super", "P"),
    (9, "super", "constructor_order", "P"),
    (9, "extends", "overriding", "P"),
    (9, "extends", "inheritance_access", "P"),
    (9, "extends", "abstract", "P"),
    (9, "extends", "object_class", "P"),
    (9, "extends", "casting_objects", "P"),
    (9, "extends", "terminology", "R"),

    (10, "overriding", "polymorphism", "P"),
    (10, "reference_types", "polymorphism", "P"),
    (10, "polymorphism", "poly_usage", "P"),
    (10, "polymorphism", "abstract_poly", "P"),
    (10, "polymorphism", "casting_poly", "P"),
    (10, "polymorphism", "non_polymorphic", "R"),
    (10, "polymorphism", "interfaces", "R"),
]

# Relationships connecting concepts in different modules.
# (source_module, source_tag, target_module, target_tag, relationship)
CROSS = [
    (3, "relational", 4, "conditions", "P"),
    (4, "conditions", 5, "while_loop", "P"),
    (5, "for_loop", 6, "traversal", "P"),
    (1, "scope", 7, "method_scope", "P"),
    (7, "parameters", 8, "constructors", "P"),
    (8, "class_basics", 9, "extends", "P"),
    (9, "overriding", 10, "overriding", "P"),
    (7, "overloading", 10, "overloading", "R"),
    (2, "casting", 9, "casting_objects", "R"),
    (1, "default_values", 6, "default_values", "R"),
    (6, "array_reference", 8, "references", "R"),
]


def main():
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Missing question bank: {QUESTIONS_FILE.name}"
        )

    if not MODULE_GRAPH_FILE.exists():
        raise FileNotFoundError(
            f"Missing original module graph: {MODULE_GRAPH_FILE.name}"
        )

    # Safety: do not silently replace a graph from an earlier run.
    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"{OUTPUT_FILE.name} already exists. "
            "Inspect or back it up before running again."
        )

    with QUESTIONS_FILE.open(encoding="utf-8-sig") as f:
        questions = json.load(f)

    with MODULE_GRAPH_FILE.open(encoding="utf-8-sig") as f:
        old_graph = json.load(f)

    old_nodes = old_graph["nodes"]
    old_edges = old_graph["edges"]

    module_by_number = {
        node["module"]: node for node in old_nodes
    }
    id_to_module = {
        node["id"]: node["module"] for node in old_nodes
    }

    # Count questions for every module-specific concept.
    counts = Counter(
        (q["module_no"], q["concept_tag"]) for q in questions
    )
    known = set(counts)

    def concept_id(module_no, tag):
        return f"m{module_no}_{tag}"

    # Recreate module nodes in the new file, without changing the original.
    nodes = [
        {
            "id": f"module_{node['module']}",
            "name": node["name"],
            "node_type": "module",
            "module_no": node["module"],
        }
        for node in old_nodes
    ]
    nodes.sort(key=lambda node: node["module_no"])

    # Add one concept node per module-specific concept tag.
    for (module_no, tag), count in sorted(counts.items()):
        if module_no not in module_by_number:
            raise ValueError(
                f"Question bank contains unknown module {module_no}"
            )

        nodes.append({
            "id": concept_id(module_no, tag),
            "name": tag.replace("_", " ").title(),
            "node_type": "concept",
            "concept_tag": tag,
            "module_no": module_no,
            "question_count": count,
        })

    # Link each module to its concepts.
    edges = [
        {
            "from": f"module_{module_no}",
            "to": concept_id(module_no, tag),
            "relation": "contains_concept",
        }
        for module_no, tag in sorted(known)
    ]

    # Preserve every original module edge and relationship type exactly.
    for edge in old_edges:
        source_module = id_to_module[edge["from"]]
        target_module = id_to_module[edge["to"]]

        edges.append({
            "from": f"module_{source_module}",
            "to": f"module_{target_module}",
            "relation": edge["relation"],
        })

    connected = set()
    missing = []
    added_concept_edges = set()

    def add_relationship(m1, tag1, m2, tag2, relation_code):
        source = (m1, tag1)
        target = (m2, tag2)

        if source not in known or target not in known:
            missing.append({
                "from": f"m{m1}_{tag1}",
                "to": f"m{m2}_{tag2}",
                "missing": [
                    f"m{m}_{tag}"
                    for m, tag in (source, target)
                    if (m, tag) not in known
                ],
            })
            return

        edge = {
            "from": concept_id(m1, tag1),
            "to": concept_id(m2, tag2),
            "relation": REL[relation_code],
        }

        # Avoid adding identical edges twice.
        edge_key = (edge["from"], edge["to"], edge["relation"])
        if edge_key not in added_concept_edges:
            edges.append(edge)
            added_concept_edges.add(edge_key)

        connected.update((source, target))

    for module_no, source_tag, target_tag, relation in WITHIN:
        add_relationship(
            module_no, source_tag,
            module_no, target_tag,
            relation,
        )

    for m1, tag1, m2, tag2, relation in CROSS:
        add_relationship(m1, tag1, m2, tag2, relation)

    graph = {
        "metadata": {
            "question_count": len(questions),
            "module_count": len(old_nodes),
            "concept_count": len(known),
            "original_module_edge_count": len(old_edges),
            "concept_relationship_count": len(added_concept_edges),
        },
        "nodes": nodes,
        "edges": edges,
    }

    # Write only to the separate output file.
    with OUTPUT_FILE.open("x", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Saved:", OUTPUT_FILE.name)
    print("Questions:", len(questions))
    print("Module nodes:", len(old_nodes))
    print("Module-specific concept nodes:", len(known))
    print("Total nodes:", len(nodes))
    print("Original module edges preserved:", len(old_edges))
    print("Concept-to-module edges:", len(known))
    print("Concept relationships added:", len(added_concept_edges))
    print("Total edges:", len(edges))
    print("Edge types:", dict(Counter(e["relation"] for e in edges)))

    if missing:
        print("\nWARNING: Unmatched relationships:")
        for item in missing:
            print(
                f"  {item['from']} -> {item['to']}; "
                f"missing: {', '.join(item['missing'])}"
            )
    else:
        print("\nRelationship tag validation: all matched.")

    loose = sorted(
        concept_id(module_no, tag)
        for module_no, tag in known
        if (module_no, tag) not in connected
    )
    print(
        f"Concepts without concept-to-concept links ({len(loose)}):",
        loose,
    )

    print("\nOriginal module graph was not modified.")


if __name__ == "__main__":
    main()
