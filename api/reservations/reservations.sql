DROP TABLE IF EXISTS reservations;

CREATE TABLE reservations (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT, -- to determine most recent
    listing_id INTEGER NOT NULL UNIQUE,
    driver_username TEXT NOT NULL,
    rider_username TEXT NOT NULL,
    ride_date TEXT NOT NULL, -- ISO 8601 date string (YYYY-MM-DD)
    ride_time TEXT NOT NULL, -- 24h time string (HH:MM)
    price INTEGER NOT NULL, -- in cents
    status TEXT NOT NULL DEFAULT 'CONFIRMED' -- reservation state
);
-- Note: driver_username and price are not redundant since the availability listing
-- gets deleted upon reservation