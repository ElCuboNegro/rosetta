import hashlib
import json
import logging
from typing import Dict, List

import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        dbname="rosetta",
        user="postgres",
        password="rosetta_password",
        host="localhost",
        port="5432",
    ):
        self.conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port,
        }
        self._conn = None

    def get_conn(self):
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg2.connect(**self.conn_params)
                register_vector(self._conn)
            except Exception as e:
                logger.error(f"Failed to connect to vector database: {e}")
                return None
        return self._conn

    def _get_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_cached_embeddings(
        self, texts: List[str], language: str, book_id: str
    ) -> Dict[str, np.ndarray]:
        """Fetch existing embeddings from cache."""
        conn = self.get_conn()
        if not conn:
            return {}

        hashes = [self._get_hash(t) for t in texts]
        results = {}

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT text_sha256, embedding FROM sentence_embeddings WHERE text_sha256 = ANY(%s) AND language = %s AND book_id = %s",
                    (hashes, language, book_id),
                )
                for sha, emb in cur.fetchall():
                    results[sha] = np.array(emb)
        except Exception as e:
            logger.error(f"Error fetching from vector cache: {e}")

        return results

    def upsert_embeddings(
        self,
        texts: List[str],
        embeddings: np.ndarray,
        language: str,
        book_id: str,
        metadata: List[Dict] = None,
    ):
        """Bulk insert embeddings into the cache."""
        conn = self.get_conn()
        if not conn:
            return

        if metadata is None:
            metadata = [{} for _ in texts]

        data = []
        for text, emb, meta in zip(texts, embeddings, metadata):
            data.append(
                (self._get_hash(text), text, emb.tolist(), language, book_id, json.dumps(meta))
            )

        try:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO sentence_embeddings (text_sha256, text, embedding, language, book_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (text_sha256, language, book_id) DO UPDATE
                    SET metadata = sentence_embeddings.metadata || EXCLUDED.metadata
                    """,
                    data,
                )
            conn.commit()
            logger.info(f"Cached {len(data)} embeddings for {book_id} ({language})")
        except Exception as e:
            logger.error(f"Error upserting to vector cache: {e}")
            conn.rollback()

    def __del__(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
