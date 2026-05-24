<script setup lang="ts">
import {
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  ChevronDown,
  BookOpen,
  LayoutGrid,
  Settings,
  Expand,
  Sparkles,
  Tags,
  ListTree,
  PenLine,
  Trash2,
  Plus,
  BookMarked,
  Save,
  FolderOpen
} from "lucide-vue-next";
import { ref, computed, watch, nextTick } from "vue";
import { debounce } from "../lib/debounce";

const props = defineProps<{
  manuscript: string;
  editorScale: number;
  wordCount: number;
  targetWordCount: number;
  activeFile: {
    path: string;
    type: "json" | "text" | "paired";
    content: any;
  } | null;
}>();

const emit = defineEmits<{
  (e: "update:manuscript", value: string): void;
  (e: "editor-wheel", event: WheelEvent): void;
  (e: "set-paper-ref", el: HTMLElement | null): void;
  (e: "set-manuscript-ref", el: HTMLTextAreaElement | null): void;
  (e: "update-file-content", path: string, content: any): void;
  (e: "dirty-change", val: boolean): void;
  (e: "open-explorer"): void;
}>();

// Determine editing mode
const isPairedMode = computed(() => props.activeFile?.type === "paired");
const isOutlineFile = computed(() => props.activeFile?.path === "knowledge/outline.json");
const isTimelineFile = computed(() => props.activeFile?.path === "knowledge/timeline.json");
const isThreadsFile = computed(() => props.activeFile?.path === "knowledge/threads.json");
const isTextMode = computed(() => props.activeFile?.type === "text" || (!props.activeFile && props.manuscript !== undefined));

// Local state for interactive editors
const localManuscript = ref("");
const localPairedJson = ref<any>({});
const localPairedMd = ref("");
const localOutline = ref<any>({ volume: "", chapters: [] });
const localTimeline = ref<string[]>([]);
const localThreads = ref<any[]>([]);

// Dirty states management
const originalContent = ref("");
const isDirty = ref(false);
let isInternalChange = false;

function getCurrentContent() {
  if (isPairedMode.value) {
    return {
      json: localPairedJson.value,
      md: localPairedMd.value
    };
  } else if (isOutlineFile.value) {
    return localOutline.value;
  } else if (isTimelineFile.value) {
    return localTimeline.value;
  } else if (isThreadsFile.value) {
    return localThreads.value;
  } else if (isTextMode.value) {
    return localManuscript.value;
  }
  return null;
}

function getCurrentContentString() {
  const content = getCurrentContent();
  if (content === null) return "";
  if (typeof content === "string") return content;
  return JSON.stringify(content);
}

function updateOriginalContent() {
  originalContent.value = getCurrentContentString();
  isDirty.value = false;
}

// Watch activeFile to populate local states
watch(
  () => props.activeFile,
  (newFile) => {
    if (!newFile) {
      originalContent.value = "";
      isDirty.value = false;
      localManuscript.value = "";
      return;
    }
    isInternalChange = true;
    
    if (newFile.type === "paired") {
      const data = newFile.content || {};
      localPairedJson.value = JSON.parse(JSON.stringify(data.json || {}));
      localPairedMd.value = data.md || "";
    } else if (newFile.path === "knowledge/outline.json") {
      localOutline.value = JSON.parse(JSON.stringify(newFile.content || { volume: "", chapters: [] }));
    } else if (newFile.path === "knowledge/timeline.json") {
      localTimeline.value = JSON.parse(JSON.stringify(newFile.content || []));
    } else if (newFile.path === "knowledge/threads.json") {
      localThreads.value = JSON.parse(JSON.stringify(newFile.content || []));
    } else if (newFile.type === "text") {
      localManuscript.value = newFile.content || "";
    }
    
    nextTick(() => {
      updateOriginalContent();
      isInternalChange = false;
    });
  },
  { immediate: true, deep: true }
);

// Watch local states to check if they are dirty
watch(
  [localPairedJson, localPairedMd, localOutline, localTimeline, localThreads, localManuscript],
  () => {
    if (isInternalChange) return;
    const currentStr = getCurrentContentString();
    // V2.3: Only compute isDirty if we are NOT in manuscript text editing mode
    if (!isTextMode.value) {
      isDirty.value = currentStr !== originalContent.value;
    } else {
      isDirty.value = false;
    }
  },
  { deep: true }
);

