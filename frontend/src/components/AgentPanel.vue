<script setup lang="ts">
import { computed } from "vue";
import {
  Bot,
  Circle,
  SlidersHorizontal,
  KeyRound,
  ArrowUp,
  Square,
  FileCode2
} from "lucide-vue-next";
import type { ChatMessage, ProviderConfig, AgentState } from "../types";
import ChatMessageComponent from "./ChatMessage.vue";

const props = defineProps<{
  messages: ChatMessage[];
  prompt: string;
  agentState: AgentState;
  activeStatus: string;
  configOpen: boolean;
  provider: ProviderConfig;
  providerReady: boolean;
  isAwaitingConfirm: boolean;
  canSend: boolean;
  isGenerating: boolean;
  activeFilePath?: string;
}>();

const emit = defineEmits<{
  (e: "update:prompt", value: string): void;
  (e: "update:configOpen", value: boolean): void;
  (e: "update:provider", value: ProviderConfig): void;
  (e: "send-prompt"): void;
  (e: "confirm-write"): void;
  (e: "cancel-write"): void;
  (e: "set-chat-log-ref", el: HTMLElement | null): void;
  (e: "stop-generation"): void;
  (e: "new-session"): void;
}>();

const localPrompt = computed({
  get() {
    return props.prompt;
  },
  set(v: string) {
    emit("update:prompt", v);
  }
});

const localConfigOpen = computed({
  get() {
    return props.configOpen;
  },
  set(v: boolean) {
    emit("update:configOpen", v);
  }
});

function handleComposerKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  if (props.isGenerating) {
    emit("stop-generation");
  } else {
    emit("send-prompt");
  }
}

function handleComposerSubmit() {
  if (props.isGenerating) {
    emit("stop-generation");
  } else {
    emit("send-prompt");
  }
}
</script>

<template>
  <aside class="agent-panel" :class="{ 'config-open': configOpen }">
    <header class="agent-head">
      <div class="agent-avatar"><Bot :size="25" /></div>
      <div>
        <h2>Hermes Agent</h2>
        <span>
          <Circle :size="8" fill="currentColor" />
          {{ providerReady ? "已连接" : "未连接 API" }}
        </span>
      </div>
      <button class="config-toggle" :class="{ active: configOpen }" @click="localConfigOpen = !localConfigOpen">
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
      <div :ref="(el) => emit('set-chat-log-ref', el as HTMLElement | null)" class="chat-log" aria-live="polite">
        <ChatMessageComponent
          v-for="message in messages"
          :key="message.id"
          :message="message"
          @confirm="emit('confirm-write')"
          @cancel="emit('cancel-write')"
        />
      </div>
    </section>

    <!-- V2 Active File Indicator Badge -->
    <div v-if="activeFilePath" class="active-file-indicator">
      <FileCode2 :size="13" class="indicator-icon" />
      <span class="indicator-text">
        聚焦上下文: <span class="path-highlight">{{ activeFilePath }}</span>
      </span>
    </div>

    <form class="agent-composer" @submit.prevent="handleComposerSubmit">
      <textarea
        v-model="localPrompt"
        rows="3"
        :placeholder="isAwaitingConfirm ? '请先确认或取消上一条写入计划。' : '例如：让主角陷入危险，或解释我的大纲...'"
        @keydown="handleComposerKeydown"
      />
      <div class="composer-tools">
        <button type="button" @click="emit('new-session')" title="重置当前会话，清除上下文记忆" class="new-session-btn">
          /new 新会话
        </button>
        <button class="send" type="submit" :disabled="!canSend && !isGenerating" :class="{ generating: isGenerating }">
          <Square v-if="isGenerating" :size="14" fill="currentColor" />
          <ArrowUp v-else :size="18" />
        </button>
      </div>
    </form>
  </aside>
</template>

<style scoped>
.active-file-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(157, 140, 255, 0.08);
  border: 1px solid rgba(157, 140, 255, 0.18);
  padding: 6px 12px;
  margin: 0;
  border-radius: 8px;
}
.indicator-icon {
  color: var(--accent);
}
.indicator-text {
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.path-highlight {
  color: #fff;
  font-family: monospace;
  font-weight: 500;
}
.new-session-btn {
  background: rgba(157, 140, 255, 0.08) !important;
  border: 1px solid rgba(157, 140, 255, 0.22) !important;
  color: var(--accent) !important;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
  height: 28px;
}
.new-session-btn:hover {
  background: var(--accent) !important;
  color: #fff !important;
  border-color: var(--accent) !important;
  box-shadow: 0 0 8px rgba(157, 140, 255, 0.35);
}
</style>
