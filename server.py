"""MVP：只接 DeepSeek（OpenAI 相容）。回傳結構化 JSON，含逾時與錯誤處理。"""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(title="Massage Prompt Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TIMEOUT_SEC = 30.0

STRUCTURED_SYSTEM_PROMPT = """你是一位頂級的 AI 影片提示詞工程師，專精於醫療保健、傳統整復、按摩療程的視覺影像生成。你的任務是將使用者選擇的零散標籤，轉化為一段流暢、具備電影感且細節豐富的英文影片生成提示詞，並提供精準的中文翻譯。

請將接收到的前端標籤融合合成一個動態的場景描述，特別強調手部的動作（如：精準的按壓、柔和的推拿）、肌肉紋理與光影變化。並根據鏡頭與角度設定，加入具體的攝影機運動描述（如：Slow panning, tracking shot）。

務必區分「調理師／師傅」與「客人」兩種角色；若有對白或說話，須寫明是誰開口。若使用者訊息含【指定說話內容】，須將該對白／口白自然融入 english_prompt 與 chinese_version，並與「說話（誰開口）」維度一致，勿忽略。

請嚴格使用以下 JSON 格式輸出，不要包含任何其他文字、說明、或 Markdown 標記（不要使用 ``` 程式碼區塊）：
{"english_prompt": "Cinematic shot, ...", "chinese_version": "電影級鏡頭，..."}

鍵名必須精確為 english_prompt 與 chinese_version；字串內的引號請正確跳脫。"""


_OUTPUT_LANG_HINT = {
    "both": """【輸出偏好】雙語：english_prompt 為給國際影片模型（如 Flow／Veo）的主英文提示；chinese_version 為對應繁體中文翻譯。""",
    "en": """【輸出偏好】英文為主：english_prompt 為完整英文影片提示（可較長）；chinese_version 僅需一行繁體中文概括。""",
    "zh": """【輸出偏好】繁中為主：chinese_version 為完整繁體中文影片提示；english_prompt 為簡短英文摘要（約 10–25 個單字或一句），供英文介面工具使用。""",
    "ja": """【輸出偏好】日文為主：JSON 鍵名仍固定——請將日文主提示詞寫在 english_prompt 欄位；chinese_version 寫繁體中文對照說明（鍵名勿改）。""",
}


_DIM_LABELS = {
    "role_therapist": "調理師（角色）",
    "role_client": "客人（角色）",
    "camera": "鏡頭",
    "bg": "背景",
    "narrative": "敘事",
    "style": "風格",
    "angle": "角度",
    "physics_detail": "動態與物理細節",
    "lighting": "光影設定",
    "speech": "說話（誰開口）",
    "subtitle": "字幕",
}


def _effective_api_key(raw: str) -> str:
    s = (raw or "").strip()
    if not s or "xxxxx" in s.lower():
        return ""
    return s


DEEPSEEK_KEY = _effective_api_key(os.environ.get("DEEPSEEK_API_KEY", ""))
DEEPSEEK_BASE = (os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").strip().rstrip("/")
DEEPSEEK_MODEL = (os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat").strip() or "deepseek-chat"


def _deepseek_base() -> str:
    b = DEEPSEEK_BASE.strip().rstrip("/")
    return b if b.endswith("/v1") else b + "/v1"


def build_user_message(
    selections: dict,
    user_input: str,
    output_lang: str = "both",
    speech_content: str = "",
) -> str:
    parts = []
    if user_input:
        parts.append(f"一句話描述：{user_input}\n")
    sc = (speech_content or "").strip()
    if sc:
        parts.append(
            "【指定說話內容】（請融入影片提示詞，並與「說話（誰開口）」維度一致；可改寫為更口語或電影感，但保留原意）\n"
            + sc
            + "\n"
        )
    parts.append("已選擇的維度元素：")
    for dim, items in selections.items():
        if items:
            label = _DIM_LABELS.get(dim, dim)
            parts.append(f"  {label}：{', '.join(items)}")
    lang = (output_lang or "both").strip()
    if lang not in _OUTPUT_LANG_HINT:
        lang = "both"
    parts.append("\n" + _OUTPUT_LANG_HINT[lang])
    return "\n".join(parts)


def _parse_llm_json_content(content: str) -> dict:
    s = (content or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    return json.loads(s)


def call_deepseek_json(user_msg: str, api_key: str | None) -> dict:
    from openai import OpenAI

    key = (api_key or DEEPSEEK_KEY or "").strip()
    if not key:
        raise HTTPException(
            status_code=401,
            detail="請在網頁貼上 DeepSeek 金鑰，或在 .env 設定 DEEPSEEK_API_KEY。",
        )

    try:
        client = OpenAI(api_key=key, base_url=_deepseek_base(), timeout=API_TIMEOUT_SEC)
        completion = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": STRUCTURED_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        err = str(e).lower()
        if "timeout" in err or "timed out" in err or "read timeout" in err:
            return JSONResponse(
                status_code=504,
                content={"error": "DeepSeek API 連線逾時（30 秒），請稍後再試。"},
            )
        if "connection" in err or "connect" in err or "network" in err:
            return JSONResponse(
                status_code=503,
                content={"error": "無法連線至 DeepSeek，請檢查網路後再試。"},
            )
        if "401" in str(e) or "invalid" in err and "api" in err or "authentication" in err:
            return JSONResponse(
                status_code=401,
                content={"error": "API 金鑰無效或未授權，請檢查 DeepSeek 金鑰。"},
            )
        if "429" in str(e) or "rate" in err:
            return JSONResponse(
                status_code=429,
                content={"error": "請求過於頻繁，請稍後再試。"},
            )
        return JSONResponse(
            status_code=502,
            content={"error": f"模型服務暫時無法使用：{str(e)[:500]}"},
        )

    choice = completion.choices[0] if completion.choices else None
    raw = (choice.message.content or "").strip() if choice and choice.message else ""
    if not raw:
        return JSONResponse(
            status_code=502,
            content={"error": "模型未回傳內容，請重試。"},
        )

    try:
        data = _parse_llm_json_content(raw)
    except (json.JSONDecodeError, ValueError) as e:
        return JSONResponse(
            status_code=502,
            content={"error": f"無法解析模型 JSON：{str(e)[:200]}"},
        )

    en = data.get("english_prompt")
    zh = data.get("chinese_version")
    if not isinstance(en, str) or not isinstance(zh, str):
        return JSONResponse(
            status_code=502,
            content={"error": "模型回傳格式錯誤：缺少 english_prompt 或 chinese_version 字串欄位。"},
        )
    en, zh = en.strip(), zh.strip()
    if not en and not zh:
        return JSONResponse(
            status_code=502,
            content={"error": "模型回傳的提示詞為空，請重試。"},
        )

    return {"english_prompt": en, "chinese_version": zh}


@app.get("/api/health")
async def health():
    return {"status": "ok", "provider": "deepseek" if DEEPSEEK_KEY else "none"}


@app.post("/api/generate")
async def generate_prompt(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="請求內容必須為 JSON。")

    selections = body.get("selections") or {}
    if not isinstance(selections, dict):
        selections = {}
    user_input = body.get("user_input") or ""
    if not isinstance(user_input, str):
        user_input = str(user_input)
    speech_content = body.get("speech_content") or ""
    if not isinstance(speech_content, str):
        speech_content = str(speech_content)

    has_selection = any(v for v in selections.values())
    if not has_selection and not user_input.strip() and not speech_content.strip():
        raise HTTPException(
            status_code=400,
            detail="請至少輸入一句話、指定說話內容，或選擇一個維度",
        )

    out_lang = (body.get("output_language") or "both").strip()
    user_msg = build_user_message(selections, user_input, out_lang, speech_content)
    client_key = _effective_api_key(str(body.get("deepseek_api_key") or ""))

    result = call_deepseek_json(user_msg, api_key=client_key or None)
    if isinstance(result, JSONResponse):
        return result
    return result


app.mount("/", StaticFiles(directory="static", html=True), name="static")
