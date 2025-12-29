-- Enable the pgvector extension to work with embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for storing sentence embeddings
CREATE TABLE IF NOT EXISTS sentence_embeddings (
    id BIGSERIAL PRIMARY KEY,
    text_sha256 CHAR(64) NOT NULL, -- SHA256 hash for fast exact-match lookup
    text TEXT NOT NULL,
    embedding VECTOR(768), -- LaBSE has 768 dimensions
    language VARCHAR(5) NOT NULL, -- 'es' or 'he'
    book_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb, -- Flexible source metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(text_sha256, language, book_id)
);

-- Index for approximate nearest neighbor search (for future cross-book semantic search)
CREATE INDEX ON sentence_embeddings USING ivfflat (embedding vector_cosine_ops);
