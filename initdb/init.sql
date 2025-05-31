CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    status VARCHAR(50) CHECK (status IN ('pending', 'approved', 'rejected')),
    payment_date DATE,
    expiry_date DATE
);
