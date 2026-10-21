
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
            "assignment",
            "constants",
            "declaration",
            "default_values",
            "initialization",
            "naming",
            "naming_convention",
            "reassignment",
            "scope",
            "shadowing",
            "type_inference",
            "variable_types",
        ],
        "prerequisites": [],
    },
    {
        "module_no": 2,
        "module_name": "Data Types",
        "concepts": [
            "boolean_type",
            "casting",
            "char_type",
            "floating_point",
            "integer_types",
            "literals",
            "overflow",
            "precision",
            "primitive_types",
            "promotion",
            "string_type",
            "wrappers",
        ],
        "prerequisites": [1],
    },
    {
        "module_no": 3,
        "module_name": "Operators",
        "concepts": [
            "arithmetic",
            "bitwise",
            "compound",
            "concat",
            "increment",
            "logical",
            "precedence",
            "relational",
            "ternary",
        ],
        "prerequisites": [1, 2],
    },
    {
        "module_no": 4,
        "module_name": "Control Flow",
        "concepts": [
            "conditions",
            "else_if",
            "fallthrough",
            "if_else",
            "modern_switch",
            "nested_if",
            "pitfalls",
            "structure",
            "switch",
            "tracing",
        ],
        "prerequisites": [1, 2, 3],
    },
    {
        "module_no": 5,
        "module_name": "Loops",
        "concepts": [
            "break_continue",
            "choice",
            "do_while",
            "enhanced_for",
            "for_loop",
            "infinite_loop",
            "nested_loops",
            "off_by_one",
            "patterns",
            "string_loop",
            "tracing",
            "while_loop",
        ],
        "prerequisites": [1, 3, 4],
    },
    {
        "module_no": 6,
        "module_name": "Arrays",
        "concepts": [
            "array_2d",
            "array_algorithms",
            "array_declaration",
            "array_length",
            "array_methods",
            "array_reference",
            "arrays_class",
            "default_values",
            "indexing",
            "initializer",
            "tracing",
            "traversal",
        ],
        "prerequisites": [1, 2, 5],
    },
    {
        "module_no": 7,
        "module_name": "Methods",
        "concepts": [
            "method_basics",
            "method_scope",
            "overloading",
            "parameters",
            "pass_by_value",
            "recursion",
            "return",
            "static_methods",
            "tracing",
            "varargs",
        ],
        "prerequisites": [1, 2, 3, 4],
    },
    {
        "module_no": 8,
        "module_name": "Classes and Objects",
        "concepts": [
            "class_basics",
            "constructors",
            "encapsulation",
            "fields_methods",
            "object_creation",
            "object_methods",
            "references",
            "static_members",
            "this_keyword",
            "tracing",
        ],
        "prerequisites": [1, 2, 7],
    },
    {
        "module_no": 9,
        "module_name": "Inheritance",
        "concepts": [
            "abstract",
            "casting_objects",
            "constructor_order",
            "extends",
            "inheritance_access",
            "inheritance_types",
            "is_a",
            "object_class",
            "overriding",
            "super",
            "terminology",
            "tracing",
        ],
        "prerequisites": [8],
    },
    {
        "module_no": 10,
        "module_name": "Polymorphism",
        "concepts": [
            "abstract_poly",
            "casting_poly",
            "interfaces",
            "non_polymorphic",
            "overloading",
            "overriding",
            "poly_usage",
            "polymorphism",
            "reference_types",
            "tracing",
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
