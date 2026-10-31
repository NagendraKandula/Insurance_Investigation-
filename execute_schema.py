import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

with open("database/schema.sql", "r") as file:
    schema_sql = file.read()

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)

    print("Schema executed successfully!")

except Exception as e:
    print("Error:", e)