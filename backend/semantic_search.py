"""Local multilingual retrieval with a persistent, content-addressed cache."""
import hashlib
import json
import logging
import math
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import httpx

from backend.rule_assistant import RuleSource, retrieve

LOGGER = logging.getLogger(__name__)
CACHE_PATH = Path(__file__).parent / "data" / "embeddings.sqlite3"


def cache_key(model: str, text: str) -> str:
    return hashlib.sha256((model + "\n" + text).encode()).hexdigest()


def read_cache(keys: list[str]) -> dict[str, list[float]]:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(CACHE_PATH, timeout=10)) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector TEXT NOT NULL)")
        connection.commit()
        found = {}
        for key in keys:
            row = connection.execute("SELECT vector FROM vectors WHERE key = ?", (key,)).fetchone()
            if row:
                found[key] = json.loads(row[0])
        return found


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0
    denominator = math.sqrt(sum(x*x for x in left) * sum(x*x for x in right))
    return sum(a*b for a, b in zip(left, right)) / denominator if denominator else 0


async def embeddings(texts: list[str]) -> list[list[float]]:
    model = os.environ.get("BGT_EMBED_MODEL", "embeddinggemma")
    keys = [cache_key(model, text) for text in texts]
    cached = read_cache(keys)
    missing = list(dict.fromkeys(key for key in keys if key not in cached))
    inputs = dict(zip(keys, texts))
    if missing:
        base = os.environ.get("BGT_OLLAMA_URL", "http://127.0.0.1:11434").rstrip('/')
        async with httpx.AsyncClient(timeout=60) as client:
            for start in range(0, len(missing), 8):
                batch = missing[start:start+8]
                response = await client.post(base + '/api/embed', json={
                    "model": model, "input": [inputs[key] for key in batch],
                    "truncate": False, "keep_alive": "5m", "options": {"num_gpu": 0},
                })
                response.raise_for_status()
                vectors = response.json()['embeddings']
                if len(vectors) != len(batch) or any(not vector or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in vector) for vector in vectors):
                    raise ValueError('Invalid embeddings response')
                with closing(sqlite3.connect(CACHE_PATH, timeout=10)) as connection:
                    for key, vector in zip(batch, vectors):
                        cached[key] = vector
                        connection.execute('INSERT OR REPLACE INTO vectors VALUES (?, ?)', (key, json.dumps(vector)))
                    connection.commit()
    return [cached[key] for key in keys]


async def hybrid_retrieve(sources: list[RuleSource], question: str, limit: int = 4):
    lexical = retrieve(sources, question, limit)
    if not sources or os.environ.get('BGT_SEMANTIC_SEARCH', '1') == '0':
        return lexical
    # Passage windows are used for scoring only; cited evidence stays complete.
    windows = [(source, source.content[i:i+1100]) for source in sources for i in range(0, len(source.content), 950)]
    texts = ['task: search result | query: ' + question]
    texts += ['title: ' + source.title + ' | text: ' + text for source, text in windows]
    try:
        vectors = await embeddings(texts)
        scores = {}
        for (source, _), vector in zip(windows, vectors[1:]):
            scores[source.id] = max(scores.get(source.id, -1), cosine(vectors[0], vector))
        ranked = sorted(sources, key=lambda source: scores.get(source.id, -1), reverse=True)
        semantic = [source for source in ranked if scores.get(source.id, 0) >= .5][:limit]
        # Reciprocal rank fusion: semantic matches can add passages but cannot
        # pull facts from another game because only this game's sources enter.
        fused = {}
        for ranking in (lexical, semantic):
            for rank, source in enumerate(ranking):
                fused[source.id] = fused.get(source.id, 0) + 1 / (30 + rank)
        return sorted([source for source in sources if source.id in fused], key=lambda source: fused[source.id], reverse=True)[:limit]
    except (httpx.HTTPError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        LOGGER.warning('Semantic retrieval unavailable (%s); using text retrieval', type(error).__name__)
        return lexical
