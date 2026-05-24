<script setup lang="ts">
import { onMounted, nextTick, watch, ref } from "vue";

// Components
import TopBar from "./components/TopBar.vue";
import KnowledgePanel from "./components/KnowledgePanel.vue";
import PanelResizer from "./components/PanelResizer.vue";
import EditorArea from "./components/EditorArea.vue";
import AgentPanel from "./components/AgentPanel.vue";

// Composables
import { useSettings } from "./composables/useSettings";
import { useEditor } from "./composables/useEditor";
import { useChat } from "./composables/useChat";
import { useLayout } from "./composables/useLayout";
import { useAgent } from "./composables/useAgent";
import { useWorkspace } from "./composables/useWorkspace";
import { useKnowledge } from "./composables/useKnowledge";

// Initialize states
const {
  provider,
  projectBrief,
  configOpen,
  providerReady,
  loadSettings
} = useSettings();

const {
  manuscript,
  editorScale,
  paperRef,
  manuscriptRef,
  targetWordCount,
  wordCount,
  progress,
  resizeManuscript,
  handleEditorWheel,
  appendManuscript,
  loadEditor
} = useEditor();

const {
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
  transitionAgent,
  reportAgentState,
  failAgent,
  scrollChat,
  forceScrollChatToBottom,
  loadChat,
  newSession
} = useChat();

const {
  leftPanelWidth,
  rightPanelWidth,
  shellStyle,
  startPanelResize,
  loadLayout
} = useLayout();

// V2 Workspace & Knowledge Manager
const {
  workspaceTree,
  activeFile,
  activeFilePath,
  activeFileContentString,
  isDirty,
  loadWorkspaceTree,
  openFile,
  saveActiveFile,
  createNewFile,
  deleteNode,
  openWorkspaceInExplorer
} = useWorkspace();

const editorAreaRef = ref<any>(null);

async function handleOpenFile(path: string) {
  if (isDirty.value && editorAreaRef.value) {
    try {
      await editorAreaRef.value.saveChanges();
    } catch (e) {
      console.error("Failed to save dirty file before switching:", e);
    }
    isDirty.value = false;
  }
  await openFile(path);
}

const { loadKnowledge, bookName, chapters } = useKnowledge(prompt, handleOpenFile);

// Coordinate agents with V2 Active File awareness
const {
  sendPrompt,
  confirmPendingWrite,
  cancelPendingWrite,
  stopGeneration
} = useAgent({
  provider,
  manuscript,
  projectBrief,
  prompt,
  messages,
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
  transitionAgent,
  reportAgentState,
  failAgent,
  scrollChat,
  forceScrollChatToBottom,
  appendManuscript,
  // Pass active file metadata to agent deps
  activeFilePath,
  activeFileContent: activeFileContentString,
  onWorkspaceModified: () => {
    // LLM update tool result callback, refresh views immediately
    loadWorkspaceTree();
    loadKnowledge();
    if (activeFilePath.value && activeFile.value?.type !== "text") {
      openFile(activeFilePath.value);
    }
  },
  newSession
});

// Watch activeFile to sync to editor's manuscript for co-writing stream
watch(
  () => activeFile.value,
  (newFile) => {
    if (!newFile) {
      manuscript.value = "";
      return;
    }
    if (newFile.type === "text") {
      manuscript.value = newFile.content || "";
    }
  },
  { deep: true }
);

async function handleSaveFile(path: string, content: any) {
  await saveActiveFile(content);
  await loadKnowledge();
}

async function handleCreateNode(parentPath: string, isDirectory: boolean) {
  const typeLabel = isDirectory ? "目录" : "文件";
  const name = window.prompt(`请输入新建${typeLabel}的名称：`);
  if (!name || !name.trim()) return;
  await createNewFile(parentPath, name.trim(), isDirectory);
  loadKnowledge();
}

onMounted(() => {
  loadSettings();
  loadEditor();
  loadChat();
  loadLayout();
  
  // V2 workspace load
  loadWorkspaceTree();
  loadKnowledge();
  
  // Default open first chapter if it exists in layout on start
  setTimeout(() => {
    const book = bookName.value || "雾城档案";
    const firstChapter = chapters.value[0] || "01_第一章：雾中来信.md";
    handleOpenFile(`${book}/chapters/${firstChapter}`);
  }, 600);

  nextTick(() => {
    scrollChat();
    resizeManuscript();
  });
});
</script>

<template>
  <main class="studio-shell" :style="shellStyle">
    <TopBar />

    <KnowledgePanel
      v-model:prompt="prompt"
      :workspace-tree="workspaceTree"
      :active-file-path="activeFilePath"
      @select-file="handleOpenFile"
      @create-node="handleCreateNode"
      @delete-node="deleteNode"
      @open-explorer="openWorkspaceInExplorer"
    />

    <PanelResizer
      side="left"
      aria-label="调整左侧知识库宽度"
      @resize-start="startPanelResize"
    />

    <EditorArea
      ref="editorAreaRef"
      v-model:manuscript="manuscript"
      :editor-scale="editorScale"
      :word-count="wordCount"
      :target-word-count="targetWordCount"
      :active-file="activeFile"
      @editor-wheel="handleEditorWheel"
      @set-paper-ref="paperRef = $event"
      @set-manuscript-ref="manuscriptRef = $event"
      @update-file-content="handleSaveFile"
      @dirty-change="isDirty = $event"
      @open-explorer="openWorkspaceInExplorer"
    />

    <PanelResizer
      side="right"
      aria-label="调整右侧 Agent 宽度"
      @resize-start="startPanelResize"
    />

    <AgentPanel
      v-model:prompt="prompt"
      v-model:config-open="configOpen"
      v-model:provider="provider"
      :messages="messages"
      :agent-state="agentState"
      :active-status="activeStatus"
      :provider-ready="providerReady"
      :is-awaiting-confirm="isAwaitingConfirm"
      :can-send="canSend"
      :is-generating="isGenerating"
      :active-file-path="activeFilePath"
      @send-prompt="sendPrompt"
      @confirm-write="confirmPendingWrite"
      @cancel-write="cancelPendingWrite"
      @stop-generation="stopGeneration"
      @set-chat-log-ref="chatLogRef = $event"
      @new-session="newSession"
    />
  </main>
</template>
