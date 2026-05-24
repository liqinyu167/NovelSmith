import { ref, type Ref } from "vue";
import type { KnowledgeTab } from "../types";

const apiBase = "";

// Module-level Singleton States for dynamic knowledge base items
const characters = ref<any[]>([]);
const worldSettings = ref<any[]>([]);
const timeline = ref<string[]>([]);
const chapters = ref<string[]>([]);
const threadCards = ref<any[]>([]);
const outline = ref<any>({ volume: "大纲", chapters: [] });

export function useKnowledge(prompt: Ref<string>, openFile?: (path: string) => void) {
  const activeKnowledgeTab = ref<KnowledgeTab>("characters");
  const selectedCharacterName = ref("林藏");
  const activeTimelineIndex = ref(4);
  const activeChapterIndex = ref(0);
  const outlineCollapsed = ref(false);
  const leftPanelNotice = ref("");
  const bookName = ref("");

  async function loadKnowledge() {
    try {
      const response = await fetch(`${apiBase}/api/workspace/knowledge`);
      if (!response.ok) throw new Error("Load knowledge failed");
      const data = await response.json();
      
      bookName.value = data.bookName || "";
      characters.value = data.characters || [];
      worldSettings.value = data.worldSettings || [];
      timeline.value = data.timeline || [];
      chapters.value = data.chapters || [];
      threadCards.value = data.threadCards || [];
      outline.value = data.outline || { volume: "大纲", chapters: [] };
      
      // Set defaults if data is populated
      if (characters.value.length > 0 && !characters.value.some(c => c.name === selectedCharacterName.value)) {
        selectedCharacterName.value = characters.value[0].name;
      }
    } catch (e) {
      console.error("Failed to load knowledge:", e);
    }
  }

  function selectKnowledgeTab(tab: KnowledgeTab) {
    activeKnowledgeTab.value = tab;
    const labels: Record<KnowledgeTab, string> = {
      characters: "角色",
      world: "世界",
      timeline: "时间",
      threads: "伏笔",
      outline: "大纲",
      files: "文件"
    };
    showLeftPanelNotice(`已切换到${labels[tab]}工作区`);
  }

  function selectCharacter(name: string) {
    selectedCharacterName.value = name;
    showLeftPanelNotice(`已选中角色：${name}`);
    if (openFile) {
      const char = characters.value.find(c => c.name === name);
      if (char && char.path) {
        openFile(char.path);
      } else {
        openFile(`${bookName.value}/knowledge/characters/${name}.md`);
      }
    }
  }

  function selectWorldSetting(title: string) {
    showLeftPanelNotice(`已选中设定：${title}`);
    if (openFile) {
      const setting = worldSettings.value.find(s => s.title === title);
      if (setting && setting.path) {
        openFile(setting.path);
      } else {
        openFile(`${bookName.value}/knowledge/world/${title}.md`);
      }
    }
  }

  function selectTimeline(index: number) {
    activeTimelineIndex.value = index;
    showLeftPanelNotice(`已定位时间线节点：${timeline.value[index]}`);
  }

  function selectChapter(index: number) {
    activeChapterIndex.value = index;
    activeKnowledgeTab.value = "outline";
    showLeftPanelNotice(`已切换章节焦点：${chapters.value[index]}`);
    if (openFile && chapters.value[index]) {
      openFile(`${bookName.value}/chapters/${chapters.value[index]}`);
    }
  }

  function queueKnowledgeAction(action: string) {
    prompt.value = action;
    showLeftPanelNotice("已把操作填入右侧输入框，可直接回车发送");
  }

  function toggleOutlineCollapsed() {
    outlineCollapsed.value = !outlineCollapsed.value;
    showLeftPanelNotice(outlineCollapsed.value ? "章节大纲已折叠" : "章节大纲已展开");
  }

  function showLeftPanelNotice(text: string) {
    leftPanelNotice.value = text;
    window.setTimeout(() => {
      if (leftPanelNotice.value === text) leftPanelNotice.value = "";
    }, 2200);
  }

  return {
    activeKnowledgeTab,
    selectedCharacterName,
    activeTimelineIndex,
    activeChapterIndex,
    outlineCollapsed,
    leftPanelNotice,
    bookName,
    characters,
    worldSettings,
    timeline,
    chapters,
    threadCards,
    outline,
    loadKnowledge,
    selectKnowledgeTab,
    selectCharacter,
    selectWorldSetting,
    selectTimeline,
    selectChapter,
    queueKnowledgeAction,
    toggleOutlineCollapsed,
    showLeftPanelNotice
  };
}
