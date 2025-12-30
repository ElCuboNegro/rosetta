-- Wiktionary Data Tables
-- Stores raw and processed wiktionary entries for Spanish and Hebrew

-- Raw Spanish entries (unfiltered)
CREATE TABLE IF NOT EXISTS raw_spanish_entries_unfiltered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),  -- Part of speech
    definition TEXT,
    examples JSONB DEFAULT '[]'::jsonb,
    synonyms JSONB DEFAULT '[]'::jsonb,
    antonyms JSONB DEFAULT '[]'::jsonb,
    related JSONB DEFAULT '[]'::jsonb,
    etymology TEXT,
    pronunciation TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_spanish_unfiltered_word ON raw_spanish_entries_unfiltered(word);
CREATE INDEX idx_raw_spanish_unfiltered_pos ON raw_spanish_entries_unfiltered(pos);

-- Raw Hebrew entries (unfiltered)
CREATE TABLE IF NOT EXISTS raw_hebrew_entries_unfiltered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definition TEXT,
    examples JSONB DEFAULT '[]'::jsonb,
    synonyms JSONB DEFAULT '[]'::jsonb,
    antonyms JSONB DEFAULT '[]'::jsonb,
    related JSONB DEFAULT '[]'::jsonb,
    etymology TEXT,
    pronunciation TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_hebrew_unfiltered_word ON raw_hebrew_entries_unfiltered(word);
CREATE INDEX idx_raw_hebrew_unfiltered_pos ON raw_hebrew_entries_unfiltered(pos);

-- Filtered Spanish entries
CREATE TABLE IF NOT EXISTS raw_spanish_entries_filtered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definition TEXT,
    examples JSONB DEFAULT '[]'::jsonb,
    synonyms JSONB DEFAULT '[]'::jsonb,
    antonyms JSONB DEFAULT '[]'::jsonb,
    related JSONB DEFAULT '[]'::jsonb,
    etymology TEXT,
    pronunciation TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_spanish_filtered_word ON raw_spanish_entries_filtered(word);
CREATE INDEX idx_raw_spanish_filtered_pos ON raw_spanish_entries_filtered(pos);
CREATE INDEX idx_raw_spanish_filtered_definition ON raw_spanish_entries_filtered USING GIN (to_tsvector('spanish', definition));

-- Filtered Hebrew entries
CREATE TABLE IF NOT EXISTS raw_hebrew_entries_filtered (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definition TEXT,
    examples JSONB DEFAULT '[]'::jsonb,
    synonyms JSONB DEFAULT '[]'::jsonb,
    antonyms JSONB DEFAULT '[]'::jsonb,
    related JSONB DEFAULT '[]'::jsonb,
    etymology TEXT,
    pronunciation TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_hebrew_filtered_word ON raw_hebrew_entries_filtered(word);
CREATE INDEX idx_raw_hebrew_filtered_pos ON raw_hebrew_entries_filtered(pos);
CREATE INDEX idx_raw_hebrew_filtered_definition ON raw_hebrew_entries_filtered USING GIN (to_tsvector('simple', definition));

-- Final Spanish entries (after processing)
CREATE TABLE IF NOT EXISTS raw_spanish_entries (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definition TEXT,
    examples JSONB DEFAULT '[]'::jsonb,
    synonyms JSONB DEFAULT '[]'::jsonb,
    antonyms JSONB DEFAULT '[]'::jsonb,
    related JSONB DEFAULT '[]'::jsonb,
    etymology TEXT,
    pronunciation TEXT,
    ipa TEXT,  -- IPA pronunciation
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_spanish_word ON raw_spanish_entries(word);
CREATE INDEX idx_raw_spanish_pos ON raw_spanish_entries(pos);
CREATE INDEX idx_raw_spanish_definition ON raw_spanish_entries USING GIN (to_tsvector('spanish', definition));

-- Final Hebrew entries (after processing)
CREATE TABLE IF NOT EXISTS raw_hebrew_entries (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    pos VARCHAR(100),
    definition TEXT,
    examples JSONB DEFAULT '[]'::jsonb,
    synonyms JSONB DEFAULT '[]'::jsonb,
    antonyms JSONB DEFAULT '[]'::jsonb,
    related JSONB DEFAULT '[]'::jsonb,
    etymology TEXT,
    pronunciation TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_hebrew_word ON raw_hebrew_entries(word);
CREATE INDEX idx_raw_hebrew_pos ON raw_hebrew_entries(pos);
CREATE INDEX idx_raw_hebrew_definition ON raw_hebrew_entries USING GIN (to_tsvector('simple', definition));

-- Example sentences tables
CREATE TABLE IF NOT EXISTS wiktionary_examples_tagged (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    sentence_text TEXT NOT NULL,
    language VARCHAR(5) NOT NULL,
    source VARCHAR(50) DEFAULT 'wiktionary',
    pos VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wiktionary_examples_word ON wiktionary_examples_tagged(word);
CREATE INDEX idx_wiktionary_examples_lang ON wiktionary_examples_tagged(language);
CREATE INDEX idx_wiktionary_examples_text ON wiktionary_examples_tagged USING GIN (to_tsvector('spanish', sentence_text));

CREATE TABLE IF NOT EXISTS tatoeba_examples_tagged (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    sentence_text TEXT NOT NULL,
    language VARCHAR(5) NOT NULL,
    source VARCHAR(50) DEFAULT 'tatoeba',
    tatoeba_id VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tatoeba_examples_word ON tatoeba_examples_tagged(word);
CREATE INDEX idx_tatoeba_examples_lang ON tatoeba_examples_tagged(language);
CREATE INDEX idx_tatoeba_examples_text ON tatoeba_examples_tagged USING GIN (to_tsvector('spanish', sentence_text));

CREATE TABLE IF NOT EXISTS clean_examples (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    sentence_text TEXT NOT NULL,
    language VARCHAR(5) NOT NULL,
    source VARCHAR(50),
    quality_score FLOAT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clean_examples_word ON clean_examples(word);
CREATE INDEX idx_clean_examples_quality ON clean_examples(quality_score);
CREATE INDEX idx_clean_examples_text ON clean_examples USING GIN (to_tsvector('spanish', sentence_text));

-- Comments
COMMENT ON TABLE raw_spanish_entries_unfiltered IS 'Raw Spanish wiktionary entries before filtering';
COMMENT ON TABLE raw_hebrew_entries_unfiltered IS 'Raw Hebrew wiktionary entries before filtering';
COMMENT ON TABLE raw_spanish_entries_filtered IS 'Filtered Spanish wiktionary entries';
COMMENT ON TABLE raw_hebrew_entries_filtered IS 'Filtered Hebrew wiktionary entries';
COMMENT ON TABLE raw_spanish_entries IS 'Final processed Spanish wiktionary entries';
COMMENT ON TABLE raw_hebrew_entries IS 'Final processed Hebrew wiktionary entries';
COMMENT ON TABLE wiktionary_examples_tagged IS 'Example sentences from Wiktionary';
COMMENT ON TABLE tatoeba_examples_tagged IS 'Example sentences from Tatoeba corpus';
COMMENT ON TABLE clean_examples IS 'Cleaned and quality-filtered example sentences';
