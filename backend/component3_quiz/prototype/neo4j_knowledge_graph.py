
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).with_name(".env"))


class JavaKnowledgeGraph:
    """Read Java modules and concepts from the Neo4j knowledge graph."""

    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if not all([uri, username, password]):
            raise RuntimeError(
                "Neo4j settings are missing from the .env file."
            )

        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
        )

    def verify_connection(self):
        """Check whether Neo4j is reachable."""
        self.driver.verify_connectivity()
        return True

    def get_modules(self):
        """Return all module names stored in Neo4j."""
        records, _, _ = self.driver.execute_query(
            """
            MATCH (m:Module)
            RETURN m.name AS module
            ORDER BY module
            """,
            database_="neo4j",
        )
        return [record["module"] for record in records]

    def get_concepts(self, module_name):
        """Return concepts connected to a particular module."""
        records, _, _ = self.driver.execute_query(
            """
            MATCH (m:Module {name: $module_name})
                  -[:CONTAINS_CONCEPT]->(c:Concept)
            RETURN c.name AS concept
            ORDER BY concept
            """,
            parameters_={"module_name": module_name},
            database_="neo4j",
        )
        return [record["concept"] for record in records]
    def get_prerequisites(self, module_name, concept_name):
        """Return concepts that should be learned before this concept."""
        records, _, _ = self.driver.execute_query(
            """
            MATCH (a:Concept)-[:PREREQUISITE_FOR]->(b:Concept)
            WHERE b.module_name = $module_name
              AND b.name = $concept_name
            RETURN a.name AS concept,
                   a.module_name AS module
            ORDER BY module, concept
            """,
            parameters_={
                "module_name": module_name,
                "concept_name": concept_name,
            },
            database_="neo4j",
        )
        return [
            {"module": record["module"], "concept": record["concept"]}
            for record in records
        ]

    def get_dependent_concepts(self, module_name, concept_name):
        """Return concepts that depend on this concept."""
        records, _, _ = self.driver.execute_query(
            """
            MATCH (a:Concept)-[:PREREQUISITE_FOR]->(b:Concept)
            WHERE a.module_name = $module_name
              AND a.name = $concept_name
            RETURN b.name AS concept,
                   b.module_name AS module
            ORDER BY module, concept
            """,
            parameters_={
                "module_name": module_name,
                "concept_name": concept_name,
            },
            database_="neo4j",
        )
        return [
            {"module": record["module"], "concept": record["concept"]}
            for record in records
        ]

    def close(self):
        """Close the database connection."""
        self.driver.close()


if __name__ == "__main__":
    graph = JavaKnowledgeGraph()

    try:
        graph.verify_connection()
        print("Neo4j knowledge graph connected.")
        print("\nAvailable Java modules:")

        for module in graph.get_modules():
            concepts = graph.get_concepts(module)
            print(f"\n{module} ({len(concepts)} concepts)")
            print(", ".join(concepts))

    finally:
        graph.close()
