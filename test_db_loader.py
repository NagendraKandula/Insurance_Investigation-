from detection.db_loader import DatabaseLoader

loader = DatabaseLoader()
data = loader.load_all_data()

print("\n========== DATABASE LOAD SUMMARY ==========")

for table, records in data.items():
    print(f"{table:25} {len(records):>8}")

print("\nDatabase loading completed successfully.")