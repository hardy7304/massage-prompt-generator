# 💆 柔手整復 · 影片提示詞生成器

Google Flow / Veo 影片提示詞快速組合工具，專為台灣按摩整復工作室設計。

## 功能

- **8 大維度多選**：角色、鏡頭、背景、敘事、風格、角度、說話、字幕
- **一句話輸入**：直接描述影片概念，AI 自動展開
- **流式輸出**：即時串流顯示生成過程
- **三種輸出格式**：完整分析 / 英文提示詞 / 中文版本
- **僅 DeepSeek**（MVP）

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

在 Zeabur 服務設定 → **Environment** 分頁，設定 **`DEEPSEEK_API_KEY`**（[申請](https://platform.deepseek.com/api_keys)）。

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

在 Railway Dashboard → Variables 設定 `DEEPSEEK_API_KEY`。

---

## 本地執行

**為什麼感覺「每次都要重新安裝」？** 若沒用虛擬環境，Windows 上可能這次用到 A 顆 Python、下次用到 B 顆，套件就裝在不同位置。**請用專案內的 `.venv`**，依賴只裝一次、永遠同一顆直譯器。

### 方式 A：一鍵啟動（Windows PowerShell，推薦）

1. **只在專案根目錄的 `.env` 填入 API Key**（複製 `.env.example` 為 `.env`）
2. 在專案根目錄執行：

```powershell
.\run.ps1
```

第一次會自動建立 `.venv` 並 `pip install`；之後再開專案**只要執行同一行**，不必重裝。

若出現「無法載入，因為這個系統上已停用指令碼」，請先執行一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 方式 B：手動虛擬環境（macOS / Linux / 想自己控管時）

**只做一次：**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

**之後每次新開終端機：** 先 `cd` 到專案、`activate`，再：

```bash
python -m uvicorn server:app --reload
# 開啟 http://localhost:8000
```

不用 activate 也可（Windows）：`.venv\Scripts\python.exe -m uvicorn server:app --reload`

---

## 技術架構

```
FastAPI (Python)
  ├── /api/health    → 檢查 LLM 連線狀態
  ├── /api/generate  → 串流生成提示詞 (SSE)
  └── /             → 靜態前端 HTML
```

LLM：**DeepSeek**（網頁金鑰或 `DEEPSEEK_API_KEY`）
