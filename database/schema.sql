-- Properties table — the core data
CREATE TABLE IF NOT EXISTS properties (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    city            TEXT NOT NULL,
    area            TEXT NOT NULL,           -- e.g. "Gulberg", "DHA Phase 6"
    property_type   TEXT NOT NULL,           -- house, apartment, plot, commercial
    price_lakhs     REAL NOT NULL,           -- price in PKR lakhs
    bedrooms        INTEGER DEFAULT 0,
    bathrooms       INTEGER DEFAULT 0,
    area_sqft       INTEGER NOT NULL,
    floor_level     INTEGER DEFAULT NULL,    -- for apartments
    is_furnished    BOOLEAN DEFAULT FALSE,
    has_parking     BOOLEAN DEFAULT TRUE,
    has_garden      BOOLEAN DEFAULT FALSE,
    contact_name    TEXT NOT NULL,
    contact_phone   TEXT NOT NULL,
    description     TEXT,
    is_available    BOOLEAN DEFAULT TRUE,
    listing_type    TEXT DEFAULT 'sale',     -- sale or rent
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast city + type searches (this is what MCP tool will query most)
CREATE INDEX IF NOT EXISTS idx_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_type ON properties(property_type);
CREATE INDEX IF NOT EXISTS idx_price ON properties(price_lakhs);
CREATE INDEX IF NOT EXISTS idx_available ON properties(is_available);