"""
🌐 DEMO API SERVER — cầu nối giữa giao diện web (client/) và Agent

Đề tài 9: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn

File này KHÔNG thay thế `src/app.py` (bản CLI của Role 4). Nó chỉ bọc lại đúng
những thành phần cả nhóm đã làm để giao diện web gọi được:
    - Tools của Role 2      → tools.execute_action / TOOL_SPECS
    - Prompts của Role 3    → prompts.CHATBOT_BASELINE_PROMPT / REACT_SYSTEM_PROMPT
    - Test cases của Role 1 → config/test_cases.json
    - Multi-provider        → providers.get_llm_provider()

Khác biệt duy nhất so với vòng lặp CLI: thay vì `print()` ra Terminal, mỗi bước
Thought / Action / Observation được trả về dưới dạng JSON để giao diện vẽ ra
Trace Log trực quan — đúng thứ Role 5 cần để chấm điểm.

⚠️ API key nằm ở server (đọc từ .env), TUYỆT ĐỐI không đẩy xuống trình duyệt.

Cách chạy:
    pip install -r requirements.txt
    python src/server.py            # mặc định http://localhost:8000
"""

import json
import os
import re
import sys
import time

# Cho phép import các module cùng thư mục src/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request

from tools import (
    AVAILABLE_TOOLS,
    TOOL_SPECS,
    execute_action,
    get_tools_description,
)
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_SYSTEM_PROMPT,
    MAX_ITERATIONS,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # chưa cài python-dotenv thì vẫn chạy được với biến môi trường sẵn có
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.getenv("PORT", "8000"))

app = Flask(__name__)


