<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  ArrowUp,
  AtSign,
  BookOpen,
  Bot,
  Boxes,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Circle,
  CircleAlert,
  Clock3,
  Copy,
  Download,
  Expand,
  FileText,
  GitBranch,
  KeyRound,
  LayoutGrid,
  Library,
  ListTree,
  Menu,
  MessageSquarePlus,
  Minus,
  MoreHorizontal,
  PenLine,
  Plus,
  RotateCcw,
  Search,
  Send,
  Settings,
  Share2,
  SlidersHorizontal,
  Sparkles,
  Star,
  Tags,
  TimerReset,
  Users,
  X
} from "lucide-vue-next";

type AgentState =
  | "idle"
  | "planning"
  | "awaiting_confirm"
  | "preparing"
  | "connecting"
  | "writing"
  | "done"
  | "error"
  | "demo";

type AgentEvent =
  | { type: "assistant_delta"; state?: AgentState; text: string }
  | { type: "manuscript_delta"; state?: AgentState; text: string }
  | { type: "status"; state?: AgentState; label: string }
  | { type: "tool_result"; state?: AgentState; name: string; content: string }
  | { type: "done"; state?: AgentState }
  | { type: "error"; state?: AgentState; message: string };

type ChatMessage = {
  id: string;
  role: "user" | "agent" | "status";
  text: string;
  time: string;
  ephemeral?: boolean;
  needsConfirmation?: boolean;
  plan?: WritePlan;
};

type ProviderConfig = {
  base_url: string;
  model: string;
  api_key: string;
};

