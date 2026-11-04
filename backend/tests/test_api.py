import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from backend import app as api


class GameApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "games.sqlite3"
        self.path_patch = patch.object(api, "DATABASE_PATH", self.database_path)
        self.path_patch.start()
        self.password_patch = patch.dict(os.environ, {"BGT_ADMIN_PASSWORD": "test-admin-password"})
        self.password_patch.start()
        self.search_patch = patch.dict(os.environ, {"BGT_SEMANTIC_SEARCH": "0"})
        self.search_patch.start()
        api.ADMIN_SESSIONS.clear()
        api.initialize_database()
        self.client = TestClient(api.app)
        login_response = self.client.post(
            "/api/admin/login", json={"password": "test-admin-password"}
        )
        self.assertEqual(login_response.status_code, 200)
        self.admin_headers = {
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        }

    def tearDown(self) -> None:
        self.search_patch.stop()
        self.password_patch.stop()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def sample_game(self) -> dict[str, object]:
        return {
            "id": "g-test-1",
            "n": "เกมทดสอบ",
            "e": "🎲",
            "pl": "2-4",
            "t": "30",
            "d": "คำอธิบายเกม",
            "pub": 0,
            "c": ["ครอบครัว"],
            "lv": "เริ่มต้นง่าย",
            "st": [["เตรียมเกม", "สับไพ่"]],
            "sit": [],
            "qz": [],
            "r": [["การเริ่มเกม", "สับไพ่ก่อนเริ่ม"]],
        }

    def test_create_and_read_game(self) -> None:
        game = self.sample_game()
        response = self.client.put(
            f"/api/games/{game['id']}", json=game, headers=self.admin_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), game)
        self.assertEqual(
            self.client.get("/api/games", headers=self.admin_headers).json(), [game]
        )

    def test_existing_import_without_lessons_uses_its_saved_rules(self) -> None:
        game = self.sample_game()
        game["st"] = []
        game["qz"] = [{"c": "เริ่มเกมอย่างไร", "o": ["สับไพ่", "ทิ้งไพ่"], "a": 0, "w": "กฎให้สับไพ่ก่อนเริ่ม"}]
        self.client.put(f"/api/games/{game['id']}", json=game, headers=self.admin_headers)
        loaded = self.client.get("/api/games", headers=self.admin_headers).json()[0]
        self.assertEqual(loaded["st"], game["r"])
        self.assertEqual(loaded["qz"], game["qz"])

    def test_generated_game_without_lessons_reuses_rules_and_warns_about_missing_quiz(self) -> None:
        content = api.GameDraftContent(d="เกม", pl="2", t="10", r=[{"title": "เตรียมเกม", "content": "สับไพ่"}])
        with patch.object(api, "request_structured_content", new=AsyncMock(return_value=content)), patch.object(
            api, "generate_practice_content", new=AsyncMock(return_value=api.PracticeContent())
        ):
            result = asyncio.run(api.generate_game_content("เกม", "กติกาต้นฉบับ"))
        self.assertEqual(result.st[0].content, "สับไพ่")
        self.assertIsNot(result.st[0], result.r[0])
        self.assertTrue(any("ข้อสอบ" in warning for warning in result.generation_warnings))

    def test_update_game_replaces_saved_content(self) -> None:
        game = self.sample_game()
        self.client.put(
            f"/api/games/{game['id']}", json=game, headers=self.admin_headers
        )
        game["pub"] = 1

        response = self.client.put(
            f"/api/games/{game['id']}", json=game, headers=self.admin_headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/games").json(), [game])

    def test_delete_game_removes_only_selected_game_from_database(self) -> None:
        game = self.sample_game()
        other = {**game, "id": "g-keep"}
        for item in (game, other):
            self.client.put(f"/api/games/{item['id']}", json=item, headers=self.admin_headers)
        response = self.client.delete(f"/api/games/{game['id']}", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted_id": game["id"]})
        self.assertEqual(self.client.get("/api/games", headers=self.admin_headers).json(), [other])
        self.assertEqual(api.read_games(), [other])

    def test_delete_game_requires_admin_and_preserves_data_on_rejection(self) -> None:
        game = self.sample_game()
        self.client.put(f"/api/games/{game['id']}", json=game, headers=self.admin_headers)
        response = self.client.delete(f"/api/games/{game['id']}")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(api.read_games(), [game])

    def test_delete_missing_game_returns_not_found(self) -> None:
        response = self.client.delete("/api/games/missing", headers=self.admin_headers)
        self.assertEqual(response.status_code, 404)

    def test_delete_is_allowed_by_cors(self) -> None:
        response = self.client.options("/api/games/game", headers={
            "Origin": "http://127.0.0.1:5500",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "authorization",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("DELETE", response.headers["access-control-allow-methods"])

    def test_rejects_mismatched_id(self) -> None:
        game = self.sample_game()

        response = self.client.put(
            "/api/games/other-id", json=game, headers=self.admin_headers
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/games").json(), [])

    def test_rejects_invalid_game(self) -> None:
        response = self.client.put(
            "/api/games/g-invalid", headers=self.admin_headers,
            json={"id": "g-invalid", "n": "ชื่อเกม"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/games").json(), [])

    def test_persists_json_as_utf8(self) -> None:
        game = self.sample_game()
        self.client.put(
            f"/api/games/{game['id']}", json=game, headers=self.admin_headers
        )

        with closing(sqlite3.connect(self.database_path)) as connection:
            stored_payload = connection.execute(
                "SELECT payload FROM games WHERE id = ?", (game["id"],)
            ).fetchone()[0]

        self.assertIn("เกมทดสอบ", stored_payload)
        self.assertEqual(json.loads(stored_payload), game)

    def test_game_write_requires_admin_authentication(self) -> None:
        game = self.sample_game()

        response = self.client.put(f"/api/games/{game['id']}", json=game)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/api/games").json(), [])

    def test_seed_import_adds_only_missing_games(self) -> None:
        existing = self.sample_game()
        self.client.put(
            f"/api/games/{existing['id']}", json=existing, headers=self.admin_headers
        )
        seed = self.sample_game()
        seed["n"] = "ชื่อเกมจาก seed"
        new_seed = self.sample_game()
        new_seed["id"] = "g-new-seed"
        new_seed["n"] = "เกม seed ใหม่"

        response = self.client.post(
            "/api/admin/import-seeds",
            json={"games": [seed, new_seed]},
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"imported_count": 1, "skipped_count": 1})
        games = self.client.get("/api/games", headers=self.admin_headers).json()
        self.assertEqual(len(games), 2)
        self.assertEqual(
            next(game for game in games if game["id"] == existing["id"])["n"],
            existing["n"],
        )
        self.assertEqual(
            next(game for game in games if game["id"] == new_seed["id"])["n"],
            new_seed["n"],
        )

    def test_seed_import_requires_admin_authentication(self) -> None:
        response = self.client.post(
            "/api/admin/import-seeds", json={"games": [self.sample_game()]}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/api/games").json(), [])

    def test_generate_game_draft_returns_unpublished_structured_game(self) -> None:
        content = api.GameDraftContent.model_validate(
            {
                "d": "เกมวางแผนผลัดกันเล่น",
                "pl": "2-4",
                "t": "30",
                "c": ["กลยุทธ์"],
                "lv": "ปานกลาง",
                "st": [
                    {
                        "title": "เตรียมเกม",
                        "content": "แจกไพ่ให้ผู้เล่น",
                        "cards": [
                            {
                                "emoji": "🧯",
                                "title": "Defuse",
                                "description": "แจกคนละ 1 ใบ",
                                "hue": 140,
                            }
                        ],
                    }
                ],
                "sit": [
                    {
                        "c": "คุณได้ไพ่พิเศษ",
                        "o": ["ใช้ทันที", "เก็บไว้ในมือ"],
                        "a": 0,
                        "w": "กติกากำหนดให้ใช้ไพ่พิเศษทันที",
                    }
                ],
                "qz": [],
                "r": [
                    {
                        "title": "ไพ่พิเศษ",
                        "content": "ใช้ได้หนึ่งครั้งต่อรอบ",
                        "cards": [],
                    }
                ],
            }
        )
        with patch.object(
            api, "generate_game_content", new=AsyncMock(return_value=content)
        ) as generate:
            response = self.client.post(
                "/api/admin/generate-game",
                json={"name": "เกมตัวอย่าง", "source": "ข้อความกติกา " * 10},
                headers=self.admin_headers,
            )

        self.assertEqual(response.status_code, 200)
        game = response.json()
        self.assertEqual(game["n"], "เกมตัวอย่าง")
        self.assertEqual(game["pub"], 0)
        self.assertEqual(
            game["st"],
            [["เตรียมเกม", "แจกไพ่ให้ผู้เล่น", [["🧯", "Defuse", "แจกคนละ 1 ใบ", 140]]]],
        )
        self.assertEqual(game["r"], [["ไพ่พิเศษ", "ใช้ได้หนึ่งครั้งต่อรอบ"]])
        generate.assert_awaited_once()
        self.assertEqual(self.client.get("/api/games").json(), [])

    def test_generate_game_draft_preserves_all_rule_sections(self) -> None:
        rules = [
            {"title": f"ความสามารถตัวละคร {index}", "content": f"รายละเอียด {index}"}
            for index in range(12)
        ]
        content = api.GameDraftContent.model_validate(
            {
                "d": "เกมโค่นอำนาจ",
                "pl": "-",
                "t": "-",
                "r": rules,
            }
        )
        with patch.object(
            api, "generate_game_content", new=AsyncMock(return_value=content)
        ):
            response = self.client.post(
                "/api/admin/generate-game",
                json={"name": "Coup", "source": "ข้อความกติกา " * 10},
                headers=self.admin_headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["r"],
            [[rule["title"], rule["content"]] for rule in rules],
        )

    def test_generation_prompt_requires_complete_character_details(self) -> None:
        ollama_response = Mock()
        ollama_response.json.return_value = {
            "message": {
                "content": json.dumps(
                    {"d": "เกม", "pl": "-", "t": "-", "r": []},
                    ensure_ascii=False,
                )
            }
        }
        ollama_client = AsyncMock()
        ollama_client.__aenter__.return_value = ollama_client
        ollama_client.__aexit__.return_value = None
        ollama_client.post.return_value = ollama_response
        source = "เจ้าพระยาเก็บอากรได้ 3 เหรียญ และรัชทายาทขัดขวางการลอบสังหาร"

        with patch.object(
            api.httpx, "AsyncClient", return_value=ollama_client
        ):
            asyncio.run(api.generate_game_content("Coup", source))

        request = ollama_client.post.await_args.kwargs["json"]
        prompt = request["messages"][1]["content"]
        system_prompt = request["messages"][0]["content"]
        self.assertIn("เขียนข้อความที่ผู้เล่นเห็นทั้งหมดเป็นภาษาไทย", prompt)
        self.assertIn("ตอบเป็นภาษาไทยทั้งหมด", system_prompt)
        self.assertIn("ห้ามย่อจนข้อมูล เงื่อนไข หรือตัวเลขสำคัญหายไป", prompt)
        self.assertIn("ความสามารถของตัวละครทุกตัว", prompt)
        self.assertIn("ห้ามรวมหลายตัวละครเป็นคำอธิบายกว้าง ๆ", prompt)
        self.assertIn("ให้สร้าง r ก่อน st, sit และ qz", prompt)
        self.assertIn('"cards"', prompt)
        self.assertIn('"hue":200', prompt)
        self.assertNotIn("กฎไม่เกิน 8 ข้อ", prompt)
        self.assertIn(source, prompt)
        self.assertEqual(request["options"]["num_predict"], 4096)
        self.assertIsInstance(request["format"], dict)
        self.assertNotIn("generation_warnings", request["format"]["properties"])

    def test_repair_pdf_text_fixes_known_thai_font_glyphs(self) -> None:
        source = "ค\uf70aูมือ ผ\uf70bูเล่น สมบูรณ\uf70e จํานวน คําตอบ"

        self.assertEqual(
            api.repair_pdf_text(source),
            "คู่มือ ผู้เล่น สมบูรณ์ จำนวน คำตอบ",
        )

    def test_generation_fills_missing_practice_without_replacing_rules(self) -> None:
        draft = {"d": "เกม", "pl": "2", "t": "10", "r": [{"title": "จบเทิร์น", "content": "จั่วไพ่หนึ่งใบ"}]}
        response = Mock()
        response.json.return_value = {"message": {"content": json.dumps(draft)}}
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response
        question = {"c": "คุณจบเทิร์น ต้องทำอะไร", "o": ["จั่วหนึ่งใบ", "ไม่จั่ว"], "a": 0, "w": "กฎจบเทิร์นระบุให้จั่วหนึ่งใบ"}
        practice = api.PracticeContent(sit=[question], qz=[question])
        with patch.object(api.httpx, "AsyncClient", return_value=client), patch.object(
            api, "generate_practice_content", new=AsyncMock(return_value=practice)
        ) as generate:
            result = asyncio.run(api.generate_game_content("เกม", "ต้นฉบับกติกา"))
        generate.assert_awaited_once_with("เกม", "ต้นฉบับกติกา")
        self.assertEqual(result.r[0].content, "จั่วไพ่หนึ่งใบ")
        self.assertEqual(len(result.sit), 1)
        self.assertEqual(len(result.qz), 1)

    def test_practice_failure_preserves_rule_draft_with_warning(self) -> None:
        draft = {"d": "เกม", "pl": "2", "t": "10", "r": [{"title": "จบเทิร์น", "content": "จั่วไพ่หนึ่งใบ"}]}
        response = Mock()
        response.json.return_value = {"message": {"content": json.dumps(draft)}}
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response
        with patch.object(api.httpx, "AsyncClient", return_value=client), patch.object(
            api, "generate_practice_content", new=AsyncMock(side_effect=api.HTTPException(status_code=502))
        ):
            result = asyncio.run(api.generate_game_content("เกม", "ต้นฉบับกติกา"))
        self.assertEqual(result.r[0].content, "จั่วไพ่หนึ่งใบ")
        self.assertTrue(result.generation_warnings)

    def test_practice_endpoint_is_authenticated_and_does_not_save_game(self) -> None:
        payload = {"name": "เกม", "source": "กติกาจากคู่มือ " * 10}
        self.assertEqual(self.client.post("/api/admin/generate-practice", json=payload).status_code, 401)
        with patch.object(api, "generate_practice_content", new=AsyncMock(return_value=api.PracticeContent())):
            response = self.client.post("/api/admin/generate-practice", json=payload, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"sit": [], "qz": []})
        self.assertEqual(self.client.get("/api/games", headers=self.admin_headers).json(), [])

    def test_practice_generation_rejects_invalid_answer_index(self) -> None:
        response = Mock()
        response.json.return_value = {"message": {"content": json.dumps({"sit": [{"c": "โจทย์", "o": ["ก", "ข"], "a": 2, "w": "เหตุผล"}]})}}
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response
        with patch.object(api.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(api.HTTPException) as error:
                asyncio.run(api.generate_practice_content("เกม", "กติกา"))
        self.assertEqual(error.exception.status_code, 502)

    def test_structured_generation_repairs_malformed_response_once(self) -> None:
        invalid, valid = Mock(), Mock()
        invalid.json.return_value = {"message": {"content": '{"sit": [invalid'}}
        valid.json.return_value = {"message": {"content": '{"sit":[],"qz":[]}'}}
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.side_effect = [invalid, valid]
        with patch.object(api.httpx, "AsyncClient", return_value=client):
            result = asyncio.run(api.request_structured_content("กติกา", "สร้างโจทย์", api.PracticeContent))
        self.assertEqual(result.sit, [])
        self.assertEqual(client.post.await_count, 2)
        first = client.post.await_args_list[0].kwargs["json"]
        second = client.post.await_args_list[1].kwargs["json"]
        self.assertEqual(first["format"], api.PracticeContent.model_json_schema())
        self.assertEqual(first["options"]["temperature"], 0)
        self.assertGreater(second["options"]["num_predict"], first["options"]["num_predict"])

    def test_structured_generation_reports_truncation_after_bounded_retry(self) -> None:
        response = Mock()
        response.json.return_value = {"done_reason": "length", "message": {"content": '{"sit":[],"qz":[]}'}}
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response
        with patch.object(api.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(api.HTTPException) as error:
                asyncio.run(api.request_structured_content("กติกา", "สร้างโจทย์", api.PracticeContent))
        self.assertIn("ถูกตัด", error.exception.detail)
        self.assertEqual(client.post.await_count, 2)

    def test_structured_generation_names_invalid_fields_without_exposing_source(self) -> None:
        response = Mock()
        response.json.return_value = {"message": {"content": '{"pl":"2","t":"10","d":{"private":"secret_source_text"}}'}}
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response
        with patch.object(api.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(api.HTTPException) as error:
                asyncio.run(api.request_structured_content("กติกา", "สร้างร่าง", api.GameDraftContent))
        self.assertIn("d", error.exception.detail)
        self.assertNotIn("secret_source_text", error.exception.detail)

    def test_structured_generation_distinguishes_connection_and_missing_model(self) -> None:
        request = api.httpx.Request("POST", "http://127.0.0.1:11434/api/chat")
        response = api.httpx.Response(404, request=request)
        failures = [
            (api.httpx.ConnectError("offline"), "เชื่อมต่อ Ollama"),
            (api.httpx.HTTPStatusError("missing", request=request, response=response), "ไม่พบโมเดล"),
        ]
        for failure, expected in failures:
            with self.subTest(expected=expected):
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.side_effect = failure
                with patch.object(api.httpx, "AsyncClient", return_value=client):
                    with self.assertRaises(api.HTTPException) as error:
                        asyncio.run(api.request_structured_content("กติกา", "สร้างร่าง", api.GameDraftContent))
                self.assertIn(expected, error.exception.detail)
                self.assertEqual(client.post.await_count, 1)

    def test_extract_pdf_text_endpoint_returns_repaired_text(self) -> None:
        extracted = "ค\uf70aูมือ ผ\uf70bูเล่น สมบูรณ\uf70e " * 5
        expected = f"[หน้า 1]\n{('คู่มือ ผู้เล่น สมบูรณ์ ' * 5).strip()}"
        with patch.object(api, "PdfReader") as pdf_reader:
            page = Mock()
            page.extract_text.return_value = extracted
            pdf_reader.return_value.is_encrypted = False
            pdf_reader.return_value.pages = [page]
            response = self.client.post(
                "/api/admin/extract-pdf-text",
                files={"file": ("rules.pdf", b"%PDF-1.7 test", "application/pdf")},
                headers=self.admin_headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"text": expected})

    def test_extract_pdf_text_endpoint_requires_admin_authentication(self) -> None:
        response = self.client.post(
            "/api/admin/extract-pdf-text",
            files={"file": ("rules.pdf", b"%PDF-1.7 test", "application/pdf")},
        )

        self.assertEqual(response.status_code, 401)

    def test_generate_game_from_pdf_extracts_text_and_returns_draft(self) -> None:
        extracted_text = "กติกาเกมฉบับทดสอบ " * 10
        page = SimpleNamespace(extract_text=Mock(return_value=extracted_text))
        reader = SimpleNamespace(is_encrypted=False, pages=[page])
        content = api.GameDraftContent.model_validate(
            {"d": "เกมจาก PDF", "pl": "2-4", "t": "30"}
        )
        with (
            patch.object(api, "PdfReader", return_value=reader),
            patch.object(
                api, "generate_game_content", new=AsyncMock(return_value=content)
            ) as generate,
        ):
            response = self.client.post(
                "/api/admin/generate-game-from-pdf",
                data={"name": "เกมทดสอบ PDF"},
                files={"file": ("rules.pdf", b"%PDF-1.7 test", "application/pdf")},
                headers=self.admin_headers,
            )

        self.assertEqual(response.status_code, 200)
        game = response.json()
        self.assertEqual(game["n"], "เกมทดสอบ PDF")
        self.assertEqual(game["pub"], 0)
        self.assertEqual(game["source_text"], f"[หน้า 1]\n{extracted_text.strip()}")
        generate.assert_awaited_once_with(
            "เกมทดสอบ PDF", f"[หน้า 1]\n{extracted_text.strip()}"
        )

    def test_generate_game_from_pdf_requires_admin_authentication(self) -> None:
        response = self.client.post(
            "/api/admin/generate-game-from-pdf",
            data={"name": "เกมทดสอบ"},
            files={"file": ("rules.pdf", b"%PDF-1.7 test", "application/pdf")},
        )

        self.assertEqual(response.status_code, 401)

    def test_generate_game_from_pdf_rejects_non_pdf_file(self) -> None:
        response = self.client.post(
            "/api/admin/generate-game-from-pdf",
            data={"name": "เกมทดสอบ"},
            files={"file": ("rules.txt", ("ข้อความกติกา " * 10).encode(), "text/plain")},
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 415)

    def test_generate_game_from_pdf_reports_scanned_document(self) -> None:
        reader = SimpleNamespace(
            is_encrypted=False,
            pages=[SimpleNamespace(extract_text=Mock(return_value=""))],
        )
        with patch.object(api, "PdfReader", return_value=reader):
            response = self.client.post(
                "/api/admin/generate-game-from-pdf",
                data={"name": "เกมทดสอบ"},
                files={"file": ("rules.pdf", b"%PDF-1.7 test", "application/pdf")},
                headers=self.admin_headers,
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("OCR", response.json()["detail"])

    def test_generate_game_from_pdf_rejects_invalid_pdf_signature(self) -> None:
        response = self.client.post(
            "/api/admin/generate-game-from-pdf",
            data={"name": "เกมทดสอบ"},
            files={"file": ("rules.pdf", b"not a PDF", "application/pdf")},
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 400)

    def test_generate_game_draft_requires_admin_authentication(self) -> None:
        response = self.client.post(
            "/api/admin/generate-game",
            json={"name": "เกมตัวอย่าง", "source": "ข้อความกติกา " * 10},
        )

        self.assertEqual(response.status_code, 401)

    def test_generate_game_rejects_short_source(self) -> None:
        response = self.client.post(
            "/api/admin/generate-game",
            json={"name": "เกมตัวอย่าง", "source": "กติกาสั้น"},
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 422)

    def test_generate_game_reports_ollama_timeout(self) -> None:
        with patch.object(
            api,
            "generate_game_content",
            new=AsyncMock(
                side_effect=api.HTTPException(status_code=504, detail="AI timeout")
            ),
        ):
            response = self.client.post(
                "/api/admin/generate-game",
                json={"name": "เกมตัวอย่าง", "source": "ข้อความกติกา " * 10},
                headers=self.admin_headers,
            )

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["detail"], "AI timeout")

    def test_generated_question_rejects_invalid_answer_index(self) -> None:
        with self.assertRaises(ValueError):
            api.PracticeQuestion.model_validate(
                {
                    "c": "คำถาม",
                    "o": ["ตัวเลือกหนึ่ง", "ตัวเลือกสอง"],
                    "a": 2,
                    "w": "เฉลย",
                }
            )

    def test_rejects_invalid_admin_password(self) -> None:
        response = self.client.post(
            "/api/admin/login", json={"password": "wrong-password"}
        )

        self.assertEqual(response.status_code, 401)

    def test_login_requires_configured_password(self) -> None:
        with patch.dict(os.environ, {"BGT_ADMIN_PASSWORD": ""}):
            response = self.client.post(
                "/api/admin/login", json={"password": "test-admin-password"}
            )

        self.assertEqual(response.status_code, 503)

    def test_public_game_list_does_not_include_drafts(self) -> None:
        draft = self.sample_game()
        self.client.put(
            f"/api/games/{draft['id']}", json=draft, headers=self.admin_headers
        )

        self.assertEqual(self.client.get("/api/games").json(), [])
        self.assertEqual(
            self.client.get("/api/games", headers=self.admin_headers).json(),
            [draft],
        )

    def test_logout_revokes_admin_token(self) -> None:
        response = self.client.post("/api/admin/logout", headers=self.admin_headers)

        self.assertEqual(response.status_code, 200)
        game = self.sample_game()
        write_response = self.client.put(
            f"/api/games/{game['id']}", json=game, headers=self.admin_headers
        )
        self.assertEqual(write_response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
