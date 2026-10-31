
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            with open("database/investigation_tables.sql", "r") as file:
                sql = file.read()

            cur.execute(sql)

    print("Investigation, ground_truth and data_exceptions created!")

except Exception as e:
    print("Error:", e)
