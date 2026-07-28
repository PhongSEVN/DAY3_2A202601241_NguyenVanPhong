"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer / Integrator)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.

Đề tài nhóm: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn

Trạng thái: ✅ MỐC 2 (Baseline Chatbot) — 🚧 Mốc 3 (ReAct Loop) sẽ làm sau.

Cách chạy:
    python src/app.py            # Demo: chạy Chatbot Baseline trên vài test case tiêu biểu
    python src/app.py --all      # Chạy Baseline trên TOÀN BỘ test cases của Role 1
    python src/app.py --case 5   # Chạy Baseline trên đúng test case có id = 5
    python src/app.py --chat     # Chế độ hỏi đáp tự do với Chatbot Baseline
"""

import json
import os
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()

# Các test case tiêu biểu dùng cho bản demo nhanh (bộc lộ rõ nhất hạn chế của Chatbot gốc):
#   1  → cần nhiều bước + dữ liệu thật  ➔ Chatbot không tra cứu được
#   2  → vị trí không tồn tại           ➔ Chatbot dễ bịa Job Description (ảo giác)
#   13 → cần Observation trước kết luận ➔ Chatbot kết luận vội khi chưa có dữ liệu
DEMO_CASE_IDS = [1, 2, 13]

SEPARATOR = "=" * 70


def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_test_case(tests: list, case_id: int):
    """Tìm test case theo trường 'id' (không phải theo vị trí trong mảng)."""
    for case in tests:
        if case.get("id") == case_id:
            return case
    return None


# =============================================================================
# 💬 MỐC 2: BASELINE CHATBOT (LLM thuần, KHÔNG có Tool)
# =============================================================================

def run_baseline_chatbot(user_query: str, provider, verbose: bool = True) -> str:
    """
    Chạy Chatbot gốc (Baseline): gọi thẳng LLM với CHATBOT_BASELINE_PROMPT của Role 3,
    KHÔNG cấp bất kỳ công cụ nào.

    Đây là mốc so sánh (baseline) để đối chiếu với ReAct Agent ở Mốc 3: vì không có
    Tool, Chatbot không thể tra cứu dữ liệu tuyển dụng thật trong data/VietJobs.csv,
    nên dễ bịa thông tin (ảo giác) hoặc trả lời chung chung.

    Args:
        user_query (str): Câu hỏi của người dùng
        provider: LLM Provider lấy từ get_llm_provider()
        verbose (bool): True thì in chi tiết System Prompt ra màn hình

    Returns:
        str: Nội dung câu trả lời của Chatbot (để Role 5 dán vào docs/trace_eval.md)
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")

    if verbose:
        print("⚙️ System Prompt đang dùng (Role 3 soạn):")
        for line in CHATBOT_BASELINE_PROMPT.strip().splitlines():
            print(f"   │ {line}")
    print("🚫 Tool khả dụng: KHÔNG CÓ (đây là Chatbot gốc, chưa phải Agent)")

    # Gọi LLM Provider thực hiện sinh câu trả lời
    try:
        response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    except Exception as e:
        response = f"[App Error]: Gọi LLM Provider thất bại - {e}"

    print(f"\n🤖 Chatbot trả lời:\n{response}\n")
    return response


def run_baseline_on_case(case: dict, provider) -> dict:
    """
    Chạy Baseline Chatbot trên đúng 1 test case của Role 1 và in kèm kỳ vọng
    để cả nhóm đối chiếu ngay trên màn hình.

    Returns:
        dict: {id, category, question, expected_behavior, baseline_answer}
    """
    print(f"\n{SEPARATOR}")
    print(f"🧪 TEST CASE #{case.get('id')} — {case.get('category', 'N/A')}")
    print(SEPARATOR)

    answer = run_baseline_chatbot(case.get("question", ""), provider, verbose=False)

    print(f"🎯 Kỳ vọng (Role 1): {case.get('expected_behavior', 'N/A')}")

    return {
        "id": case.get("id"),
        "category": case.get("category"),
        "question": case.get("question"),
        "expected_behavior": case.get("expected_behavior"),
        "baseline_answer": answer,
    }


def run_baseline_batch(tests: list, provider, case_ids: list = None) -> list:
    """
    Chạy Baseline Chatbot hàng loạt trên nhiều test case.

    Args:
        tests (list): Toàn bộ test cases đọc từ config/test_cases.json
        provider: LLM Provider
        case_ids (list): Danh sách id cần chạy. None = chạy tất cả.

    Returns:
        list: Danh sách kết quả để Role 5 tổng hợp vào docs/trace_eval.md
    """
    selected = tests if case_ids is None else [c for c in tests if c.get("id") in case_ids]

    if not selected:
        print("⚠️ Không có test case nào khớp với danh sách id đã chọn.")
        return []

    results = []
    for case in selected:
        results.append(run_baseline_on_case(case, provider))

    print(f"\n{SEPARATOR}")
    print(f"📊 TỔNG KẾT: Đã chạy {len(results)}/{len(tests)} test case qua Chatbot Baseline.")
    print("👉 Role 5: copy phần '🤖 Chatbot trả lời' ở trên vào docs/trace_eval.md,")
    print("   ghi chú xem Chatbot có bịa thông tin (ảo giác) hay trả lời chung chung không.")
    print(SEPARATOR)
    return results