type WritePlan = {
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

const stateMeta: Record<AgentState, { label: string; hint: string }> = {
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

const apiBase = "";
const chatStorageKey = "novelsmith.chatMessages";
const leftPanelStorageKey = "novelsmith.leftPanelWidth";
const rightPanelStorageKey = "novelsmith.rightPanelWidth";
const provider = ref<ProviderConfig>({
  base_url: "http://localhost:11434/v1",
  model: "qwen2.5:7b",
  api_key: ""
});
const projectBrief = ref("长篇连载悬疑小说。近未来都市，主线围绕雾城档案、失忆调查员与灰塔组织展开。");
const manuscript = ref("");
const prompt = ref("");
const messages = ref<ChatMessage[]>([]);
const agentState = ref<AgentState>("idle");
const activeStatus = ref(stateMeta.idle.hint);
const configOpen = ref(false);
const editorScale = ref(1);
const leftPanelWidth = ref(384);
const rightPanelWidth = ref(430);
const activeStatusMessageId = ref<string | null>(null);
const pendingPrompt = ref("");
const pendingPlan = ref<WritePlan | null>(null);
const pendingMessageId = ref<string | null>(null);
const chatLogRef = ref<HTMLElement | null>(null);
const paperRef = ref<HTMLElement | null>(null);
const manuscriptRef = ref<HTMLTextAreaElement | null>(null);

const wordCount = computed(() => manuscript.value.replace(/\s/g, "").length);
const targetWordCount = 4000;
const isGenerating = computed(() => ["preparing", "connecting", "writing", "demo"].includes(agentState.value));
const isAwaitingConfirm = computed(() => agentState.value === "awaiting_confirm");
const canSend = computed(() => prompt.value.trim().length > 0 && !isGenerating.value && !isAwaitingConfirm.value);
const providerReady = computed(
  () => provider.value.base_url.trim() && provider.value.model.trim() && provider.value.api_key.trim()
);
const progress = computed(() => Math.min(100, Math.round((wordCount.value / targetWordCount) * 100)));
const shellStyle = computed(() => ({
  "--left-panel-width": `${leftPanelWidth.value}px`,
  "--right-panel-width": `${rightPanelWidth.value}px`
}));

const characters = [
  { name: "林藏", role: "主角", desc: "失忆调查员", tags: ["理性", "执着", "过去成谜"], score: 24 },
  { name: "苏黎", role: "盟友", desc: "档案管理员 / 灰塔组织成员", tags: ["冷静", "清醒", "守护秘密"], score: 18 },
  { name: "夜枭", role: "反派", desc: "灰塔组织联络者", tags: ["神秘", "窥视", "目标不明"], score: 32 }
];
const worldSettings = [
  { title: "雾城C区", desc: "常年被浓雾笼罩的沿海都市，权力分割混乱。" },
  { title: "灰塔组织", desc: "掌控情报与秩序的隐秘组织，信仰秩序即正义。" }
];
const timeline = ["三年前", "第一次调查中失踪，记忆自此断裂。", "第一卷", "灰塔组织收紧控制，雾城局势暗流涌动。", "Chapter 01"];

onMounted(() => {
  const savedProvider = localStorage.getItem("novelsmith.provider");
  const savedDraft = localStorage.getItem("novelsmith.manuscript");
  const savedBrief = localStorage.getItem("novelsmith.projectBrief");
  const savedScale = localStorage.getItem("novelsmith.editorScale");
  const savedMessages = localStorage.getItem(chatStorageKey);
  const savedLeftPanelWidth = localStorage.getItem(leftPanelStorageKey);
  const savedRightPanelWidth = localStorage.getItem(rightPanelStorageKey);
  if (savedProvider) provider.value = JSON.parse(savedProvider);
  if (savedDraft) manuscript.value = savedDraft;
  if (savedBrief) projectBrief.value = savedBrief;
  if (savedScale) editorScale.value = Number(savedScale);
  if (savedMessages) messages.value = restoreMessages(savedMessages);
  if (savedLeftPanelWidth) leftPanelWidth.value = clampPanelWidth(Number(savedLeftPanelWidth), 72, 900);
  if (savedRightPanelWidth) rightPanelWidth.value = clampPanelWidth(Number(savedRightPanelWidth), 72, 1000);
  nextTick(scrollChat);
  resizeManuscript();
});

watch(
  provider,
  (value) => localStorage.setItem("novelsmith.provider", JSON.stringify(value)),
  { deep: true }
);
watch(projectBrief, (value) => localStorage.setItem("novelsmith.projectBrief", value));
watch(manuscript, (value) => {
  localStorage.setItem("novelsmith.manuscript", value);
  resizeManuscript();
});
watch(editorScale, (value) => localStorage.setItem("novelsmith.editorScale", String(value)));
watch(leftPanelWidth, (value) => localStorage.setItem(leftPanelStorageKey, String(value)));
watch(rightPanelWidth, (value) => localStorage.setItem(rightPanelStorageKey, String(value)));
watch(
  messages,
  (value) => {
    localStorage.setItem(chatStorageKey, JSON.stringify(value.filter(shouldPersistMessage).slice(-120)));
  },
  { deep: true }
);

async function resizeManuscript() {
  await nextTick();
  if (!manuscriptRef.value) return;
  manuscriptRef.value.style.height = "auto";
  manuscriptRef.value.style.height = `${Math.max(manuscriptRef.value.scrollHeight, 620)}px`;
}

async function sendPrompt() {
  if (!canSend.value) return;

  const userPrompt = prompt.value.trim();
  prompt.value = "";
  pendingPrompt.value = userPrompt;
  appendMessage("user", userPrompt);
  activeStatusMessageId.value = null;
  forceScrollChatToBottom();
  await startChat(userPrompt);
}

async function startChat(userPrompt: string) {
  transitionAgent("preparing", "准备对话上下文");
  try {
    const response = await fetch(`${apiBase}/api/agent/chats`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: userPrompt,
        manuscript: manuscript.value,
        project_brief: projectBrief.value,
        provider: provider.value
      })
    });
    if (!response.ok) throw new Error(`Create chat failed: ${response.status}`);
    const { run_id } = (await response.json()) as { run_id: string };
    streamChat(run_id);
  } catch (error) {
    failAgent(error instanceof Error ? error.message : "Unknown error");
  }
}

