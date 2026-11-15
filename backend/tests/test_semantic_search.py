import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from backend import semantic_search as search
from backend.rule_assistant import RuleSource


class SemanticSearchTests(unittest.TestCase):
    def test_cross_language_passage_can_be_found_without_literal_word_match(self):
        sources = [RuleSource(id='M1', title='Loans', kind='คู่มือต้นฉบับ', content='Players may not borrow money.'),
                   RuleSource(id='M2', title='Setup', kind='คู่มือต้นฉบับ', content='Shuffle the deck.')]
        with patch.object(search, 'embeddings', new=AsyncMock(return_value=[[1.,0.],[.99,.01],[0.,1.]])):
            results = asyncio.run(search.hybrid_retrieve(sources, 'ขอเงินคนอื่นได้ไหม'))
        self.assertEqual([source.id for source in results], ['M1'])

    def test_missing_embedding_service_keeps_literal_search_available(self):
        sources = [RuleSource(id='R1', title='Nope', kind='กฎ', content='ยกเลิกแอ็กชันได้')]
        with patch.object(search, 'embeddings', new=AsyncMock(side_effect=httpx.ConnectError('offline'))):
            results = asyncio.run(search.hybrid_retrieve(sources, 'Nope คืออะไร'))
        self.assertEqual(results[0].id, 'R1')

    def test_cache_reuses_vectors_but_new_content_has_a_new_key(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(search, 'CACHE_PATH', Path(directory)/'cache.sqlite3'):
            response = Mock()
            response.json.return_value = {'embeddings': [[1.,0.]]}
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.post.return_value = response
            with patch.object(search.httpx, 'AsyncClient', return_value=client):
                self.assertEqual(asyncio.run(search.embeddings(['rule one'])), [[1.,0.]])
                self.assertEqual(asyncio.run(search.embeddings(['rule one'])), [[1.,0.]])
                self.assertEqual(client.post.await_count, 1)
                asyncio.run(search.embeddings(['rule changed']))
                self.assertEqual(client.post.await_count, 2)

    def test_zero_vectors_are_not_matches(self):
        self.assertEqual(search.cosine([0.,0.], [1.,0.]), 0)
        self.assertEqual(search.cosine([1.], [1.,0.]), 0)


if __name__ == '__main__':
    unittest.main()
