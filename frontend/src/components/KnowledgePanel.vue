<script setup lang="ts">
import {
  Search,
  ChevronDown,
  Users,
  Library,
  TimerReset,
  GitBranch,
  ListTree,
  Plus,
  MoreHorizontal,
  Boxes,
  Star,
  FolderClosed,
  FolderOpen
} from "lucide-vue-next";
import { customRef } from "vue";
import { useKnowledge } from "../composables/useKnowledge";
import FileTree from "./FileTree.vue";

const props = defineProps<{
  prompt: string;
  workspaceTree?: any;
  activeFilePath?: string;
}>();

const emit = defineEmits<{
  (e: "update:prompt", value: string): void;
  (e: "select-file", path: string): void;
  (e: "create-node", parentPath: string, isDirectory: boolean): void;
  (e: "delete-node", path: string): void;
  (e: "open-explorer"): void;
}>();

const promptRef = customRef<string>((track, trigger) => ({
  get() {
    track();
    return props.prompt;
  },
  set(v: string) {
    emit("update:prompt", v);
    trigger();
  }
}));

const {
  activeKnowledgeTab,
  selectedCharacterName,
  activeTimelineIndex,
  activeChapterIndex,
  outlineCollapsed,
  leftPanelNotice,
  characters,
  worldSettings,
  timeline,
  chapters,
  threadCards,
  outline,
  selectKnowledgeTab,
  selectCharacter,
  selectWorldSetting,
  selectTimeline,
  selectChapter,
  queueKnowledgeAction,
  toggleOutlineCollapsed
} = useKnowledge(promptRef, (path) => {
  emit("select-file", path);
});
</script>

