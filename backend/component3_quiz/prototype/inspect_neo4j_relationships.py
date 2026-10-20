
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).with_name(".env"))

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(
        os.getenv("NEO4J_USERNAME"),
        os.getenv("NEO4J_PASSWORD"),
    ),
)

try:
    driver.verify_connectivity()

    records, _, _ = driver.execute_query(
        """
        MATCH (a)-[r]->(b)
        RETURN labels(a) AS from_labels,
               coalesce(a.name, a.module_name) AS from_name,
               type(r) AS relationship,
               labels(b) AS to_labels,
               coalesce(b.name, b.module_name) AS to_name
        ORDER BY relationship, from_name, to_name
        LIMIT 100
        """,
        database_="neo4j",
    )

    print("Existing relationships:")
    for record in records:
        print(
            f"{record['from_labels']} {record['from_name']} "
            f"--[{record['relationship']}]--> "
            f"{record['to_labels']} {record['to_name']}"
        )

    if not records:
        print("No relationships found.")

finally:
    driver.close()
