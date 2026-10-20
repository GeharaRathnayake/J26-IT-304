from neo4j_knowledge_graph import JavaKnowledgeGraph

graph = JavaKnowledgeGraph()

try:
    graph.verify_connection()

    print("Prerequisites for casting:")
    print(graph.get_prerequisites("Data Types", "casting"))

    print("\nConcepts that depend on arithmetic:")
    print(graph.get_dependent_concepts("Operators", "arithmetic"))

finally:
    graph.close()