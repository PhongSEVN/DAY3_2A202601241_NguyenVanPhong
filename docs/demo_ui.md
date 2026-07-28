# 🖥️ GIAO DIỆN DEMO — Trợ Lý Sàng Lọc Hồ Sơ & Hẹn Phỏng Vấn

Giao diện web để demo trực quan Agent trước lớp: thấy được **từng vòng Thought → Action →
Observation**, thấy Agent gọi tool nào, và đặt cạnh nhau **Chatbot gốc vs ReAct Agent** trên
cùng một câu hỏi.

---

## 🚀 1. CHẠY DEMO (2 TERMINAL)

**Terminal 1 — Backend (Agent + Tools):**

```bash
pip install -r requirements.txt
python src/server.py
```

**Terminal 2 — Giao diện:**

```bash
cd client
npm install
npm run dev
```

Mở http://localhost:5173

> ⚙️ Backend đọc API key từ file `.env` ở thư mục gốc. Nhớ đặt `LLM_PROVIDER` trùng với
> provider mà bạn có key thật (`openai` / `gemini` / `anthropic` / `openrouter`). Chưa có key
> nào thì đặt `LLM_PROVIDER=mock` để xem thử giao diện.

---

## 🧩 2. KIẾN TRÚC GHÉP NỐI

```text
Trình duyệt (React + Vite, cổng 5173)
        │  fetch /api/*  ──► proxy của Vite ──►  Flask (cổng 8000)
        ▼
  client/src/pages/ChatPage.tsx          src/server.py
  client/src/components/AgentTrace.tsx        │
  client/src/lib/api.ts                       ├── vòng lặp ReAct + Guardrails
                                              ├── src/tools.py     [Role 2]
                                              ├── src/prompts.py   [Role 3]
                                              ├── src/providers.py (multi-provider)
                                              └── config/test_cases.json [Role 1]
```

`src/server.py` **không thay thế** `src/app.py`. Bản CLI của Role 4 giữ nguyên; server chỉ
bọc lại đúng các thành phần đó và trả JSON thay vì `print()` ra Terminal.

### 🔑 API key nằm ở đâu

Bản giao diện gốc gọi thẳng OpenAI từ trình duyệt bằng `VITE_OPENAI_API_KEY`. Mọi biến
`VITE_*` bị nhúng cứng vào bundle JavaScript — ai mở DevTools cũng đọc được key. Bản tích hợp
này bỏ hẳn cách đó: **key chỉ nằm trong `.env` ở server**, trình duyệt không thấy gì.

---

## 📡 3. API ENDPOINTS

| Endpoint | Việc |
| :--- | :--- |
| `GET /api/health` | Provider/model đang dùng, đã có API key chưa, danh sách tool |
| `GET /api/tools` | Tool Contract từ `TOOL_SPECS` — hiển thị ở sidebar |
| `GET /api/test-cases` | Bộ test case của Role 1 — bấm 1 phát là chạy |
| `POST /api/chat` | `{question, mode: "react"｜"baseline"｜"both", max_iterations}` |

`POST /api/chat` trả về mỗi bước dưới dạng có cấu trúc, đúng thứ Role 5 cần cho `trace_eval.md`:

```json
{
  "react": {
    "answer": "...",
    "steps": [
      {"index": 1, "thought": "...", "action": "search_jobs[\"Kế toán\", \"TP. HCM\", 3]",
       "observation": "Tìm thấy 3 vị trí...", "tool": "search_jobs",
       "is_error": false, "final": false}
    ],
    "iterations": 2,
    "tools_used": ["search_jobs"],
    "guardrail_triggered": false,
    "duration_ms": 4512
  }
}
```

---

## 🎬 4. KỊCH BẢN DEMO TRƯỚC LỚP

1. **Chọn "So sánh cả hai"** → bấm test case **#5 (🔴 Bẫy — Kỹ sư Hạt nhân trên Sao Hỏa)**.
   - *Chatbot gốc*: trả lời chung chung, tự suy đoán về thị trường việc làm.
   - *ReAct Agent*: gọi `search_jobs["Kỹ sư Hạt nhân", "Sao Hỏa"]` → Observation
     `LỖI: Địa điểm 'Sao Hỏa' không có trong dữ liệu` → thành thật hỏi lại người dùng thay vì
     bịa. Trace Log hiện rõ badge đỏ **TOOL TRẢ LỖI**.

2. **Chuyển "ReAct Agent"** → bấm test case **#3 (🟡 Multi-step)** để thấy Agent đi 2 bước
   liên tiếp: `search_jobs` rồi `schedule_interview`.

3. **Kéo thanh Guardrail xuống 1** rồi hỏi lại câu multi-step → Agent chưa kịp chốt đã bị ngắt,
   giao diện hiện badge **"Guardrail ngắt lặp"**. Đây là minh chứng `MAX_ITERATIONS` hoạt động.

4. **Bấm vào từng tool ở sidebar** để mở Tool Contract (mô tả, tham số, READ hay WRITE) —
   dữ liệu lấy trực tiếp từ `TOOL_SPECS` trong `src/tools.py`, không gõ tay lại.

---

## 🧹 5. GHI CHÚ VỀ THƯ MỤC `client/`

Thư mục này vốn là mảnh giao diện của một dự án khác (VietCropDoctor — chẩn đoán bệnh cây
trồng). Khi tích hợp đã dọn:

- Xóa `hooks/useAdmin.ts`, `hooks/useExpert.ts`, `types/admin.ts`, `types/expert.ts`,
  `constants/domain.tsx` — đều import `@/lib/expert-api`, `@/lib/api` không tồn tại nên
  `npm run build` sẽ gãy.
- Xóa `.env.local` (chứa API key OpenAI thật) và bổ sung `.env*.local` vào `client/.gitignore`
  — bản `.gitignore` cũ là của Next.js, **không** chặn `.env.local`, chỉ cần `git add client/`
  là key bị đẩy lên repo nhóm.
- Giữ nguyên `Markdown.tsx` (dùng để render câu trả lời của LLM) và bảng màu Material trong
  `styles/globals.css`.
