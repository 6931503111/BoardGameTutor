import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(
    os.environ.get("BGT_DATABASE_PATH", BASE_DIR / "data" / "games.sqlite3")
)
LOCAL_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "BGT_ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]


class Game(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1, max_length=80)
    n: str = Field(min_length=1, max_length=200)
    e: str = Field(min_length=1, max_length=16)
    pl: str = Field(min_length=1, max_length=40)
    t: str = Field(min_length=1, max_length=40)
    d: str = Field(min_length=1, max_length=2000)
    pub: int = Field(default=0, ge=0, le=1)
    c: list[str] = Field(default_factory=list)
    lv: str = Field(default="เริ่มต้นง่าย", max_length=100)
    st: list[list[Any]] = Field(default_factory=list)
    sit: list[dict[str, Any]] = Field(default_factory=list)
    qz: list[dict[str, Any]] = Field(default_factory=list)
    r: list[list[Any]] = Field(default_factory=list)


class AdminLogin(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class AdminSession(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SeedImport(BaseModel):
    games: list[Game] = Field(min_length=1, max_length=100)


class GenerateGameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=50, max_length=100_000)


class RuleSection(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10_000)


class PracticeQuestion(BaseModel):
    c: str = Field(min_length=1, max_length=2000)
    o: list[str] = Field(min_length=2, max_length=8)
    a: int = Field(ge=0)
    w: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_answer_index(self) -> "PracticeQuestion":
        if self.a >= len(self.o):
            raise ValueError("คำตอบที่ถูกต้องต้องตรงกับลำดับตัวเลือก")
        return self


class GameDraftContent(BaseModel):
    d: str = Field(min_length=1, max_length=2000)
    pl: str = Field(min_length=1, max_length=40)
    t: str = Field(min_length=1, max_length=40)
    c: list[str] = Field(default_factory=list, max_length=10)
    lv: str = Field(default="เริ่มต้นง่าย", max_length=100)
    st: list[RuleSection] = Field(default_factory=list, max_length=30)
    sit: list[PracticeQuestion] = Field(default_factory=list, max_length=30)
    qz: list[PracticeQuestion] = Field(default_factory=list, max_length=30)
    r: list[RuleSection] = Field(default_factory=list, max_length=50)


ADMIN_SESSIONS: dict[str, float] = {}
ADMIN_SESSION_TTL = 8 * 60 * 60


def require_admin(authorization: str | None = Header(default=None)) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    expires_at = ADMIN_SESSIONS.get(token) if scheme.lower() == "bearer" else None
    if not token or expires_at is None or expires_at <= time.monotonic():
        ADMIN_SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบผู้ดูแลก่อน")
    return token


def is_admin_session(authorization: str | None) -> bool:
    scheme, _, token = (authorization or "").partition(" ")
    expires_at = ADMIN_SESSIONS.get(token) if scheme.lower() == "bearer" else None
    if expires_at is None or expires_at <= time.monotonic():
        ADMIN_SESSIONS.pop(token, None)
        return False
    return True


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with closing(connect()) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def read_games() -> list[dict[str, Any]]:
    with closing(connect()) as connection:
        rows = connection.execute(
            "SELECT payload FROM games ORDER BY updated_at, id"
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def write_game(game: Game) -> dict[str, Any]:
    payload = game.model_dump()
    with closing(connect()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO games (id, payload, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (game.id, json.dumps(payload, ensure_ascii=False)),
            )
    return payload


async def generate_game_content(name: str, source: str) -> GameDraftContent:
    base_url = os.environ.get("BGT_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("BGT_OLLAMA_MODEL", "qwen3:1.7b")
    prompt = f"""แปลงข้อความกติกาเป็น JSON object หนึ่งรายการตามรูปแบบนี้เท่านั้น ห้ามใส่ markdown ห้ามใส่ wrapper:
{{"d":"คำอธิบายเกม","pl":"จำนวนผู้เล่นหรือ -","t":"เวลาเล่นหรือ -","c":["หมวดหมู่"],"lv":"ระดับความยาก","r":[{{"title":"หัวข้อกฎ","content":"เนื้อหา"}}],"st":[{{"title":"หัวข้อบทเรียน","content":"เนื้อหา"}}],"sit":[{{"c":"สถานการณ์","o":["ตัวเลือก 1","ตัวเลือก 2"],"a":0,"w":"คำอธิบายเฉลย"}}],"qz":[{{"c":"คำถาม","o":["ตัวเลือก 1","ตัวเลือก 2"],"a":0,"w":"คำอธิบายเฉลย"}}]}}

ข้อกำหนด:
- ชื่อเกม: {json.dumps(name, ensure_ascii=False)} (ไม่ต้องใส่ชื่อเกมลง JSON)
- ใช้เฉพาะข้อเท็จจริงจากข้อความต้นฉบับ ห้ามแต่งหรือคาดเดากติกา
- เก็บรายละเอียดจากต้นฉบับให้ครบ ห้ามย่อจนข้อมูล เงื่อนไข หรือตัวเลขสำคัญหายไป
- ใน r ให้แยกกฎตามหัวข้อ และระบุความสามารถของตัวละครทุกตัวที่ต้นฉบับกล่าวถึง โดยบอกชื่อ หน้าที่/แอ็กชัน เงื่อนไข ค่าใช้จ่าย ผลลัพธ์ และการขัดขวางหรือการท้าพิสูจน์ที่เกี่ยวข้องให้ครบตามที่มีในต้นฉบับ
- หากต้นฉบับมีรายการหรือตารางตัวละคร ให้ตรวจว่าทุกตัวละครและทุกความสามารถในรายการนั้นปรากฏใน r ก่อนตอบ ห้ามรวมหลายตัวละครเป็นคำอธิบายกว้าง ๆ ที่ทำให้แยกความสามารถไม่ได้
- อย่าตัดจำนวนหัวข้อกฎเพื่อให้สั้นลง ให้สร้างหัวข้อ r เท่าที่จำเป็นเพื่อครอบคลุมข้อมูลทั้งหมด
- ให้สร้าง r ก่อน st, sit และ qz หากต้องจำกัดความยาว ให้ลดหรือละสถานการณ์และข้อสอบก่อน ห้ามละกฎหรือความสามารถตัวละคร
- ถ้าไม่พบข้อมูลจำนวนผู้เล่นหรือเวลา ให้ใส่ "-"
- หากข้อมูลไม่พอสำหรับบทเรียน สถานการณ์ หรือข้อสอบ ให้ใช้ array ว่างหรือไม่ต้องสร้างรายการนั้น
- สร้างบทเรียนไม่เกิน 15 ขั้น
- สร้างสถานการณ์และข้อสอบอย่างละไม่เกิน 2 ข้อ เฉพาะเมื่อข้อมูลรองรับชัดเจน
- ใน sit และ qz, a คือ index คำตอบที่ถูกต้อง เริ่มนับจาก 0 และต้องอยู่ในช่วงตัวเลือก
- ค่าของ st และ r ต้องเป็น object ที่มี title และ content
- JSON ต้องมี key d, pl, t, c, lv, r, st, sit, qz ครบทุกตัว

ข้อความต้นฉบับ:
{source}"""
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "options": {"num_predict": 4096},
                    "messages": [
                        {
                            "role": "system",
                            "content": "คุณช่วยจัดโครงสร้างกติกาเกมอย่างครบถ้วนและระมัดระวัง ให้สร้างกฎทั้งหมดก่อนบทเรียนและข้อสอบ ห้ามย่อจนรายละเอียดหาย โดยเฉพาะความสามารถของตัวละครทุกตัวและเงื่อนไขที่เกี่ยวข้อง ส่งเฉพาะ JSON ที่ถูกต้อง และห้ามแต่งข้อมูลที่ไม่มีในแหล่งข้อมูล",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            raw_content = response.json()["message"]["content"]
        return GameDraftContent.model_validate_json(raw_content)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="AI ใช้เวลาประมวลผลนานเกินไป ตรวจสอบ Ollama แล้วลองอีกครั้ง",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama ตอบกลับด้วยสถานะ HTTP {exc.response.status_code}",
        ) from exc
    except (httpx.RequestError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="เรียก Ollama ไม่สำเร็จ หรือ AI ส่งข้อมูลที่ไม่ถูกต้อง ตรวจสอบ Ollama แล้วลองอีกครั้ง",
        ) from exc


app = FastAPI(title="BoardGameTutor API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)
initialize_database()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/games")
def get_games(
    authorization: str | None = Header(default=None),
) -> list[dict[str, Any]]:
    games = read_games()
    return games if is_admin_session(authorization) else [g for g in games if g.get("pub")]


@app.get("/api/admin/session")
def admin_session(_: str = Depends(require_admin)) -> dict[str, str]:
    return {"status": "authenticated"}


@app.post("/api/admin/login", response_model=AdminSession)
def admin_login(credentials: AdminLogin) -> AdminSession:
    expected_password = os.environ.get("BGT_ADMIN_PASSWORD", "")
    if not expected_password:
        raise HTTPException(
            status_code=503,
            detail="ยังไม่ได้ตั้งรหัสผ่านผู้ดูแลในตัวแปร BGT_ADMIN_PASSWORD",
        )
    if not secrets.compare_digest(credentials.password, expected_password):
        raise HTTPException(status_code=401, detail="รหัสผ่านไม่ถูกต้อง")
    token = secrets.token_urlsafe(32)
    ADMIN_SESSIONS[token] = time.monotonic() + ADMIN_SESSION_TTL
    return AdminSession(access_token=token)


@app.post("/api/admin/logout")
def admin_logout(token: str = Depends(require_admin)) -> dict[str, str]:
    ADMIN_SESSIONS.pop(token, None)
    return {"status": "ok"}


@app.post("/api/admin/import-seeds")
def import_seed_games(
    payload: SeedImport, _: str = Depends(require_admin)
) -> dict[str, int]:
    ids = [game.id for game in payload.games]
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", game_id) for game_id in ids):
        raise HTTPException(status_code=400, detail="พบรหัสเกมตัวอย่างที่ไม่ถูกต้อง")
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="พบรหัสเกมตัวอย่างซ้ำกัน")

    with closing(connect()) as connection:
        with connection:
            inserted = 0
            for game in payload.games:
                result = connection.execute(
                    """
                    INSERT OR IGNORE INTO games (id, payload, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (game.id, json.dumps(game.model_dump(), ensure_ascii=False)),
                )
                inserted += result.rowcount

    return {
        "imported_count": inserted,
        "skipped_count": len(payload.games) - inserted,
    }


@app.post("/api/admin/generate-game")
async def generate_game_draft(
    request: GenerateGameRequest, _: str = Depends(require_admin)
) -> dict[str, Any]:
    content = await generate_game_content(request.name, request.source)
    generated = content.model_dump()
    for key in ("st", "r"):
        generated[key] = [
            [section["title"], section["content"]] for section in generated[key]
        ]
    return {
        "id": "g" + secrets.token_hex(8),
        "n": request.name,
        "e": "🎲",
        **generated,
        "pub": 0,
    }


@app.put("/api/games/{game_id}")
def put_game(
    game_id: str, game: Game, _: str = Depends(require_admin)
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", game_id):
        raise HTTPException(status_code=400, detail="รูปแบบรหัสเกมไม่ถูกต้อง")
    if game.id != game_id:
        raise HTTPException(status_code=400, detail="รหัสเกมใน URL และข้อมูลไม่ตรงกัน")
    return write_game(game)
