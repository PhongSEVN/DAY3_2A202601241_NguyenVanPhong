import { useEffect, useRef, useState } from "react";

import AgentTrace from "@/components/AgentTrace";
import {
  getHealth,
  getTestCases,
  getTools,
  sendChat,
  type ChatResponse,
  type Health,
  type TestCase,
  type ToolSpec,
} from "@/lib/api";

type Mode = "react" | "baseline" | "both";

interface Turn {
  question: string;
  response?: ChatResponse;
  error?: string;
}

const MODE_LABEL: Record<Mode, string> = {
  react: "ReAct Agent",
  baseline: "Chatbot gốc",
  both: "So sánh cả hai",
};

export default function ChatPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<Mode>("react");
  const [maxIterations, setMaxIterations] = useState(5);

  const [health, setHealth] = useState<Health | null>(null);
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [cases, setCases] = useState<TestCase[]>([]);
  const [backendDown, setBackendDown] = useState(false);
  const [openTool, setOpenTool] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getHealth()
      .then((h) => {
        setHealth(h);
        setMaxIterations(Math.max(h.max_iterations, 5));
      })
      .catch(() => setBackendDown(true));
    getTools().then(setTools).catch(() => undefined);
    getTestCases().then(setCases).catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || loading) return;

    setInput("");
    setLoading(true);
    const at = turns.length;
    setTurns((prev) => [...prev, { question: text }]);

    try {
      const response = await sendChat(text, mode, maxIterations);
      setTurns((prev) => prev.map((t, i) => (i === at ? { ...t, response } : t)));
    } catch (e) {
      const message = e instanceof Error ? e.message : "Lỗi không xác định";
      setTurns((prev) => prev.map((t, i) => (i === at ? { ...t, error: message } : t)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen bg-background text-on-surface w-full overflow-hidden">
      {/* ------------------------------- SIDEBAR ------------------------------- */}
      <aside className="w-80 border-r border-outline-variant bg-surface flex flex-col shrink-0 overflow-y-auto chat-scroll">
        <div className="px-5 py-4 border-b border-outline-variant">
          <h1 className="font-bold text-base text-primary leading-tight">
            Trợ Lý Sàng Lọc Hồ Sơ
            <br />& Hẹn Phỏng Vấn
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">Đề tài 9 — ReAct Agent</p>
        </div>

        {/* Chế độ chạy */}
        <div className="px-5 py-4 border-b border-outline-variant">
          <h2 className="text-xs font-bold uppercase tracking-wide text-on-surface-variant mb-2.5">
            Chế độ chạy
          </h2>
          <div className="space-y-1.5">
            {(Object.keys(MODE_LABEL) as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors border ${
                  mode === m
                    ? "bg-primary text-on-primary border-primary"
                    : "bg-surface-container-lowest border-outline-variant hover:bg-surface-container"
                }`}
              >
                {MODE_LABEL[m]}
              </button>
            ))}
          </div>
          <p className="text-xs text-on-surface-variant mt-2 leading-relaxed">
            "So sánh cả hai" chạy song song Chatbot gốc và ReAct Agent trên cùng câu hỏi —
            thấy ngay Agent tra dữ liệu thật còn Chatbot thì không.
          </p>
        </div>

        {/* Guardrail */}
        <div className="px-5 py-4 border-b border-outline-variant">
          <h2 className="text-xs font-bold uppercase tracking-wide text-on-surface-variant mb-2.5">
            🛡️ Guardrail
          </h2>
          <label className="flex justify-between text-sm font-medium mb-2">
            <span>Số vòng lặp tối đa</span>
            <span className="text-primary font-bold">{maxIterations}</span>
          </label>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={maxIterations}
            onChange={(e) => setMaxIterations(parseInt(e.target.value, 10))}
            className="w-full accent-primary"
          />
          <p className="text-xs text-on-surface-variant mt-1.5 leading-relaxed">
            Chặn Agent lặp vô tận. Hạ xuống 1 để thấy Guardrail kích hoạt giữa chừng.
          </p>
        </div>

        {/* Tool registry */}
        <div className="px-5 py-4 border-b border-outline-variant">
          <h2 className="text-xs font-bold uppercase tracking-wide text-on-surface-variant mb-2.5">
            🛠️ Tool đã đăng ký ({tools.length})
          </h2>
          <div className="space-y-1.5">
            {tools.map((t) => (
              <div
                key={t.name}
                className="rounded-lg border border-outline-variant bg-surface-container-lowest overflow-hidden"
              >
                <button
                  onClick={() => setOpenTool(openTool === t.name ? null : t.name)}
                  className="w-full flex items-center gap-2 px-2.5 py-2 text-left hover:bg-surface-container"
                >
                  <code className="text-xs font-mono font-semibold flex-1 truncate">
                    {t.name}
                  </code>
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                      t.side_effect.toUpperCase().startsWith("WRITE")
                        ? "bg-secondary-fixed text-on-secondary-fixed"
                        : "bg-surface-container-highest text-on-surface-variant"
                    }`}
                  >
                    {t.side_effect.toUpperCase().startsWith("WRITE") ? "WRITE" : "READ"}
                  </span>
                </button>
                {openTool === t.name && (
                  <div className="px-2.5 pb-2.5 text-xs text-on-surface-variant space-y-1.5">
                    <p className="leading-relaxed">{t.description}</p>
                    <div>
                      <span className="font-semibold text-on-surface">Tham số:</span>
                      <ul className="list-disc pl-4 mt-0.5 space-y-0.5">
                        {Object.entries(t.input_schema).map(([k, v]) => (
                          <li key={k}>
                            <code className="font-mono">{k}</code>: {v}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {tools.length === 0 && (
              <p className="text-xs text-on-surface-variant">Chưa nạp được danh sách tool.</p>
            )}
          </div>
        </div>

        {/* Provider */}
        <div className="px-5 py-4 mt-auto text-xs text-on-surface-variant space-y-1">
          {health ? (
            <>
              <div className="flex justify-between">
                <span>Provider</span>
                <span className="font-semibold text-on-surface">{health.provider}</span>
              </div>
              <div className="flex justify-between gap-2">
                <span>Model</span>
                <span className="font-semibold text-on-surface truncate">{health.model}</span>
              </div>
              {!health.has_api_key && (
                <p className="text-error font-medium pt-1">
                  Chưa có API key trong .env — đặt LLM_PROVIDER=mock để xem thử giao diện.
                </p>
              )}
            </>
          ) : (
            <span className="text-error font-medium">Backend chưa chạy</span>
          )}
        </div>
      </aside>

      {/* --------------------------------- MAIN -------------------------------- */}
      <div className="flex flex-col h-full bg-surface-bright relative flex-1 min-w-0">
        <header className="flex items-center gap-3 px-6 h-16 w-full bg-surface border-b border-outline-variant shrink-0">
          <span className="material-symbols-outlined text-primary">work</span>
          <span className="text-lg font-bold text-primary">HR Agent Demo</span>
          <span className="ml-auto text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary">
            {MODE_LABEL[mode]}
          </span>
        </header>

        <div className="flex-1 overflow-y-auto chat-scroll p-4 lg:p-8 flex flex-col gap-8 max-w-5xl mx-auto w-full">
          {backendDown && (
            <div className="rounded-xl border border-error/40 bg-error-container/40 px-4 py-3 text-sm text-on-error-container">
              <p className="font-semibold mb-1">Không kết nối được backend.</p>
              <p>
                Mở một terminal khác ở thư mục gốc dự án và chạy:{" "}
                <code className="font-mono bg-surface-container px-1.5 py-0.5 rounded">
                  python src/server.py
                </code>
              </p>
            </div>
          )}

          {turns.length === 0 && !backendDown && (
            <div className="text-center text-on-surface-variant py-10">
              <span className="material-symbols-outlined text-5xl text-primary/40">
                smart_toy
              </span>
              <p className="mt-3 text-sm">
                Hỏi về tuyển dụng, sàng lọc CV hoặc đặt lịch phỏng vấn — hoặc bấm thẳng một
                test case bên dưới.
              </p>
            </div>
          )}

          {turns.map((turn, i) => (
            <div key={i} className="space-y-4">
              {/* Câu hỏi */}
              <div className="flex gap-3 max-w-[85%] self-end ml-auto flex-row-reverse">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary text-xs font-bold shrink-0 mt-1">
                  U
                </div>
                <div className="bg-primary/10 border border-primary/20 rounded-2xl rounded-tr-sm px-4 py-3 min-w-0">
                  <p className="text-sm whitespace-pre-wrap break-words">{turn.question}</p>
                </div>
              </div>

              {/* Trả lời */}
              {(turn.response || turn.error) && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary shrink-0 mt-1">
                    <span className="material-symbols-outlined text-sm">smart_toy</span>
                  </div>

                  <div className="flex-1 min-w-0">
                    {turn.error && (
                      <div className="rounded-xl border border-error/40 bg-error-container/40 px-4 py-3 text-sm text-on-error-container">
                        {turn.error}
                      </div>
                    )}

                    {turn.response && (
                      <div
                        className={
                          turn.response.baseline && turn.response.react
                            ? "grid lg:grid-cols-2 gap-5"
                            : ""
                        }
                      >
                        {turn.response.baseline && (
                          <AgentTrace
                            run={turn.response.baseline}
                            label={
                              turn.response.react ? "Chatbot gốc (baseline)" : undefined
                            }
                          />
                        )}
                        {turn.response.react && (
                          <AgentTrace
                            run={turn.response.react}
                            label={turn.response.baseline ? "ReAct Agent" : undefined}
                          />
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary shrink-0 mt-1">
                <span className="material-symbols-outlined text-sm">smart_toy</span>
              </div>
              <div className="bg-surface border border-outline-variant rounded-2xl rounded-tl-sm px-5 py-4 flex items-center gap-1.5">
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" />
                <span className="ml-2 text-xs text-on-surface-variant">
                  Agent đang suy luận...
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Test case + ô nhập */}
        <div className="p-4 bg-surface-bright border-t border-outline-variant shrink-0">
          <div className="max-w-5xl mx-auto">
            {cases.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pb-2.5 chat-scroll">
                {cases.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => ask(c.question)}
                    disabled={loading}
                    title={c.expected_behavior}
                    className="shrink-0 text-xs px-3 py-1.5 rounded-full border border-outline-variant bg-surface hover:border-primary hover:text-primary transition-colors disabled:opacity-50"
                  >
                    <span className="font-semibold">#{c.id}</span> {c.category}
                  </button>
                ))}
              </div>
            )}

            <div className="relative">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    ask(input);
                  }
                }}
                disabled={loading}
                className="w-full bg-surface border border-outline-variant rounded-full py-3 pl-5 pr-12 focus:ring-2 focus:ring-primary/50 focus:border-primary focus:outline-none shadow-sm text-base disabled:opacity-50"
                placeholder="VD: Tìm 5 vị trí Lập trình viên Python tại Hà Nội..."
              />
              <button
                onClick={() => ask(input)}
                disabled={loading || !input.trim()}
                className="absolute inset-y-1 right-1 w-10 h-10 bg-primary text-on-primary rounded-full flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-sm">send</span>
              </button>
            </div>

            <p className="text-center mt-2 text-xs font-semibold text-on-surface-variant">
              Dữ liệu lấy từ data/VietJobs.csv. Agent có thể mắc sai lầm — hãy kiểm chứng.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
