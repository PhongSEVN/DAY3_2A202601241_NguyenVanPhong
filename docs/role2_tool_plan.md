# 🛠️ KẾ HOẠCH ĐỊNH NGHĨA TOOLS (ROLE 2)

**Dự án**: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn
**Bộ dữ liệu**: `data/VietJobs.csv` (238,986 vị trí tuyển dụng thực tế)
**Nhánh Git**: `role/tool-engineer-nhi`
**Người thực hiện**: Role 2 - Tool & Spec Engineer

---

## 🎯 1. TỔNG QUAN 3 TOOL ĐÃ TRIỂN KHAI (`src/tools.py`)

Khớp đúng hợp đồng tool mà Role 3 đã draft sẵn trong `docs/role3_failure_modes.md`:

| Tool | Tham số | Vai trò |
| :--- | :--- | :--- |
| `search_jobs` | `keyword, location, top_n` | Tra cứu vị trí tuyển dụng thật trong `VietJobs.csv` |
| `screen_resume` | `cv_text, job_requirements` | **Chấm độ tương đồng CV ↔ yêu cầu công việc** |
| `schedule_interview` | `candidate_name, slot` | Đặt lịch phỏng vấn (mock, lưu trong bộ nhớ phiên) |

Luồng ReAct điển hình: Agent gọi `search_jobs` để lấy `job_id` + `requirements_text` thật từ dataset → gọi `screen_resume(cv_text, requirements_text_vừa_lấy)` để chấm độ phù hợp → nếu phù hợp, gọi `schedule_interview` để chốt lịch.

---

## 🔍 2. TÌM ĐỘ TƯƠNG ĐỒNG CV DỰA TRÊN DATA ĐÃ CÓ (`screen_resume`)

Không thêm thư viện ngoài `requirements.txt` hiện có (không dùng `pandas`/`sklearn`/`numpy`) để tránh phá môi trường của các Role khác. Thuật toán hoàn toàn thuần Python:

1. **Tokenize**: lowercase, bỏ dấu câu bằng `re.sub(r"[^\w\s]", " ", text)` (Python 3 `\w` hỗ trợ Unicode nên giữ nguyên tiếng Việt có dấu), loại bỏ danh sách stopword tiếng Việt ngắn.
2. **Vector hoá**: đếm tần suất từ bằng `collections.Counter` cho cả `cv_text` và `job_requirements`.
3. **Cosine similarity**: `dot(vec_a, vec_b) / (norm(vec_a) * norm(vec_b))` — chỉ so 2 đoạn text ngắn mỗi lần gọi nên không cần numpy, tốc độ tức thời.
4. **Giải thích kết quả**: trích giao của 2 tập token làm "từ khóa trùng khớp" để Agent/người dùng hiểu vì sao có điểm số đó, tránh Agent "diễn giải mù".
5. **Xếp loại**: `>=70%` Phù hợp cao / `40–70%` Phù hợp trung bình / `<40%` Không phù hợp.

**Vì sao không chạy similarity trên toàn bộ 239k dòng cùng lúc?** `screen_resume` chỉ so 1 CV với 1 đoạn yêu cầu công việc cụ thể (lấy từ kết quả `search_jobs`) — việc "quét" dataset lớn được tách riêng sang `search_jobs` (lọc substring, dừng sớm khi đủ `top_n`). Tách 2 bước giúp giữ đúng 3-tool contract, không cần thêm tool thứ 4, và mỗi tool chỉ làm một việc rõ ràng.

---

## 🛡️ 3. GUARDRAILS THEO TỪNG FAILURE MODE (đối chiếu `role3_failure_modes.md`)

| # | Failure Mode | Xử lý trong tools.py |
| :---: | :--- | :--- |
| 1 | No Match Found | `search_jobs` trả `"LỖI: Không tìm thấy..."` khi rỗng kết quả, không bịa dữ liệu |
| 2 | Ambiguous/Quá tải Token | `keyword` rỗng → lỗi yêu cầu rõ ràng; kết quả giới hạn `top_n` + cắt `requirements_text` còn ~300 ký tự |
| 4 | Invalid Date/Time Format | `schedule_interview` bắt `ValueError` từ `datetime.strptime`, trả lỗi định dạng rõ ràng |
| 5 | Past Date Scheduling | So sánh `dt < datetime.now()` để chặn lịch quá khứ |
| 6 | Schedule Conflict | Set `_BOOKED_SLOTS` phát hiện trùng khung giờ |
| 7 | Empty/Unreadable Resume | `screen_resume` chặn khi `cv_text` dưới ~30 từ |
| 8 | Mismatched Job Requirements | Điểm cosine tự nhiên thấp khi CV và JD khác ngành, kèm verdict rõ ràng để Agent nêu trong Final Answer |
| 9 | Prompt Injection via Resume | `screen_resume` chỉ đếm token, không diễn giải nội dung CV như chỉ thị — miễn nhiễm ở tầng tool, cộng thêm guardrail prompt của Role 3 |

Tất cả lỗi trả về dạng chuỗi `"LỖI: ..."` (không raise Exception), khớp yêu cầu checklist Mốc 3: "các hàm trong `src/tools.py` khi gặp lỗi sẽ trả về chuỗi thông báo lỗi chứ không crash code."

---

## 🤝 4. BÀN GIAO CHO CÁC ROLE KHÁC

- **Role 4 (Core Developer)**: `src/app.py` hiện còn `import get_weather, search_flights` (boilerplate cũ) — cần `git pull` và cập nhật để import 3 tool mới (`search_jobs`, `screen_resume`, `schedule_interview`) qua `AVAILABLE_TOOLS`, đồng thời viết parser cho cú pháp `Action: tool[arg1, arg2]`.
- **Role 3 (Prompt Engineer)**: Bản nháp `REACT_SYSTEM_PROMPT` trong `role3_failure_modes.md` đã khớp sẵn với chữ ký 3 tool này, chỉ cần copy chính thức vào `src/prompts.py`.
- **Role 1 (Product Architect)**: Có thể bổ sung `config/test_cases.json` với case dùng `screen_resume` (VD: CV IT vs yêu cầu Kế toán → Agent phải chỉ ra sự không khớp ngành).