// Watch isDirty to tell parent App.vue
watch(isDirty, (newVal) => {
  emit("dirty-change", newVal);
});

// V2.3: Debounced save specifically for manuscript text mode (无感自动保存)
const saveManuscriptDebounced = debounce((val: string) => {
  if (props.activeFile && isTextMode.value) {
    emit("update:manuscript", val);
    emit("update-file-content", props.activeFile.path, val);
    // Silent sync original content
    originalContent.value = val;
  }
}, 500);

// V2.3: Watch manuscript text mode changes to auto-save silently
watch(localManuscript, (newVal) => {
  if (isInternalChange || !isTextMode.value) return;
  saveManuscriptDebounced(newVal);
});

// Watch external manuscript changes (e.g. from Agent co-writing streaming)
watch(
  () => props.manuscript,
  (newVal) => {
    if (isTextMode.value && localManuscript.value !== newVal) {
      isInternalChange = true;
      localManuscript.value = newVal;
      nextTick(() => {
        isInternalChange = false;
        originalContent.value = newVal;
        isDirty.value = false;
      });
    }
  }
);

// Tags processing helper
const localTagsString = computed({
  get() {
    return Array.isArray(localPairedJson.value?.tags) ? localPairedJson.value.tags.join(", ") : "";
  },
  set(val: string) {
    localPairedJson.value.tags = val.split(",").map(t => t.trim()).filter(Boolean);
  }
});

// Outline editor helpers
function removeOutlineChapter(idx: number) {
  localOutline.value.chapters.splice(idx, 1);
}
function addOutlineChapter() {
  localOutline.value.chapters.push(`Chapter ${localOutline.value.chapters.length + 1} 新章节`);
}

// Timeline editor helpers
function removeTimelineNode(idx: number) {
  localTimeline.value.splice(idx, 1);
}
function addTimelineNode() {
  localTimeline.value.push("新时间线事件说明");
}

// Threads editor helpers
function removeThread(idx: number) {
  localThreads.value.splice(idx, 1);
}
function addThread() {
  localThreads.value.push({ title: "新设定伏笔", desc: "点击在此输入未回收伏笔的思考..." });
}

// Helper to determine title in the topbar
const activeFileTitle = computed(() => {
  if (!props.activeFile) return "第一章：雾中来信";
  const parts = props.activeFile.path.split("/");
  const filename = parts[parts.length - 1];
  return filename.replace(/\.(json|md)$/i, "");
});

function saveChanges() {
  if (!props.activeFile) return;
  const content = getCurrentContent();
  
  if (isTextMode.value) {
    emit("update:manuscript", localManuscript.value);
  }
  
  emit("update-file-content", props.activeFile.path, content);
  
  // Reset dirty status
  originalContent.value = getCurrentContentString();
  isDirty.value = false;
}

defineExpose({
  saveChanges
});
</script>