@app.after_request
def _allow_cors(response):
    """Mở CORS cho Vite dev server (localhost:5173) khi không đi qua proxy."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# =============================================================================
# 🧩 GHÉP SYSTEM PROMPT THẬT CHO REACT AGENT
# =============================================================================

# Lưới an toàn: nếu REACT_SYSTEM_PROMPT phát cho Agent một danh sách tool KHÔNG khớp
# với AVAILABLE_TOOLS (như hồi prompt còn boilerplate get_weather / search_flights) thì
# Agent sẽ gọi toàn tool không tồn tại. Thiếu tool nào thì chèn mô tả sinh tự động từ
# TOOL_SPECS của Role 2.
# 👉 Từ khi Role 3 liệt kê đủ 4 tool thật trong prompts.py, nhánh vá KHÔNG chạy nữa —
#    prompt của Role 3 được dùng nguyên vẹn, tránh phát trùng danh sách tool 2 lần.
_TOOL_LIST_BLOCK = re.compile(
    r"Danh sách các công cụ bạn có thể sử dụng:.*?(?=\n\s*QUY TẮC BẮT BUỘC)",
    re.DOTALL,
)


def build_react_prompt() -> str:
    """Trả về System Prompt ReAct (đảm bảo đủ tool thật) + bối cảnh ngày hiện tại."""
    missing = [name for name in AVAILABLE_TOOLS if name not in REACT_SYSTEM_PROMPT]

    if not missing:
        prompt = REACT_SYSTEM_PROMPT.rstrip()
    else:
        real_block = "Danh sách các công cụ bạn có thể sử dụng:\n" + get_tools_description()
        if _TOOL_LIST_BLOCK.search(REACT_SYSTEM_PROMPT):
            prompt = _TOOL_LIST_BLOCK.sub(lambda _m: real_block, REACT_SYSTEM_PROMPT)
        else:
            prompt = REACT_SYSTEM_PROMPT.rstrip() + "\n\n" + real_block

    today = time.strftime("%d/%m/%Y")
    return (
        f"{prompt}\n\nBỐI CẢNH: Hôm nay là ngày {today}. "
        "Chỉ được dùng đúng các công cụ trong danh sách trên, không tự bịa thêm công cụ. "
        "Nếu Observation bắt đầu bằng 'LỖI:', hãy đọc kỹ thông báo lỗi và sửa lại lời gọi "
        "hoặc trả lời thành thật cho người dùng, TUYỆT ĐỐI không bịa dữ liệu.\n"
    )


# =============================================================================
# 🔍 BÓC TÁCH OUTPUT CỦA LLM
# =============================================================================

def _grab(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _parse_llm_turn(response: str) -> dict:
    """Tách một lượt trả lời của LLM thành thought / action / final_answer."""
    return {
        "thought": _grab(r"Thought\s*:\s*(.+?)(?:\n|$)", response),
        "action": _grab(r"Action\s*:\s*(.+?)(?:\n|$)", response),
        "final_answer": _grab(r"Final Answer\s*:\s*([\s\S]+)$", response),
    }


# =============================================================================
# 🤖 HAI CHẾ ĐỘ CHẠY: BASELINE vs REACT AGENT
# =============================================================================

def run_baseline(question: str, provider) -> dict:
    """Chatbot gốc: LLM thuần, không có tool — dùng làm mốc so sánh."""
    started = time.time()
    try:
        answer = provider.generate(question, system_prompt=CHATBOT_BASELINE_PROMPT)
        error = ""
    except Exception as exc:
        answer, error = "", f"Gọi LLM thất bại: {exc}"

    return {
        "mode": "baseline",
        "answer": answer,
        "steps": [],
        "iterations": 0,
        "tools_used": [],
        "guardrail_triggered": False,
        "duration_ms": int((time.time() - started) * 1000),
        "error": error,
    }


def run_react(question: str, provider, max_iterations: int) -> dict:
    """
    Vòng lặp ReAct có Guardrails, trả về trace đầy đủ cho giao diện.

    Bám đúng logic `run_react_agent()` trong app.py của Role 4, chỉ thay phần in ra
    Terminal bằng việc gom từng bước vào danh sách `steps` để trả về JSON.
    """
    started = time.time()
    system_prompt = build_react_prompt()
    history = f"Câu hỏi của người dùng: {question}"

    steps, tools_used = [], []
    answer, error = "", ""
    guardrail_triggered = False
    step = 0

    while step < max_iterations:
        step += 1

        try:
            response = provider.generate(history, system_prompt=system_prompt)
        except Exception as exc:
            error = f"Gọi LLM thất bại ở bước {step}: {exc}"
            break

        turn = _parse_llm_turn(response)

        # LLM đã đủ thông tin để chốt câu trả lời
        if turn["final_answer"]:
            answer = turn["final_answer"]
            steps.append({
                "index": step,
                "thought": turn["thought"],
                "action": "",
                "observation": "",
                "tool": "",
                "is_error": False,
                "final": True,
            })
            break

        # LLM muốn gọi tool
        if turn["action"]:
            observation = execute_action(turn["action"])
            tool_name = turn["action"].split("[")[0].strip()
            if tool_name in AVAILABLE_TOOLS and tool_name not in tools_used:
                tools_used.append(tool_name)

            steps.append({
                "index": step,
                "thought": turn["thought"],
                "action": turn["action"],
                "observation": observation,
                "tool": tool_name,
                "is_error": observation.startswith("LỖI:"),
                "final": False,
            })
            history += f"\n{response}\nObservation: {observation}"
        else:
            # LLM lan man, không ra Action cũng không ra Final Answer
            steps.append({
                "index": step,
                "thought": turn["thought"] or response.strip()[:400],
                "action": "",
                "observation": "",
                "tool": "",
                "is_error": False,
                "final": False,
            })
            history += f"\n{response}"

    # 🛡️ Guardrail: chạm trần vòng lặp mà vẫn chưa có Final Answer
    if not answer and not error:
        guardrail_triggered = True
        answer = (
            f"⚠️ Agent đã chạm giới hạn {max_iterations} vòng lặp mà chưa chốt được câu "
            "trả lời. Hệ thống ngắt an toàn để tránh lặp vô tận. Bạn thử diễn đạt lại "
            "câu hỏi cụ thể hơn nhé."
        )

    return {
        "mode": "react",
        "answer": answer,
        "steps": steps,
        "iterations": step,
        "tools_used": tools_used,
        "guardrail_triggered": guardrail_triggered,
        "duration_ms": int((time.time() - started) * 1000),
        "error": error,
    }


# =============================================================================
# 🚏 API ENDPOINTS
# =============================================================================

@app.get("/api/health")
def health():
    """Giao diện gọi lúc khởi động để biết đang chạy provider nào, tool nào."""
    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower()
    key_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    key_name = key_map.get(provider_name, "")
    has_key = bool(os.getenv(key_name)) if key_name else True

    return jsonify({
        "status": "ok",
        "provider": provider_name,
        "model": os.getenv("LLM_MODEL") or "(mặc định của provider)",
        "has_api_key": has_key,
        "tools": list(AVAILABLE_TOOLS.keys()),
        "max_iterations": MAX_ITERATIONS,
    })


@app.get("/api/tools")
def list_tools():
    """Bảng đăng ký tool (Tool Contract của Role 2) để hiển thị ở sidebar."""
    return jsonify([
        {
            "name": name,
            "description": spec.get("description", ""),
            "input_schema": spec.get("input_schema", {}),
            "returns": spec.get("returns", ""),
            "side_effect": spec.get("side_effect", ""),
            "error_semantics": spec.get("error_semantics", ""),
        }
        for name, spec in TOOL_SPECS.items()
    ])


@app.get("/api/test-cases")
def test_cases():
    """Bộ test case của Role 1 — bấm 1 phát là chạy thẳng, khỏi gõ tay khi demo."""
    path = os.path.join(BASE_DIR, "config", "test_cases.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as exc:
        return jsonify({"error": f"Không đọc được test_cases.json: {exc}"}), 500


@app.post("/api/chat")
def chat():
    """
    Body: {question: str, mode: "react" | "baseline" | "both", max_iterations?: int}

    Trả về kết quả một chế độ, hoặc cả hai để so sánh cạnh nhau khi mode="both".
    """
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    mode = str(payload.get("mode", "react")).lower()
    max_iterations = payload.get("max_iterations") or MAX_ITERATIONS

    if not question:
        return jsonify({"error": "Vui lòng nhập câu hỏi."}), 400

    try:
        max_iterations = max(1, min(10, int(max_iterations)))
    except (TypeError, ValueError):
        max_iterations = MAX_ITERATIONS

    # Khởi tạo provider theo từng request để đổi .env là ăn ngay, khỏi restart server
    try:
        from providers import get_llm_provider

        provider = get_llm_provider()
    except Exception as exc:
        return jsonify({
            "error": (
                f"Không khởi tạo được LLM Provider: {exc}. "
                "Kiểm tra LLM_PROVIDER và API key trong file .env, "
                "hoặc đặt LLM_PROVIDER=mock để xem thử giao diện."
            )
        }), 500

    result = {"question": question, "max_iterations": max_iterations}

    if mode in ("baseline", "both"):
        result["baseline"] = run_baseline(question, provider)
    if mode in ("react", "both"):
        result["react"] = run_react(question, provider, max_iterations)

    return jsonify(result)


if __name__ == "__main__":
    print("=" * 68)
    print("🌐 DEMO API SERVER — Trợ Lý Sàng Lọc Hồ Sơ & Hẹn Phỏng Vấn")
    print("=" * 68)
    print(f"🔌 Provider     : {os.getenv('LLM_PROVIDER', 'gemini')}")
    print(f"🛠️  Tool đã nạp  : {', '.join(AVAILABLE_TOOLS.keys())}")
    print(f"🛡️  MAX_ITERATIONS: {MAX_ITERATIONS}")
    print(f"👉 API chạy tại : http://localhost:{PORT}")
    print(f"👉 Giao diện    : cd client && npm install && npm run dev")
    print("=" * 68)
    app.run(host="0.0.0.0", port=PORT, debug=False)