def run_interactive_chat(provider):
    """Chế độ hỏi đáp tự do với Chatbot Baseline (gõ 'exit' để thoát)."""
    print(f"\n{SEPARATOR}")
    print("💬 CHẾ ĐỘ CHAT TỰ DO VỚI CHATBOT BASELINE (gõ 'exit' hoặc Ctrl+C để thoát)")
    print(SEPARATOR)

    while True:
        try:
            query = input("\n👤 Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Đã thoát chế độ chat.")
            return

        if not query:
            continue
        if query.lower() in ("exit", "quit", "thoat", "thoát"):
            print("👋 Đã thoát chế độ chat.")
            return

        run_baseline_chatbot(query, provider, verbose=False)


# =============================================================================
# 🤖 MỐC 3: REACT AGENT LOOP (Thought -> Action -> Observation) — CHƯA LÀM
# =============================================================================

def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    step = 0
    history = f"Câu hỏi của người dùng: {user_query}"
    
    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM Provider thực hiện suy luận ReAct
        response = provider.generate(history, system_prompt=REACT_SYSTEM_PROMPT)
        print(response)
        
        # Nếu LLM đưa ra Final Answer thì hoàn tất
        if "Final Answer:" in response:
            break
            
        # Tìm và thực thi Action nếu có
        if "Action:" in response:
            action_line = [line for line in response.split("\n") if "Action:" in line][0]
            action_str = action_line.replace("Action:", "").strip()
            
            if "[" in action_str and "]" in action_str:
                tool_name = action_str.split("[")[0].strip()
                params_raw = action_str.split("[")[1].split("]")[0].strip()
                params = [p.strip().strip("'\"") for p in params_raw.split(",") if p.strip()]
                
                if tool_name in AVAILABLE_TOOLS:
                    try:
                        obs = AVAILABLE_TOOLS[tool_name](*params)
                    except Exception as e:
                        obs = f"LỖI THỰC THI TOOL '{tool_name}': {str(e)}"
                else:
                    obs = f"LỖI: Không tìm thấy công cụ '{tool_name}' trong hệ thống."
            else:
                obs = "LỖI: Định dạng Action không đúng quy tắc tên_công_cụ[tham_số]."
                
            print(f"👁️ Observation: {obs}")
            history += f"\n{response}\nObservation: {obs}"
        else:
            history += f"\n{response}"
            
    if step >= MAX_ITERATIONS and "Final Answer:" not in history:
        print(f"\n🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa {MAX_ITERATIONS} bước. Ngắt lặp an toàn!")


# =============================================================================
# ▶️ ENTRY POINT
# =============================================================================

def print_header(provider, tests):
    """In banner + trạng thái môi trường để cả nhóm biết App đang chạy với cấu hình gì."""
    print(SEPARATOR)
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("📌 Đề tài: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn")
    print(SEPARATOR)

    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider: {provider.__class__.__name__} (Model: {model_name})")

    if provider.__class__.__name__ == "MockProvider":
        print("⚠️ Đang chạy OFFLINE MOCK — câu trả lời là giả lập, không phải LLM thật.")
        print("   👉 Muốn thấy Chatbot ảo giác thật: copy .env.example thành .env,")
        print("      điền API key và đặt LLM_PROVIDER=gemini (hoặc openai/anthropic/openrouter).")

    print(f"🛠️ Tool đã đăng ký (Role 2): {', '.join(AVAILABLE_TOOLS.keys())}")
    print(f"✅ Đã tải {len(tests)} Test Cases từ config/test_cases.json (Role 1)")


def main():
    args = sys.argv[1:]

    provider = get_llm_provider()
    tests = load_test_cases()
    print_header(provider, tests)

    # --chat : hỏi đáp tự do
    if "--chat" in args:
        run_interactive_chat(provider)
        return

    # --all : chạy toàn bộ test case
    if "--all" in args:
        run_baseline_batch(tests, provider, case_ids=None)
        return

    # --case N : chạy đúng 1 test case theo id
    if "--case" in args:
        idx = args.index("--case")
        if idx + 1 >= len(args):
            print("\n❌ Thiếu số id. Ví dụ đúng: python src/app.py --case 5")
            return
        try:
            case_id = int(args[idx + 1])
        except ValueError:
            print(f"\n❌ '{args[idx + 1]}' không phải số. Ví dụ đúng: python src/app.py --case 5")
            return

        case = find_test_case(tests, case_id)
        if case is None:
            valid_ids = ", ".join(str(c.get("id")) for c in tests)
            print(f"\n❌ Không tìm thấy test case id={case_id}. Các id hợp lệ: {valid_ids}")
            return

        run_baseline_on_case(case, provider)
        return

    # Mặc định: demo Baseline trên vài test case tiêu biểu
    print(f"\n▶️ DEMO MỐC 2 — Chatbot Baseline trên test case {DEMO_CASE_IDS}")
    print("   (dùng --all để chạy hết, --case N để chạy 1 câu, --chat để hỏi tự do)")
    run_baseline_batch(tests, provider, case_ids=DEMO_CASE_IDS)


if __name__ == "__main__":
    main()
