DROP TABLE IF EXISTS balances;

CREATE TABLE balances (
    username TEXT PRIMARY KEY,
    balance INTEGER NOT NULL -- cents
);