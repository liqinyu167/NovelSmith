<script setup lang="ts">
defineProps<{
  side: "left" | "right";
  "aria-label": string;
}>();

const emit = defineEmits<{
  (e: "resize-start", side: "left" | "right", event: PointerEvent): void;
}>();
</script>

<template>
  <div
    class="panel-resizer"
    :class="side === 'left' ? 'left-resizer' : 'right-resizer'"
    role="separator"
    :aria-label="$props['aria-label']"
    @pointerdown.prevent="emit('resize-start', side, $event)"
  ></div>
</template>