<template>
  <section class="editor-area">
    <!-- Welcome state (No file opened) -->
    <div v-if="!activeFile" class="welcome-card">
      <div class="welcome-container">
        <BookMarked :size="48" class="welcome-icon" />
        <h2>NovelSmith 雾城档案</h2>
        <p>近未来长篇连载悬疑小说写作空间</p>
        <div class="welcome-tips">
          <span>💡 提示：在左侧面板中点击“角色/世界观/大纲”卡片即可在此编辑设定</span>
          <span>📁 你也可以切换到“文件”视图，双击树节点以直接操作底层结构化文件</span>
        </div>
      </div>
    </div>

    <!-- Paired character or world setting editor -->
    <div v-else-if="isPairedMode" class="paired-editor-card">
      <div class="paired-editor-header">
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <span class="file-path-badge">📁 {{ activeFile.path }}</span>
          <button @click="emit('open-explorer')" title="在资源管理器中打开项目" class="header-icon-btn">
            <FolderOpen :size="14" />
          </button>
        </div>
        <h2>{{ activeFileTitle }} 配对设定卡</h2>
      </div>

      <div class="paired-editor-body">
        <!-- Metadata Form (JSON) -->
        <div class="paired-meta-form">
          <div class="form-section-title">📊 结构属性设定 (.json)</div>
          
          <!-- Character specific properties -->
          <div v-if="activeFile.path.includes('characters/')" class="meta-form-grid">
            <div class="form-group">
              <label>姓名</label>
              <input type="text" v-model="localPairedJson.name" placeholder="请输入姓名" />
            </div>
            <div class="form-group">
              <label>身份角色</label>
              <input type="text" v-model="localPairedJson.role" placeholder="主角 / 盟友 / 反派 / 配角" />
            </div>
            <div class="form-group">
              <label>设定分值 (Score: {{ localPairedJson.score ?? 0 }})</label>
              <input type="range" min="0" max="100" v-model.number="localPairedJson.score" />
            </div>
            <div class="form-group">
              <label>主要标签 (以逗号分隔)</label>
              <input type="text" v-model="localTagsString" placeholder="例如: 理性, 执着, 失忆者" />
            </div>
          </div>

          <!-- World settings specific properties -->
          <div v-else class="meta-form-grid">
            <div class="form-group">
              <label>设定标题</label>
              <input type="text" v-model="localPairedJson.title" placeholder="设定名称" />
            </div>
            <div class="form-group">
              <label>设定类型</label>
              <input type="text" v-model="localPairedJson.type" placeholder="例如: 组织 / 道具 / 地理" />
            </div>
          </div>
        </div>

        <!-- Markdown Editor (MD) -->
        <div class="paired-markdown-editor">
          <div class="form-section-title">📝 背景与设定细节描述 (.md)</div>
          <textarea
            v-model="localPairedMd"
            class="markdown-textarea"
            placeholder="在此处输入角色的生平设定、世界观细节特征...支持使用 Markdown 格式。"
          />
        </div>
      </div>
    </div>

    <!-- Visual Editor for outline.json -->
    <div v-else-if="isOutlineFile" class="visual-json-card">
      <div class="visual-json-header">
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <span class="file-path-badge">📋 {{ activeFile.path }}</span>
          <button @click="emit('open-explorer')" title="在资源管理器中打开项目" class="header-icon-btn">
            <FolderOpen :size="14" />
          </button>
        </div>
        <h2>📖 章节大纲可视化编辑器</h2>
      </div>
      <div class="visual-json-body">
        <div class="form-group">
          <label>大纲分卷卷名 (Volume)</label>
          <input type="text" v-model="localOutline.volume" placeholder="输入本卷名称" />
        </div>
        <div class="outline-chapters-container">
          <label>章节编排列表</label>
          <div v-for="(chap, idx) in localOutline.chapters" :key="idx" class="outline-chapter-row">
            <span class="chap-badge">Ch.{{ idx + 1 }}</span>
            <input type="text" v-model="localOutline.chapters[idx]" placeholder="章节名称" />
            <button class="delete-chapter-btn" @click="removeOutlineChapter(idx)"><Trash2 :size="14" /></button>
          </div>
          <button class="add-chapter-btn" @click="addOutlineChapter"><Plus :size="14" /> 追加章节</button>
        </div>
      </div>
    </div>

    <!-- Visual Editor for timeline.json -->
    <div v-else-if="isTimelineFile" class="visual-json-card">
      <div class="visual-json-header">
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <span class="file-path-badge">⏳ {{ activeFile.path }}</span>
          <button @click="emit('open-explorer')" title="在资源管理器中打开项目" class="header-icon-btn">
            <FolderOpen :size="14" />
          </button>
        </div>
        <h2>⌛ 事件时间线可视化编辑器</h2>
      </div>
      <div class="visual-json-body">
        <div class="timeline-nodes-list">
          <div v-for="(node, idx) in localTimeline" :key="idx" class="timeline-node-row">
            <div class="timeline-axis-graph">
              <div class="timeline-axis-dot"></div>
              <div v-if="idx < localTimeline.length - 1" class="timeline-axis-line"></div>
            </div>
            <input type="text" v-model="localTimeline[idx]" placeholder="输入时间刻度或描述事件" />
            <button class="delete-chapter-btn" @click="removeTimelineNode(idx)"><Trash2 :size="14" /></button>
          </div>
          <button class="add-chapter-btn" @click="addTimelineNode"><Plus :size="14" /> 追加事件节点</button>
        </div>
      </div>
    </div>

    <!-- Visual Editor for threads.json -->
    <div v-else-if="isThreadsFile" class="visual-json-card">
      <div class="visual-json-header">
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <span class="file-path-badge">🎯 {{ activeFile.path }}</span>
          <button @click="emit('open-explorer')" title="在资源管理器中打开项目" class="header-icon-btn">
            <FolderOpen :size="14" />
          </button>
        </div>
        <h2>🔱 伏笔追踪可视化编辑器</h2>
      </div>
      <div class="visual-json-body">
        <div class="threads-cards-grid">
          <div v-for="(thread, idx) in localThreads" :key="idx" class="thread-card-editor">
            <div class="thread-card-title-row">
              <input type="text" v-model="thread.title" placeholder="伏笔关键字" />
              <button class="delete-chapter-btn" @click="removeThread(idx)"><Trash2 :size="14" /></button>
            </div>
            <textarea v-model="thread.desc" placeholder="输入关于此伏笔在文中何时埋下、回收的思考..." />
          </div>
          <div class="add-thread-card" @click="addThread">
            <Plus :size="20" />
            <span>添加新伏笔设定</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Standard Text / Manuscript Editor (V1 Editor) -->
    <div v-else-if="isTextMode" class="editor-card">
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
          <button @click="emit('open-explorer')" title="在资源管理器中打开项目"><FolderOpen :size="16" /></button>
          <button><Settings :size="16" /></button>
          <button><Expand :size="16" /></button>
        </div>
      </div>

      <div :ref="(el) => emit('set-paper-ref', el as HTMLElement | null)" class="paper" @wheel="emit('editor-wheel', $event)">
        <div class="chapter-heading">
          <span>Chapters Excerpt</span>
          <h2>{{ activeFileTitle }}</h2>
          <i></i>
          <p>目标 {{ targetWordCount }} 字　/　当前 {{ wordCount }} 字　/　POV：主视角　/　同步状态：实时无感保存</p>
        </div>
        <textarea
          :ref="(el) => emit('set-manuscript-ref', el as HTMLTextAreaElement | null)"
          v-model="localManuscript"
          class="manuscript"
          :style="{ '--editor-scale': editorScale }"
          spellcheck="false"
          placeholder="正文内容保存在工作区。Agent 可以直接在此处为您进行协同续写。"
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

    <!-- V2 Premium Arc Floating Save Changes Button (Only shown in Non-Text Mode) -->
    <transition name="fade-slide">
      <div v-if="isDirty" class="dirty-save-floating-banner">
        <span>⚠️ 检测到未保存的更改</span>
        <button class="save-floating-btn" @click="saveChanges">
          <Save :size="13" /> 确认保存更改
        </button>
      </div>
    </transition>
  </section>
