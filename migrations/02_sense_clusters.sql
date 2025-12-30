-- Sense Induction Tables
-- Stores clustered word senses discovered from corpus

-- Main sense clusters table
CREATE TABLE IF NOT EXISTS sense_clusters (
    id BIGSERIAL PRIMARY KEY,
    source_word VARCHAR(255) NOT NULL,
    sense_cluster_id INTEGER NOT NULL,
    sentence_text TEXT NOT NULL,
    corpus_source VARCHAR(100),
    clustering_method VARCHAR(50),
    cluster_quality_score FLOAT,
    embedding_vector VECTOR(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast lookups
CREATE INDEX idx_sense_clusters_word ON sense_clusters(source_word);
CREATE INDEX idx_sense_clusters_cluster ON sense_clusters(source_word, sense_cluster_id);
CREATE INDEX idx_sense_clusters_quality ON sense_clusters(cluster_quality_score);

-- Full-text search index for Spanish sentences
CREATE INDEX idx_sense_clusters_sentence_text ON sense_clusters USING GIN (to_tsvector('spanish', sentence_text));

-- Cluster metadata table (stores meaning definitions, labels, etc.)
CREATE TABLE IF NOT EXISTS cluster_metadata (
    id BIGSERIAL PRIMARY KEY,
    source_word VARCHAR(255) NOT NULL,
    sense_cluster_id INTEGER NOT NULL,
    sense_label VARCHAR(500),
    definition TEXT,
    usage_notes TEXT,
    example_sentences TEXT,
    additional_notes TEXT,
    manual_corrections JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_word, sense_cluster_id)
);

CREATE INDEX idx_cluster_metadata_word ON cluster_metadata(source_word);

-- Aligned book sentences table
CREATE TABLE IF NOT EXISTS aligned_book_sentences (
    id BIGSERIAL PRIMARY KEY,
    source_book VARCHAR(500) NOT NULL,
    target_book VARCHAR(500) NOT NULL,
    source_es TEXT NOT NULL,
    target_he TEXT NOT NULL,
    similarity FLOAT,
    alignment_method VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for aligned sentences
CREATE INDEX idx_aligned_books ON aligned_book_sentences(source_book, target_book);
CREATE INDEX idx_aligned_similarity ON aligned_book_sentences(similarity);

-- Full-text search for Spanish
CREATE INDEX idx_aligned_source_text ON aligned_book_sentences USING GIN (to_tsvector('spanish', source_es));

-- Full-text search for Hebrew (using simple text search since PostgreSQL doesn't have Hebrew dictionary)
CREATE INDEX idx_aligned_target_text ON aligned_book_sentences USING GIN (to_tsvector('simple', target_he));

-- Book validation results table
CREATE TABLE IF NOT EXISTS book_validation_results (
    id BIGSERIAL PRIMARY KEY,
    spanish_file VARCHAR(500) NOT NULL,
    hebrew_file VARCHAR(500) NOT NULL,
    confidence_score FLOAT,
    recommendation VARCHAR(50),
    sentence_ratio FLOAT,
    title_similarity FLOAT,
    content_alignment FLOAT,
    proper_noun_overlap FLOAT,
    numeric_overlap FLOAT,
    chapter_structure FLOAT,
    warnings JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(spanish_file, hebrew_file)
);

CREATE INDEX idx_book_validation_status ON book_validation_results(status);
CREATE INDEX idx_book_validation_confidence ON book_validation_results(confidence_score);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_sense_clusters_updated_at BEFORE UPDATE
    ON sense_clusters FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cluster_metadata_updated_at BEFORE UPDATE
    ON cluster_metadata FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE sense_clusters IS 'Stores clustered word senses discovered from Spanish-Hebrew corpus';
COMMENT ON TABLE cluster_metadata IS 'Stores manual annotations and meaning definitions for sense clusters';
COMMENT ON TABLE aligned_book_sentences IS 'Stores aligned Spanish-Hebrew sentence pairs from books';
COMMENT ON TABLE book_validation_results IS 'Stores validation results for book pair alignments';
