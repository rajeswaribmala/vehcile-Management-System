PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS service_requests;
DROP TABLE IF EXISTS service_categories;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS branches;

CREATE TABLE branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_name TEXT NOT NULL,
    location TEXT NOT NULL
);


INSERT INTO branches (branch_name, location) VALUES
('Chennai Central', 'Chennai'),
('Coimbatore Hub', 'Coimbatore'),
('Madurai Service Point', 'Madurai');


CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','user','mechanic')),
    status TEXT DEFAULT 'pending',
    branch_id INTEGER,
    is_active INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    FOREIGN KEY (branch_id) REFERENCES branches(id)
);

CREATE TABLE vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vehicle_number TEXT NOT NULL,
    model TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


CREATE TABLE service_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    price REAL NOT NULL
);

INSERT INTO service_categories (name, price) VALUES
('Oil Change', 700),
('Brake Service', 1200),
('Engine Repair', 2500),
('General Service', 1500);

CREATE TABLE service_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    vehicle_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    mechanic_id INTEGER,

    status TEXT DEFAULT 'Assigned',
    cost REAL DEFAULT 0,

    additional_repair TEXT,
    additional_cost REAL DEFAULT 0,
    additional_status TEXT DEFAULT 'None',

    payment_status TEXT DEFAULT 'Unpaid',

    start_time TEXT,
    end_time TEXT,
    completed_at TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (service_id) REFERENCES service_categories(id),
    FOREIGN KEY (mechanic_id) REFERENCES users(id),
    FOREIGN KEY (branch_id) REFERENCES branches(id)
);


CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_request_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_request_id) REFERENCES service_requests(id) ON DELETE CASCADE
);


CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_request_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    mechanic_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (service_request_id) REFERENCES service_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (mechanic_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);