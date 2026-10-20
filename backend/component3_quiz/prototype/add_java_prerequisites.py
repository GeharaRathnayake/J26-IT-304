
from neo4j_knowledge_graph import JavaKnowledgeGraph


# Each pair means:
# (prerequisite module, prerequisite concept,
#  next module, next concept)

PREREQUISITES = [
    ("Variables", "declaration", "Variables", "initialization"),
    ("Variables", "initialization", "Variables", "assignment"),
    ("Variables", "assignment", "Variables", "reassignment"),
    ("Variables", "declaration", "Variables", "variable_types"),
    ("Variables", "variable_types", "Variables", "constants"),
    ("Data Types", "primitive_types", "Data Types", "integer_types"),
    ("Data Types", "primitive_types", "Data Types", "boolean_type"),
    ("Data Types", "primitive_types", "Data Types", "char_type"),
    ("Data Types", "primitive_types", "Data Types", "floating_point"),
    ("Data Types", "integer_types", "Data Types", "promotion"),
    ("Data Types", "promotion", "Data Types", "casting"),
    ("Data Types", "floating_point", "Data Types", "precision"),
    ("Variables", "variable_types", "Data Types", "casting"),
    ("Variables", "initialization", "Operators", "arithmetic"),
    ("Operators", "arithmetic", "Operators", "precedence"),
    ("Operators", "relational", "Operators", "logical"),
    ("Operators", "arithmetic", "Operators", "compound"),
    ("Operators", "arithmetic", "Operators", "increment"),
]


def main():
    graph = JavaKnowledgeGraph()

    try:
        graph.verify_connection()

        # Check every endpoint before creating any relationships.
        for from_module, from_concept, to_module, to_concept in PREREQUISITES:
            source_exists = graph.get_concepts(from_module)
            target_exists = graph.get_concepts(to_module)

            if from_concept not in source_exists:
                raise ValueError(
                    f"Missing source concept: {from_module}/{from_concept}"
                )

            if to_concept not in target_exists:
                raise ValueError(
                    f"Missing target concept: {to_module}/{to_concept}"
                )

        created = 0

        for from_module, from_concept, to_module, to_concept in PREREQUISITES:
            records, _, _ = graph.driver.execute_query(
                """
                MATCH (source:Concept {
                    name: $from_concept,
                    module_name: $from_module
                })
                MATCH (target:Concept {
                    name: $to_concept,
                    module_name: $to_module
                })
                MERGE (source)-[r:PREREQUISITE_FOR]->(target)
                RETURN count(r) AS relationship_count
                """,
                parameters_={
                    "from_module": from_module,
                    "from_concept": from_concept,
                    "to_module": to_module,
                    "to_concept": to_concept,
                },
                database_="neo4j",
            )
            created += records[0]["relationship_count"]

        print(f"Prerequisite relationships checked: {created}")
        print("Existing module and concept relationships were preserved.")

    finally:
        graph.close()


if __name__ == "__main__":
    main()
