from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json, os

app = FastAPI(title="Massage Prompt Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Detect which LLM provider to use ──
# Priority: ANTHROPIC_API_KEY > GEMINI_API_KEY > OPENAI_API_KEY
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """你是專業的按摩整復影片提示詞工程師，擅長為台灣傳統整復推拿工作室生成 Google Flow / Veo 影片提示詞。

用戶會提供已選擇的8大維度元素（中文），你需要：
1. 先用繁體中文列出每個維度的最終選擇
2. 然後生成一段完整的英文影片提示詞（適用於 Google Veo / Flow）
3. 英文提示詞自然流暢、具電影感，長度 60-100 字

回應格式（嚴格遵守）：
### 維度組合
角色：[元素]
鏡頭：[元素]
背景：[元素]
敘事：[元素]
風格：[元素]
角度：[元素]
說話：[元素]
字幕：[元素]

### 完整提示詞（Google Flow 直接使用）
[英文提示詞，60-100 字]

### 備用中文版本
[中文提示詞，40-60 字]

語氣要專業、有感染力，突顯台灣傳統整復的文化價值。"""


def build_user_message(selections: dict, user_input: str) -> str:
    parts = []
    if user_input:
        parts.append(f"一句話描述：{user_input}\n")
    parts.append("已選擇的維度元素：")
    for dim, items in selections.items():
        if items:
            parts.append(f"  {dim}：{', '.join(items)}")
    return "\n".join(parts)


def stream_anthropic(user_msg: str):
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_KEY)
    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}]
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"
    yield "data: [DONE]\n\n"


def stream_gemini(user_msg: str):
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT
    )
    response = model.generate_content(user_msg, stream=True)
    for chunk in response:
        if chunk.text:
            yield f"data: {json.dumps({'text': chunk.text})}\n\n"
    yield "data: [DONE]\n\n"


def stream_openai(user_msg: str):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_KEY)
    with client.chat.completions.stream(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        max_tokens=1024,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield f"data: {json.dumps({'text': delta.content})}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/api/health")
async def health():
    provider = "anthropic" if ANTHROPIC_KEY else ("gemini" if GEMINI_KEY else ("openai" if OPENAI_KEY else "none"))
    return {"status": "ok", "provider": provider}


@app.post("/api/generate")
async def generate_prompt(request: Request):
    body = await request.json()
    selections = body.get("selections", {})
    user_input = body.get("user_input", "")

    has_selection = any(v for v in selections.values())
    if not has_selection and not user_input:
        return {"error": "請至少輸入一句話或選擇一個維度"}

    user_msg = build_user_message(selections, user_input)

    if ANTHROPIC_KEY:
        gen = stream_anthropic(user_msg)
    elif GEMINI_KEY:
        gen = stream_gemini(user_msg)
    elif OPENAI_KEY:
        gen = stream_openai(user_msg)
    else:
        async def no_key():
            yield f"data: {json.dumps({'text': '❌ 未設定 API Key。請在環境變數中設定 ANTHROPIC_API_KEY、GEMINI_API_KEY 或 OPENAI_API_KEY。'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(no_key(), media_type="text/event-stream")

    return StreamingResponse(gen, media_type="text/event-stream")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
