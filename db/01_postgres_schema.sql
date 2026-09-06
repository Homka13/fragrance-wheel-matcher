-- 01_postgres_schema.sql
-- Продакшн DDL схема для PostgreSQL 15+
-- Включає підтримку 14 підгруп Колеса Едвардса, ольфакторної піраміди та ідемпотентного кешування

CREATE TABLE IF NOT EXISTS wheel_families (
    code VARCHAR(20) PRIMARY KEY,
    name_uk VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    color_hex VARCHAR(7) NOT NULL,
    profile TEXT
);

CREATE TABLE IF NOT EXISTS wheel_subfamilies (
    id VARCHAR(50) PRIMARY KEY,
    ring_index INT NOT NULL UNIQUE CHECK (ring_index >= 0 AND ring_index <= 13),
    family_code VARCHAR(20) NOT NULL REFERENCES wheel_families(code) ON DELETE CASCADE,
    name_uk VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    color_hex VARCHAR(7) NOT NULL,
    profile TEXT,
    key_ingredients TEXT[]
);

CREATE TABLE IF NOT EXISTS brands (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    country VARCHAR(100),
    is_niche BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS fragrances (
    id VARCHAR(100) PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    gender VARCHAR(30) DEFAULT 'unisex',
    concentration VARCHAR(50), -- EDP, EDT, Extrait de Parfum, Cologne
    primary_subfamily_id VARCHAR(50) NOT NULL REFERENCES wheel_subfamilies(id),
    top_notes TEXT[] DEFAULT '{}',
    heart_notes TEXT[] DEFAULT '{}',
    base_notes TEXT[] DEFAULT '{}',
    price_uah NUMERIC(10, 2),
    product_sku VARCHAR(100),
    product_url TEXT,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Індекси для швидкого пошуку
CREATE INDEX IF NOT EXISTS idx_fragrances_subfamily ON fragrances(primary_subfamily_id);
CREATE INDEX IF NOT EXISTS idx_fragrances_brand ON fragrances(brand_id);

-- Таблиця кешування розрахованих парних рекомендацій (Ідемпотентне оновлення)
CREATE TABLE IF NOT EXISTS recommendation_cache (
    source_fragrance_id VARCHAR(100) NOT NULL REFERENCES fragrances(id) ON DELETE CASCADE,
    target_fragrance_id VARCHAR(100) NOT NULL REFERENCES fragrances(id) ON DELETE CASCADE,
    match_type VARCHAR(20) NOT NULL, -- 'exact', 'adjacent', 'complementary', 'other'
    ring_distance INT NOT NULL,
    similarity_score NUMERIC(5, 4) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (source_fragrance_id, target_fragrance_id)
);

CREATE INDEX IF NOT EXISTS idx_rec_cache_lookup 
ON recommendation_cache(source_fragrance_id, match_type, similarity_score DESC);

-- Приклад ідемпотентного запиту ранжування та кешування:
-- INSERT INTO recommendation_cache (...)
-- VALUES (...)
-- ON CONFLICT (source_fragrance_id, target_fragrance_id)
-- DO UPDATE SET
--     similarity_score = EXCLUDED.similarity_score,
--     match_type = EXCLUDED.match_type,
--     ring_distance = EXCLUDED.ring_distance,
--     updated_at = NOW();
