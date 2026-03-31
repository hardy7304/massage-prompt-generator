# 💆 柔手整復 · 影片提示詞生成器

Google Flow / Veo 影片提示詞快速組合工具，專為台灣按摩整復工作室設計。

## 功能

- **8 大維度多選**：角色、鏡頭、背景、敘事、風格、角度、說話、字幕
- **一句話輸入**：直接描述影片概念，AI 自動展開
- **流式輸出**：即時串流顯示生成過程
- **三種輸出格式**：完整分析 / 英文提示詞 / 中文版本
- **支援三種 LLM**：Anthropic Claude、Google Gemini、OpenAI GPT

---

## 部署到 Zeabur（推薦）

### 1. 上傳到 GitHub

```bash
git init
git add .
git commit -m "init: massage prompt generator"
git remote add origin https://github.com/你的帳號/massage-prompt-generator.git
git push -u origin main
```

### 2. 在 Zeabur 建立服務

1. 前往 [zeabur.com](https://zeabur.com) → 新建 Project
2. 選擇 **Deploy from GitHub**
3. 選擇你的 repo
4. Zeabur 會自動偵測 `zbpack.json` 或 `Dockerfile`

### 3. 設定環境變數

在 Zeabur 服務設定 → **Environment** 分頁，加入以下其中一個：

| 變數名稱 | 說明 | 免費方案 |
|---------|------|---------|
| `GEMINI_API_KEY` | Google AI Studio Key | ✅ 有免費額度 |
| `ANTHROPIC_API_KEY` | Claude API Key | ❌ 付費 |
| `OPENAI_API_KEY` | OpenAI Key | ❌ 付費 |

> **推薦使用 Gemini**：申請免費 Key → https://aistudio.google.com/apikey
> 
> Gemini 2.0 Flash 每分鐘 15 次、每天 1500 次免費呼叫

### 4. 完成部署

Zeabur 自動建置完成後，會給你一個 `.zeabur.app` 的公開網址。

---

## 部署到 Railway

```bash
# 安裝 Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
```

在 Railway Dashboard → Variables 設定 `GEMINI_API_KEY`。

---

## 本地執行

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=你的Key
uvicorn server:app --reload --port 8080
# 開啟 http://localhost:8080
```

---

## 技術架構

```
FastAPI (Python)
  ├── /api/health    → 檢查 LLM 連線狀態
  ├── /api/generate  → 串流生成提示詞 (SSE)
  └── /             → 靜態前端 HTML
```

LLM 優先順序：`ANTHROPIC_API_KEY` > `GEMINI_API_KEY` > `OPENAI_API_KEY`
