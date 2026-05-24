import { ref, computed, nextTick, watch } from "vue";
import { debounce } from "../lib/debounce";

export function useEditor() {
  const manuscript = ref("");
  const editorScale = ref(1);
  const paperRef = ref<HTMLElement | null>(null);
  const manuscriptRef = ref<HTMLTextAreaElement | null>(null);
  const targetWordCount = 4000;
  const wordCount = computed(() => manuscript.value.replace(/\s/g, "").length);
  const progress = computed(() => Math.min(100, Math.round((wordCount.value / targetWordCount) * 100)));

  const saveManuscript = debounce((value: string) => {
    localStorage.setItem("novelsmith.manuscript", value);
  }, 300);

  async function resizeManuscript() {
    await nextTick();
    if (!manuscriptRef.value) return;
    manuscriptRef.value.style.height = "auto";
    manuscriptRef.value.style.height = `${Math.max(manuscriptRef.value.scrollHeight, 620)}px`;
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

  async function appendManuscript(text: string) {
    manuscript.value += text;
    await resizeManuscript();
    if (paperRef.value) {
      paperRef.value.scrollTop = paperRef.value.scrollHeight;
    }
  }

  function loadEditor() {
    const saved = localStorage.getItem("novelsmith.manuscript");
    const savedScale = localStorage.getItem("novelsmith.editorScale");
    if (saved) manuscript.value = saved;
    if (savedScale) editorScale.value = Number(savedScale);
  }

  watch(manuscript, (v) => {
    saveManuscript(v);
    resizeManuscript();
  });

  watch(editorScale, (v) => {
    localStorage.setItem("novelsmith.editorScale", String(v));
  });

  return {
    manuscript,
    editorScale,
    paperRef,
    manuscriptRef,
    targetWordCount,
    wordCount,
    progress,
    resizeManuscript,
    zoomEditor,
    resetEditorZoom,
    handleEditorWheel,
    handleZoomWheel,
    appendManuscript,
    loadEditor
  };
}
