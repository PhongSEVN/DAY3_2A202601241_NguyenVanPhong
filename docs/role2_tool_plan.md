# 🛠️ KẾ HOẠCH ĐỊNH NGHĨA TOOLS (ROLE 2)

**Dự án**: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn
**Bộ dữ liệu**: `data/VietJobs.csv` (48,092 vị trí tuyển dụng thực tế — đã đếm lại bằng `csv.DictReader`, con số 238,986 ghi ở Mốc 1 là sai)
**Nhánh Git**: `role/tool-engineer-nhi`
**Người thực hiện**: Role 2 - Tool & Spec Engineer
**Trạng thái**: ✅ Mốc 1, Mốc 2 & Mốc 3 hoàn thành

---

## 🎯 1. TỔNG QUAN 4 TOOL ĐÃ TRIỂN KHAI (`src/tools.py`)

Khớp đúng hợp đồng tool mà Role 3 đã draft sẵn trong `docs/role3_failure_modes.md`:

| Tool | Tham số | Vai trò | Side effect |
| :--- | :--- | :--- | :--- |
| `search_jobs` | `keyword, location, top_n` | Tra cứu vị trí tuyển dụng thật trong `VietJobs.csv` | read-only |
| `screen_resume` | `cv_text, job_requirements` | **Chấm độ phù hợp CV ↔ yêu cầu công việc** | read-only |
| `check_available_slots` | `date, top_n` | Xem khung giờ phỏng vấn còn trống (**bổ sung ở Mốc 2**) | read-only |
| `schedule_interview` | `candidate_name, slot` | Đặt lịch phỏng vấn (mock, lưu trong bộ nhớ phiên) | **WRITE** |

> 🆕 **Vì sao thêm `check_available_slots` ở Mốc 2?** Test case #1 và #7 của Role 1 gọi thẳng tên tool này, và Failure Mode #6 của Role 3 quy định *"Agent phải tra khung giờ rảnh trước khi chốt lịch"*. Nếu thiếu, Agent sẽ rơi vào Phantom Tool (Failure Mode #10) ngay ở happy path.

Luồng ReAct điển hình: `search_jobs` lấy `job_id` + `requirements_text` thật từ dataset → `screen_resume(cv_text, requirements_text_vừa_lấy)` chấm độ phù hợp → `check_available_slots` tìm giờ trống → `schedule_interview` chốt lịch.

---

## 🔍 2. TÌM ĐỘ PHÙ HỢP CV DỰA TRÊN DATA ĐÃ CÓ (`screen_resume`)

Không thêm thư viện ngoài `requirements.txt` hiện có (không dùng `pandas`/`sklearn`/`numpy`) để tránh phá môi trường của các Role khác. Thuật toán hoàn toàn thuần Python:

1. **Tokenize**: lowercase, bỏ dấu câu bằng `re.sub(r"[^\w\s]", " ", text)` (Python 3 `\w` hỗ trợ Unicode nên giữ nguyên tiếng Việt có dấu), loại bỏ danh sách stopword tiếng Việt ngắn.
2. **Điểm chính — Độ phủ từ khóa JD**: `|từ khóa JD ∩ từ khóa CV| / |từ khóa JD|`, tức tỉ lệ yêu cầu công việc mà CV đáp ứng được (đúng cách ATS thật chấm hồ sơ).
3. **Điểm phụ — Cosine similarity**: `dot(vec_a, vec_b) / (norm(vec_a) * norm(vec_b))` trên vector term-frequency, báo kèm để tham khảo.
4. **Giải thích kết quả**: liệt kê cả **từ khóa trùng khớp** lẫn **từ khóa yêu cầu còn thiếu**, để Agent nêu được *"CV thiếu kỹ năng gì"* trong Final Answer (đúng kỳ vọng test case #9) thay vì "diễn giải mù".
5. **Xếp loại**: `>=70%` Phù hợp cao / `40–70%` Phù hợp trung bình / `<40%` Không phù hợp.

> ⚠️ **Đổi thang điểm ở Mốc 2 (cosine ➔ độ phủ từ khóa)**: khi self-test, một CV IT khớp hoàn toàn với JD IT chỉ đạt **39.9% cosine ➔ bị xếp "❌ Không phù hợp"**. Nguyên nhân là cosine bị kéo thấp một cách máy móc khi CV dài (nhiều token thừa) còn JD ngắn. Với thang độ phủ từ khóa, đúng CV đó đạt **100% ➔ "✅ Phù hợp cao"**, còn CV Kế toán đối chiếu JD IT vẫn chỉ **2.8% ➔ "❌ Không phù hợp"**. Nếu giữ cosine, happy path (test case #1) sẽ không bao giờ đi tới bước đặt lịch.

**Vì sao không chạy similarity trên toàn bộ 48k dòng cùng lúc?** `screen_resume` chỉ so 1 CV với 1 đoạn yêu cầu công việc cụ thể (lấy từ kết quả `search_jobs`) — việc "quét" dataset lớn được tách riêng sang `search_jobs` (lọc substring, dừng sớm khi đủ `top_n`). Mỗi tool chỉ làm một việc rõ ràng.

---

## 🛡️ 3. GUARDRAILS THEO TỪNG FAILURE MODE (đối chiếu `role3_failure_modes.md`)

| # | Failure Mode | Xử lý trong tools.py |
| :---: | :--- | :--- |
| 1 | No Match Found | `search_jobs` trả `"LỖI: Không tìm thấy..."` khi rỗng kết quả, không bịa dữ liệu |
| 2 | Ambiguous/Quá tải Token | `keyword` rỗng → lỗi yêu cầu rõ ràng; kết quả giới hạn `top_n ≤ 20` + cắt `requirements_text` còn ~300 ký tự |
| 3 | Out-of-Scope Location | `_known_location()` đối chiếu địa điểm với index thật của dataset → `"LỖI: Địa điểm 'Sao Hỏa' không có trong dữ liệu..."` ngay từ lần gọi đầu, Agent không lặp tìm |
| 4 | Invalid Date/Time Format | `schedule_interview` & `check_available_slots` bắt `ValueError` từ `datetime.strptime`, trả lỗi định dạng rõ ràng |
| 5 | Past Date Scheduling | So sánh `dt < datetime.now()` để chặn lịch quá khứ (cả 2 tool lịch) |
| 6 | Schedule Conflict | `check_available_slots` cho xem giờ trống trước; `_BOOKED_SLOTS` phát hiện trùng và **gợi ý gọi lại `check_available_slots[<ngày>]`** |
| 7 | Empty/Unreadable Resume | `screen_resume` chặn khi `cv_text` dưới ~30 từ |
| 8 | Mismatched Job Requirements | Độ phủ từ khóa tự nhiên thấp khi CV và JD khác ngành, kèm verdict + **danh sách từ khóa còn thiếu** để Agent nêu cụ thể trong Final Answer |
| 9 | Prompt Injection via Resume | `screen_resume` chỉ đếm token, không diễn giải nội dung CV như chỉ thị; thêm `_detect_injection()` gắn dòng `⚠️ CẢNH BÁO BẢO MẬT` vào Observation để Agent báo cáo lại đúng bản chất |
| 10 | Unknown / Phantom Tool | `run_tool()` tra `AVAILABLE_TOOLS`, tool lạ → `"LỖI: Công cụ 'send_email' không tồn tại. Chỉ được dùng: ..."` thay vì `KeyError` |
| 11 | Malformed Action Syntax | `_as_text()` gỡ dấu nháy thừa, `_as_int()` ép `top_n="5"` → `5`; `run_tool()` bắt `TypeError` và trả lại **chữ ký đúng** của tool |
| 14 | PII Leakage | `_mask_pii()` che số điện thoại/email lẫn trong mô tả công việc trước khi trả cho Agent |

Tất cả lỗi trả về dạng chuỗi `"LỖI: ..."` (không raise Exception), khớp yêu cầu checklist Mốc 3: "các hàm trong `src/tools.py` khi gặp lỗi sẽ trả về chuỗi thông báo lỗi chứ không crash code." `run_tool()` còn có `except Exception` bao ngoài làm phao cứu sinh cuối cùng.

---

---

# 📍 PHẦN MỐC 2 — TOOL SPECS CHUẨN HOÁ

## 📋 5. TOOL CONTRACT — 8 TRƯỜNG CHUẨN (theo CODELAB mục 3)

Mỗi tool trong `src/tools.py` có docstring ghi đủ 8 trường dưới đây, và cùng nội dung đó được khai báo dạng máy đọc được trong dict `TOOL_SPECS`.

### 5.1 `search_jobs[keyword, location, top_n]`

| Field | Nội dung |
| :--- | :--- |
| **Name** | `search_jobs` |
| **Purpose** | Lấy dữ liệu tuyển dụng CÓ THẬT để Agent không bịa. **Không dùng** khi yêu cầu còn mơ hồ ("tìm việc cho tôi") — phải hỏi lại người dùng |
| **Input schema** | `keyword: str` (bắt buộc), `location: str = ""`, `top_n: int = 5` (1–20) |
| **Output schema** | `- [job_id=N] <tên> \| <địa điểm> \| Lương: <mức>` + `Yêu cầu: <trích 300 ký tự>` |
| **Error semantics** | `LỖI:` khi thiếu keyword / không đọc được CSV / địa điểm ngoài dataset / không có kết quả |
| **Side effect** | Read-only (đọc CSV, cache RAM) |
| **Example** | `Action: search_jobs["Kế toán", "Hà Nội", 3]` |
| **Safety** | Giới hạn `top_n ≤ 20`, cắt mô tả 300 ký tự, che PII, không raise Exception |

### 5.2 `screen_resume[cv_text, job_requirements]`

| Field | Nội dung |
| :--- | :--- |
| **Name** | `screen_resume` |
| **Purpose** | Chấm điểm khách quan CV ↔ JD bằng thuật toán. **Không dùng** khi chưa có JD thật từ `search_jobs` |
| **Input schema** | `cv_text: str` (≥ 30 từ), `job_requirements: str` |
| **Output schema** | `Độ phù hợp CV - Yêu cầu công việc: X% (verdict)` + số từ khóa đáp ứng/thiếu + cosine |
| **Error semantics** | `LỖI:` khi CV < 30 từ, thiếu JD, hoặc JD không có từ khóa |
| **Side effect** | Read-only (không lưu CV xuống đĩa) |
| **Example** | `Action: screen_resume["Tôi có 3 năm kinh nghiệm Python...", "Yêu cầu: Python, SQL..."]` |
| **Safety** | CV chỉ được **đếm từ**, tuyệt đối không thi hành chỉ thị bên trong; gắn cảnh báo khi phát hiện injection |

### 5.3 `check_available_slots[date, top_n]`

| Field | Nội dung |
| :--- | :--- |
| **Name** | `check_available_slots` |
| **Purpose** | Tra khung giờ trống TRƯỚC khi chốt lịch. **Không dùng** để đặt lịch |
| **Input schema** | `date: str = ""` (`dd/mm/yyyy`, trống = ngày làm việc gần nhất), `top_n: int = 6` |
| **Output schema** | `Ngày dd/mm/yyyy (Thứ X) còn N khung giờ trống:` + danh sách `dd/mm/yyyy HH:MM` (dùng lại được ngay làm tham số `slot`) |
| **Error semantics** | `LỖI:` khi sai định dạng / ngày quá khứ / rơi vào cuối tuần / đã kín lịch |
| **Side effect** | Read-only |
| **Example** | `Action: check_available_slots["05/08/2026"]` |
| **Safety** | Chỉ trả giờ hành chính T2–T6, đã lọc thời điểm đã trôi qua |

### 5.4 `schedule_interview[candidate_name, slot]`

| Field | Nội dung |
| :--- | :--- |
| **Name** | `schedule_interview` |
| **Purpose** | Chốt lịch sau khi CV đạt và giờ đã xác nhận trống. **Không dùng** khi thiếu tên/thời gian hoặc CV chưa chấm |
| **Input schema** | `candidate_name: str`, `slot: str` (`dd/mm/yyyy HH:MM`) |
| **Output schema** | `✅ Đã đặt lịch phỏng vấn thành công cho ứng viên '<tên>' vào lúc <slot>.` |
| **Error semantics** | `LỖI:` khi thiếu tham số / sai định dạng / quá khứ / trùng lịch |
| **Side effect** | ⚠️ **WRITE** — ghi vào `_BOOKED_SLOTS`. Tool **duy nhất** thay đổi trạng thái |
| **Example** | `Action: schedule_interview["Nguyễn Văn A", "05/08/2026 14:30"]` |
| **Safety** | Chặn ngày quá khứ & double-booking, gợi ý gọi `check_available_slots` khi trùng |

---

## 🔗 6. MỘT NGUỒN SỰ THẬT: `TOOL_SPECS` + `get_tools_description()`

`src/tools.py` xuất ra 4 thứ cho các Role khác dùng lại:

| Export | Dành cho | Công dụng |
| :--- | :--- | :--- |
| `AVAILABLE_TOOLS` | Role 4 | dict `tên → hàm` để vòng lặp ReAct thực thi |
| `TOOL_SPECS` | Role 3 & 5 | Mô tả 8 trường dạng máy đọc được của từng tool |
| `get_tools_description()` | **Role 3** | Sinh sẵn khối text "Danh sách công cụ" để dán thẳng vào `REACT_SYSTEM_PROMPT` |
| `run_tool(name, *args)` | **Role 4** | Lớp bọc an toàn: tool ma / sai tham số / exception bất ngờ đều thành chuỗi `LỖI:` |
| `parse_action()` / `execute_action()` | **Role 4** | *(bổ sung ở Mốc 3)* Bóc tách dòng `Action: tool[...]` tôn trọng dấu nháy rồi thực thi — xem mục 10.1 |

**Vì sao quan trọng?** Nếu Role 3 tự gõ tay danh sách tool vào prompt, chỉ cần lệch một chữ (`search_job` vs `search_jobs`) là Agent gọi tool ma. Dùng `get_tools_description()` thì prompt luôn khớp 100% với `AVAILABLE_TOOLS` — Failure Mode #10 bị chặn từ gốc.

```python
# src/prompts.py — Role 3 chỉ cần:
from tools import get_tools_description

REACT_SYSTEM_PROMPT = f"""Bạn là Trợ Lý AI Tuyển Dụng Thông Minh (HR ReAct Agent).

Danh sách công cụ được phép dùng (KHÔNG được dùng công cụ nào ngoài danh sách này):
{get_tools_description()}
...
"""
```

---

## 🧪 7. KẾT QUẢ CHẠY THỬ TOOL ĐỘC LẬP (Checkpoint Mốc 2)

```bash
python src/tools.py
```

Self-test nằm ngay trong `src/tools.py` (không cần API key, không cần mạng), phủ cả happy path lẫn mọi câu bẫy của Role 1. Sau Mốc 3, bộ test này mở rộng thành **94 phép kiểm tra** (32 case chức năng + 62 lần dội tham số rác):

```
📊 KẾT QUẢ: 94/94 PASS, 0 FAIL
🛠️ Tool đã đăng ký: search_jobs, screen_resume, check_available_slots, schedule_interview
```

Ngoài ra tool còn được đối chiếu với các Failure Mode của Role 3 — xem bảng ở mục 3 và bảng test case cập nhật ở mục 10.

---

## 🤝 8. BÀN GIAO SAU MỐC 2

- **Role 3 (Prompt Engineer)**: thay danh sách tool gõ tay bằng `get_tools_description()` (snippet ở mục 6).
- **Role 4 (Core Developer)**: gọi tool qua `run_tool(name, *args)` thay vì `AVAILABLE_TOOLS[name](...)`.
- **Role 1 (Product Architect)**: 4 tên tool trong `expected_behavior` khớp 100% với `AVAILABLE_TOOLS`.
- **Role 5 (Observability)**: `TOOL_SPECS[...]["side_effect"]` cho biết tool nào read-only, tool nào WRITE — tiện cho cột "tác động" trong Scoring Matrix.

---

# 📍 PHẦN MỐC 3 — TOOL KHÔNG BAO GIỜ LÀM CRASH AGENT

> **Nhiệm vụ Role 3 theo checklist**: *"Đảm bảo các hàm trong `src/tools.py` khi gặp lỗi sẽ trả về chuỗi thông báo lỗi chứ không crash code."*

## 🧨 9. FUZZ TEST — BẰNG CHỨNG KHÔNG CRASH

Không tự nhận "chắc là an toàn", mà dội thẳng tham số rác vào **mọi tool**: `()`, `("",)`, `(None,)`, `(0,)`, `(-1,)`, `([],)`, `({},)`, chuỗi 5.000 ký tự, `<script>alert(1)</script>`, `'; DROP TABLE jobs;--`, emoji, thừa 5 tham số, số thực/boolean… và dội tiếp vào lớp parser: `""`, `None`, `"Action:"`, `"search_jobs["`, `"]]][[["`, `12345`.

```
🧨 FUZZ TEST: 4 tool × 13 bộ tham số rác
✅ PASS — 62/62 lần gọi trả về chuỗi an toàn, 0 crash

📊 KẾT QUẢ: 94/94 PASS, 0 FAIL
```

Ba lớp phòng thủ xếp chồng:

1. `_as_text()` / `_as_int()` — ép kiểu mọi tham số LLM truyền sang trước khi dùng.
2. Từng tool tự kiểm tra đầu vào và trả `"LỖI: ..."` thay vì `raise`.
3. `run_tool()` bọc ngoài cùng: `except TypeError` (sai số lượng tham số, trả lại **chữ ký đúng** cho Agent tự sửa) + `except Exception` (phao cứu sinh cuối).

---

## 🔧 10. BA LỖI THẬT PHÁT HIỆN KHI GHÉP VỚI CODE MỚI CỦA NHÓM

Sau khi `git pull` bản Mốc 3 của Role 1 & Role 4, chạy thử 6 test case ở tầng tool thì lộ ra 3 lỗi — đều đã sửa:

### 10.1 Parser tách tham số bằng `split(",")` làm vỡ test case #4

`src/app.py` (dòng 216) bóc tham số bằng `params_raw.split(",")`. CV trong test case #4 chứa dấu phẩy ("Python, SQL, ETL, xây dựng pipeline…") nên **1 tham số bị vỡ thành 7**:

```
so tham so parser boc ra: 7
=> CRASH: TypeError screen_resume() takes 2 positional arguments but 7 were given
```

➔ Role 2 bổ sung `parse_action()` (tôn trọng dấu nháy) và `execute_action()`. Vòng lặp ReAct của Role 4 rút gọn còn **1 dòng**:

```python
# src/app.py — thay toàn bộ khối parse + execute (dòng 209–228) bằng:
from tools import execute_action
...
if "Action:" in response:
    action_line = [l for l in response.split("\n") if "Action:" in l][0]
    obs = execute_action(action_line)      # tự parse, tự bắt lỗi, luôn trả str
    print(f"👁️ Observation: {obs}")
    history += f"\n{response}\nObservation: {obs}"
```

### 10.2 Ngưỡng CV 30 từ chặn mất chính test case #4

CV mà Role 1 đưa vào test case #4 chỉ có **25 từ** → tool trả `LỖI: CV quá ngắn`, trong khi `expected_behavior` ghi *"trả về điểm tương đồng cùng verdict"*. Nếu giữ nguyên, happy path multi-step không bao giờ chạy được.

➔ Tách 2 ngưỡng: **dưới 15 từ** mới từ chối chấm (`MIN_CV_WORDS_HARD`), **15–29 từ** vẫn chấm nhưng gắn `ℹ️ LƯU Ý: CV khá ngắn (25 từ), điểm chỉ mang tính tham khảo`. CV rác kiểu *"Tôi tên Nam. Tôi muốn xin việc."* (7 từ) vẫn bị chặn như cũ.

### 10.3 "TP. HCM" bị báo không tìm thấy dù có 15,311 vị trí

Dataset chỉ lưu một dạng duy nhất là `hồ chí minh`, nên test case #3 hỏi "Kế toán ở TP. HCM" trả về `LỖI: Không tìm thấy`.

➔ Thêm `_normalize_location()` + bảng `_LOCATION_ALIASES`: `TP. HCM` / `TPHCM` / `Sài Gòn` / `SG` → `hồ chí minh`; `HN` → `hà nội`; `ĐN` → `đà nẵng`… Bỏ tiền tố `TP.` / `Thành phố` / `Tỉnh` trước khi so khớp.

---

## ✅ 11. ĐỐI CHIẾU 6 TEST CASE HIỆN TẠI CỦA ROLE 1 (ở tầng tool)

| # | Câu hỏi | Action Agent cần sinh | Observation tool trả về |
| :---: | :--- | :--- | :--- |
| 1 | Lập trình viên Python tại Hà Nội | `search_jobs["Lập trình viên Python", "Hà Nội", 5]` | ✅ `Tìm thấy 1 vị trí phù hợp` (dữ liệu thật, không bịa cho đủ 5) |
| 2 | Đặt lịch 05/08/2026 14:30 | `schedule_interview["Nguyễn Văn An", "05/08/2026 14:30"]` | ✅ `Đã đặt lịch phỏng vấn thành công...` |
| 3 | Kế toán ở TP. HCM → đặt lịch | `search_jobs["Kế toán", "TP. HCM", 3]` → `schedule_interview[...]` | ✅ `Tìm thấy 3 vị trí` (nhờ alias địa điểm) |
| 4 | Chấm CV cho Data Engineer | `search_jobs[...]` → `screen_resume[cv, jd]` | ✅ `ℹ️ LƯU Ý: CV khá ngắn (25 từ)...` + điểm & verdict |
| 5 | Kỹ sư Hạt nhân trên Sao Hỏa | `search_jobs["Kỹ sư Hạt nhân", "Sao Hỏa"]` | ✅ `LỖI: Địa điểm 'Sao Hỏa' không có trong dữ liệu` — Agent không có gì để bịa |
| 6 | Đặt lịch 31/02/2026 25:99 | `schedule_interview["Phạm Văn C", "31/02/2026 25:99"]` | ✅ `LỖI: Định dạng ngày giờ ... không hợp lệ` |

---

## 🤝 12. BÀN GIAO CHO CÁC ROLE KHÁC (sau Mốc 3)

- **Role 4**: đổi khối parse thủ công sang `execute_action()` như snippet mục 10.1 — hết lỗi vỡ tham số chứa dấu phẩy và hết `KeyError` khi Agent gọi tool ma.
- **Role 3**: `src/prompts.py` **vẫn đang là boilerplate `get_weather` / `search_flights`** — Agent hiện được phát danh sách tool sai hoàn toàn so với `AVAILABLE_TOOLS`, đây là lỗi chặn Mốc 3. Thay bằng `get_tools_description()`. Ngoài ra `MAX_ITERATIONS = 3` vừa đủ cho test case #3 và #4 (2 lượt gọi tool + 1 lượt Final Answer) — không còn dư bước nào để Agent sửa sai, nên cân nhắc nâng lên 5.
- **Role 5**: `execute_action()` trả Observation dạng chuỗi thống nhất, mọi lỗi đều mở đầu bằng `LỖI:` — tiện lọc khi soi Trace Log và phân loại *correct / safe fallback / hallucinated*.
