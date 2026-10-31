
import os
import random
from faker import Faker
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing. Check your .env file.")

# Reproducibility
RANDOM_SEED = 20261031

random.seed(RANDOM_SEED)

fake = Faker("en_IN")
Faker.seed(RANDOM_SEED)

# Dataset configuration
DATASET_CONFIG = {
    "claimants": 2000,
    "providers": 500,
    "policies": 3000,
    "incidents": 4000,
    "claims": 5000,
    "invoices": 6000,
    "payments": 8000,
    "relationship_edges": 8000,
}

# Suspicious and benign patterns
PATTERN_CONFIG = {
    "min_suspicious_networks": 20,
    "max_suspicious_networks": 30,
    "min_benign_communities": 10,
    "max_benign_communities": 15,
}

GENERATOR_VERSION = "1.0.0"