async function createWritePlan(userPrompt: string) {
  transitionAgent("planning", "拟定写作计划");
  updateStatusMessage("我会先整理意图、正文和知识库，生成一份待确认的写入计划。", true);
  try {
    const response = await fetch(`${apiBase}/api/agent/plans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: userPrompt,
        manuscript: manuscript.value,
        project_brief: projectBrief.value,
        provider: provider.value
      })
    });
    if (!response.ok) throw new Error(`Create plan failed: ${response.status}`);
    const plan = (await response.json()) as WritePlan;
    pendingPlan.value = plan;
    transitionAgent("awaiting_confirm", stateMeta.awaiting_confirm.hint);
    updateStatusMessage("写入计划已准备好，等待确认。", false);
    activeStatusMessageId.value = null;
    const message = appendMessage("agent", "我准备这样写入正文：");
    message.plan = plan;
    message.needsConfirmation = true;
    pendingMessageId.value = message.id;
    scrollChat();
  } catch (error) {
    failAgent(error instanceof Error ? error.message : "Unknown error");
  }
}

function cancelPendingWrite() {
  const message = pendingMessageId.value ? messages.value.find((item) => item.id === pendingMessageId.value) : null;
  if (message) {
    message.needsConfirmation = false;
    message.text += "\n\n已取消，本次不会写入正文。";
  }
  pendingPrompt.value = "";
  pendingPlan.value = null;
  pendingMessageId.value = null;
  transitionAgent("idle", stateMeta.idle.hint);
}

async function confirmPendingWrite() {
  if (!pendingPrompt.value || isGenerating.value) return;
  const message = pendingMessageId.value ? messages.value.find((item) => item.id === pendingMessageId.value) : null;
  if (message) {
    message.needsConfirmation = false;
    message.text += "\n\n已确认，开始写入。";
  }
  const confirmedPrompt = pendingPrompt.value;
  const confirmedPlan = pendingPlan.value;
  pendingPrompt.value = "";
  pendingPlan.value = null;
  pendingMessageId.value = null;
  await startGeneration(confirmedPrompt, confirmedPlan);
}

async function startGeneration(userPrompt: string, writePlan: WritePlan | null) {
  transitionAgent("preparing", "创建生成任务");
  try {
    const response = await fetch(`${apiBase}/api/agent/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: userPrompt,
        manuscript: manuscript.value,
        project_brief: projectBrief.value,
        write_plan: writePlan,
        provider: provider.value
      })
    });

    if (!response.ok) throw new Error(`Create run failed: ${response.status}`);
    const { run_id } = (await response.json()) as { run_id: string };
    streamRun(run_id);
  } catch (error) {
    failAgent(error instanceof Error ? error.message : "Unknown error");
  }
}

function streamRun(runId: string) {
  const source = new EventSource(`${apiBase}/api/agent/runs/${runId}/events`);
  source.onmessage = (event) => {
    const packet = JSON.parse(event.data) as AgentEvent;
    handleAgentEvent(packet, source);
  };
  source.onerror = () => {
    source.close();
    failAgent("SSE 连接中断，请重试。");
  };
}

function streamChat(runId: string) {
  const source = new EventSource(`${apiBase}/api/agent/chats/${runId}/events`);
  let messageId: string | null = null;
  source.onmessage = (event) => {
    const packet = JSON.parse(event.data) as AgentEvent;
    messageId = handleChatEvent(packet, source, messageId);
  };
  source.onerror = () => {
    source.close();
    failAgent("SSE 连接中断，请重试。");
  };
}

function handleChatEvent(event: AgentEvent, source: EventSource, messageId: string | null) {
  if (event.type === "status") reportAgentState(event.state ?? "preparing", event.label);
  if (event.type === "tool_result") reportToolResult(event);
  if (event.type === "assistant_delta") {
    if (!messageId) {
      messageId = appendMessage("agent", "").id;
    }
    const message = messages.value.find((item) => item.id === messageId);
    if (message) message.text += event.text;
  }
  if (event.type === "manuscript_delta") {
    appendManuscript(event.text);
  }
  if (event.type === "error") {
    source.close();
    failAgent(event.message);
  }
  if (event.type === "done") {
    source.close();
    reportAgentState(event.state ?? "done", "对话完成");
  }
  scrollChat();
  return messageId;
}

function reportToolResult(event: Extract<AgentEvent, { type: "tool_result" }>) {
  if (event.name === "read_project_context") {
    updateStatusMessage("我读取了当前项目上下文。", true);
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
    updateStatusMessage(summary, false);
  }
}

