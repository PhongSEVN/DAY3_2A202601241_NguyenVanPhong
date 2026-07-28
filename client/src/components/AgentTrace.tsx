import { useState } from "react";
import Markdown from "@/components/Markdown";
import type { AgentRun } from "@/lib/api";

/**
 * Hiển thị Trace Log của một lượt chạy Agent: từng vòng Thought → Action → Observation,
 * kèm chỉ số để chấm điểm (số vòng lặp, tool đã gọi, thời gian, guardrail có kích hoạt không).
 */

function StepCard({
  index,
  thought,
  action,
  observation,
  tool,
  isError,
  isFinal,
}: {
  index: number;
  thought: string;
  action: string;
  observation: string;
  tool: string;
  isError: boolean;
  isFinal: boolean;
}) {
  return (
    <div className="rounded-xl border border-outline-variant bg-surface-container-lowest overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-surface-container border-b border-outline-variant">
        <span className="w-5 h-5 rounded-full bg-primary text-on-primary text-[11px] font-bold flex items-center justify-center shrink-0">
          {index}
        </span>
        {isFinal ? (
          <span className="text-xs font-semibold text-primary">Chốt câu trả lời</span>
        ) : tool ? (
          <code className="text-xs font-mono font-semibold text-on-surface">{tool}</code>
        ) : (
          <span className="text-xs font-semibold text-on-surface-variant">Suy luận</span>
        )}
        {isError && (
          <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-error-container text-on-error-container">
            TOOL TRẢ LỖI
          </span>
        )}
      </div>

      <div className="p-3 space-y-2.5 text-sm">
        {thought && (
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-on-surface-variant mb-1">
              💭 Thought
            </div>
            <p className="text-on-surface whitespace-pre-wrap break-words">{thought}</p>
          </div>
        )}

        {action && (
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-on-surface-variant mb-1">
              ⚡ Action
            </div>
            <code className="block font-mono text-xs bg-surface-container-high rounded-lg px-2.5 py-2 text-on-surface break-all">
              {action}
            </code>
          </div>
        )}

        {observation && (
          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-on-surface-variant mb-1">
              👁️ Observation
            </div>
            <pre
              className={`text-xs whitespace-pre-wrap break-words rounded-lg px-2.5 py-2 max-h-56 overflow-y-auto font-sans ${
                isError
                  ? "bg-error-container/40 text-on-error-container"
                  : "bg-surface-container-high text-on-surface"
              }`}
            >
              {observation}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AgentTrace({ run, label }: { run: AgentRun; label?: string }) {
  const [open, setOpen] = useState(true);
  const isReact = run.mode === "react";

  return (
    <div className="min-w-0">
      {label && (
        <div className="flex items-center gap-2 mb-2">
          <span
            className={`text-xs font-bold px-2 py-1 rounded-md ${
              isReact
                ? "bg-primary text-on-primary"
                : "bg-surface-container-highest text-on-surface-variant"
            }`}
          >
            {label}
          </span>
          {!isReact && (
            <span className="text-xs text-on-surface-variant">không có tool</span>
          )}
        </div>
      )}

      {run.error && (
        <div className="mb-3 rounded-lg border border-error/40 bg-error-container/40 px-3 py-2 text-sm text-on-error-container">
          {run.error}
        </div>
      )}

      {run.steps.length > 0 && (
        <div className="mb-3">
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline mb-2"
          >
            <span className="material-symbols-outlined text-[16px]">
              {open ? "expand_less" : "expand_more"}
            </span>
            Trace Log ({run.steps.length} bước)
          </button>

          {open && (
            <div className="space-y-2">
              {run.steps.map((s) => (
                <StepCard
                  key={s.index}
                  index={s.index}
                  thought={s.thought}
                  action={s.action}
                  observation={s.observation}
                  tool={s.tool}
                  isError={s.is_error}
                  isFinal={s.final}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {run.answer && (
        <div
          className={`rounded-xl px-4 py-3 border ${
            run.guardrail_triggered
              ? "border-secondary/50 bg-secondary-fixed/40"
              : "border-outline-variant bg-surface-container-lowest"
          }`}
        >
          <Markdown
            content={run.answer}
            className="text-base leading-relaxed space-y-2 break-words"
          />
        </div>
      )}

      <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-on-surface-variant">
        {isReact && (
          <span className="flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">refresh</span>
            {run.iterations} vòng lặp
          </span>
        )}
        <span className="flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">schedule</span>
          {(run.duration_ms / 1000).toFixed(1)}s
        </span>
        {run.tools_used.length > 0 && (
          <span className="flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">build</span>
            {run.tools_used.join(", ")}
          </span>
        )}
        {isReact && run.tools_used.length === 0 && !run.error && (
          <span className="text-secondary font-medium">không gọi tool nào</span>
        )}
        {run.guardrail_triggered && (
          <span className="flex items-center gap-1 font-semibold text-secondary">
            <span className="material-symbols-outlined text-[14px]">shield</span>
            Guardrail ngắt lặp
          </span>
        )}
      </div>
    </div>
  );
}
