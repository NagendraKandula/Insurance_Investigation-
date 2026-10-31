
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            with open("database/additional_indexes.sql", "r") as file:
                cur.execute(file.read())

    print("Additional indexes created successfully!")

except Exception as e:
    print("Error:", e)
