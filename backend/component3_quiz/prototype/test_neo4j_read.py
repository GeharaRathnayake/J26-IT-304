
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).with_name(".env"))

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

with GraphDatabase.driver(uri, auth=(username, password)) as driver:
    driver.verify_connectivity()

    records, _, _ = driver.execute_query(
        """
        MATCH (:Module {name: $module_name})
              -[:CONTAINS_CONCEPT]->(c:Concept)
        RETURN c.name AS concept
        ORDER BY concept
        """,
        parameters_={"module_name": "Variables"},
        database_="neo4j",
    )

    print("Variables concepts:")
    for record in records:
        print("- " + record["concept"])
