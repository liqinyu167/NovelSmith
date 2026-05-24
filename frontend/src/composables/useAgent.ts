import { type Ref, ref } from "vue";
import type { AgentState, AgentEvent, ChatMessage, ProviderConfig, WritePlan } from "../types";
import { stateMeta } from "../types";

const apiBase = "";

type AgentDeps = {
  provider: Ref<ProviderConfig>;
  manuscript: Ref<string>;
  projectBrief: Ref<string>;
  prompt: Ref<string>;
  messages: Ref<ChatMessage[]>;
  agentState: Ref<AgentState>;
  activeStatus: Ref<string>;
  activeStatusMessageId: Ref<string | null>;
  pendingPrompt: Ref<string>;
  pendingPlan: Ref<WritePlan | null>;
  pendingMessageId: Ref<string | null>;
  chatLogRef: Ref<HTMLElement | null>;
  isGenerating: Ref<boolean>;
  isAwaitingConfirm: Ref<boolean>;
  canSend: Ref<boolean>;
  appendMessage: (role: ChatMessage["role"], text: string, ephemeral?: boolean) => ChatMessage;
  appendToLastAgent: (text: string) => void;
  updateStatusMessage: (text: string, ephemeral: boolean) => void;
  transitionAgent: (nextState: AgentState, label?: string) => void;
  reportAgentState: (nextState: AgentState, label?: string) => void;
  failAgent: (message: string) => void;
  scrollChat: () => void;
  forceScrollChatToBottom: () => void;
  appendManuscript: (text: string) => void;
  activeFilePath?: Ref<string>;
  activeFileContent?: Ref<string>;
  onWorkspaceModified?: () => void;
  newSession?: () => void;
};

