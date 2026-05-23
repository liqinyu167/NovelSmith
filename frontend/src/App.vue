<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  ArrowUp,
  AtSign,
  Bot,
  Check,
  ChevronRight,
  CircleAlert,
  Copy,
  KeyRound,
  Menu,
  MessageSquarePlus,
  Minus,
  PanelRight,
  Plus,
  Send,
  Settings,
  SlidersHorizontal,
  Sparkles,
  X
} from "lucide-vue-next";

type AgentState = "idle" | "planning" | "awaiting_confirm" | "preparing" | "connecting" | "writing" | "done" | "error" | "demo";

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
  planning: { label: "规划", hint: "准备写入说明" },
  awaiting_confirm: { label: "待确认", hint: "等待你确认是否写入正文" },
  preparing: { label: "准备", hint: "组装模型上下文" },
  connecting: { label: "连接", hint: "连接 API 与模型" },
  writing: { label: "写作", hint: "流式写入正文" },
  done: { label: "完成", hint: "正文已同步" },
  error: { label: "错误", hint: "调用失败，需要处理" },
  demo: { label: "演示", hint: "未配置 API，使用本地文本" }
};

const apiBase = "";
const provider = ref<ProviderConfig>({
  base_url: "http://localhost:11434/v1",
  model: "qwen2.5:7b",
  api_key: ""
});
const projectBrief = ref(
  "类型：近未来悬疑都市。语气：冷冽、细腻、有强烈画面感。目标：用一个强钩子的雨夜开场吸引读者。"
);
const manuscript = ref("");
const prompt = ref("");
const messages = ref<ChatMessage[]>([
  {
    id: crypto.randomUUID(),
    role: "agent",
    text: "你好，我是 NovelSmith 总管智能体。告诉我你要写什么，我会先说明准备写入的内容，等你确认后再动正文。",
    time: nowTime()
  }
]);
const agentState = ref<AgentState>("idle");
const activeStatus = ref(stateMeta.idle.hint);
const configOpen = ref(false);
const workspaceOpen = ref(false);
const editorScale = ref(1);
const activeStatusMessageId = ref<string | null>(null);
const pendingPrompt = ref("");
const pendingPlan = ref<WritePlan | null>(null);
const pendingMessageId = ref<string | null>(null);
const chatLogRef = ref<HTMLElement | null>(null);
const manuscriptRef = ref<HTMLTextAreaElement | null>(null);

const wordCount = computed(() => manuscript.value.replace(/\s/g, "").length);
const isGenerating = computed(() => ["preparing", "connecting", "writing", "demo"].includes(agentState.value));
const isAwaitingConfirm = computed(() => agentState.value === "awaiting_confirm");
const canSend = computed(() => prompt.value.trim().length > 0 && !isGenerating.value && !isAwaitingConfirm.value);
const providerReady = computed(
  () => provider.value.base_url.trim() && provider.value.model.trim() && provider.value.api_key.trim()
);
const workspaces = ["正文", "大纲", "设定", "角色", "记忆"];

onMounted(() => {
  const savedProvider = localStorage.getItem("novelsmith.provider");
  const savedDraft = localStorage.getItem("novelsmith.manuscript");
  const savedBrief = localStorage.getItem("novelsmith.projectBrief");
  const savedScale = localStorage.getItem("novelsmith.editorScale");
  if (savedProvider) provider.value = JSON.parse(savedProvider);
  if (savedDraft) manuscript.value = savedDraft;
  if (savedBrief) projectBrief.value = savedBrief;
  if (savedScale) editorScale.value = Number(savedScale);
});

watch(
  provider,
  (value) => localStorage.setItem("novelsmith.provider", JSON.stringify(value)),
  { deep: true }
);
watch(projectBrief, (value) => localStorage.setItem("novelsmith.projectBrief", value));
watch(manuscript, (value) => localStorage.setItem("novelsmith.manuscript", value));
watch(editorScale, (value) => localStorage.setItem("novelsmith.editorScale", String(value)));

async function sendPrompt() {
  if (!canSend.value) return;

  const userPrompt = prompt.value.trim();
  prompt.value = "";
  pendingPrompt.value = userPrompt;
  activeStatusMessageId.value = null;
  appendMessage("user", userPrompt);
  await routeUserIntent(userPrompt);
}

