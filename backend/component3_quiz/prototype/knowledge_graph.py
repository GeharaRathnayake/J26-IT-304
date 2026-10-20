
"""knowledge_graph.py
Java learning concepts and their prerequisite relationships.
Uses only Python's standard library.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
GRAPH_PATH = BASE_DIR / "java_knowledge_graph.json"

MODULES = [
    {
        "module_no": 1,
        "module_name": "Variables",
        "concepts": [
            "declaration",
            "initialization",
            "naming",
            "variable_types",
            "default_values",
            "scope",
        ],
        "prerequisites": [],
    },
    {
        "module_no": 2,
        "module_name": "Data Types",
        "concepts": [
            "primitive_types",
            "reference_types",
            "typecasting",
            "type_conversion",
        ],
        "prerequisites": [1],
    },
    {
        "module_no": 3,
        "module_name": "Operators",
        "concepts": [
            "arithmetic_operators",
            "comparison_operators",
            "logical_operators",
            "assignment_operators",
        ],
        "prerequisites": [1, 2],
    },
    {
        "module_no": 4,
        "module_name": "Control Flow",
        "concepts": [
            "if_else",
            "switch",
            "conditional_logic",
        ],
        "prerequisites": [1, 2, 3],
    },
    {
        "module_no": 5,
        "module_name": "Loops",
        "concepts": [
            "for_loop",
            "while_loop",
            "do_while_loop",
            "nested_loops",
            "break_continue",
        ],
        "prerequisites": [1, 3, 4],
    },
    {
        "module_no": 6,
        "module_name": "Arrays",
        "concepts": [
            "array_declaration",
            "array_initialization",
            "array_access",
            "multidimensional_arrays",
        ],
        "prerequisites": [1, 2, 5],
    },
    {
        "module_no": 7,
        "module_name": "Methods",
        "concepts": [
            "method_declaration",
            "parameters_arguments",
            "return_values",
            "method_overloading",
        ],
        "prerequisites": [1, 2, 3, 4],
    },
    {
        "module_no": 8,
        "module_name": "Classes and Objects",
        "concepts": [
            "class_declaration",
            "object_creation",
            "constructors",
            "encapsulation",
        ],
        "prerequisites": [1, 2, 7],
    },
    {
        "module_no": 9,
        "module_name": "Inheritance",
        "concepts": [
            "extends_keyword",
            "method_overriding",
            "super_keyword",
        ],
        "prerequisites": [8],
    },
    {
        "module_no": 10,
        "module_name": "Polymorphism",
        "concepts": [
            "runtime_polymorphism",
            "dynamic_method_dispatch",
            "polymorphic_references",
        ],
        "prerequisites": [8, 9],
    },
]


def build_graph():
    """Build and save the module/concept prerequisite graph."""
    modules_by_id = {item["module_no"]: item for item in MODULES}

    graph = {
        "title": "Java Programming Knowledge Graph",
        "modules": MODULES,
        "edges": [
            {
                "from_module": prerequisite,
                "to_module": module["module_no"],
                "relationship": "prerequisite_of",
            }
            for module in MODULES
            for prerequisite in module["prerequisites"]
            if prerequisite in modules_by_id
        ],
    }

    GRAPH_PATH.write_text(
        json.dumps(graph, indent=2),
        encoding="utf-8",
    )
    return graph


def get_module(module_no):
    """Return a module definition, or None if it does not exist."""
    for module in MODULES:
        if module["module_no"] == int(module_no):
            return module
    return None


def get_concepts(module_no):
    """Return the concepts belonging to a module."""
    module = get_module(module_no)
    return list(module["concepts"]) if module else []


def get_prerequisite_modules(module_no):
    """Return prerequisite module numbers."""
    module = get_module(module_no)
    return list(module["prerequisites"]) if module else []


def find_concept_module(concept):
    """Find the module containing a concept."""
    target = str(concept).strip().casefold()

    for module in MODULES:
        for item in module["concepts"]:
            if item.casefold() == target:
                return module["module_no"]

    return None


if __name__ == "__main__":
    graph = build_graph()

    print(f"Knowledge graph saved to: {GRAPH_PATH}")
    print(f"Modules: {len(graph['modules'])}")
    print(f"Prerequisite relationships: {len(graph['edges'])}")

    print("\nModule 1 concepts:")
    print(get_concepts(1))

    print("\nPrerequisites for Polymorphism:")
    print(get_prerequisite_modules(10))
