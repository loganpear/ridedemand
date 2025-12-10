DROP TABLE IF EXISTS passwords;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    email_address TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT UNIQUE NOT NULL,
    salt TEXT,
    rating_sum INTEGER NOT NULL,  -- initialize at 0
    rating_count INTEGER NOT NULL, -- initialize at 0
    driver INTEGER NOT NULL -- 1 for drivers, 0 for passengers
    -- balance will be handled in the payments micro service
);

CREATE TABLE passwords (
    email_address TEXT NOT NULL ,
    password_hash TEXT NOT NULL,
    is_current INTEGER NOT NULL,  -- 1 for True (current), 0 for False (past password)
    FOREIGN KEY (email_address) REFERENCES users(email_address)
);