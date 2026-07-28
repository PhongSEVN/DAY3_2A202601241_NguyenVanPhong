/**
 * Lớp gọi API tới backend Agent (src/server.py).
 *
 * Đi qua proxy của Vite (xem vite.config.ts) nên base URL để rỗng là đủ.
 * API key nằm ở server, không có key nào lọt xuống trình duyệt.
 */

const BASE = import.meta.env.VITE_API_URL ?? "";

export interface AgentStep {
  index: number;
  thought: string;
  action: string;
  observation: string;
  tool: string;
  is_error: boolean;
  final: boolean;
}

export interface AgentRun {
  mode: "react" | "baseline";
  answer: string;
  steps: AgentStep[];
  iterations: number;
  tools_used: string[];
  guardrail_triggered: boolean;
  duration_ms: number;
  error: string;
}

export interface ChatResponse {
  question: string;
  max_iterations: number;
  react?: AgentRun;
  baseline?: AgentRun;
  error?: string;
}

export interface ToolSpec {
  name: string;
  description: string;
  input_schema: Record<string, string>;
  returns: string;
  side_effect: string;
  error_semantics: string;
}

export interface TestCase {
  id: number;
  category: string;
  question: string;
  expected_behavior: string;
}

export interface Health {
  status: string;
  provider: string;
  model: string;
  has_api_key: boolean;
  tools: string[];
  max_iterations: number;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} trả về ${res.status}`);
  return res.json() as Promise<T>;
}

export const getHealth = () => get<Health>("/api/health");
export const getTools = () => get<ToolSpec[]>("/api/tools");
export const getTestCases = () => get<TestCase[]>("/api/test-cases");

export async function sendChat(
  question: string,
  mode: "react" | "baseline" | "both",
  maxIterations: number,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode, max_iterations: maxIterations }),
  });

  const data = (await res.json().catch(() => ({}))) as ChatResponse;
  if (!res.ok) {
    throw new Error(
      data.error || `Backend trả về ${res.status}. Đã chạy 'python src/server.py' chưa?`,
    );
  }
  return data;
}
