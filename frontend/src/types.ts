export type AgentState =
  | "idle"
  | "planning"
  | "awaiting_confirm"
  | "preparing"
  | "connecting"
  | "writing"
  | "done"
  | "error"
  | "demo";

export type AgentEvent =
  | { type: "assistant_delta"; state?: AgentState; text: string }
  | { type: "manuscript_delta"; state?: AgentState; text: string }
  | { type: "status"; state?: AgentState; label: string }
  | { type: "tool_result"; state?: AgentState; name: string; content: string }
  | { type: "done"; state?: AgentState }
  | { type: "error"; state?: AgentState; message: string };

export type ChatMessage = {
  id: string;
  role: "user" | "agent" | "status";
  text: string;
  time: string;
  ephemeral?: boolean;
  needsConfirmation?: boolean;
  plan?: WritePlan;
};

export type ProviderConfig = {
  base_url: string;
  model: string;
  api_key: string;
};

export type KnowledgeTab = "characters" | "world" | "timeline" | "threads" | "outline" | "files";

export type WorkspaceNode = {
  name: string;
  type: "file" | "directory";
  path: string;
  size?: number;
  children?: WorkspaceNode[];
};

export type WritePlan = {
  intent: string;
  target: string;
  summary: string;
  steps: string[];
  constraints: string[];
  risks: string[];
  estimated_length: string;
  write_position: string;
  requires_confirmation: boolean;
};

export const stateMeta: Record<AgentState, { label: string; hint: string }> = {
  idle: { label: "待命", hint: "等待你的写作指令" },
  planning: { label: "规划中", hint: "正在分析意图与上下文" },
  awaiting_confirm: { label: "待确认", hint: "等待确认写入计划" },
  preparing: { label: "准备中", hint: "正在组装模型上下文" },
  connecting: { label: "连接中", hint: "正在连接模型服务" },
  writing: { label: "写作中", hint: "正在流式写入正文" },
  done: { label: "已完成", hint: "正文已同步" },
  error: { label: "异常", hint: "调用失败，需要处理" },
  demo: { label: "演示", hint: "未配置 API，使用本地文本" }
};
