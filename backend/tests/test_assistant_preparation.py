import copy
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from backend import app as api
from backend.rule_assistant import ModelRuleAnswer, ModelAnswerReview, knowledge, retrieve, source_fingerprint
from scripts.prepare_assistant import prepare


class AssistantPreparationTests(unittest.TestCase):
    def setUp(self):
        self.game = {'id': 'test', 'n': 'Test', 'r': [['Original', 'Draw one card.']], 'st': []}
        source = knowledge(self.game)[0]
        self.hint = {'source_id': source.id, 'source_hash': source_fingerprint(source),
                     'questions': ['กองจั่วว่างต้องทำอะไร']}
        self.bank = {'test': [['R1', self.hint['questions'], 'คำถามใหม่']],
                     '_source_hashes': {'test': {'R1': self.hint['source_hash']}}}

    def test_thai_question_finds_english_evidence_without_changing_it(self):
        question = self.hint['questions'][0]
        self.assertEqual(retrieve(knowledge(self.game), question), [])
        source = knowledge({**self.game, 'retrieval_hints': [self.hint]})[0]
        self.assertEqual(retrieve([source], question)[0].id, 'R1')
        self.assertEqual(source.content, 'Draw one card.')
        self.assertNotIn(question, str(source.model_dump()))
        self.assertNotIn(question, source.model_dump_json())

    def test_change_to_any_part_of_source_invalidates_hint(self):
        changed = {**self.game, 'r': [['Original', 'Draw one card. Except when skipped.']],
                   'retrieval_hints': [self.hint]}
        self.assertEqual(knowledge(changed)[0].search_text, '')

    def test_missing_source_and_malformed_hints_are_ignored(self):
        hints = [None, 'bad', {**self.hint, 'source_id': 'R9'},
                 {**self.hint, 'source_id': []},
                 {**self.hint, 'questions': 'not a list'}]
        self.assertEqual(knowledge({**self.game, 'retrieval_hints': hints})[0].search_text, '')

    def test_hints_cannot_create_evidence_or_reviewed_answers(self):
        game = {**self.game, 'retrieval_hints': [self.hint]}
        self.assertEqual(len(knowledge(game)), 1)
        self.assertNotIn('verified_qa', game)
        self.assertEqual(knowledge(self.game)[0].search_text, '')

    def test_reapplying_preserves_custom_data_and_does_not_duplicate_bank(self):
        custom = {**self.hint, 'questions': ['คำถามส่วนตัว']}
        original = {**self.game, 'retrieval_hints': [custom], 'verified_qa': [{'answer': 'unchanged'}]}
        staged, cases = prepare([original], self.bank)
        again, _ = prepare(staged, self.bank)
        self.assertEqual(staged, again)
        self.assertEqual(len(staged[0]['retrieval_hints']), 2)
        self.assertEqual(staged[0]['verified_qa'], original['verified_qa'])
        self.assertEqual([c['split'] for c in cases], ['preparation', 'heldout'])
        self.assertNotIn('คำถามใหม่', staged[0]['retrieval_hints'][1]['questions'])

    def test_stale_bank_fails_before_database_write(self):
        bank = copy.deepcopy(self.bank)
        bank['_source_hashes']['test']['R1'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            prepare([self.game], bank)

    def test_ollama_schema_limits_answer_and_review_to_current_evidence(self):
        for result_type, raw, field in (
            (ModelRuleAnswer, {'status': 'answered', 'answer': 'Draw one card from the deck.', 'source_ids': ['R1']}, 'source_ids'),
            (ModelAnswerReview, {'verdict': 'supported', 'source_id': 'R1', 'quote': 'Draw one card.'}, 'source_id'),
        ):
            client = AsyncMock()
            client.__aenter__.return_value = client
            response = Mock()
            response.json.return_value = {'message': {'content': json.dumps(raw)}}
            client.post.return_value = response
            with patch.object(api.httpx, 'AsyncClient', return_value=client):
                asyncio.run(api.request_structured_content('question', 'system', result_type, context_window=4096, allowed_source_ids=['R1', 'M2']))
            schema = client.post.await_args.kwargs['json']['format']['properties'][field]
            if field == 'source_ids':
                schema = schema['items']
            self.assertEqual(schema['enum'], ['R1', 'M2'])
            request = client.post.await_args.kwargs['json']
            self.assertEqual(request['options']['num_ctx'], 8192)
            self.assertEqual(request['keep_alive'], '30m')
            if field == 'source_ids':
                self.assertIn('source_ids', request['format']['required'])
            fresh = result_type.model_json_schema()['properties'][field]
            self.assertNotIn('enum', fresh.get('items', fresh))

    def test_hybrid_manual_match_is_not_displaced_by_lexical_noise(self):
        game = {'id': 'test', 'n': 'Test', 'pub': 1,
                'r': [[f'Rule {i}', 'Unrelated summary.'] for i in range(6)],
                'source_text': 'The guard must draw a card if the accusation is wrong.'}
        sources = knowledge(game)
        manual = sources[-1]
        with patch.object(api, 'read_games', return_value=[game]), \
             patch.object(api, 'resolve_context', return_value=(sources[:5], None)), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=[manual])), \
             patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[
                 ModelRuleAnswer(status='answered', answer='ยามต้องจั่วการ์ดหากกล่าวหาผิด', source_ids=[manual.id]),
                 ModelAnswerReview(verdict='supported', source_id=manual.id, quote=manual.content),
             ])):
            result = asyncio.run(api.ask_game_rule('test', api.RuleQuestion(question='กล่าวหาผิดต้องทำอะไร'), None))
        self.assertEqual(result.status, 'answered')
        self.assertEqual(result.sources[0].id, manual.id)


if __name__ == '__main__':
    unittest.main()