export function useAgent(deps: AgentDeps) {
  const currentAbortController = ref<AbortController | null>(null);

  function getSignal() {
    if (currentAbortController.value) {
      currentAbortController.value.abort();
    }
    currentAbortController.value = new AbortController();
    return currentAbortController.value.signal;
  }

  function abortCurrent() {
    if (currentAbortController.value) {
      currentAbortController.value.abort();
    }
  }

  async function sendPrompt() {
    if (!deps.canSend.value) return;

    const userPrompt = deps.prompt.value.trim();
    deps.prompt.value = "";

    if (userPrompt.toLowerCase() === "/new") {
      if (deps.newSession) {
        deps.newSession();
      }
      return;
    }

    deps.pendingPrompt.value = userPrompt;
    deps.appendMessage("user", userPrompt);
    deps.activeStatusMessageId.value = null;
    deps.forceScrollChatToBottom();

    await startChat(userPrompt);
  }

  async function startChat(userPrompt: string) {
    deps.transitionAgent("preparing", "准备对话上下文");
    try {
      const response = await fetch(`${apiBase}/api/agent/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: userPrompt,
          manuscript: deps.manuscript.value,
          project_brief: deps.projectBrief.value,
          provider: deps.provider.value,
          active_file_path: deps.activeFilePath?.value || "",
          active_file_content: deps.activeFileContent?.value || ""
        }),
        signal: getSignal()
      });
      if (!response.ok) throw new Error(`Create chat failed: ${response.status}`);
      const { run_id } = (await response.json()) as { run_id: string };
      streamChat(run_id);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;
      deps.failAgent(error instanceof Error ? error.message : "Unknown error");
    }
  }

  async function createWritePlan(userPrompt: string) {
    deps.transitionAgent("planning", "拟定写作计划");
    deps.updateStatusMessage("我会先整理意图、正文和知识库，生成一份待确认的写入计划。", true);
    try {
      const response = await fetch(`${apiBase}/api/agent/plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: userPrompt,
          manuscript: deps.manuscript.value,
          project_brief: deps.projectBrief.value,
          provider: deps.provider.value,
          active_file_path: deps.activeFilePath?.value || "",
          active_file_content: deps.activeFileContent?.value || ""
        }),
        signal: getSignal()
      });
      if (!response.ok) throw new Error(`Create plan failed: ${response.status}`);
      const plan = (await response.json()) as WritePlan;
      deps.pendingPlan.value = plan;
      deps.transitionAgent("awaiting_confirm", stateMeta.awaiting_confirm.hint);
      deps.updateStatusMessage("写入计划已准备好，等待确认。", false);
      deps.activeStatusMessageId.value = null;
      const message = deps.appendMessage("agent", "我准备这样写入正文：");
      message.plan = plan;
      message.needsConfirmation = true;
      deps.pendingMessageId.value = message.id;
      deps.scrollChat();
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;
      deps.failAgent(error instanceof Error ? error.message : "Unknown error");
    }
  }

  function cancelPendingWrite() {
    abortCurrent();
    const message = deps.pendingMessageId.value
      ? deps.messages.value.find((item) => item.id === deps.pendingMessageId.value)
      : null;
    if (message) {
      message.needsConfirmation = false;
      message.text += "\n\n已取消，本次不会写入正文。";
    }
    deps.pendingPrompt.value = "";
    deps.pendingPlan.value = null;
    deps.pendingMessageId.value = null;
    deps.transitionAgent("idle", stateMeta.idle.hint);
  }

  async function confirmPendingWrite() {
    if (!deps.pendingPrompt.value || deps.isGenerating.value) return;
    const message = deps.pendingMessageId.value
      ? deps.messages.value.find((item) => item.id === deps.pendingMessageId.value)
      : null;
    if (message) {
      message.needsConfirmation = false;
      message.text += "\n\n已确认，开始写入。";
    }
    const confirmedPrompt = deps.pendingPrompt.value;
    const confirmedPlan = deps.pendingPlan.value;
    deps.pendingPrompt.value = "";
    deps.pendingPlan.value = null;
    deps.pendingMessageId.value = null;
    await startGeneration(confirmedPrompt, confirmedPlan);
  }

  const activeEventSource = ref<EventSource | null>(null);

  function stopGeneration() {
    if (activeEventSource.value) {
      activeEventSource.value.close();
      activeEventSource.value = null;
      deps.transitionAgent("idle", "已中止当前生成");
      deps.updateStatusMessage("已中止当前生成。", false);
    }
  }

  async function startGeneration(userPrompt: string, writePlan: WritePlan | null) {
    deps.transitionAgent("preparing", "创建生成任务");
    try {
      const response = await fetch(`${apiBase}/api/agent/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: userPrompt,
          manuscript: deps.manuscript.value,
          project_brief: deps.projectBrief.value,
          write_plan: writePlan,
          provider: deps.provider.value,
          active_file_path: deps.activeFilePath?.value || "",
          active_file_content: deps.activeFileContent?.value || ""
        })
      });

      if (!response.ok) throw new Error(`Create run failed: ${response.status}`);
      const { run_id } = (await response.json()) as { run_id: string };
      streamRun(run_id);
    } catch (error) {
      deps.failAgent(error instanceof Error ? error.message : "Unknown error");
    }
  }

  function streamRun(runId: string) {
    const source = new EventSource(`${apiBase}/api/agent/runs/${runId}/events`);
    activeEventSource.value = source;
    source.onmessage = (event) => {
      const packet = JSON.parse(event.data) as AgentEvent;
      handleAgentEvent(packet, source);
    };
    source.onerror = () => {
      source.close();
      activeEventSource.value = null;
      deps.failAgent("SSE 连接中断，请重试。");
    };
  }

  function streamChat(runId: string) {
    const source = new EventSource(`${apiBase}/api/agent/chats/${runId}/events`);
    activeEventSource.value = source;
    let messageId: string | null = null;
    source.onmessage = (event) => {
      const packet = JSON.parse(event.data) as AgentEvent;
      messageId = handleChatEvent(packet, source, messageId);
    };
    source.onerror = () => {
      source.close();
      activeEventSource.value = null;
      deps.failAgent("SSE 连接中断，请重试。");
    };
  }

  function handleChatEvent(
    event: AgentEvent,
    source: EventSource,
    messageId: string | null
  ): string | null {
    if (event.type === "status") {
      deps.reportAgentState(event.state ?? "preparing", event.label);
    }
    if (event.type === "tool_result") {
      reportToolResult(event);
    }
    if (event.type === "assistant_delta") {
      if (!messageId) {
        messageId = deps.appendMessage("agent", "").id;
      }
      const message = deps.messages.value.find((item) => item.id === messageId);
      if (message) message.text += event.text;
    }
    if (event.type === "manuscript_delta") {
      deps.appendManuscript(event.text);
    }
    if (event.type === "error") {
      source.close();
      activeEventSource.value = null;
      deps.failAgent(event.message);
    }
    if (event.type === "done") {
      source.close();
      activeEventSource.value = null;
      deps.reportAgentState(event.state ?? "done", "对话完成");
      if (deps.onWorkspaceModified) {
        deps.onWorkspaceModified();
      }
    }
    deps.scrollChat();
    return messageId;
  }

  function reportToolResult(event: Extract<AgentEvent, { type: "tool_result" }>) {
    if (event.name === "read_project_context") {
      deps.updateStatusMessage("我读取了当前项目上下文。", true);
      return;
    }
    if (event.name === "append_to_manuscript") {
      let summary = "正在调用正文编辑器写入正文。";
      try {
        const payload = JSON.parse(event.content) as { chars?: number; summary?: string };
        summary = payload.summary || `已调用正文编辑器，写入约 ${payload.chars ?? 0} 字。`;
      } catch {
        summary = "已调用正文编辑器写入正文。";
      }
      deps.updateStatusMessage(summary, false);
    }
    if (event.name === "update_workspace_file") {
      try {
        const payload = JSON.parse(event.content) as { ok?: boolean; path?: string };
        if (payload.ok) {
          deps.updateStatusMessage(`Agent 协同修改了文件: ${payload.path}`, false);
          if (deps.onWorkspaceModified) {
            deps.onWorkspaceModified();
          }
        }
      } catch {
        deps.updateStatusMessage("Agent 协同修改了工作区文件。", false);
        if (deps.onWorkspaceModified) {
          deps.onWorkspaceModified();
        }
      }
    }
  }

  function handleAgentEvent(event: AgentEvent, source: EventSource) {
    if (event.type === "status") {
      deps.reportAgentState(event.state ?? "preparing", event.label);
    }
    if (event.type === "assistant_delta") {
      deps.appendToLastAgent(event.text);
    }
    if (event.type === "manuscript_delta") {
      deps.appendManuscript(event.text);
    }
    if (event.type === "error") {
      source.close();
      activeEventSource.value = null;
      deps.failAgent(event.message);
    }
    if (event.type === "done") {
      source.close();
      activeEventSource.value = null;
      deps.reportAgentState(event.state ?? "done", "正文已同步到编辑区");
      if (deps.onWorkspaceModified) {
        deps.onWorkspaceModified();
      }
    }
    deps.scrollChat();
  }

  return {
    sendPrompt,
    startChat,
    createWritePlan,
    cancelPendingWrite,
    confirmPendingWrite,
    startGeneration,
    stopGeneration
  };
}
