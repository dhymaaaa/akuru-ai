-- Create the database
CREATE DATABASE IF NOT EXISTS akuru;

-- Use the database
USE akuru;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optionally, create an admin user (replace with your values)
-- INSERT INTO users (email, password) VALUES ('admin@example.com', 'hashed_password_here');

-- Create indexes for faster queries
CREATE INDEX idx_email ON users(email);