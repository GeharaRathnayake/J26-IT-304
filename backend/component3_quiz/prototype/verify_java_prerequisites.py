
from neo4j_knowledge_graph import JavaKnowledgeGraph

graph = JavaKnowledgeGraph()

try:
    graph.verify_connection()

    records, _, _ = graph.driver.execute_query(
        """
        MATCH (a:Concept)-[:PREREQUISITE_FOR]->(b:Concept)
        RETURN count(*) AS total
        """,
        database_="neo4j",
    )

    print("Total prerequisite relationships:", records[0]["total"])

    records, _, _ = graph.driver.execute_query(
        """
        MATCH (a:Concept)-[:PREREQUISITE_FOR]->(b:Concept)
        RETURN a.name AS prerequisite,
               a.module_name AS source_module,
               b.name AS next_concept,
               b.module_name AS target_module
        ORDER BY source_module, prerequisite
        LIMIT 10
        """,
        database_="neo4j",
    )

    print("\nFirst 10 relationships:")

    for record in records:
        print(
            f"{record['source_module']}: {record['prerequisite']} "
            f"-> {record['target_module']}: {record['next_concept']}"
        )

finally:
    graph.close()