function handleAgentEvent(event: AgentEvent, source: EventSource) {
  if (event.type === "status") reportAgentState(event.state ?? "preparing", event.label);
  if (event.type === "assistant_delta") appendToLastAgent(event.text);
  if (event.type === "manuscript_delta") {
    appendManuscript(event.text);
  }
  if (event.type === "error") {
    source.close();
    failAgent(event.message);
  }
  if (event.type === "done") {
    source.close();
    reportAgentState(event.state ?? "done", "正文已同步到编辑区");
  }
  scrollChat();
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

function appendManuscript(text: string) {
  transitionAgent("writing", stateMeta.writing.hint);
  manuscript.value += text;
  nextTick(() => {
    resizeManuscript();
    if (paperRef.value) paperRef.value.scrollTop = paperRef.value.scrollHeight;
  });
}

function appendMessage(role: ChatMessage["role"], text: string, ephemeral = false) {
  const message: ChatMessage = { id: crypto.randomUUID(), role, text, time: nowTime(), ephemeral };
  messages.value.push(message);
  return message;
}

function shouldPersistMessage(message: ChatMessage) {
  if (message.ephemeral) return false;
  return Boolean(message.text.trim() || message.plan);
}

function restoreMessages(raw: string) {
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

function formatStatusMessage(state: AgentState, label: string) {
  if (state === "planning" || state === "preparing") return "我在整理当前正文和项目记忆。";
  if (state === "connecting") return label;
  if (state === "writing" || state === "demo") return "我正在把正文写入中间编辑区。";
  if (state === "done") return "完成，正文已同步到编辑区。";
  if (state === "error") return label;
  return label;
}

function appendToLastAgent(text: string) {
  const last = [...messages.value].reverse().find((message) => message.role === "agent");
  if (last) last.text += text;
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

function nowTime() {
  return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function renderMarkdown(text: string) {
  const escaped = escapeHtml(text).replace(/\r\n/g, "\n").trim();
  if (!escaped) return "";

  const blocks: string[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (!listItems.length) return;
    blocks.push(`<ol>${listItems.join("")}</ol>`);
    listItems = [];
  }

  for (const rawLine of escaped.split("\n")) {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(line);
    if (heading) {
      flushList();
      const level = Math.min(heading[1].length + 2, 5);
      blocks.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    const numbered = /^\d+[.、]\s*(.+)$/.exec(line);
    const bullet = /^[-*]\s+(.+)$/.exec(line);
    if (numbered || bullet) {
      listItems.push(`<li>${renderInlineMarkdown((numbered || bullet)?.[1] ?? "")}</li>`);
      continue;
    }

    if (/^---+$/.test(line)) {
      flushList();
      blocks.push("<hr>");
      continue;
    }

    flushList();
    blocks.push(`<p>${renderInlineMarkdown(line)}</p>`);
  }
  flushList();
  return blocks.join("");
}

function renderInlineMarkdown(text: string) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function zoomEditor(delta: number) {
  editorScale.value = Math.min(1.45, Math.max(0.75, Number((editorScale.value + delta).toFixed(2))));
}

function resetEditorZoom() {
  editorScale.value = 1;
}

function handleEditorWheel(event: WheelEvent) {
  if (!event.ctrlKey && !event.metaKey) return;
  event.preventDefault();
  zoomEditor(event.deltaY < 0 ? 0.05 : -0.05);
}

function handleZoomWheel(event: WheelEvent) {
  event.preventDefault();
  zoomEditor(event.deltaY < 0 ? 0.05 : -0.05);
}

function handleComposerKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  sendPrompt();
}

function startPanelResize(side: "left" | "right", event: PointerEvent) {
  const startX = event.clientX;
  const startWidth = side === "left" ? leftPanelWidth.value : rightPanelWidth.value;
  document.body.classList.add("is-resizing-panel");

  function move(moveEvent: PointerEvent) {
    const delta = moveEvent.clientX - startX;
    if (side === "left") {
      leftPanelWidth.value = clampPanelWidth(startWidth + delta, 72, maxPanelWidth(900));
      return;
    }
    rightPanelWidth.value = clampPanelWidth(startWidth - delta, 72, maxPanelWidth(1000));
  }

  function stop() {
    document.body.classList.remove("is-resizing-panel");
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
    window.removeEventListener("pointercancel", stop);
  }

  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop);
  window.addEventListener("pointercancel", stop);
}

function clampPanelWidth(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, Math.round(value)));
}

function maxPanelWidth(limit: number) {
  return Math.max(72, Math.min(limit, window.innerWidth - 420));
}
</script>

<template>
  <main class="studio-shell" :style="shellStyle">
    <header class="topbar">
      <section class="brand">
        <div class="brand-mark"><Bot :size="26" /></div>
        <div>
          <h1>Agent 小说生成器</h1>
          <span>Hermes 架构</span>
        </div>
      </section>

      <section class="project-switch">
        <div class="cover"></div>
        <div>
          <strong>雾城档案</strong>
          <span>长篇连载中 · 已保存</span>
        </div>
        <ChevronDown :size="18" />
      </section>

      <section class="chapter-select">
        <button>第一卷 / Chapter 01 <ChevronDown :size="16" /></button>
      </section>

      <nav class="mode-switch" aria-label="写作模式">
        <button>大纲</button>
        <button class="active">正文</button>
        <button>润色</button>
        <button>审稿</button>
      </nav>

      <section class="top-actions">
        <span class="saved"><Check :size="16" /> 已保存</span>
        <button><Download :size="17" /> 导出</button>
        <button><Share2 :size="17" /> 分享</button>
        <button class="icon-only"><Clock3 :size="18" /></button>
      </section>
    </header>

    <aside class="knowledge-panel">
      <div class="panel-title">
        <strong>知识库</strong>
        <div>
          <Search :size="18" />
          <ChevronDown :size="18" />
        </div>
      </div>

      <div class="knowledge-tabs">
        <button class="active"><Users :size="15" />角色</button>
        <button><Library :size="15" />世界观</button>
        <button><TimerReset :size="15" />时间线</button>
        <button><GitBranch :size="15" />伏笔</button>
        <button><ListTree :size="15" />大纲</button>
      </div>

      <section class="kb-section">
        <div class="section-heading">
          <span>主要角色</span>
          <button><Plus :size="14" /> 新建角色</button>
        </div>
        <article v-for="character in characters" :key="character.name" class="character-card">
          <div class="portrait"></div>
          <div class="character-main">
            <div>
              <strong>{{ character.name }}</strong>
              <em>{{ character.role }}</em>
            </div>
            <p>{{ character.desc }}</p>
            <div class="tags">
              <span v-for="tag in character.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>
          <span class="score"><Star :size="13" />{{ character.score }}</span>
        </article>
      </section>

      <section class="kb-section">
        <div class="section-heading"><span>世界观设定</span></div>
        <article v-for="item in worldSettings" :key="item.title" class="setting-card">
          <Boxes :size="18" />
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.desc }}</p>
          </div>
        </article>
      </section>

      <section class="kb-section">
        <div class="section-heading">
          <span>事件时间线</span>
          <button><Plus :size="14" /> 新建事件</button>
        </div>
        <div class="timeline">
          <span v-for="(item, index) in timeline" :key="`${item}-${index}`" :class="{ active: item === 'Chapter 01' }">
            {{ item }}
          </span>
        </div>
      </section>

      <section class="kb-section outline">
        <div class="section-heading">
          <span>章节大纲</span>
          <button><MoreHorizontal :size="14" /> 折叠全部</button>
        </div>
        <div class="chapter-tree">
          <strong>第一卷：迷雾初起</strong>
          <button class="active">Chapter 01　第一章：雾中来信</button>
          <button>Chapter 02　雾城的规则</button>
          <button>Chapter 03　灰塔的影子</button>
        </div>
      </section>
    </aside>

    <div
      class="panel-resizer left-resizer"
      role="separator"
      aria-label="调整左侧知识库宽度"
      @pointerdown.prevent="startPanelResize('left', $event)"
    ></div>

    <section class="editor-area">
      <div class="editor-card">
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <button><ChevronLeft :size="18" /></button>
            <button><ChevronRight :size="18" /></button>
            <button><RotateCcw :size="16" />版本历史</button>
            <button>v1.2 <ChevronDown :size="14" /></button>
          </div>
          <div class="toolbar-right">
            <button><BookOpen :size="16" /></button>
            <button><LayoutGrid :size="16" /></button>
            <span>{{ wordCount }} / {{ targetWordCount }} 字</span>
            <button><Settings :size="16" /></button>
            <button><Expand :size="16" /></button>
          </div>
        </div>

        <div ref="paperRef" class="paper" @wheel="handleEditorWheel">
          <div class="chapter-heading">
            <span>Chapter 01</span>
            <h2>第一章：雾中来信</h2>
            <i></i>
            <p>目标 {{ targetWordCount }} 字　/　当前 {{ wordCount }} 字　/　POV：林藏　/　场景：雨夜</p>
          </div>
          <textarea
            ref="manuscriptRef"
            v-model="manuscript"
            class="manuscript"
            :style="{ '--editor-scale': editorScale }"
            spellcheck="false"
            placeholder="正文会在这里生成。你也可以直接在这里修改。"
          />
        </div>

        <div class="floating-format">
          <button><Sparkles :size="16" /> AI 续写</button>
          <button>B</button>
          <button><em>I</em></button>
          <button>U</button>
          <button><Tags :size="16" /></button>
          <button>“</button>
          <button><ListTree :size="16" /></button>
          <button><PenLine :size="16" /></button>
        </div>
      </div>
    </section>

    <div
      class="panel-resizer right-resizer"
      role="separator"
      aria-label="调整右侧 Agent 宽度"
      @pointerdown.prevent="startPanelResize('right', $event)"
    ></div>

    <aside class="agent-panel" :class="{ 'config-open': configOpen }">
      <header class="agent-head">
        <div class="agent-avatar"><Bot :size="25" /></div>
        <div>
          <h2>Hermes Agent</h2>
          <span><Circle :size="8" fill="currentColor" /> {{ providerReady ? "已连接" : "未连接 API" }}</span>
        </div>
        <button class="config-toggle" :class="{ active: configOpen }" @click="configOpen = !configOpen">
          <SlidersHorizontal :size="18" />
        </button>
      </header>

      <form v-if="configOpen" class="api-config" @submit.prevent>
        <label>
          Base URL
          <input v-model="provider.base_url" autocomplete="off" />
        </label>
        <label>
          Model
          <input v-model="provider.model" autocomplete="off" />
        </label>
        <label>
          API Key
          <span class="key-field">
            <KeyRound :size="15" />
            <input v-model="provider.api_key" type="password" autocomplete="off" />
          </span>
        </label>
        <strong :class="{ ready: providerReady }">{{ providerReady ? "READY" : "OFFLINE" }}</strong>
      </form>

      <section class="agent-chat">
        <div ref="chatLogRef" class="chat-log" aria-live="polite">
          <article
            v-for="message in messages"
            :key="message.id"
            class="chat-message"
            :class="[message.role, { ephemeral: message.ephemeral }]"
          >
            <div v-if="message.role !== 'user'" class="msg-avatar">
              <Bot v-if="message.role === 'agent'" :size="16" />
              <Sparkles v-else-if="message.role === 'status' && message.ephemeral" :size="16" />
              <Check v-else-if="message.role === 'status'" :size="16" />
              <CircleAlert v-else :size="16" />
            </div>
            <div class="msg-body">
              <strong v-if="message.role === 'agent'">Hermes</strong>
              <div class="markdown-body" v-html="renderMarkdown(message.text)"></div>
              <div v-if="message.plan" class="plan-card">
                <div><span>意图</span><b>{{ message.plan.intent }}</b></div>
                <div><span>目标</span><b>{{ message.plan.target }}</b></div>
                <p>{{ message.plan.summary }}</p>
                <dl>
                  <div><dt>写入位置</dt><dd>{{ message.plan.write_position }}</dd></div>
                  <div><dt>预计长度</dt><dd>{{ message.plan.estimated_length }}</dd></div>
                </dl>
                <section>
                  <span>执行步骤</span>
                  <ol><li v-for="step in message.plan.steps" :key="step">{{ step }}</li></ol>
                </section>
                <section>
                  <span>约束</span>
                  <ul><li v-for="item in message.plan.constraints" :key="item">{{ item }}</li></ul>
                </section>
              </div>
              <div v-if="message.needsConfirmation" class="confirm-actions">
                <button class="confirm-button" @click="confirmPendingWrite"><Check :size="15" />确认写入</button>
                <button class="cancel-button" @click="cancelPendingWrite"><X :size="15" />取消</button>
              </div>
              <time>{{ message.time }}</time>
            </div>
          </article>
        </div>
      </section>

      <form class="agent-composer" @submit.prevent="sendPrompt">
        <textarea
          v-model="prompt"
          rows="3"
          :placeholder="isAwaitingConfirm ? '请先确认或取消上一条写入计划。' : '例如：让主角陷入危险，或揭示一个新线索...'"
          @keydown="handleComposerKeydown"
        />
        <div class="composer-tools">
          <button type="button">@ 角色</button>
          <button type="button"># 世界观</button>
          <button type="button">/ 指令库</button>
          <button class="send" type="submit" :disabled="!canSend">
            <ArrowUp v-if="!isGenerating" :size="18" />
            <Send v-else :size="18" />
          </button>
        </div>
      </form>
    </aside>
  </main>
</template>
