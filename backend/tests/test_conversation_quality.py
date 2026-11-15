import json
import os
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
import httpx

from fastapi.testclient import TestClient
from backend import app as api
from backend.rule_assistant import (
    ChatTurn, ModelAnswerReview, ModelRuleAnswer, ModelQuestionContext, RuleSource,
    compatible_conditions, conversation_for_question, knowledge,
    matching_reviewed_candidates, original_evidence, resolve_context,
    preserves_question,
    needs_situation_context, explicit_count_followup,
    named_situation_is_complete,
    focused_source,
    canonical_source_quote, PERMISSION_ANSWERS,
    permission_quote_conflicts,
)


class ConversationQualityTests(unittest.TestCase):
    def test_named_exceptions_and_prohibitions_cannot_be_overridden_by_model_approval(self):
        self.assertTrue(permission_quote_conflicts('Alpha ใช้กับ Beta ได้ไหม', 'Stop any action except Beta and Gamma.'))
        self.assertFalse(permission_quote_conflicts('Alpha ใช้กับ Delta ได้ไหม', 'Stop any action except Beta and Gamma.'))
        self.assertTrue(permission_quote_conflicts('ใช้ Alpha ต่อได้ไหม', 'Alpha cannot be played again.'))
        self.assertTrue(permission_quote_conflicts('โกงได้ไหม', 'ห้ามโกงในระหว่างตัดสิน'))
        self.assertFalse(permission_quote_conflicts('Alpha ใช้ Alpha ต่อได้ไหม', 'If the victim plays Alpha, the effects stack.'))

    def test_literal_exception_blocks_a_false_allowed_answer_before_review_and_cache(self):
        import asyncio
        text = 'Alpha stops any action except Beta.'
        game = {'id': 'exception-test', 'n': 'Test', 'pub': 1, 'r': [['Alpha', text]]}
        with patch.object(api, 'ASSISTANT_ANSWER_CACHE', OrderedDict()), \
             patch.object(api, 'read_games', return_value=[game]), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=[])), \
             patch.object(api, 'request_structured_content', new=AsyncMock(return_value=
                 ModelRuleAnswer(status='answered', answer=PERMISSION_ANSWERS[0], source_quote=text, source_ids=['R1']))) as model:
            answer = asyncio.run(api.ask_game_rule('exception-test', api.RuleQuestion(question='Alpha ใช้กับ Beta ได้ไหม'), None))
            self.assertEqual(answer.status, 'excerpt')
            self.assertEqual(len(api.ASSISTANT_ANSWER_CACHE), 0)
        self.assertEqual(model.await_count, 1)
        self.assertIn('ข้อห้ามหรือข้อยกเว้น', answer.answer)

    def test_quote_format_recovery_keeps_original_trailing_conditions_and_numbers(self):
        text = 'Alpha may continue, unless Beta blocks it. Spend 4.0 coins.'
        self.assertEqual(canonical_source_quote('Alpha may continue.', text), 'Alpha may continue, unless Beta blocks it.')
        self.assertIsNone(canonical_source_quote('Alpha can.', 'Alpha cannot continue.'))
        self.assertIsNone(canonical_source_quote('Spend 40 coins.', text))
        self.assertEqual(canonical_source_quote("It's allowed.", 'It’s allowed.'), 'It’s allowed.')
        self.assertEqual(canonical_source_quote('Alpha may continue, unless Beta blocks it.', text.replace('continue, ', 'continue,\n')), text.replace('continue, ', 'continue,\n').split(' Spend')[0])

    def test_permission_schema_cannot_generate_extra_scenario_details(self):
        import asyncio
        client = AsyncMock(); client.__aenter__.return_value = client
        response = Mock()
        response.json.return_value = {'message': {'content': json.dumps({
            'source_quote': 'Alpha may continue.', 'status': 'answered',
            'answer': PERMISSION_ANSWERS[0], 'source_ids': ['R1']})}}
        client.post.return_value = response
        with patch.object(api.httpx, 'AsyncClient', return_value=client):
            asyncio.run(api.request_structured_content('question', 'system', ModelRuleAnswer, concise_permission=True))
        schema = client.post.await_args.kwargs['json']['format']
        self.assertEqual(schema['properties']['answer']['enum'], list(PERMISSION_ANSWERS))
        self.assertIn('source_quote', schema['required'])

    def test_negative_review_must_explain_the_specific_problem_without_being_turned_into_approval(self):
        import asyncio
        client = AsyncMock(); client.__aenter__.return_value = client
        responses = []
        for issue in ['', 'The cited rule explicitly prohibits this play.']:
            response = Mock()
            response.json.return_value = {'message': {'content': json.dumps({
                'verdict': 'unsupported', 'issue': issue, 'source_id': 'R1', 'quote': 'Alpha cannot be played.'})}}
            responses.append(response)
        client.post.side_effect = responses
        with patch.object(api.httpx, 'AsyncClient', return_value=client):
            result = asyncio.run(api.request_structured_content('question', 'system', ModelAnswerReview))
        self.assertEqual(result.verdict, 'unsupported')
        self.assertTrue(result.issue)
        self.assertEqual(client.post.await_count, 2)
        self.assertIn('issue', client.post.await_args.kwargs['json']['format']['required'])

    def test_definition_answers_are_not_candidates_for_permission_scenarios(self):
        source = RuleSource(id='Q1', title='Alpha คืออะไร', kind='คำตอบตรวจเทียบกฎ', content='A definition')
        self.assertEqual(matching_reviewed_candidates([source], 'ถ้าโดน Alpha ใช้ Alpha ต่อได้ไหม'), [])

    def test_original_rules_drive_generation_while_review_still_checks_conflicting_summaries(self):
        import asyncio
        game = {'id': 'primary-test', 'n': 'Test', 'pub': 1,
                'r': [['Alpha', 'Alpha cannot be played twice.']],
                'source_text': 'Alpha may be played after another Alpha.'}
        with patch.object(api, 'read_games', return_value=[game]), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=knowledge(game))), \
             patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[
                 ModelRuleAnswer(status='answered', answer='ใช้ Alpha ต่อจาก Alpha ได้ตามคู่มือต้นฉบับ', source_ids=['M2']),
                 ModelAnswerReview(verdict='unclear', source_id='M2', quote=game['source_text']),
             ])) as model:
            answer = asyncio.run(api.ask_game_rule('primary-test', api.RuleQuestion(question='ใช้ Alpha ต่อจาก Alpha ได้ไหม'), None))
        generated = json.loads(model.await_args_list[0].args[0])['evidence']
        reviewed = json.loads(model.await_args_list[1].args[0])['evidence']
        self.assertEqual([e['id'] for e in generated], ['M2'])
        self.assertEqual({e['id'] for e in reviewed}, {'R1', 'M2'})
        self.assertEqual(answer.status, 'excerpt')

    def test_live_answer_cache_reuses_only_supported_answers_and_invalidates_on_rule_edit(self):
        import asyncio
        game = {'id': 'cache-test', 'n': 'Test', 'pub': 1, 'r': [['Alpha', 'Alpha can be played twice.']]}
        checked = ModelRuleAnswer(status='answered', answer='ใช้ Alpha ต่ออีกใบได้ตามกฎที่บันทึกไว้', source_ids=['R1'])
        review = ModelAnswerReview(verdict='supported', source_id='R1', quote='Alpha can be played twice.')
        with patch.object(api, 'ASSISTANT_ANSWER_CACHE', OrderedDict()), \
             patch.object(api, 'read_games', side_effect=lambda: [game]), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=[])), \
             patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[checked, review, checked, review])) as model:
            request = api.RuleQuestion(question='ใช้ Alpha ต่อได้ไหม')
            first = asyncio.run(api.ask_game_rule('cache-test', request, None))
            again = asyncio.run(api.ask_game_rule('cache-test', request, None))
            self.assertEqual(model.await_count, 2)
            self.assertEqual(first, again)
            self.assertEqual(again.method, 'model')
            game['r'][0][1] += ' Check the current round first.'
            changed = asyncio.run(api.ask_game_rule('cache-test', request, None))
            self.assertEqual(model.await_count, 4)
            self.assertIn('Check the current round first.', changed.sources[0].content)

    def test_rejected_answers_are_not_cached(self):
        import asyncio
        game = {'id': 'cache-test', 'n': 'Test', 'pub': 1, 'r': [['Alpha', 'Alpha cannot be played twice.']]}
        proposed = ModelRuleAnswer(status='answered', answer='ใช้ Alpha ต่ออีกใบได้อย่างแน่นอน', source_ids=['R1'])
        review = ModelAnswerReview(verdict='unsupported', source_id='R1', quote='Alpha cannot be played twice.')
        with patch.object(api, 'ASSISTANT_ANSWER_CACHE', OrderedDict()), \
             patch.object(api, 'read_games', return_value=[game]), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=[])), \
             patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[proposed, review, proposed, review])) as model:
            for _ in range(2):
                self.assertEqual(asyncio.run(api.ask_game_rule('cache-test', api.RuleQuestion(question='ใช้ Alpha ต่อได้ไหม'), None)).status, 'excerpt')
            self.assertEqual(model.await_count, 4)
            self.assertEqual(len(api.ASSISTANT_ANSWER_CACHE), 0)

    def test_long_rules_focus_on_named_actions_with_adjacent_exceptions(self):
        content = ('Unrelated setup instructions. ' * 160 +
                   'Alpha may be played after another Alpha. Unless the player has already ended the round, the effect stacks. '
                   + 'Other setup details. ' * 100)
        source = RuleSource(id='M1', title='Manual', kind='คู่มือต้นฉบับ', content=content)
        focused = focused_source(source, 'ใช้ Alpha ซ้อนได้ไหม')
        self.assertTrue(focused['is_excerpt'])
        self.assertIn('Alpha may be played after another Alpha.', focused['content'])
        self.assertIn('Unless the player has already ended the round', focused['content'])
        self.assertLess(len(focused['content']), 1800)
        self.assertEqual(source.content, content)

    def test_unmatched_or_unsplittable_sources_remain_complete(self):
        source = RuleSource(id='M1', title='Manual', kind='คู่มือต้นฉบับ', content='Alpha ' * 600)
        self.assertEqual(focused_source(source, 'ใช้ Alpha ได้ไหม')['content'], source.content)
        self.assertEqual(focused_source(source, 'เตรียมเกมอย่างไร')['content'], source.content)

    def test_answer_and_review_share_passages_but_reader_gets_full_original(self):
        import asyncio
        content = 'Unrelated setup instructions. ' * 160 + 'Alpha may be played after another Alpha. The effects stack.'
        game = {'id': 'test', 'n': 'Test', 'pub': 1, 'source_text': content}
        with patch.object(api, 'read_games', return_value=[game]), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=knowledge(game))), \
             patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[
                 ModelRuleAnswer(status='answered', answer='ใช้ Alpha ต่อจาก Alpha อีกใบได้ตามกฎ', source_ids=['M1']),
                 ModelAnswerReview(verdict='supported', source_id='M1', quote='Alpha may be played after another Alpha.'),
             ])) as model:
            answer = asyncio.run(api.ask_game_rule('test', api.RuleQuestion(question='ใช้ Alpha ซ้อนได้ไหม'), None))
        generation = json.loads(model.await_args_list[0].args[0])['evidence'][0]
        review = json.loads(model.await_args_list[1].args[0])['evidence'][0]
        self.assertEqual(generation, review)
        self.assertTrue(generation['is_excerpt'])
        self.assertEqual(answer.sources[0].content, content)
        self.assertNotIn('is_excerpt', answer.sources[0].model_dump())

    def test_explicit_named_scenario_does_not_need_an_extra_context_model(self):
        history = [ChatTurn(role='user', content='Attack คืออะไร')]
        for question in ['ถ้าโดน Attack สามารถใช้ Attack ต่อได้ไหม', 'ถ้าโดน Attack ใช้ Skip ได้ไหม', 'Can I use Nope on Attack?']:
            with self.subTest(question=question):
                self.assertTrue(named_situation_is_complete(question))
                self.assertFalse(needs_situation_context(question, history))
        self.assertFalse(named_situation_is_complete('ถ้าใช้มันกับ Attack ได้ไหม'))
        self.assertFalse(named_situation_is_complete('ถ้าโดน Attack ใช้การ์ดนี้กับ Attack ได้ไหม'))
        self.assertFalse(named_situation_is_complete('ถ้าใช้ Attack ได้ไหม'))
        self.assertTrue(needs_situation_context('ถ้าใช้มันกับ Attack ได้ไหม', history))

    def test_chat_timeout_has_no_manual_upload_instructions(self):
        import asyncio
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.side_effect = httpx.ReadTimeout('slow')
        with patch.object(api.httpx, 'AsyncClient', return_value=client), \
             patch.dict(os.environ, {'BGT_ASSISTANT_NUM_GPU': '0'}):
            with self.assertRaises(api.HTTPException) as error:
                asyncio.run(api.request_structured_content('question', 'system', ModelRuleAnswer))
        self.assertEqual(error.exception.status_code, 504)
        self.assertNotIn('คู่มือ', error.exception.detail)
        self.assertEqual(client.post.await_args.kwargs['json']['options']['num_gpu'], 0)

    def test_short_elliptical_followups_use_context_but_complete_new_questions_do_not(self):
        history = [ChatTurn(role='user', content='ทำได้กี่ครั้ง')]
        for question in ['สองครั้งได้ไหม', '3 ใบล่ะ', 'อีกคนได้ไหม', 'ไม่ทำได้ไหม', 'อีกสองครั้งได้ไหม']:
            with self.subTest(question=question):
                self.assertTrue(needs_situation_context(question, history))
        self.assertFalse(needs_situation_context('สองครั้งได้ไหม', []))
        self.assertFalse(needs_situation_context('เงินเริ่มเกมมีเท่าไร', history))

    def count_fixture(self, content='ตรวจผู้เล่นได้หนึ่งคนต่อคืน', quote=None):
        unit = next(unit for unit in ['ครั้ง', 'ใบ', 'คน', 'รอบ', 'ตา'] if unit in content)
        game = {'r': [['ตรวจผู้เล่น', content]], 'verified_qa': [{
            'question': f'ทำได้กี่{unit}ต่อรอบ', 'answer': content,
            'source_id': 'R1', 'quote': quote or content, 'reviewed': True}]}
        history = [ChatTurn(role='user', content=game['verified_qa'][0]['question']),
                   ChatTurn(role='assistant', content=content, status='answered', source_ids=['R1'])]
        return game, knowledge(game), history

    def test_exceeding_a_current_inspected_count_is_answered_without_a_model(self):
        for content, question in [('ตรวจผู้เล่นได้หนึ่งคนต่อคืน', 'สองคนได้ไหม'),
                                  ('จั่วได้สามใบต่อรอบตามกฎ', '4 ใบได้ไหม'),
                                  ('ทายได้ครั้งเดียวต่อรอบเท่านั้น', 'สองครั้งได้ไหม')]:
            game, sources, history = self.count_fixture(content)
            with self.subTest(question=question):
                result = explicit_count_followup(game, sources, question, history)
                self.assertIsNotNone(result)
                self.assertEqual(result.source_ids, ['R1'])
                self.assertIn('ไม่ได้ครับ', result.answer)

    def test_count_comparison_does_not_invent_scope_or_override_exceptions(self):
        for content, question in [('ตรวจได้อย่างน้อยหนึ่งคนต่อคืน', 'สองคนได้ไหม'),
                                  ('ตรวจผู้เล่นได้หนึ่งคนต่อคืน ยกเว้นใช้พลังพิเศษ', 'สองคนได้ไหม'),
                                  ('ตรวจผู้เล่นได้ยี่สิบคนต่อคืน', '15 คนได้ไหม'),
                                  ('ตรวจผู้เล่นได้1,000คนต่อคืน', '15 คนได้ไหม'),
                                  ('ตรวจผู้เล่นได้หนึ่งคนต่อคืน', 'สองใบได้ไหม'),
                                  ('ตรวจผู้เล่นได้หนึ่งคนต่อคืน', 'ศูนย์คนได้ไหม'),
                                  ('ตรวจผู้เล่นได้หนึ่งคนต่อคืน', 'อีกสองคนได้ไหม')]:
            game, sources, history = self.count_fixture(content)
            with self.subTest(question=question):
                self.assertIsNone(explicit_count_followup(game, sources, question, history))
        game, _, history = self.count_fixture()
        game['r'][0][1] = 'กฎแก้ใหม่ที่ไม่มีข้อความตรวจแล้ว'
        self.assertIsNone(explicit_count_followup(game, knowledge(game), 'สองคนได้ไหม', history))
        game, sources, history = self.count_fixture()
        history[-1].status = 'excerpt'
        self.assertIsNone(explicit_count_followup(game, sources, 'สองคนได้ไหม', history))

    def test_count_only_chain_keeps_topic_until_another_question_changes_it(self):
        game, sources, history = self.count_fixture()
        history += [ChatTurn(role='user', content='สองคนได้ไหม'),
                    ChatTurn(role='assistant', content='ไม่ได้ กฎระบุหนึ่งคน', status='answered')]
        self.assertIsNotNone(explicit_count_followup(game, sources, '3 คนได้ไหม', history))
        history += [ChatTurn(role='user', content='อีกบทบาทเล่นยังไง'),
                    ChatTurn(role='assistant', content='คำตอบหัวข้อใหม่', status='answered')]
        self.assertIsNone(explicit_count_followup(game, sources, '3 คนได้ไหม', history))

    def test_endpoint_uses_current_count_evidence_without_calling_the_model(self):
        import asyncio
        game, _, history = self.count_fixture('ทายได้ครั้งเดียวต่อรอบเท่านั้น')
        game.update(id='any-game', n='Test', pub=1)
        with patch.object(api, 'read_games', return_value=[game]), \
             patch.object(api, 'request_structured_content', new=AsyncMock()) as model, \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock()) as search:
            answer = asyncio.run(api.ask_game_rule('any-game', api.RuleQuestion(
                question='สองครั้งได้ไหม', history=history), None))
        self.assertEqual(answer.status, 'answered')
        self.assertEqual(answer.method, 'calculation')
        self.assertEqual(answer.sources[0].id, 'R1')
        model.assert_not_awaited()
        search.assert_not_awaited()

    def test_changed_polarity_and_timing_do_not_reuse_cached_conclusions(self):
        cases = [
            ('จั่วไพ่แล้วทำอะไรต่อ', 'แล้วถ้าไม่จั่วไพ่เลยได้ไหม'),
            ('เปิดการ์ดแล้วเปลี่ยนได้ไหม', 'แล้วถ้าไม่เปิดการ์ดเลยได้ไหม'),
            ('ประมูลแล้วถอนตัวได้เงินคืนไหม', 'ถ้าไม่ประมูลเลยได้เงินคืนไหม'),
            ('ทิ้งไพ่หลังจบรอบได้ไหม', 'ทิ้งไพ่ก่อนจบรอบได้ไหม'),
            ('Can I draw after playing?', 'Can I draw before playing?'),
            ('Can I reveal the card?', 'Can I play without revealing the card?'),
        ]
        for title, question in cases:
            with self.subTest(question=question):
                self.assertFalse(compatible_conditions(question, title))
                source = RuleSource(id='Q1', kind='คำตอบตรวจเทียบกฎ', title=title, content='cached')
                self.assertEqual(matching_reviewed_candidates([source], question), [])

    def test_question_suffix_and_nouns_are_not_negative_actions(self):
        self.assertTrue(compatible_conditions('ใช้ไพ่ได้หรือไม่', 'ใช้ไพ่ได้ไหม'))
        self.assertTrue(compatible_conditions('เผลอพูดคำของตัวเองแล้วคุยต่อได้หรือเปล่า', 'หลุดคำต้องห้ามแล้วยังพูดต่อได้ไหม'))

    def test_subject_resolution_cannot_drop_actions_polarity_numbers_or_timing(self):
        self.assertTrue(preserves_question('แล้วถ้าไม่จั่วสองใบได้ไหม', 'ผู้เล่นปัจจุบัน: ถ้าไม่จั่วสองใบได้ไหม'))
        for resolved in ('ถ้าจั่วสองใบได้ไหม', 'ถ้าไม่จั่วหนึ่งใบได้ไหม', 'หลังจบตา ถ้าไม่จั่วสองใบได้ไหม'):
            self.assertFalse(preserves_question('แล้วถ้าไม่จั่วสองใบได้ไหม', resolved))

    def test_ambiguous_situation_asks_one_question_without_searching_or_answering_rules(self):
        game = {'id': 'test', 'n': 'Test', 'pub': 1, 'r': []}
        with patch.object(api, 'read_games', return_value=[game]), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock()) as search, \
             patch.object(api, 'request_structured_content', new=AsyncMock(return_value=
                 ModelQuestionContext(status='clarify', subject='', question='หมายถึงก่อนเริ่มตาหรือหลังจบตาครับ?'))) as model:
            import asyncio
            result = asyncio.run(api.ask_game_rule('test', api.RuleQuestion(
                question='แล้วถ้าไม่ทำเลยได้ไหม', history=[ChatTurn(role='user', content='จบตาต้องทำอะไร')]), None))
        self.assertEqual(result.status, 'clarify')
        self.assertEqual(result.sources, [])
        self.assertEqual(model.await_count, 1)
        self.assertEqual(model.await_args.args[2], ModelQuestionContext)
        search.assert_not_awaited()
        context = json.loads(model.await_args.args[0])
        self.assertEqual(context['latest_question'], 'แล้วถ้าไม่ทำเลยได้ไหม')
        self.assertNotIn('evidence', context)

    def test_failed_replies_are_not_carried_forward_as_answer_context(self):
        history = [ChatTurn(role='user', content='ใช้การ์ดนี้อย่างไร'),
                   ChatTurn(role='assistant', content='คำตอบที่ตรวจแล้ว', status='answered'),
                   ChatTurn(role='assistant', content='ข้อความเก่าที่ยืนยันไม่ได้', status='excerpt'),
                   ChatTurn(role='assistant', content='ข้อความเก่าที่หาไม่เจอ', status='insufficient'),
                   ChatTurn(role='assistant', content='บริการขัดข้อง', status='error')]
        context = conversation_for_question('แล้วถ้าไม่ใช้เลยล่ะ', history)
        self.assertEqual([x['content'] for x in context], ['ใช้การ์ดนี้อย่างไร', 'คำตอบที่ตรวจแล้ว'])

    def test_middle_of_sentence_then_does_not_restore_old_topic(self):
        history = [ChatTurn(role='user', content='เงินคืนเท่าไร')]
        self.assertEqual(conversation_for_question('หมดเวลาแล้วคิดคะแนนยังไง', history), [])
        self.assertEqual(conversation_for_question('เงินเริ่มต้นมีเท่าไร', history), [])

    def test_excerpt_sources_do_not_anchor_a_vague_followup(self):
        sources = [RuleSource(id='R1', title='Nope', kind='กฎ', content='Nope cancels an action')]
        history = [ChatTurn(role='user', content='สถานการณ์หนึ่ง'),
                   ChatTurn(role='assistant', content='ยังยืนยันไม่ได้', source_ids=['R1'], status='excerpt')]
        hits, _ = resolve_context(sources, 'แล้วอันนี้ล่ะ', history)
        # No valid last answer exists from which to inherit a conclusion.
        self.assertEqual(hits, [])
        self.assertEqual(conversation_for_question('แล้วอันนี้ล่ะ', history)[-1]['role'], 'user')

    def test_related_qa_locates_original_rules_without_inserting_old_question(self):
        game = {'r': [['การจั่ว', 'เมื่อจบตาให้จั่วหนึ่งใบ']], 'verified_qa': [
            {'question': 'ต้องจั่วกี่ใบ', 'answer': 'ต้องจั่วหนึ่งใบเมื่อจบตาตามกฎ',
             'source_id': 'R1', 'quote': 'เมื่อจบตาให้จั่วหนึ่งใบ', 'reviewed': True}]}
        sources = knowledge(game)
        qa = next(s for s in sources if s.id == 'Q1')
        result = original_evidence(game, sources, [qa, sources[0]])
        self.assertEqual([s.id for s in result], ['R1'])
        self.assertNotIn('คำถาม:', result[0].content)

    def test_unverified_fallback_is_short_and_never_repeats_an_old_answer(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(api, 'DATABASE_PATH', Path(directory) / 'games.sqlite3'), \
             patch.dict(os.environ, {'BGT_SEMANTIC_SEARCH': '0'}):
            api.initialize_database()
            game = {'id': 'test', 'n': 'Test', 'e': 'x', 'pl': '2', 't': '10', 'd': 'Test', 'pub': 1,
                    'r': [['การเปิดการ์ด', 'หลังเปิดการ์ดให้คิดคะแนน']],
                    'verified_qa': [{'question': 'เปิดการ์ดแล้วได้คะแนนไหม',
                        'answer': 'คำตอบเก่าที่เกี่ยวกับการเปิดการ์ดและคิดคะแนน',
                        'source_id': 'R1', 'quote': 'หลังเปิดการ์ดให้คิดคะแนน', 'reviewed': True}]}
            api.write_game(api.Game(**game))
            client = TestClient(api.app)
            with patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[
                ModelQuestionContext(status='resolved', subject='ผู้เล่น', question='แล้วถ้าไม่เปิดการ์ดเลยได้ไหม'),
                ModelRuleAnswer(status='answered', answer='ข้อสรุปผิดที่ต้องไม่ปรากฏให้ผู้ใช้เห็น', source_ids=['R1']),
                ModelAnswerReview(verdict='unsupported', source_id='R1', quote='หลังเปิดการ์ดให้คิดคะแนน'),
            ])) as model:
                response = client.post('/api/games/test/ask', json={
                    'question': 'แล้วถ้าไม่เปิดการ์ดเลยได้ไหม',
                    'history': [{'role': 'user', 'content': 'เปิดการ์ดแล้วได้คะแนนไหม'},
                                {'role': 'assistant', 'content': 'คำตอบเก่า', 'status': 'answered', 'source_ids': ['R1']}]})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body['status'], 'excerpt')
            self.assertEqual(body['method'], 'retrieval')
            self.assertLess(len(body['answer']), 180)
            self.assertNotIn('ข้อสรุปผิด', body['answer'])
            self.assertNotIn('คำตอบเก่า', body['answer'])
            self.assertNotIn('คำถาม:', body['answer'])
            context = json.loads(model.await_args_list[1].args[0])
            self.assertTrue(all(s['kind'] != 'คำตอบตรวจเทียบกฎ' for s in context['evidence']))
            review = json.loads(model.await_args_list[2].args[0])
            self.assertEqual(review['question'], 'แล้วถ้าไม่เปิดการ์ดเลยได้ไหม')
            self.assertEqual(review['conversation'], [])
            self.assertIn('ผู้เล่น', review['resolved_question'])


if __name__ == '__main__':
    unittest.main()
