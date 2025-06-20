-- Create the database
CREATE DATABASE IF NOT EXISTS akuru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE akuru;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    role ENUM('user', 'akuru') NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS dialects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    eng_term VARCHAR(100) NOT NULL,
    male_term VARCHAR(200),
    huvadhoo_term VARCHAR(200),
    addu_term VARCHAR(200),
    male_transliteration VARCHAR(255),
    huvadhoo_transliteration VARCHAR(255),
    addu_transliteration VARCHAR(255)
);



-- INSERT INTO dialects (eng_term, male_term, huvadhoo_term, addu_term, male_transliteration, huvadhoo_transliteration, addu_transliteration) VALUES
-- ('Mother', 'މަންމަ', 'މަންމަ', 'މަންމާ / އަމާ', 'manma', 'manma', 'manmaa / amaa')),
-- ('Father', 'ބައްޕަ', 'ބައްޕަ / އައްޕަ', 'ބައްޕާ', 'bappa', 'bappa / appa', 'bappaa'),
-- ('Son', 'ފިރިހެން ދަރި', 'ހުތާ', 'ފުތާ', 'firihen dhari', 'huthaa', 'futhaa'),
-- ('Daughter', 'އަންހެން ދަރި', 'ދިޔެ', 'ދިޔެ', 'anhen dhari', 'dhiye', 'dhiye'),
-- ('Brother older', 'ބޭބެ', 'ބޭބެ', 'ބޭބެ', 'beybe', 'beybe', 'beybe'),
-- ('Sister older', 'ދައްތަ', 'ދައްތަ', 'ދައްތަ', 'dhahtha', 'dhahtha', 'dhahtha'),
-- ('Brother / sister younger', 'ކޮއްކޮ', 'ކޮއްކޮ', 'ކޮއްކޮ', 'kokko', 'kokko', 'kokko'),
-- ('Grandmother', 'މާމަ', 'މާމަ / މުންނާ', 'މާމަ / މުންނާ', 'maama', 'maama / munnaa', 'maama / munnaa'),
-- ('Grandfather', 'ކާފަ', 'ކާފަ', 'ކާފަ', 'kaafa', 'kaafa', 'kaafa'),
-- ('Aunt', 'ބޮޑު ދައިތަ', 'ބޮޑެއައްތާ', 'ބޮންޑޮ ދައިތާ', 'bodu dhaitha', 'bodeahthaa', 'bondo dhaithaa'),
-- ('Uncle', 'ބޮޑު ބޭބެ', 'ބޮޑެބޭ', 'ބޮންޑޮ ބޭބޭ', 'bodu beybe', 'bodebey', 'bondo beybey');



-- Create indexes for faster queries
-- CREATE INDEX idx_email ON users(email);
-- CREATE INDEX idx_user_id ON conversations(user_id);
-- CREATE INDEX idx_conversation_id ON messages(conversation_id);
