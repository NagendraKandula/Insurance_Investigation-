CREATE TABLE claimants (
    claimant_id VARCHAR(30) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),
    email VARCHAR(255),
    normalized_email VARCHAR(255),
    phone VARCHAR(30),
    normalized_phone VARCHAR(30),
    address TEXT,
    normalized_address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE users (
    user_id VARCHAR(30) PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(30) NOT NULL
        CHECK (role IN ('ANALYST', 'REVIEWER', 'ADMIN')),
    status VARCHAR(30) NOT NULL
        CHECK (status IN ('ACTIVE', 'INACTIVE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE providers (
    provider_id VARCHAR(30) PRIMARY KEY,
    provider_name VARCHAR(200) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    registration_number VARCHAR(100) UNIQUE,
    email VARCHAR(255),
    normalized_email VARCHAR(255),
    phone VARCHAR(30),
    normalized_phone VARCHAR(30),
    address TEXT,
    normalized_address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    registration_date DATE,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


