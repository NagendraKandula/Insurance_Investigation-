
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            with open("database/supporting_tables.sql", "r") as file:
                sql = file.read()

            cur.execute(sql)

    print("All five supporting tables created successfully!")

except Exception as e:
    print("Error:", e)
