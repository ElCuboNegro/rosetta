-- Book Catalog Metadata Tables
-- Stores metadata about Gutenberg and Ben Yehuda book collections

-- Gutenberg catalog (Spanish books)
CREATE TABLE IF NOT EXISTS gutenberg_catalog (
    id BIGSERIAL PRIMARY KEY,
    gutenberg_id VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(1000),
    author VARCHAR(500),
    language VARCHAR(50),
    subjects JSONB DEFAULT '[]'::jsonb,
    bookshelves JSONB DEFAULT '[]'::jsonb,
    download_url VARCHAR(1000),
    file_path VARCHAR(1000),
    file_size BIGINT,
    encoding VARCHAR(50),
    downloads INTEGER,
    release_date DATE,
    copyright_status VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gutenberg_id ON gutenberg_catalog(gutenberg_id);
CREATE INDEX idx_gutenberg_title ON gutenberg_catalog(title);
CREATE INDEX idx_gutenberg_author ON gutenberg_catalog(author);
CREATE INDEX idx_gutenberg_language ON gutenberg_catalog(language);
CREATE INDEX idx_gutenberg_downloads ON gutenberg_catalog(downloads);

-- Full-text search on title and author
CREATE INDEX idx_gutenberg_title_text ON gutenberg_catalog USING GIN (to_tsvector('spanish', title));
CREATE INDEX idx_gutenberg_author_text ON gutenberg_catalog USING GIN (to_tsvector('spanish', author));

-- Ben Yehuda catalog (Hebrew books) - raw
CREATE TABLE IF NOT EXISTS benyehuda_catalog_raw (
    id BIGSERIAL PRIMARY KEY,
    book_id VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(1000),
    author VARCHAR(500),
    translator VARCHAR(500),
    genre VARCHAR(200),
    original_language VARCHAR(50),
    publication_year INTEGER,
    download_url VARCHAR(1000),
    file_path VARCHAR(1000),
    file_size BIGINT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_benyehuda_raw_id ON benyehuda_catalog_raw(book_id);
CREATE INDEX idx_benyehuda_raw_title ON benyehuda_catalog_raw(title);
CREATE INDEX idx_benyehuda_raw_author ON benyehuda_catalog_raw(author);
CREATE INDEX idx_benyehuda_raw_genre ON benyehuda_catalog_raw(genre);

-- Full-text search (Hebrew uses 'simple' dictionary)
CREATE INDEX idx_benyehuda_raw_title_text ON benyehuda_catalog_raw USING GIN (to_tsvector('simple', title));
CREATE INDEX idx_benyehuda_raw_author_text ON benyehuda_catalog_raw USING GIN (to_tsvector('simple', author));

-- Ben Yehuda catalog (enriched with additional metadata)
CREATE TABLE IF NOT EXISTS benyehuda_catalog_enriched (
    id BIGSERIAL PRIMARY KEY,
    book_id VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(1000),
    title_normalized VARCHAR(1000),  -- For matching
    author VARCHAR(500),
    author_normalized VARCHAR(500),  -- For matching
    translator VARCHAR(500),
    genre VARCHAR(200),
    original_language VARCHAR(50),
    publication_year INTEGER,
    download_url VARCHAR(1000),
    file_path VARCHAR(1000),
    file_size BIGINT,
    word_count INTEGER,
    chapter_count INTEGER,
    sentence_count INTEGER,
    enrichment_metadata JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_benyehuda_enriched_id ON benyehuda_catalog_enriched(book_id);
CREATE INDEX idx_benyehuda_enriched_title ON benyehuda_catalog_enriched(title);
CREATE INDEX idx_benyehuda_enriched_author ON benyehuda_catalog_enriched(author);
CREATE INDEX idx_benyehuda_enriched_title_norm ON benyehuda_catalog_enriched(title_normalized);
CREATE INDEX idx_benyehuda_enriched_author_norm ON benyehuda_catalog_enriched(author_normalized);

-- Aligned catalogs (matched Spanish-Hebrew book pairs)
CREATE TABLE IF NOT EXISTS aligned_catalogs (
    id BIGSERIAL PRIMARY KEY,
    gutenberg_id VARCHAR(100) NOT NULL,
    benyehuda_id VARCHAR(100) NOT NULL,
    spanish_title VARCHAR(1000),
    hebrew_title VARCHAR(1000),
    spanish_author VARCHAR(500),
    hebrew_author VARCHAR(500),
    match_score FLOAT,
    match_method VARCHAR(100),
    title_similarity FLOAT,
    author_similarity FLOAT,
    is_translation BOOLEAN DEFAULT false,
    validation_status VARCHAR(50) DEFAULT 'pending',  -- pending, validated, rejected
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(gutenberg_id, benyehuda_id)
);

CREATE INDEX idx_aligned_catalogs_gutenberg ON aligned_catalogs(gutenberg_id);
CREATE INDEX idx_aligned_catalogs_benyehuda ON aligned_catalogs(benyehuda_id);
CREATE INDEX idx_aligned_catalogs_score ON aligned_catalogs(match_score);
CREATE INDEX idx_aligned_catalogs_status ON aligned_catalogs(validation_status);

-- Download manifests (track what has been downloaded)
CREATE TABLE IF NOT EXISTS download_manifests (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,  -- 'gutenberg', 'ben_yehuda', 'gutenberg_counterparts'
    file_id VARCHAR(200) NOT NULL,
    file_path VARCHAR(1000),
    download_date TIMESTAMP WITH TIME ZONE,
    file_size BIGINT,
    checksum VARCHAR(100),
    status VARCHAR(50),  -- 'downloaded', 'processed', 'failed'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, file_id)
);

CREATE INDEX idx_manifests_source ON download_manifests(source);
CREATE INDEX idx_manifests_status ON download_manifests(status);
CREATE INDEX idx_manifests_file_id ON download_manifests(file_id);

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_gutenberg_catalog_updated_at BEFORE UPDATE
    ON gutenberg_catalog FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_benyehuda_catalog_raw_updated_at BEFORE UPDATE
    ON benyehuda_catalog_raw FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_benyehuda_catalog_enriched_updated_at BEFORE UPDATE
    ON benyehuda_catalog_enriched FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_aligned_catalogs_updated_at BEFORE UPDATE
    ON aligned_catalogs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE gutenberg_catalog IS 'Metadata for Spanish books from Project Gutenberg';
COMMENT ON TABLE benyehuda_catalog_raw IS 'Raw metadata for Hebrew books from Ben Yehuda Project';
COMMENT ON TABLE benyehuda_catalog_enriched IS 'Enriched Hebrew book metadata with text statistics';
COMMENT ON TABLE aligned_catalogs IS 'Matched Spanish-Hebrew book pairs for translation alignment';
COMMENT ON TABLE download_manifests IS 'Tracks downloaded files from all sources';