async function routeUserIntent(userPrompt: string) {
  transitionAgent("planning", "判断你的意图");
  updateStatusMessage("我先判断这是普通对话，还是需要写入正文。", true);
  try {
    const response = await fetch(`${apiBase}/api/agent/intents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: userPrompt,
        manuscript: manuscript.value,
        project_brief: projectBrief.value,
        provider: provider.value
      })
    });
    if (!response.ok) throw new Error(`Detect intent failed: ${response.status}`);
    const intent = (await response.json()) as { action: "chat" | "write"; reason: string };
    if (intent.action === "write") {
      await createWritePlan(userPrompt);
      return;
    }
    await startChat(userPrompt);
  } catch (error) {
    failAgent(error instanceof Error ? error.message : "Unknown error");
  }
}

async function startChat(userPrompt: string) {
  transitionAgent("preparing", "准备对话上下文");
  const agentMessage = appendMessage("agent", "");
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
    streamChat(run_id, agentMessage.id);
  } catch (error) {
    failAgent(error instanceof Error ? error.message : "Unknown error");
  }
}

async function createWritePlan(userPrompt: string) {
  transitionAgent("planning", "正在拟定写作计划");
  updateStatusMessage("我先整理你的意图和当前正文，生成一份可确认的写入计划。", true);
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
    updateStatusMessage("我已经准备好写入计划，等你确认后再执行。", false);
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

function streamChat(runId: string, messageId: string) {
  const source = new EventSource(`${apiBase}/api/agent/chats/${runId}/events`);
  source.onmessage = (event) => {
    const packet = JSON.parse(event.data) as AgentEvent;
    handleChatEvent(packet, source, messageId);
  };
  source.onerror = () => {
    source.close();
    failAgent("SSE 连接中断，请重试。");
  };
}

function handleChatEvent(event: AgentEvent, source: EventSource, messageId: string) {
  if (event.type === "status") reportAgentState(event.state ?? "preparing", event.label);

  if (event.type === "tool_result") {
    updateStatusMessage("我读取了当前项目上下文。", true);
  }

  if (event.type === "assistant_delta") {
    const message = messages.value.find((item) => item.id === messageId);
    if (message) message.text += event.text;
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
}

function handleAgentEvent(event: AgentEvent, source: EventSource) {
  if (event.type === "status") reportAgentState(event.state ?? "preparing", event.label);

  if (event.type === "assistant_delta") appendToLastAgent(event.text);

  if (event.type === "manuscript_delta") {
    transitionAgent(event.state ?? "writing", stateMeta.writing.hint);
    manuscript.value += event.text;
    nextTick(() => {
      if (manuscriptRef.value) manuscriptRef.value.scrollTop = manuscriptRef.value.scrollHeight;
    });
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

function appendMessage(role: ChatMessage["role"], text: string, ephemeral = false) {
  const message: ChatMessage = { id: crypto.randomUUID(), role, text, time: nowTime(), ephemeral };
  messages.value.push(message);
  return message;
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
  if (state === "done") return "完成，正文已同步到中间编辑区。";
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

function nowTime() {
  return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
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
</script>

<template>
  <main class="app-shell">
    <section class="writing-pane" aria-label="小说正文编辑区">
      <header class="writing-header">
        <div class="workspace-switcher">
          <button class="hamburger" aria-label="切换工作区" @click="workspaceOpen = !workspaceOpen">
            <Menu :size="23" />
          </button>
          <div>
            <h1>Untitled</h1>
            <p>Chapter 01 · 正文</p>
          </div>
        </div>

        <div class="writing-meta">
          <span>{{ wordCount }} 字</span>
          <span>{{ activeStatus }}</span>
        </div>

        <nav v-if="workspaceOpen" class="workspace-menu" aria-label="工作区">
          <button v-for="item in workspaces" :key="item" :class="{ active: item === '正文' }">
            {{ item }}
          </button>
        </nav>
      </header>

      <div class="novel-paper" @wheel="handleEditorWheel">
        <div class="zoom-controls" aria-label="正文缩放" @wheel.stop="handleZoomWheel">
          <button type="button" aria-label="缩小正文" @click="zoomEditor(-0.08)">
            <Minus :size="18" />
          </button>
          <button type="button" class="zoom-value" aria-label="重置正文缩放" @click="resetEditorZoom">
            {{ Math.round(editorScale * 100) }}%
          </button>
          <button type="button" aria-label="放大正文" @click="zoomEditor(0.08)">
            <Plus :size="18" />
          </button>
        </div>
        <textarea
          ref="manuscriptRef"
          v-model="manuscript"
          class="novel-editor"
          :style="{ '--editor-scale': editorScale }"
          spellcheck="false"
          placeholder="正文会在这里实时生成。你也可以直接在这里改稿。"
        />
      </div>
    </section>

    <aside class="agent-dock" aria-label="总管智能体对话">
      <header class="agent-header">
        <div class="agent-identity">
          <div class="agent-orb" :class="{ live: isGenerating || isAwaitingConfirm, error: agentState === 'error' }">
            <Bot :size="23" />
          </div>
          <div>
            <h2>RH 智能体</h2>
            <button class="session-copy" type="button" aria-label="复制会话 ID">
              sess-205...303682 <Copy :size="13" />
            </button>
          </div>
        </div>

        <div class="agent-tools">
          <button aria-label="新对话"><MessageSquarePlus :size="21" /></button>
          <button
            class="config-toggle"
            :class="{ active: configOpen }"
            aria-label="切换 API 配置"
            @click="configOpen = !configOpen"
          >
            <SlidersHorizontal :size="21" />
          </button>
          <button aria-label="收起面板"><ChevronRight :size="24" /></button>
        </div>
      </header>

      <form v-if="configOpen" class="api-popover" @submit.prevent>
        <div class="api-popover-title">
          <Settings :size="18" />
          <span>API 接入配置</span>
          <strong :class="{ ready: providerReady }">{{ providerReady ? "READY" : "DEMO" }}</strong>
        </div>
        <label>
          Base URL
          <input v-model="provider.base_url" autocomplete="off" placeholder="https://api.openai.com/v1" />
        </label>
        <label>
          Model
          <input v-model="provider.model" autocomplete="off" placeholder="gpt-4.1 / deepseek-chat" />
        </label>
        <label>
          API Key
          <span class="key-field">
            <KeyRound :size="16" />
            <input v-model="provider.api_key" type="password" autocomplete="off" placeholder="sk-..." />
          </span>
        </label>
        <label>
          项目记忆
          <textarea v-model="projectBrief" rows="3" />
        </label>
      </form>

      <div ref="chatLogRef" class="chat-thread" aria-live="polite">
        <article
          v-for="message in messages"
          :key="message.id"
          class="chat-message"
          :class="[message.role, { ephemeral: message.ephemeral }]"
        >
          <template v-if="message.role === 'user'">
            <div class="bubble user-bubble">{{ message.text }}</div>
            <time>{{ message.time }}</time>
          </template>

          <template v-else>
            <div class="message-avatar">
              <Bot v-if="message.role === 'agent'" :size="18" />
              <CircleAlert v-else :size="18" />
            </div>
            <div class="message-body">
              <p>{{ message.text }}</p>
              <div v-if="message.plan" class="plan-card">
                <div>
                  <span>意图</span>
                  <strong>{{ message.plan.intent }}</strong>
                </div>
                <div>
                  <span>目标</span>
                  <strong>{{ message.plan.target }}</strong>
                </div>
                <p>{{ message.plan.summary }}</p>
                <dl>
                  <div>
                    <dt>写入位置</dt>
                    <dd>{{ message.plan.write_position }}</dd>
                  </div>
                  <div>
                    <dt>预计长度</dt>
                    <dd>{{ message.plan.estimated_length }}</dd>
                  </div>
                </dl>
                <section>
                  <span>执行步骤</span>
                  <ol>
                    <li v-for="step in message.plan.steps" :key="step">{{ step }}</li>
                  </ol>
                </section>
                <section>
                  <span>约束</span>
                  <ul>
                    <li v-for="item in message.plan.constraints" :key="item">{{ item }}</li>
                  </ul>
                </section>
                <section v-if="message.plan.risks.length">
                  <span>注意</span>
                  <ul>
                    <li v-for="risk in message.plan.risks" :key="risk">{{ risk }}</li>
                  </ul>
                </section>
              </div>
              <div v-if="message.needsConfirmation" class="confirm-actions">
                <button type="button" class="confirm-button" @click="confirmPendingWrite">
                  <Check :size="16" />
                  确认写入
                </button>
                <button type="button" class="cancel-button" @click="cancelPendingWrite">
                  <X :size="16" />
                  取消
                </button>
              </div>
              <div class="message-reactions" v-if="message.role === 'agent' && !message.needsConfirmation">
                <Copy :size="16" />
                <AtSign :size="16" />
                <Sparkles :size="16" />
                <time>{{ message.time }}</time>
              </div>
            </div>
          </template>
        </article>
      </div>

      <form class="composer" @submit.prevent="sendPrompt">
        <textarea
          id="prompt"
          v-model="prompt"
          rows="3"
          :placeholder="isAwaitingConfirm ? '请先确认或取消上一条写入计划。' : '输入你的想法，或让智能体继续写当前正文。'"
        />

        <div class="composer-footer">
          <div class="mode-tabs">
            <button type="button" class="active"><Sparkles :size="17" /> Agent</button>
            <button type="button" aria-label="引用"><AtSign :size="18" /></button>
            <button type="button"><PanelRight :size="17" /> Ask</button>
          </div>

          <button class="send-fab" type="submit" :disabled="!canSend" aria-label="发送">
            <ArrowUp v-if="!isGenerating" :size="22" />
            <Send v-else :size="20" />
          </button>
        </div>
      </form>

      <div class="dock-status" :class="{ live: isGenerating || isAwaitingConfirm, error: agentState === 'error' }">
        <Check v-if="agentState !== 'error'" :size="14" />
        <CircleAlert v-else :size="14" />
        <span>{{ activeStatus }}</span>
      </div>
    </aside>
  </main>
</template>
