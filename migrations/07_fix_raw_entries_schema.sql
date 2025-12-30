-- Fix raw entries schemas to match actual parquet file structure
-- These tables had schemas based on assumptions rather than actual data

-- Drop all raw entry tables and recreate with correct schemas
DROP TABLE IF EXISTS raw_spanish_entries_unfiltered CASCADE;
DROP TABLE IF EXISTS raw_hebrew_entries_unfiltered CASCADE;
DROP TABLE IF EXISTS raw_spanish_entries_filtered CASCADE;
DROP TABLE IF EXISTS raw_hebrew_entries_filtered CASCADE;
DROP TABLE IF EXISTS raw_spanish_entries CASCADE;
DROP TABLE IF EXISTS raw_hebrew_entries CASCADE;

-- Raw Spanish entries (unfiltered)
-- Matches parquet schema: word, pos, ipa, definitions[], examples[], translations_*, frequency_score, frequency_rank
CREATE TABLE raw_spanish_entries_unfiltered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    ipa TEXT,  -- IPA pronunciation
    definitions JSONB DEFAULT '[]'::jsonb,  -- Array of definitions
    examples JSONB DEFAULT '[]'::jsonb,     -- Array of examples
    translations_en JSONB DEFAULT '[]'::jsonb,
    translations_fr JSONB DEFAULT '[]'::jsonb,
    translations_de JSONB DEFAULT '[]'::jsonb,
    translations_he JSONB DEFAULT '[]'::jsonb,
    frequency_score FLOAT,
    frequency_rank INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_spanish_unfiltered_word ON raw_spanish_entries_unfiltered(word);
CREATE INDEX idx_raw_spanish_unfiltered_pos ON raw_spanish_entries_unfiltered(pos);
CREATE INDEX idx_raw_spanish_unfiltered_freq ON raw_spanish_entries_unfiltered(frequency_rank);

-- Raw Hebrew entries (unfiltered)
-- Matches parquet schema: word, pos, definitions[], translations_*
CREATE TABLE raw_hebrew_entries_unfiltered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definitions JSONB DEFAULT '[]'::jsonb,
    translations_en JSONB DEFAULT '[]'::jsonb,
    translations_fr JSONB DEFAULT '[]'::jsonb,
    translations_de JSONB DEFAULT '[]'::jsonb,
    translations_es JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_hebrew_unfiltered_word ON raw_hebrew_entries_unfiltered(word);
CREATE INDEX idx_raw_hebrew_unfiltered_pos ON raw_hebrew_entries_unfiltered(pos);

-- Filtered Spanish entries (same schema as unfiltered)
CREATE TABLE raw_spanish_entries_filtered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    ipa TEXT,
    definitions JSONB DEFAULT '[]'::jsonb,
    examples JSONB DEFAULT '[]'::jsonb,
    translations_en JSONB DEFAULT '[]'::jsonb,
    translations_fr JSONB DEFAULT '[]'::jsonb,
    translations_de JSONB DEFAULT '[]'::jsonb,
    translations_he JSONB DEFAULT '[]'::jsonb,
    frequency_score FLOAT,
    frequency_rank INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_spanish_filtered_word ON raw_spanish_entries_filtered(word);
CREATE INDEX idx_raw_spanish_filtered_pos ON raw_spanish_entries_filtered(pos);
CREATE INDEX idx_raw_spanish_filtered_freq ON raw_spanish_entries_filtered(frequency_rank);

-- Filtered Hebrew entries (same schema as unfiltered)
CREATE TABLE raw_hebrew_entries_filtered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definitions JSONB DEFAULT '[]'::jsonb,
    translations_en JSONB DEFAULT '[]'::jsonb,
    translations_fr JSONB DEFAULT '[]'::jsonb,
    translations_de JSONB DEFAULT '[]'::jsonb,
    translations_es JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_hebrew_filtered_word ON raw_hebrew_entries_filtered(word);
CREATE INDEX idx_raw_hebrew_filtered_pos ON raw_hebrew_entries_filtered(pos);

-- Final Spanish entries (same schema as filtered)
CREATE TABLE raw_spanish_entries (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    ipa TEXT,
    definitions JSONB DEFAULT '[]'::jsonb,
    examples JSONB DEFAULT '[]'::jsonb,
    translations_en JSONB DEFAULT '[]'::jsonb,
    translations_fr JSONB DEFAULT '[]'::jsonb,
    translations_de JSONB DEFAULT '[]'::jsonb,
    translations_he JSONB DEFAULT '[]'::jsonb,
    frequency_score FLOAT,
    frequency_rank INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_spanish_word ON raw_spanish_entries(word);
CREATE INDEX idx_raw_spanish_pos ON raw_spanish_entries(pos);
CREATE INDEX idx_raw_spanish_freq ON raw_spanish_entries(frequency_rank);
CREATE INDEX idx_raw_spanish_definitions ON raw_spanish_entries USING GIN (definitions);

-- Final Hebrew entries (same schema as filtered)
CREATE TABLE raw_hebrew_entries (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definitions JSONB DEFAULT '[]'::jsonb,
    translations_en JSONB DEFAULT '[]'::jsonb,
    translations_fr JSONB DEFAULT '[]'::jsonb,
    translations_de JSONB DEFAULT '[]'::jsonb,
    translations_es JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_hebrew_word ON raw_hebrew_entries(word);
CREATE INDEX idx_raw_hebrew_pos ON raw_hebrew_entries(pos);
CREATE INDEX idx_raw_hebrew_definitions ON raw_hebrew_entries USING GIN (definitions);

-- Comments
COMMENT ON TABLE raw_spanish_entries_unfiltered IS 'Raw Spanish wiktionary entries before filtering - matches parquet schema';
COMMENT ON TABLE raw_hebrew_entries_unfiltered IS 'Raw Hebrew wiktionary entries before filtering - matches parquet schema';
COMMENT ON TABLE raw_spanish_entries_filtered IS 'Filtered Spanish wiktionary entries (proper nouns removed)';
COMMENT ON TABLE raw_hebrew_entries_filtered IS 'Filtered Hebrew wiktionary entries (proper nouns removed)';
COMMENT ON TABLE raw_spanish_entries IS 'Final processed Spanish wiktionary entries';
COMMENT ON TABLE raw_hebrew_entries IS 'Final processed Hebrew wiktionary entries';
