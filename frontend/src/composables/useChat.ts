import { ref, computed, nextTick, watch } from "vue";
import { debounce } from "../lib/debounce";
import type { AgentState, ChatMessage, WritePlan } from "../types";
import { stateMeta } from "../types";

export function useChat() {
  const messages = ref<ChatMessage[]>([]);
  const prompt = ref("");
  const agentState = ref<AgentState>("idle");
  const activeStatus = ref(stateMeta.idle.hint);
  const activeStatusMessageId = ref<string | null>(null);
  const pendingPrompt = ref("");
  const pendingPlan = ref<WritePlan | null>(null);
  const pendingMessageId = ref<string | null>(null);
  const chatLogRef = ref<HTMLElement | null>(null);

  const isGenerating = computed(() =>
    ["preparing", "connecting", "writing", "demo"].includes(agentState.value)
  );
  const isAwaitingConfirm = computed(() => agentState.value === "awaiting_confirm");
  const canSend = computed(
    () =>
      prompt.value.trim().length > 0 &&
      !isGenerating.value &&
      !isAwaitingConfirm.value
  );

  function appendMessage(
    role: ChatMessage["role"],
    text: string,
    ephemeral = false
  ): ChatMessage {
    const message: ChatMessage = {
      id: crypto.randomUUID(),
      role,
      text,
      time: nowTime(),
      ephemeral
    };
    messages.value.push(message);
    return message;
  }

  function appendToLastAgent(text: string) {
    const last = [...messages.value].reverse().find((message) => message.role === "agent");
    if (last) last.text += text;
  }

  function updateStatusMessage(text: string, ephemeral: boolean) {
    const id = activeStatusMessageId.value;
    const existing = id ? messages.value.find((message) => message.id === id) : null;
    if (existing) {
      existing.text = text;
      existing.time = nowTime();
      existing.ephemeral = ephemeral;
      return;
    }
    const message = appendMessage("status", text, ephemeral);
    activeStatusMessageId.value = message.id;
  }

  function formatStatusMessage(state: AgentState, label: string): string {
    if (state === "planning" || state === "preparing") return "我在整理当前正文和项目记忆。";
    if (state === "connecting") return label;
    if (state === "writing" || state === "demo") return "我正在把正文写入中间编辑区。";
    if (state === "done") return "完成，正文已同步到编辑区。";
    if (state === "error") return label;
    return label;
  }

  function transitionAgent(nextState: AgentState, label?: string) {
    agentState.value = nextState;
    activeStatus.value = label || stateMeta[nextState].hint;
  }

  function reportAgentState(nextState: AgentState, label?: string) {
    transitionAgent(nextState, label);
    const text = formatStatusMessage(nextState, activeStatus.value);
    if (nextState === "done") {
      updateStatusMessage(text, false);
      activeStatusMessageId.value = null;
      return;
    }
    updateStatusMessage(text, true);
  }

  function failAgent(message: string) {
    transitionAgent("error", message);
    updateStatusMessage(message, false);
    activeStatusMessageId.value = null;
  }

  function scrollChat() {
    nextTick(() => {
      if (chatLogRef.value) chatLogRef.value.scrollTop = chatLogRef.value.scrollHeight;
    });
  }

  function forceScrollChatToBottom() {
    if (chatLogRef.value) chatLogRef.value.scrollTop = chatLogRef.value.scrollHeight;
    nextTick(() => {
      requestAnimationFrame(() => {
        if (chatLogRef.value) chatLogRef.value.scrollTop = chatLogRef.value.scrollHeight;
      });
    });
  }

  function nowTime(): string {
    return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }

  function shouldPersistMessage(message: ChatMessage): boolean {
    if (message.ephemeral) return false;
    return Boolean(message.text.trim() || message.plan);
  }

  function restoreMessages(raw: string): ChatMessage[] {
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter((item): item is ChatMessage => {
          return (
            item &&
            typeof item.id === "string" &&
            ["user", "agent", "status"].includes(item.role) &&
            typeof item.text === "string" &&
            typeof item.time === "string"
          );
        })
        .map((item) => ({ ...item, ephemeral: false, needsConfirmation: false }));
    } catch {
      return [];
    }
  }

  const saveMessages = debounce((msgs: ChatMessage[]) => {
    localStorage.setItem(
      "novelsmith.chatMessages",
      JSON.stringify(msgs.filter(shouldPersistMessage).slice(-120))
    );
  }, 500);

  function loadChat() {
    const saved = localStorage.getItem("novelsmith.chatMessages");
    if (saved) messages.value = restoreMessages(saved);
  }

  function newSession() {
    messages.value = [];
    agentState.value = "idle";
    activeStatus.value = stateMeta.idle.hint;
    activeStatusMessageId.value = null;
    pendingPrompt.value = "";
    pendingPlan.value = null;
    pendingMessageId.value = null;
    appendMessage("agent", "你好，我是 Hermes Agent 协同写作助手。会话已重置，记忆已更新，请问有什么可以帮你的？");
  }

  watch(messages, (v) => saveMessages(v), { deep: true });

  return {
    messages,
    prompt,
    agentState,
    activeStatus,
    activeStatusMessageId,
    pendingPrompt,
    pendingPlan,
    pendingMessageId,
    chatLogRef,
    isGenerating,
    isAwaitingConfirm,
    canSend,
    appendMessage,
    appendToLastAgent,
    updateStatusMessage,
    formatStatusMessage,
    transitionAgent,
    reportAgentState,
    failAgent,
    scrollChat,
    forceScrollChatToBottom,
    loadChat,
    newSession
  };
}
