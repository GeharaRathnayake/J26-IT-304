
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load credentials from the .env file beside this script.
load_dotenv(Path(__file__).with_name(".env"))

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

if not all([uri, username, password]):
    raise SystemExit(
        "Configuration missing. Check NEO4J_URI, "
        "NEO4J_USERNAME and NEO4J_PASSWORD in .env."
    )

try:
    with GraphDatabase.driver(
        uri,
        auth=(username, password)
    ) as driver:
        driver.verify_connectivity()
        record = driver.execute_query(
            """
            MATCH (m:Module)-[:CONTAINS_CONCEPT]->(c:Concept)
            RETURN count(*) AS connections,
                   count(DISTINCT m) AS modules
            """,
            database="neo4j",
            result_transformer_=lambda result: result.single()
        )

        print("Connection successful!")
        print("Module-concept connections:", record["connections"])
        print("Modules with concepts:", record["modules"])

except Exception as exc:
    print("Connection test failed:", type(exc).__name__)
    print("Check that Neo4j is running and your .env settings are correct.")
