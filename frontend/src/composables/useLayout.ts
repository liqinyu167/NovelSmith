import { ref, computed, watch } from "vue";

export function useLayout() {
  const leftPanelWidth = ref(384);
  const rightPanelWidth = ref(430);
  const shellStyle = computed(() => ({
    "--left-panel-width": `${leftPanelWidth.value}px`,
    "--right-panel-width": `${rightPanelWidth.value}px`
  }));

  function clampPanelWidth(value: number, min: number, max: number): number {
    if (!Number.isFinite(value)) return min;
    return Math.min(max, Math.max(min, Math.round(value)));
  }

  function maxPanelWidth(limit: number): number {
    return Math.max(72, Math.min(limit, window.innerWidth - 420));
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

  function loadLayout() {
    const savedLeft = localStorage.getItem("novelsmith.leftPanelWidth");
    const savedRight = localStorage.getItem("novelsmith.rightPanelWidth");
    if (savedLeft) leftPanelWidth.value = clampPanelWidth(Number(savedLeft), 72, 900);
    if (savedRight) rightPanelWidth.value = clampPanelWidth(Number(savedRight), 72, 1000);
  }

  watch(leftPanelWidth, (value) => localStorage.setItem("novelsmith.leftPanelWidth", String(value)));
  watch(rightPanelWidth, (value) => localStorage.setItem("novelsmith.rightPanelWidth", String(value)));

  return {
    leftPanelWidth,
    rightPanelWidth,
    shellStyle,
    startPanelResize,
    loadLayout
  };
}