<template>
  <aside class="knowledge-panel">
    <div class="panel-title">
      <strong>项目空间</strong>
      <div style="display: flex; gap: 8px; align-items: center;">
        <button 
          @click="emit('open-explorer')" 
          title="在资源管理器中打开项目" 
          class="title-action-btn"
          style="background: transparent; border: 0; padding: 4px; color: var(--muted); cursor: pointer; display: flex; align-items: center;"
        >
          <FolderOpen :size="16" />
        </button>
        <Search :size="18" />
        <ChevronDown :size="18" />
      </div>
    </div>

    <div class="knowledge-tabs">
      <button :class="{ active: activeKnowledgeTab === 'characters' }" @click="selectKnowledgeTab('characters')">
        <Users :size="15" />角色
      </button>
      <button :class="{ active: activeKnowledgeTab === 'world' }" @click="selectKnowledgeTab('world')">
        <Library :size="15" />世界
      </button>
      <button :class="{ active: activeKnowledgeTab === 'timeline' }" @click="selectKnowledgeTab('timeline')">
        <TimerReset :size="15" />时间
      </button>
      <button :class="{ active: activeKnowledgeTab === 'threads' }" @click="selectKnowledgeTab('threads')">
        <GitBranch :size="15" />伏笔
      </button>
      <button :class="{ active: activeKnowledgeTab === 'outline' }" @click="selectKnowledgeTab('outline')">
        <ListTree :size="15" />大纲
      </button>
      <button :class="{ active: activeKnowledgeTab === 'files' }" @click="selectKnowledgeTab('files')">
        <FolderClosed :size="15" />文件
      </button>
    </div>

    <div v-if="leftPanelNotice" class="left-panel-notice">{{ leftPanelNotice }}</div>

    <div class="panel-content-scroll">
      <!-- Characters tab -->
      <section v-if="activeKnowledgeTab === 'characters'" class="kb-section">
        <div class="section-heading">
          <span>角色卡片</span>
          <button @click="queueKnowledgeAction('请帮我新建一个名为 苏荷 的盟友角色卡。')">
            <Plus :size="14" /> 新建角色
          </button>
        </div>
        <article
          v-for="character in characters"
          :key="character.name"
          class="character-card"
          :class="{ selected: selectedCharacterName === character.name }"
          role="button"
          tabindex="0"
          @click="selectCharacter(character.name)"
          @keydown.enter.prevent="selectCharacter(character.name)"
        >
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

      <!-- World settings tab -->
      <section v-if="activeKnowledgeTab === 'world'" class="kb-section">
        <div class="section-heading">
          <span>设定卡片</span>
          <button @click="queueKnowledgeAction('请帮我新建一个名为 灰塔地下档案室 的世界观设定。')">
            <Plus :size="14" /> 新建设定
          </button>
        </div>
        <article
          v-for="item in worldSettings"
          :key="item.title"
          class="setting-card interactive-card"
          role="button"
          tabindex="0"
          @click="selectWorldSetting(item.title)"
          @keydown.enter.prevent="selectWorldSetting(item.title)"
        >
          <Boxes :size="18" />
          <div>
            <strong>{{ item.title }}</strong>
            <em>{{ item.type }}</em>
            <p>{{ item.desc }}</p>
          </div>
        </article>
      </section>

      <!-- Timeline tab -->
      <section v-if="activeKnowledgeTab === 'timeline'" class="kb-section">
        <div class="section-heading">
          <span>事件时间线</span>
          <button @click="queueKnowledgeAction('请根据当前正文补充一个新的时间线事件。')">
            <Plus :size="14" /> 新建事件
          </button>
        </div>
        <div class="timeline">
          <button
            v-for="(item, index) in timeline"
            :key="`${item}-${index}`"
            :class="{ active: activeTimelineIndex === index }"
            @click="selectTimeline(index)"
          >
            {{ item }}
          </button>
        </div>
      </section>

      <!-- Threads tab -->
      <section v-if="activeKnowledgeTab === 'threads'" class="kb-section">
        <div class="section-heading">
          <span>伏笔追踪</span>
          <button @click="queueKnowledgeAction('请从当前正文中整理未回收伏笔。')">
            <Plus :size="14" /> 整理伏笔
          </button>
        </div>
        <article
          v-for="thread in threadCards"
          :key="thread.title"
          class="setting-card interactive-card"
          role="button"
          tabindex="0"
          @click="queueKnowledgeAction(`请检查伏笔「${thread.title}」是否需要回收。`)"
          @keydown.enter.prevent="queueKnowledgeAction(`请检查伏笔「${thread.title}」是否需要回收。`)"
        >
          <GitBranch :size="18" />
          <div>
            <strong>{{ thread.title }}</strong>
            <p>{{ thread.desc }}</p>
          </div>
        </article>
      </section>

      <!-- Outline tab -->
      <section v-if="activeKnowledgeTab === 'outline'" class="kb-section outline">
        <div class="section-heading">
          <span>章节大纲</span>
          <button @click="toggleOutlineCollapsed">
            <MoreHorizontal :size="14" /> {{ outlineCollapsed ? "展开全部" : "折叠全部" }}
          </button>
        </div>
        <div v-if="!outlineCollapsed" class="chapter-tree">
          <strong>{{ outline.volume || '第一卷' }}</strong>
          <button
            v-for="(chapter, index) in chapters"
            :key="chapter"
            :class="{ active: activeChapterIndex === index }"
            @click="selectChapter(index)"
          >
            Ch.{{ index + 1 }} {{ chapter.replace(/\.md$/i, '') }}
          </button>
        </div>
      </section>

      <!-- Files Tab (FileTree Node Explorer) -->
      <section v-if="activeKnowledgeTab === 'files'" class="kb-section">
        <div class="section-heading">
          <span>项目文件目录</span>
          <button @click="emit('open-explorer')" title="在资源管理器中打开工作区" class="open-explorer-btn">
            <FolderOpen :size="13" /> 打开目录
          </button>
        </div>
        <div class="file-tree-wrapper">
          <FileTree
            v-if="workspaceTree"
            :node="workspaceTree"
            :active-path="activeFilePath"
            @select-file="emit('select-file', $event)"
            @create-node="emit('create-node', $event, false)"
            @delete-node="emit('delete-node', $event)"
          />
          <div v-else class="tree-loading">正在读取工作区...</div>
        </div>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.knowledge-tabs {
  grid-template-columns: repeat(6, 1fr) !important;
}
.panel-content-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.knowledge-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.setting-card em {
  margin-left: 6px;
  padding: 1px 4px;
  border-radius: 4px;
  color: var(--accent);
  background: rgba(157, 140, 255, 0.12);
  font-size: 10px;
  font-style: normal;
}
.file-tree-wrapper {
  padding: 4px 0;
  max-height: 520px;
  overflow-y: auto;
}
.tree-loading {
  font-size: 12px;
  color: var(--muted);
  padding: 10px;
  text-align: center;
}
.title-action-btn:hover {
  color: #fff !important;
}
</style>