</template>

<style scoped>
/* Welcome Card Styling */
.welcome-card {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: var(--panel-3);
  border-radius: 11px;
  border: 1px solid var(--line);
  box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.2);
}
.welcome-container {
  text-align: center;
  max-width: 460px;
  padding: 24px;
}
.welcome-icon {
  color: var(--accent);
  margin-bottom: 16px;
  filter: drop-shadow(0 0 10px rgba(157, 140, 255, 0.4));
}
.welcome-container h2 {
  font-size: 22px;
  margin: 0 0 8px;
  font-family: "Noto Serif SC", serif;
  color: #fff;
}
.welcome-container p {
  color: var(--muted);
  font-size: 13px;
  margin: 0 0 24px;
}
.welcome-tips {
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--line);
}
.welcome-tips span {
  font-size: 12px;
  line-height: 1.5;
  color: #aeb5be;
}

/* Paired Editor Card */
.paired-editor-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 11px;
  background: var(--panel);
  overflow: hidden;
}
.paired-editor-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  background: rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.file-path-badge {
  font-family: monospace;
  font-size: 11px;
  color: var(--accent);
}
.paired-editor-header h2 {
  font-size: 16px;
  margin: 0;
  color: #fff;
  font-weight: 600;
}
.paired-editor-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.form-section-title {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  font-weight: bold;
  color: var(--green);
  display: flex;
  align-items: center;
  gap: 8px;
}
.paired-meta-form {
  border-bottom: 1px solid var(--line-strong);
}
.meta-form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  padding: 16px 20px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
}
.form-group input[type="text"] {
  border: 1px solid var(--line);
  border-radius: 6px;
  color: #fff;
  background: rgba(0, 0, 0, 0.2);
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}
.form-group input[type="text"]:focus {
  border-color: var(--accent);
}
.form-group input[type="range"] {
  height: 32px;
  accent-color: var(--green);
}
.paired-markdown-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.markdown-textarea {
  flex: 1;
  width: 100%;
  border: 0;
  outline: 0;
  resize: none;
  background: var(--panel-3);
  color: #e2e8f0;
  font-family: "Noto Serif SC", serif;
  font-size: 15px;
  line-height: 1.8;
  padding: 20px;
  overflow-y: auto;
}

