-- Language Alignment Data Tables
-- Stores aligned Spanish-Hebrew dictionary entries and matches

-- Bridge entries (English intermediate)
CREATE TABLE IF NOT EXISTS bridge_entries (
    id BIGSERIAL PRIMARY KEY,
    spanish_word VARCHAR(500),
    english_word VARCHAR(500),
    hebrew_word VARCHAR(500),
    spanish_pos VARCHAR(100),
    english_pos VARCHAR(100),
    hebrew_pos VARCHAR(100),
    spanish_definition TEXT,
    english_definition TEXT,
    hebrew_definition TEXT,
    confidence_score FLOAT,
    alignment_method VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bridge_spanish ON bridge_entries(spanish_word);
CREATE INDEX idx_bridge_english ON bridge_entries(english_word);
CREATE INDEX idx_bridge_hebrew ON bridge_entries(hebrew_word);
CREATE INDEX idx_bridge_confidence ON bridge_entries(confidence_score);

-- Aligned matches (Spanish-Hebrew direct matches)
CREATE TABLE IF NOT EXISTS aligned_matches (
    id BIGSERIAL PRIMARY KEY,
    spanish_word VARCHAR(500) NOT NULL,
    hebrew_word VARCHAR(500) NOT NULL,
    spanish_pos VARCHAR(100),
    hebrew_pos VARCHAR(100),
    spanish_definition TEXT,
    hebrew_definition TEXT,
    match_score FLOAT,
    match_type VARCHAR(50),  -- direct, via_english, semantic, etc.
    alignment_method VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_aligned_spanish ON aligned_matches(spanish_word);
CREATE INDEX idx_aligned_hebrew ON aligned_matches(hebrew_word);
CREATE INDEX idx_aligned_match_type ON aligned_matches(match_type);
CREATE INDEX idx_aligned_score ON aligned_matches(match_score);

-- Orphaned entries (no match found)
CREATE TABLE IF NOT EXISTS orphaned_entries (
    id BIGSERIAL PRIMARY KEY,
    word VARCHAR(500) NOT NULL,
    language VARCHAR(5) NOT NULL,  -- 'es' or 'he'
    pos VARCHAR(100),
    definition TEXT,
    reason VARCHAR(200),  -- Why no match was found
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orphaned_word ON orphaned_entries(word);
CREATE INDEX idx_orphaned_lang ON orphaned_entries(language);
CREATE INDEX idx_orphaned_reason ON orphaned_entries(reason);

-- Enriched entries (raw - before final processing)
CREATE TABLE IF NOT EXISTS enriched_entries_raw (
    id BIGSERIAL PRIMARY KEY,
    spanish_word VARCHAR(500) NOT NULL,
    hebrew_word VARCHAR(500) NOT NULL,
    spanish_pos VARCHAR(100),
    hebrew_pos VARCHAR(100),
    spanish_definition TEXT,
    hebrew_definition TEXT,
    spanish_examples JSONB DEFAULT '[]'::jsonb,
    hebrew_examples JSONB DEFAULT '[]'::jsonb,
    spanish_synonyms JSONB DEFAULT '[]'::jsonb,
    hebrew_synonyms JSONB DEFAULT '[]'::jsonb,
    match_score FLOAT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_enriched_raw_spanish ON enriched_entries_raw(spanish_word);
CREATE INDEX idx_enriched_raw_hebrew ON enriched_entries_raw(hebrew_word);
CREATE INDEX idx_enriched_raw_score ON enriched_entries_raw(match_score);

-- Enriched entries (final - after processing)
CREATE TABLE IF NOT EXISTS enriched_entries (
    id BIGSERIAL PRIMARY KEY,
    spanish_word VARCHAR(500) NOT NULL,
    hebrew_word VARCHAR(500) NOT NULL,
    spanish_pos VARCHAR(100),
    hebrew_pos VARCHAR(100),
    spanish_definition TEXT,
    hebrew_definition TEXT,
    spanish_ipa TEXT,  -- Spanish IPA pronunciation
    hebrew_ipa TEXT,   -- Hebrew pronunciation
    spanish_examples JSONB DEFAULT '[]'::jsonb,
    hebrew_examples JSONB DEFAULT '[]'::jsonb,
    spanish_synonyms JSONB DEFAULT '[]'::jsonb,
    hebrew_synonyms JSONB DEFAULT '[]'::jsonb,
    match_score FLOAT,
    quality_score FLOAT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_enriched_spanish ON enriched_entries(spanish_word);
CREATE INDEX idx_enriched_hebrew ON enriched_entries(hebrew_word);
CREATE INDEX idx_enriched_quality ON enriched_entries(quality_score);
CREATE INDEX idx_enriched_spanish_pos ON enriched_entries(spanish_word, spanish_pos);
CREATE INDEX idx_enriched_hebrew_pos ON enriched_entries(hebrew_word, hebrew_pos);

-- Full-text search on definitions
CREATE INDEX idx_enriched_spanish_def ON enriched_entries USING GIN (to_tsvector('spanish', spanish_definition));
CREATE INDEX idx_enriched_hebrew_def ON enriched_entries USING GIN (to_tsvector('simple', hebrew_definition));

-- Trigger for updating updated_at
CREATE TRIGGER update_enriched_entries_updated_at BEFORE UPDATE
    ON enriched_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE bridge_entries IS 'English bridge entries for Spanish-Hebrew alignment';
COMMENT ON TABLE aligned_matches IS 'Matched Spanish-Hebrew word pairs';
COMMENT ON TABLE orphaned_entries IS 'Entries that could not be aligned';
COMMENT ON TABLE enriched_entries_raw IS 'Enriched entries before final processing';
COMMENT ON TABLE enriched_entries IS 'Final enriched Spanish-Hebrew dictionary entries';
