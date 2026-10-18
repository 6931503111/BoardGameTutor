import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
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
                "st": [{"title": "เตรียมเกม", "content": "แจกไพ่ให้ผู้เล่น"}],
                "sit": [
                    {
                        "c": "คุณได้ไพ่พิเศษ",
                        "o": ["ใช้ทันที", "เก็บไว้ในมือ"],
                        "a": 0,
                        "w": "กติกากำหนดให้ใช้ไพ่พิเศษทันที",
                    }
                ],
                "qz": [],
                "r": [{"title": "ไพ่พิเศษ", "content": "ใช้ได้หนึ่งครั้งต่อรอบ"}],
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
        self.assertEqual(game["st"], [["เตรียมเกม", "แจกไพ่ให้ผู้เล่น"]])
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
        self.assertIn("ห้ามย่อจนข้อมูล เงื่อนไข หรือตัวเลขสำคัญหายไป", prompt)
        self.assertIn("ความสามารถของตัวละครทุกตัว", prompt)
        self.assertIn("ห้ามรวมหลายตัวละครเป็นคำอธิบายกว้าง ๆ", prompt)
        self.assertIn("ให้สร้าง r ก่อน st, sit และ qz", prompt)
        self.assertNotIn("กฎไม่เกิน 8 ข้อ", prompt)
        self.assertIn(source, prompt)
        self.assertEqual(request["options"]["num_predict"], 4096)

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