/* Visual JSON Card (Outline, Timeline, Threads) */
.visual-json-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 11px;
  background: var(--panel);
  overflow: hidden;
}
.visual-json-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  background: rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.visual-json-header h2 {
  font-size: 16px;
  margin: 0;
  color: #fff;
  font-weight: 600;
}
.visual-json-body {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Outline rows list */
.outline-chapters-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.outline-chapter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.12);
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--line);
}
.chap-badge {
  font-size: 11px;
  font-weight: bold;
  color: var(--accent);
  min-width: 44px;
}
.outline-chapter-row input {
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: #fff;
  font-size: 13px;
  padding: 4px 0;
}
.delete-chapter-btn {
  background: transparent;
  border: 0;
  color: var(--dim);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.delete-chapter-btn:hover {
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.1);
}
.add-chapter-btn {
  border: 1px dashed var(--line-strong);
  color: var(--muted);
  background: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  padding: 8px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s;
}
.add-chapter-btn:hover {
  border-color: var(--accent);
  color: #fff;
  background: rgba(157, 140, 255, 0.05);
}

/* Timeline axis list */
.timeline-nodes-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.timeline-node-row {
  display: flex;
  align-items: center;
  gap: 14px;
  position: relative;
  padding-bottom: 20px;
}
.timeline-axis-graph {
  width: 16px;
  position: absolute;
  top: 0;
  bottom: 0;
  left: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.timeline-axis-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--green);
  border: 2px solid var(--panel);
  z-index: 2;
  margin-top: 14px;
}
.timeline-axis-line {
  flex: 1;
  width: 2px;
  background: var(--line-strong);
  margin-top: -2px;
}
.timeline-node-row input {
  margin-left: 28px;
  flex: 1;
  border: 1px solid var(--line);
  background: rgba(0, 0, 0, 0.15);
  color: #fff;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
}
.timeline-node-row input:focus {
  border-color: var(--green);
}
.timeline-node-row .delete-chapter-btn {
  margin-top: 0;
}

/* Threads Card Grid */
.threads-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.thread-card-editor {
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.2s;
}
.thread-card-editor:focus-within {
  border-color: var(--accent);
}
.thread-card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.thread-card-title-row input {
  font-size: 13px;
  font-weight: bold;
  color: #fff;
  background: transparent;
  border: 0;
  outline: 0;
  flex: 1;
}
.thread-card-editor textarea {
  background: transparent;
  border: 0;
  outline: 0;
  resize: none;
  font-size: 12px;
  color: var(--muted);
  height: 60px;
}
.add-thread-card {
  border: 1px dashed var(--line-strong);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.01);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--muted);
  cursor: pointer;
  min-height: 114px;
  transition: all 0.2s;
}
.add-thread-card:hover {
  border-color: var(--accent);
  color: #fff;
  background: rgba(157, 140, 255, 0.03);
}

/* V2 Premium Arc Floating Save Changes Button */
.dirty-save-floating-banner {
  position: absolute;
  bottom: 26px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 20px;
  border-radius: 30px;
  background: rgba(20, 23, 27, 0.94);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 178, 54, 0.35);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
  z-index: 100;
}

.save-floating-btn {
  background: linear-gradient(135deg, #b6ff92, #8ee66f);
  color: #111;
  border: 0;
  border-radius: 20px;
  padding: 6px 18px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(142, 230, 111, 0.25);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.save-floating-btn:hover {
  transform: scale(1.04);
  box-shadow: 0 6px 16px rgba(142, 230, 111, 0.4);
}

.dirty-save-floating-banner span {
  font-size: 12px;
  color: #ffb236;
  font-weight: 500;
}

/* Vue transitions */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  transform: translate(-50%, 20px);
  opacity: 0;
}

.header-icon-btn {
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.header-icon-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}
</style>
