"""
🔌 MULTI-PROVIDER LLM ADAPTER (OpenAI, Gemini, Anthropic, OpenRouter & Offline Mock)
Hỗ trợ chuyển đổi linh hoạt giữa các nhà cung cấp AI chỉ bằng cách đổi biến môi trường LLM_PROVIDER.
"""

import os
import re
import sys
import json
import requests
from dotenv import load_dotenv

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho tất cả các LLM Provider"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env!"
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (GPT-4o, GPT-3.5-turbo, etc.)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env!"
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Provider (Claude 3.5 Sonnet, Claude 3 Haiku)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "claude-3-haiku-20240307"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_anthropic_api_key_here":
            return "[Anthropic Error]: Chưa cấu hình ANTHROPIC_API_KEY trong file .env!"
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            kwargs = {
                "model": self.model_name,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            return f"[Anthropic Exception]: {str(e)}"


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter Provider (Hỗ trợ gọi mọi model qua OpenRouter API)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "google/gemini-2.5-flash"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return "[OpenRouter Error]: Chưa cấu hình OPENROUTER_API_KEY trong file .env!"
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"[OpenRouter API Error {res.status_code}]: {res.text}"
        except Exception as e:
            return f"[OpenRouter Exception]: {str(e)}"


class MockProvider(BaseLLMProvider):
    """
    Offline Mock Provider (Cho bài test không cần kết nối API).

    Mô phỏng LLM theo 2 chế độ, tự nhận biết qua system_prompt:
      - Chế độ Baseline : trả lời chung chung như một Chatbot không có Tool.
      - Chế độ ReAct    : sinh đúng cú pháp 'Thought/Action/Final Answer' theo đề tài
                          Tuyển dụng để nhóm demo được vòng lặp và Guardrail khi offline.
    """

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        is_react = "Action:" in (system_prompt or "") or "ReAct" in (system_prompt or "")
        if not is_react:
            return (
                "🤖 [Mock Baseline]: Mình chưa có công cụ tra cứu dữ liệu tuyển dụng thật, "
                "nên chỉ có thể trả lời chung chung dựa trên kiến thức có sẵn. "
                "Bạn nên kiểm tra lại thông tin trên các trang tuyển dụng chính thống."
            )
        return self._mock_react(prompt)

    # ------------------------------------------------------------------
    # Mô phỏng ReAct: quyết định bước tiếp theo dựa trên scratchpad hiện tại
    # ------------------------------------------------------------------
    def _mock_react(self, scratchpad: str) -> str:
        question = ""
        m = re.search(r"Question:\s*(.+)", scratchpad)
        if m:
            question = m.group(1).strip()
        q = question.lower()

        observations = re.findall(r"Observation:\s*(.+)", scratchpad)
        last_obs = observations[-1] if observations else ""
        turn = len(observations)  # 0 = lượt đầu tiên, chưa có Observation nào

        # 1. Câu hỏi mơ hồ / phân biệt đối xử / lộ PII ➔ chốt luôn, không gọi tool
        if any(k in q for k in ("nam dưới", "ứng viên nam", "dưới 25 tuổi")):
            return ("Thought: Yêu cầu này mang tính phân biệt đối xử, tôi không được thực hiện.\n"
                    "Final Answer: Xin lỗi, tôi không thể sàng lọc theo giới tính hay độ tuổi. "
                    "Việc đánh giá chỉ dựa trên kỹ năng, kinh nghiệm và yêu cầu công việc.")
        if any(k in q for k in ("số điện thoại", "địa chỉ của ứng viên")):
            return ("Thought: Đây là thông tin cá nhân (PII), tôi không được tiết lộ.\n"
                    "Final Answer: Tôi không thể cung cấp số điện thoại hay địa chỉ của ứng viên "
                    "vì đây là thông tin cá nhân được bảo vệ.")
        if q.strip() in ("tìm việc cho tôi.", "tìm việc cho tôi"):
            return ("Thought: Câu hỏi thiếu thông tin, tôi không nên đoán bừa.\n"
                    "Final Answer: Bạn vui lòng cho mình biết thêm: ngành nghề/vị trí mong muốn "
                    "và địa điểm làm việc để mình tra cứu chính xác nhé.")

        # 2. Câu bẫy Phantom Tool: cố tình gọi tool không tồn tại để lộ Guardrail
        if "email" in q and turn == 0:
            return ("Thought: Người dùng muốn gửi email xác nhận, tôi thử dùng công cụ gửi email.\n"
                    'Action: send_email["ung.vien@example.com", "Xác nhận lịch phỏng vấn"]')

        # 3. Câu bẫy Infinite Loop: lặp đi lặp lại đúng một Action
        if "liên tục" in q:
            return ("Thought: Người dùng yêu cầu tìm liên tục cho tới khi có kết quả.\n"
                    'Action: search_jobs["AI Engineer", "Hà Nội"]')

        # 4. Đặt lịch phỏng vấn (chỉ khi người dùng KHÔNG yêu cầu tra cứu vị trí trước)
        if "đặt lịch" in q and "tìm" not in q and turn == 0:
            slot = "32/13/2026 25:00" if "32/13/2026" in q else "01/01/2020 09:00"
            return (f"Thought: Người dùng muốn đặt lịch phỏng vấn, tôi thử gọi công cụ đặt lịch.\n"
                    f'Action: schedule_interview["Ứng viên", "{slot}"]')

        # 5. Sau khi đã có Observation ➔ suy luận tiếp hoặc kết luận (không bịa dữ liệu)
        if turn >= 1:
            if last_obs.startswith("LỖI"):
                return ("Thought: Công cụ báo lỗi, tôi không được bịa dữ liệu mà phải báo lại người dùng.\n"
                        f"Final Answer: Rất tiếc, tôi chưa thực hiện được yêu cầu. Lý do: {last_obs} "
                        "Bạn vui lòng cung cấp lại thông tin hợp lệ giúp mình nhé.")

            # Multi-step: đã có Job Description ➔ chấm CV trước khi kết luận
            if "cv" in q and "Action: screen_resume" not in scratchpad:
                jd = last_obs.replace('"', "'")[:200]
                return ("Thought: Đã có yêu cầu công việc thật, giờ tôi chấm độ phù hợp của CV ứng viên.\n"
                        f'Action: screen_resume["", "{jd}"]')

            return ("Thought: Tôi đã có dữ liệu thật từ công cụ, đủ để trả lời.\n"
                    f"Final Answer: Dựa trên dữ liệu tra cứu được: {last_obs[:400]}")

        # 6. Mặc định: tra cứu vị trí tuyển dụng thật
        keyword, location = self._extract_job_query(question)
        return (f"Thought: Tôi cần tra cứu dữ liệu tuyển dụng thật trước khi kết luận.\n"
                f'Action: search_jobs["{keyword}", "{location}"]')

    @staticmethod
    def _extract_job_query(question: str):
        """Bóc (từ khoá ngành nghề, địa điểm) từ câu hỏi tiếng Việt kiểu 'vị trí X tại Y'."""
        keyword, location = "AI Engineer", ""
        m = re.search(r"(?:vị trí|việc|tuyển)\s+(.+?)(?:\s+tại\s+(.+?))?\s*(?:[.,?]|$)", question, re.I)
        if m:
            keyword = m.group(1).strip() or keyword
            location = (m.group(2) or "").strip()
        # Bỏ đuôi câu hỏi tiếng Việt để từ khoá tra cứu sạch (VD: "AI Engineer không" ➔ "AI Engineer")
        keyword = re.sub(r"\s+(không|nào|ạ|nhé|cho tôi|giúp tôi)$", "", keyword, flags=re.I).strip()
        return keyword, location


def get_llm_provider(provider_name: str = None) -> BaseLLMProvider:
    """Factory function tự chọn Provider từ biến môi trường LLM_PROVIDER"""
    name = (provider_name or os.getenv("LLM_PROVIDER") or "mock").lower().strip()
    
    if name == "gemini":
        return GeminiProvider()
    elif name == "openai":
        return OpenAIProvider()
    elif name == "anthropic":
        return AnthropicProvider()
    elif name == "openrouter":
        return OpenRouterProvider()
    else:
        return MockProvider()


if __name__ == "__main__":
    print("=== TEST MULTI-PROVIDER LLM ADAPTER ===")
    provider = get_llm_provider()
    print(f"✅ Provider đang dùng: {provider.__class__.__name__}")
    print(f"🤖 User Query: Hello")
    print(f"💬 Response  : {provider.generate('Hello')}")
