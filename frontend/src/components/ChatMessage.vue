<script setup lang="ts">
import { Bot, Sparkles, Check, CircleAlert, X } from "lucide-vue-next";
import type { ChatMessage } from "../types";
import { renderMarkdown } from "../lib/markdown";

defineProps<{
  message: ChatMessage;
}>();

defineEmits<{
  (e: "confirm"): void;
  (e: "cancel"): void;
}>();
</script>

<template>
  <article
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
        <button class="confirm-button" @click="$emit('confirm')">
          <Check :size="15" />确认写入
        </button>
        <button class="cancel-button" @click="$emit('cancel')">
          <X :size="15" />取消
        </button>
      </div>
      <time>{{ message.time }}</time>
    </div>
  </article>
</template>
