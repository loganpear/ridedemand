DROP TABLE IF EXISTS listings;

CREATE TABLE listings (
    listing_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL, -- driver's username
    ride_date TEXT NOT NULL, -- ISO 8601 date string (YYYY-MM-DD)
    ride_time TEXT NOT NULL, -- 24h time string (HH:MM)
    price INTEGER NOT NULL -- in cents
);