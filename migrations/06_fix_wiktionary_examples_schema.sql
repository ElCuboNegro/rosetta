-- Fix wiktionary_examples_tagged schema to match actual parquet data
-- Drop and recreate with correct columns

DROP TABLE IF EXISTS wiktionary_examples_tagged CASCADE;
DROP TABLE IF EXISTS tatoeba_examples_tagged CASCADE;

-- Wiktionary examples with correct schema (matching parquet file)
CREATE TABLE IF NOT EXISTS wiktionary_examples_tagged (
    id BIGSERIAL PRIMARY KEY,
    source_word VARCHAR(500) NOT NULL,
    example_text TEXT NOT NULL,
    tokens JSONB DEFAULT '[]'::jsonb,
    pos_tags JSONB DEFAULT '[]'::jsonb,
    dependencies JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wiktionary_examples_source_word ON wiktionary_examples_tagged(source_word);
CREATE INDEX idx_wiktionary_examples_text ON wiktionary_examples_tagged USING GIN (to_tsvector('spanish', example_text));

-- Tatoeba examples with correct schema
CREATE TABLE IF NOT EXISTS tatoeba_examples_tagged (
    id BIGSERIAL PRIMARY KEY,
    source_word VARCHAR(500) NOT NULL,
    example_text TEXT NOT NULL,
    tokens JSONB DEFAULT '[]'::jsonb,
    pos_tags JSONB DEFAULT '[]'::jsonb,
    dependencies JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tatoeba_examples_source_word ON tatoeba_examples_tagged(source_word);
CREATE INDEX idx_tatoeba_examples_text ON tatoeba_examples_tagged USING GIN (to_tsvector('spanish', example_text));

COMMENT ON TABLE wiktionary_examples_tagged IS 'Example sentences from Wiktionary with NLP annotations';
COMMENT ON TABLE tatoeba_examples_tagged IS 'Example sentences from Tatoeba corpus with NLP annotations';
