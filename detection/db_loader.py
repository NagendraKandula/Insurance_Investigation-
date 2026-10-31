import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


class DatabaseLoader:
    def __init__(self):
        load_dotenv()

        self.conn_str = os.getenv("DATABASE_URL")

        if not self.conn_str:
            raise ValueError("DATABASE_URL environment variable is missing.")

    def load_all_data(self):
        """Load all required datasets using one consistent database snapshot."""

        print("Loading data from Neon PostgreSQL...")

        queries = {
            "claimants": "SELECT * FROM claimants;",
            "policies": "SELECT * FROM policies;",
            "incidents": "SELECT * FROM incidents;",
            "claims": "SELECT * FROM claims;",
            "providers": "SELECT * FROM providers;",
            "invoices": "SELECT * FROM invoices;",
            "payments": "SELECT * FROM payments;",
            "relationship_edges": "SELECT * FROM relationship_edges;",
            "ground_truth": "SELECT * FROM ground_truth;"
        }

        data = {}

        with psycopg.connect(
    self.conn_str,
    row_factory=dict_row,
    connect_timeout=30,
    keepalives=1,
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5
) as conn:

            with conn.transaction():
                conn.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY;"
                )

                with conn.cursor() as cur:
                    for table_name, query in queries.items():

                        print(f"Loading {table_name}...")

                        cur.execute(query)
                        data[table_name] = cur.fetchall()

                        print(
                            f"Loaded {len(data[table_name])} "
                            f"records from {table_name}"
                        )

        print("Data load complete.")

        return data