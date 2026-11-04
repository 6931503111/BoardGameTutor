import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend import app as api
from backend.rule_assistant import ChatTurn, ModelAnswerReview, ModelReviewedMatch, ModelRuleAnswer, knowledge, matching_reviewed_candidates, reviewed_answer, resolve_context, retrieve


class RuleAssistantTests(unittest.TestCase):
    def setUp(self):
        self.search_patch = patch.dict(os.environ, {"BGT_SEMANTIC_SEARCH": "0"})
        self.search_patch.start()
        self.directory = tempfile.TemporaryDirectory()
        self.path = patch.object(api, "DATABASE_PATH", Path(self.directory.name) / "games.sqlite3")
        self.path.start()
        api.initialize_database()
        self.client = TestClient(api.app)
        self.game = {
            "id": "kittens", "n": "เกมแมว", "e": "game", "pl": "2-5", "t": "15", "d": "เกมทดสอบ", "pub": 1,
            "r": [["Nope", "Nope ยกเลิกแอ็กชันได้ แต่ยกเลิก Exploding Kitten และ Defuse ไม่ได้ และ Nope ถูก Nope ได้"],
                  ["Attack", "Attack จบตาโดยไม่จั่ว แล้วให้คนถัดไปเล่นสองตา"],
                  ["จบเทิร์น", "เมื่อจบเทิร์นให้จั่วไพ่หนึ่งใบ"]],
            "st": [], "sit": [], "qz": [],
        }
        api.write_game(api.Game(**self.game))
        api.write_game(api.Game(**{**self.game, "id": "other", "n": "เกมอื่น", "r": [["การซื้อบ้าน", "ซื้อบ้านต้องจ่ายเงิน 500 เหรียญ"]]}))

    def tearDown(self):
        self.search_patch.stop()
        self.path.stop()
        self.directory.cleanup()

    def ask(self, question, **kwargs):
        return self.client.post("/api/games/kittens/ask", json={"question": question, **kwargs})

    def test_retrieves_only_the_selected_game_and_cites_actual_text(self):
        with patch.object(api, "request_structured_content", new=AsyncMock(side_effect=[ModelRuleAnswer(
            status="answered", answer="Nope ใช้ยกเลิกแอ็กชัน ยกเว้นระเบิดและ Defuse", source_ids=["R1"]
        ), ModelAnswerReview(verdict="supported", source_id="R1", quote=self.game["r"][0][1])])) as model:
            response = self.ask("Nope ใช้ยังไง")
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["game_id"], "kittens")
        self.assertEqual(result["sources"][0]["title"], "Nope")
        self.assertIn("Defuse", result["sources"][0]["content"])
        context = json.loads(model.await_args_list[0].args[0])
        self.assertNotIn("500", json.dumps(context["evidence"], ensure_ascii=False))

    def test_unsupported_question_does_not_call_model(self):
        with patch.object(api, "request_structured_content", new=AsyncMock()) as model:
            response = self.ask("ซื้อบ้านราคา 500 เหรียญได้ไหม")
        self.assertEqual(response.json()["status"], "insufficient")
        self.assertEqual(response.json()["sources"], [])
        model.assert_not_awaited()

    def test_followup_uses_recent_conversation_and_prior_evidence(self):
        history = [
            {"role": "user", "content": "Nope คืออะไร"},
            {"role": "assistant", "content": "ใช้ยกเลิกแอ็กชัน", "source_ids": ["R1"], "status": "answered"},
        ]
        with patch.object(api, "request_structured_content", new=AsyncMock(side_effect=[ModelRuleAnswer(
            status="answered", answer="ตัวอย่างจากกฎ: Nope ถูกยกเลิกด้วย Nope ได้", source_ids=["R1"]
        ), ModelAnswerReview(verdict="supported", source_id="R1", quote="Nope ถูก Nope ได้")])) as model:
            response = self.ask("ขอยกตัวอย่างเพิ่มเติมหน่อย", history=history)
        self.assertEqual(response.json()["status"], "answered")
        context = json.loads(model.await_args_list[0].args[0])
        self.assertEqual(context["conversation"][0]["content"], "Nope คืออะไร")
        self.assertEqual(context["evidence"][0]["id"], "R1")

    def test_ambiguous_first_turn_requests_clarification_without_model(self):
        with patch.object(api, "request_structured_content", new=AsyncMock()) as model:
            response = self.ask("ทำแบบนี้ได้ไหม")
        self.assertEqual(response.json()["status"], "clarify")
        model.assert_not_awaited()

    def test_ambiguous_followup_with_multiple_topics_requests_clarification(self):
        history = [
            {"role": "user", "content": "Nope กับ Attack ต่างกันยังไง"},
            {"role": "assistant", "content": "ทั้งสองมีหน้าที่ต่างกัน", "source_ids": ["R1", "R2"]},
        ]
        with patch.object(api, "request_structured_content", new=AsyncMock()) as model:
            response = self.ask("แล้วอันนี้ล่ะ", history=history)
        self.assertEqual(response.json()["status"], "clarify")
        model.assert_not_awaited()

    def test_explicit_new_topic_does_not_get_stuck_on_previous_rule(self):
        history = [ChatTurn(role="user", content="Nope คืออะไร"), ChatTurn(role="assistant", content="ยกเลิกแอ็กชัน", source_ids=["R1"])]
        hits, clarification = resolve_context(knowledge(self.game), "แล้ว Attack ใช้ยังไง", history)
        self.assertIsNone(clarification)
        self.assertEqual([hit.id for hit in hits], ["R2"])

    def test_unknown_citation_is_not_presented_as_a_supported_answer(self):
        with patch.object(api, "request_structured_content", new=AsyncMock(return_value=ModelRuleAnswer(
            status="answered", answer="คำตอบที่ไม่มีหลักฐาน", source_ids=["R999"]
        ))):
            response = self.ask("Nope คืออะไร")
        self.assertEqual(response.json()["status"], "insufficient")
        self.assertNotIn("คำตอบที่ไม่มีหลักฐาน", response.json()["answer"])

    def test_ai_can_request_missing_situation_details(self):
        with patch.object(api, "request_structured_content", new=AsyncMock(return_value=ModelRuleAnswer(
            status="clarify", answer="การ์ดที่ใช้ก่อนหน้านี้คือใบไหนครับ", source_ids=[]
        ))):
            response = self.ask("ใช้ Nope กับการ์ดที่เพิ่งลงได้ไหม")
        self.assertEqual(response.json()["status"], "clarify")

    def test_contradicted_answer_is_withheld_and_real_evidence_is_shown(self):
        with patch.object(api, "request_structured_content", new=AsyncMock(side_effect=[
            ModelRuleAnswer(status="answered", answer="Nope ยกเลิก Defuse ได้แน่นอน", source_ids=["R1"]),
            ModelAnswerReview(verdict="unsupported", source_id="R1", quote="Defuse ไม่ได้"),
        ])):
            response = self.ask("Nope ยกเลิก Defuse ได้ไหม")
        self.assertEqual(response.json()["status"], "excerpt")
        self.assertNotIn("ได้แน่นอน", response.json()["answer"])
        self.assertEqual(response.json()["sources"][0]["id"], "R1")

    def test_review_must_quote_actual_source_text(self):
        with patch.object(api, "request_structured_content", new=AsyncMock(side_effect=[
            ModelRuleAnswer(status="answered", answer="ใช้ Nope ยกเลิกการกระทำได้", source_ids=["R1"]),
            ModelAnswerReview(verdict="supported", source_id="R1", quote="ข้อความอ้างอิงที่แต่งขึ้น"),
        ])):
            response = self.ask("Nope ใช้ยังไง")
        self.assertEqual(response.json()["status"], "excerpt")
        self.assertNotIn("ข้อความอ้างอิงที่แต่งขึ้น", response.json()["answer"])

    def test_service_error_remains_an_error_not_a_rule_answer(self):
        with patch.object(api, "request_structured_content", new=AsyncMock(side_effect=api.HTTPException(status_code=502, detail="เปิด Ollama แล้วลองใหม่"))):
            response = self.ask("Nope คืออะไร")
        self.assertEqual(response.status_code, 502)
        self.assertIn("Ollama", response.json()["detail"])

    def test_missing_or_unpublished_game_does_not_disclose_rules(self):
        api.write_game(api.Game(**{**self.game, "id": "private", "pub": 0}))
        for game_id in ("missing", "private"):
            response = self.client.post(f"/api/games/{game_id}/ask", json={"question": "Nope คืออะไร"})
            self.assertEqual(response.status_code, 404)

    def test_demo_returns_real_excerpts_and_deduplicates_rule_lessons(self):
        with patch.object(api, "request_structured_content", new=AsyncMock()) as model:
            response = self.ask("Nope คืออะไร", demo=True)
        self.assertEqual(response.json()["status"], "excerpt")
        self.assertEqual(len(response.json()["sources"]), 1)
        model.assert_not_awaited()

    def test_empty_question_is_rejected(self):
        self.assertEqual(self.ask("   ").status_code, 422)

    def test_hypothetical_auction_amounts_retrieve_the_comparison_rule(self):
        game = {"r": [["การประมูล", "ผู้เล่นต้องวางเงินให้มากกว่าจำนวนเงินประมูลล่าสุดหรือบอกผ่าน"]]}
        for question in ("ราคาประมูลล่าสุด 4000 เสนอ 300 ได้ไหม", "ประมูลล่าสุด 9500 เสนอ 12000 ได้ไหม"):
            self.assertEqual(retrieve(knowledge(game), question)[0].id, "R1")

    def test_partial_answer_keeps_supported_alternative_and_marks_unknown_part(self):
        with patch.object(api, "request_structured_content", new=AsyncMock(side_effect=[
            ModelRuleAnswer(status="partial", answer="Nope ยกเลิกแอ็กชันได้ ส่วนการขอยืมไพ่ไม่มีข้อมูลระบุ", source_ids=["R1"]),
            ModelAnswerReview(verdict="supported", source_id="R1", quote="Nope ยกเลิกแอ็กชันได้"),
        ])) as model:
            response = self.ask("Nope ใช้ยังไง และขอยืมไพ่ได้ไหม")
        self.assertEqual(response.json()["status"], "partial")
        prompt = model.await_args_list[0].args[1]
        self.assertIn("เปรียบเทียบตัวเลข", prompt)
        self.assertIn("ตอบได้บางส่วน", prompt)
        self.assertEqual(response.json()["sources"][0]["id"], "R1")

    def test_original_import_text_remains_searchable_with_page_reference(self):
        game = {"r": [["สรุป", "ประมูลบ้าน"]], "source_text": "[หน้า 2]\nผู้เล่นบอกผ่านได้ และได้รับเงินคืนตามกฎในคู่มือ"}
        hits = retrieve(knowledge(game), "บอกผ่านได้เงินคืนยังไง")
        self.assertTrue(any(source.kind == "คู่มือต้นฉบับ" and "หน้า 2" in source.title for source in hits))

    def test_cash_shortage_still_shows_verified_pass_option_when_loan_rule_is_unknown(self):
        api.write_game(api.Game(**{**self.game, "r": [["ประมูลบ้าน", "ผู้เล่นต้องวางเงินให้มากกว่าจำนวนเงินประมูลล่าสุดหรือบอกผ่าน"]]}))
        with patch.object(api, "request_structured_content", new=AsyncMock(return_value=ModelRuleAnswer(
            status="insufficient", answer="ข้อมูลไม่มีข้อกำหนดเกี่ยวกับการขอเงินจากผู้เล่นอื่น", source_ids=[]
        ))):
            response = self.ask("เงินไม่พอขอเงินคนอื่นได้ไหม")
        self.assertEqual(response.json()["status"], "partial")
        self.assertIn("เลือกบอกผ่านได้", response.json()["answer"])
        self.assertIn("ยังสรุปว่าอนุญาตหรือห้ามไม่ได้", response.json()["answer"])
        self.assertEqual(response.json()["sources"][0]["id"], "R1")

    def test_explicit_auction_comparisons_do_not_depend_on_model_review(self):
        api.write_game(api.Game(**{**self.game, "r": [["ประมูลบ้าน", "ผู้เล่นต้องวางเงินให้มากกว่าจำนวนเงินประมูลล่าสุดหรือบอกผ่าน"]]}))
        cases = [
            ("งั้นถ้าคนล่าสุดประมูล 4000 คนต่อไปประมูล 3000 ได้ไหม", "answered", "3,000"),
            ("ถ้าล่าสุด 4,000 เสนอ 4,000 ได้ไหม", "answered", "เท่ากับ"),
            ("ถ้าล่าสุด 9500 เราเสนอ 12000 ได้ไหม", "partial", "ผ่านเงื่อนไขเรื่องราคา"),
            ("ล่าสุด 4 พัน เราเสนอ 3 พันได้ไหม", "answered", "3,000"),
            ("มีเงิน 4000 เสนอประมูลบ้านได้ไหม", "clarify", "ราคาประมูลล่าสุดเท่าไร"),
        ]
        with patch.object(api, "request_structured_content", new=AsyncMock()) as model:
            for question, status, expected in cases:
                with self.subTest(question=question):
                    response = self.ask(question)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["status"], status)
                    self.assertIn(expected, response.json()["answer"])
                    self.assertEqual(response.json()["sources"][0]["id"], "R1")
        model.assert_not_awaited()

    def test_auction_arithmetic_is_not_used_without_a_matching_rule(self):
        with patch.object(api, "request_structured_content", new=AsyncMock()) as model:
            response = self.ask("ล่าสุดประมูล 4000 เสนอ 3000 ได้ไหม")
        self.assertEqual(response.json()["status"], "insufficient")
        model.assert_not_awaited()

    def test_refund_math_requires_explicit_rounding_rule(self):
        from backend.rule_assistant import RuleSource, explicit_refund_answer
        rule = RuleSource(id='R1', title='บอกผ่าน', kind='กฎ', content='เมื่อบอกผ่าน รับธนบัตรที่ลงไว้คืนครึ่งหนึ่งโดยปัดจำนวนธนบัตรลง')
        for question, expected in [('วางธนบัตรไปห้าใบแล้วถอนตัว ได้กลับมากี่ใบ', '2 ใบ'), ('ลงไป 8 ใบแล้วบอกผ่าน จะได้คืนกี่ใบ', '4 ใบ')]:
            result = explicit_refund_answer([rule], question)
            self.assertIn(expected, result.answer)
        self.assertIsNone(explicit_refund_answer([], 'ลงไป 5 ใบแล้วบอกผ่าน จะได้คืนกี่ใบ'))
        self.assertIsNone(explicit_refund_answer([rule], 'คนสุดท้ายลงไป 5 ใบแล้วบอกผ่าน จะได้คืนกี่ใบ'))
        self.assertIsNone(explicit_refund_answer([rule], 'วางไพ่ไปห้าใบแล้วถอนตัว ได้กลับมากี่ใบ'))

    def add_reviewed_answer(self):
        entry = {'question': 'Nope ยกเลิก Defuse ได้ไหม', 'aliases': ['ใช้ Nope หยุด Defuse ได้ไหม'],
                 'answer': 'ไม่ได้ เพราะกฎยกเว้น Defuse จากการใช้ Nope ยกเลิก',
                 'source_id': 'R1', 'quote': 'ยกเลิก Exploding Kitten และ Defuse ไม่ได้', 'reviewed': True}
        game = {**self.game, 'verified_qa': [entry]}
        api.write_game(api.Game(**game))
        return game

    def test_reviewed_alias_answers_without_ai_and_keeps_source(self):
        self.add_reviewed_answer()
        with patch.object(api, 'request_structured_content', new=AsyncMock()) as model:
            response = self.ask('ใช้ Nope หยุด Defuse ได้มั้ยครับ?')
        self.assertEqual(response.json()['method'], 'reviewed')
        self.assertEqual(response.json()['sources'][0]['id'], 'R1')
        model.assert_not_awaited()

    def test_reviewed_answer_does_not_match_a_different_target(self):
        game = self.add_reviewed_answer()
        self.assertIsNone(reviewed_answer(game, knowledge(game), 'Nope ยกเลิก Attack ได้ไหม'))
        self.assertEqual(matching_reviewed_candidates(knowledge(game), 'Nope ยกเลิก Attack ได้ไหม'), [])

    def test_paraphrase_reuses_reviewed_answer_and_shows_original_question(self):
        self.add_reviewed_answer()
        with patch.object(api, 'request_structured_content', new=AsyncMock(return_value=ModelReviewedMatch(
            verdict='same_intent', source_id='Q1'))) as model:
            result = self.ask('ถ้าเพื่อนใช้ Defuse ฉันหยุดเขาด้วย Nope ได้หรือเปล่า').json()
        self.assertEqual(result['method'], 'reviewed')
        self.assertIn('คำตอบที่ตรวจไว้สำหรับคำถาม', result['answer'])
        self.assertIn('Nope ยกเลิก Defuse ได้ไหม', result['answer'])
        self.assertEqual(model.await_count, 1)

    def test_matching_reviewed_candidates_does_not_ignore_changed_numbers(self):
        from backend.rule_assistant import RuleSource
        source = RuleSource(id='Q1', title='ประมูล 4000 ได้ไหม', kind='คำตอบตรวจเทียบกฎ', content='หลักฐาน')
        self.assertEqual(matching_reviewed_candidates([source], 'ประมูล 3000 ได้ไหม'), [])

    def test_thai_money_questions_do_not_reuse_a_refund_answer_for_starting_cash(self):
        from backend.rule_assistant import RuleSource
        source = RuleSource(id='Q1', title='บอกผ่านประมูลจะได้เงินคืนเท่าไร', kind='คำตอบตรวจเทียบกฎ', content='คืนครึ่งหนึ่ง')
        history = [ChatTurn(role='user', content=source.title)]
        for question in ['เงินเริ่มเกมจะมีกี่เท่าไหร่', 'เงินเริ่มเกมจะมีเท่าไหร่', 'แล้วเงินตอนเริ่มประมูลมีเท่าไร']:
            with self.subTest(question=question):
                self.assertEqual(matching_reviewed_candidates([source], question, history), [])

    def test_conservative_thai_topic_gate_keeps_specific_paraphrases(self):
        from backend.rule_assistant import RuleSource
        cases = [('บทผู้หยั่งรู้สามารถตรวจบทบาทได้หลายคนในคืนเดียวหรือเปล่า', 'ผู้หยั่งรู้ดูได้กี่คนต่อคืน'),
                 ('ถ้าฉันเผลอพูดคำบนหน้าผากตัวเอง ฉันยังคุยในรอบนั้นต่อได้หรือเปล่า', 'หลุดคำต้องห้ามแล้วยังพูดต่อได้ไหม')]
        for question, title in cases:
            source = RuleSource(id='Q1', title=title, kind='คำตอบตรวจเทียบกฎ', content='ข้อความกฎ')
            with self.subTest(question=question):
                self.assertEqual(matching_reviewed_candidates([source], question), [source])

    def test_reviewed_intent_candidates_are_not_lost_by_a_short_evidence_window(self):
        self.add_reviewed_answer()
        attack = next(source for source in knowledge(self.game) if source.id == 'R2')
        with patch.object(api, 'resolve_context', return_value=([attack], None)), \
             patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=[])), \
             patch.object(api, 'request_structured_content', new=AsyncMock(return_value=ModelReviewedMatch(
                 verdict='same_intent', source_id='Q1'))):
            result = self.ask('ถ้าเพื่อนใช้ Defuse ฉันหยุดเขาด้วย Nope ได้หรือเปล่า').json()
        self.assertEqual(result['method'], 'reviewed')
        self.assertIn('Defuse', result['answer'])

    def test_new_topic_uses_current_question_and_not_the_previous_refund_context(self):
        game = {**self.game, 'r': [
            ['บอกผ่าน', 'บอกผ่านแล้วได้เงินคืนครึ่งหนึ่ง'],
            ['เงินเริ่มเกม', 'เล่นสี่คนแจกเงินเริ่มเกมคนละ 21000']],
            'verified_qa': [{'question':'บอกผ่านประมูลจะได้เงินคืนเท่าไร',
                'answer':'ได้เงินคืนครึ่งหนึ่งตามกฎบอกผ่าน', 'source_id':'R1',
                'quote':'บอกผ่านแล้วได้เงินคืนครึ่งหนึ่ง', 'reviewed':True}]}
        api.write_game(api.Game(**game))
        question = 'เงินเริ่มเกมจะมีกี่เท่าไหร่'
        history = [
            {'role':'user', 'content':'บอกผ่านประมูลจะได้เงินคืนเท่าไร'},
            {'role':'assistant', 'content':'ได้เงินคืนครึ่งหนึ่ง', 'source_ids':['R1'], 'status':'answered'}]
        with patch.object(api, 'hybrid_retrieve', new=AsyncMock(return_value=[])) as search, patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[
            ModelRuleAnswer(status='answered', answer='ถ้าเล่นสี่คน เงินเริ่มเกมคนละ 21000 ตามกฎที่บันทึกไว้', source_ids=['R2']),
            ModelAnswerReview(verdict='supported', source_id='R2', quote='เล่นสี่คนแจกเงินเริ่มเกมคนละ 21000'),
        ])) as model:
            result = self.ask(question, history=history).json()
        self.assertEqual(result['method'], 'model')
        self.assertIn('21000', result['answer'])
        search.assert_awaited_once()
        self.assertEqual(search.await_args.args[1], question)
        context = json.loads(model.await_args_list[0].args[0])
        self.assertEqual(context['conversation'], [])
        self.assertEqual(model.await_args_list[0].args[2], ModelRuleAnswer)

    def test_followup_candidate_keeps_the_new_target_and_recovers_the_previous_action(self):
        from backend.rule_assistant import RuleSource
        sources = [RuleSource(id='Q1', title='Nope ยกเลิก Defuse ได้ไหม', kind='คำตอบตรวจเทียบกฎ', content='กฎ'),
                   RuleSource(id='Q2', title='Nope ยกเลิก Attack ได้ไหม', kind='คำตอบตรวจเทียบกฎ', content='กฎ')]
        history = [ChatTurn(role='user', content='Nope ยกเลิก Defuse ได้ไหม')]
        self.assertEqual([source.id for source in matching_reviewed_candidates(sources, 'แล้วใช้กับ Attack ล่ะ', history)], ['Q2'])

    def test_explicit_followup_target_change_uses_only_an_exact_reviewed_question(self):
        game = self.add_reviewed_answer()
        game['verified_qa'].append({'question':'Nope ใช้ยกเลิก Attack ได้ไหม',
            'answer':'ใช้ Nope ยกเลิก Attack ได้ตามกฎยกเลิกแอ็กชัน',
            'source_id':'R1','quote':'Nope ยกเลิกแอ็กชันได้','reviewed':True})
        api.write_game(api.Game(**game))
        history = [{'role':'user','content':'Nope ใช้ยกเลิก Defuse ได้ไหม'},
                   {'role':'assistant','content':'ใช้กับ Defuse ไม่ได้','source_ids':['R1'],'status':'answered'}]
        with patch.object(api,'request_structured_content',new=AsyncMock()) as model:
            result = self.ask('แล้วใช้กับ Attack ล่ะ',history=history).json()
        self.assertEqual(result['method'],'reviewed')
        self.assertIn('Nope ใช้ยกเลิก Attack ได้ไหม',result['answer'])
        model.assert_not_awaited()

    def test_followup_rewrite_does_not_treat_new_topics_or_missing_actors_as_target_changes(self):
        from backend.rule_assistant import reviewed_followup_question
        history = [ChatTurn(role='user',content='Nope ใช้ยกเลิก Defuse ได้ไหม')]
        self.assertIsNone(reviewed_followup_question('เงินเริ่มเกมจะมีเท่าไหร่',history))
        self.assertIsNone(reviewed_followup_question('แล้วใช้ Attack ล่ะ',history))
        self.assertIsNone(reviewed_followup_question('แล้วใช้กับ Attack ล่ะ',[]))

    def test_matcher_cannot_choose_an_unoffered_reviewed_answer(self):
        self.add_reviewed_answer()
        with patch.object(api, 'request_structured_content', new=AsyncMock(side_effect=[
            ModelReviewedMatch(verdict='same_intent', source_id='Q999'),
            ModelRuleAnswer(status='insufficient', answer='ไม่มีหลักฐานเพิ่มเติมที่ยืนยันสถานการณ์นี้ได้', source_ids=[]),
        ])) as model:
            result = self.ask('ถ้าเพื่อนใช้ Defuse ฉันหยุดเขาด้วย Nope ได้หรือเปล่า').json()
        self.assertEqual(result['status'], 'insufficient')
        self.assertNotEqual(result['method'], 'reviewed')
        self.assertEqual(model.await_count, 2)

    def test_source_edit_invalidates_reviewed_answer_and_searchable_translation(self):
        game = self.add_reviewed_answer()
        self.assertTrue(any(source.id == 'Q1' for source in knowledge(game)))
        game['r'] = [['Nope', 'ข้อความกฎฉบับใหม่ที่ยังไม่ได้ตรวจคำตอบ']]
        sources = knowledge(game)
        self.assertIsNone(reviewed_answer(game, sources, 'Nope ยกเลิก Defuse ได้ไหม'))
        self.assertFalse(any(source.id.startswith('Q') for source in sources))

    def test_unreviewed_or_malformed_answers_are_not_used(self):
        game = self.add_reviewed_answer()
        for changes in ({'reviewed': False}, {'reviewed': 'yes'}, {'quote': 'แต่งเอง'}, {'answer': 'สั้น'}, {'status': 'wrong'}):
            with self.subTest(changes=changes):
                edited = {**game, 'verified_qa': [{**game['verified_qa'][0], **changes}]}
                self.assertIsNone(reviewed_answer(edited, knowledge(edited), 'Nope ยกเลิก Defuse ได้ไหม'))

    def test_readiness_and_source_review_require_admin(self):
        self.assertEqual(self.client.get('/api/admin/readiness').status_code, 401)
        self.assertEqual(self.client.get('/api/admin/games/kittens/knowledge').status_code, 401)
        with patch.dict(os.environ, {'BGT_ADMIN_PASSWORD': 'test-password'}):
            token = self.client.post('/api/admin/login', json={'password': 'test-password'}).json()['access_token']
        headers = {'Authorization': 'Bearer ' + token}
        self.add_reviewed_answer()
        report = self.client.get('/api/admin/readiness', headers=headers)
        self.assertEqual(report.status_code, 200)
        kittens = next(game for game in report.json()['games'] if game['id'] == 'kittens')
        self.assertEqual(kittens['reviewed_answers'], 1)
        self.assertIn('ยังไม่ระบุฉบับเกม', ' '.join(kittens['issues']))
        source = self.client.get('/api/admin/games/kittens/knowledge', headers=headers)
        self.assertEqual(source.status_code, 200)
        self.assertIn('Q1', [item['id'] for item in source.json()['sources']])


if __name__ == "__main__":
    unittest.main()
