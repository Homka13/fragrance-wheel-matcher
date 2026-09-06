-- Cloudflare D1 (SQLite) Schema for Fragrance Wheel Matcher

-- 1. Таблиця 4 базових родин Колеса
CREATE TABLE IF NOT EXISTS wheel_families (
    code TEXT PRIMARY KEY,
    name_uk TEXT NOT NULL,
    name_en TEXT NOT NULL,
    color_hex TEXT NOT NULL,
    profile TEXT NOT NULL
);

-- 2. Таблиця 14 ольфакторних підгруп
CREATE TABLE IF NOT EXISTS wheel_subfamilies (
    id TEXT PRIMARY KEY,
    ring_index INTEGER NOT NULL UNIQUE,
    family_code TEXT NOT NULL REFERENCES wheel_families(code) ON DELETE CASCADE,
    name_uk TEXT NOT NULL,
    name_en TEXT NOT NULL,
    color_hex TEXT NOT NULL,
    profile TEXT NOT NULL,
    key_ingredients TEXT NOT NULL -- JSON array
);

-- 3. Бренди
CREATE TABLE IF NOT EXISTS brands (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    country TEXT
);

-- 4. Парфумерний каталог
CREATE TABLE IF NOT EXISTS fragrances (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    brand_name TEXT NOT NULL,
    name TEXT NOT NULL,
    gender TEXT DEFAULT 'unisex',
    concentration TEXT DEFAULT 'Eau de Parfum',
    primary_subfamily_id TEXT NOT NULL REFERENCES wheel_subfamilies(id) ON DELETE RESTRICT,
    family_code TEXT NOT NULL REFERENCES wheel_families(code) ON DELETE RESTRICT,
    top_notes TEXT NOT NULL, -- JSON array
    heart_notes TEXT NOT NULL, -- JSON array
    base_notes TEXT NOT NULL, -- JSON array
    price_uah REAL,
    product_sku TEXT UNIQUE,
    product_url TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Індекси
CREATE INDEX IF NOT EXISTS idx_fragrances_subfamily ON fragrances(primary_subfamily_id);
CREATE INDEX IF NOT EXISTS idx_fragrances_family ON fragrances(family_code);
CREATE INDEX IF NOT EXISTS idx_fragrances_sku ON fragrances(product_sku);
