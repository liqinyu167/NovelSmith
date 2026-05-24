<script setup lang="ts">
import { Bot, ChevronDown, Check, Download, Share2, Clock3 } from "lucide-vue-next";
</script>

<template>
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
</template>
