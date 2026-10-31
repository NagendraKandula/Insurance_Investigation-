
import os
import psycopg
from dotenv import load_dotenv

print("Starting database connection test...")

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
else:
    print("DATABASE_URL loaded successfully.")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                result = cur.fetchone()

                print("\nConnected to Neon successfully!")
                print("PostgreSQL version:", result[0])

    except Exception as e:
        print("\nDatabase connection failed:")
        print(e)
