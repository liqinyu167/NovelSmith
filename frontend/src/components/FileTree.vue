<script setup lang="ts">
import { ref } from "vue";
import { Folder, FolderOpen, FileText, Plus, Trash2 } from "lucide-vue-next";
import type { WorkspaceNode } from "../types";

const props = defineProps<{
  node: WorkspaceNode;
  activePath?: string;
}>();

const emit = defineEmits<{
  (e: "select-file", path: string): void;
  (e: "create-node", parentPath: string, isDirectory: boolean): void;
  (e: "delete-node", path: string): void;
}>();

const expanded = ref(false);

function toggleExpanded() {
  if (props.node.type === "directory") {
    expanded.value = !expanded.value;
  }
}

function handleNodeClick() {
  if (props.node.type === "file") {
    emit("select-file", props.node.path);
  } else {
    toggleExpanded();
  }
}
</script>

<template>
  <div class="file-tree-node">
    <div
      class="node-row"
      :class="{
        'is-active': activePath === node.path,
        'is-directory': node.type === 'directory'
      }"
      @click="handleNodeClick"
    >
      <span class="icon-holder">
        <template v-if="node.type === 'directory'">
          <FolderOpen v-if="expanded" :size="16" />
          <Folder v-else :size="16" />
        </template>
        <template v-else>
          <FileText :size="15" />
        </template>
      </span>
      <span class="node-name">{{ node.name }}</span>

      <!-- Actions -->
      <span class="node-actions" @click.stop>
        <button
          v-if="node.type === 'directory'"
          title="新建文件"
          @click="emit('create-node', node.path, false)"
        >
          <Plus :size="13" />
        </button>
        <button
          v-if="node.path !== '' && node.path !== 'chapters' && node.path !== 'knowledge'"
          class="delete-btn"
          title="删除"
          @click="emit('delete-node', node.path)"
        >
          <Trash2 :size="13" />
        </button>
      </span>
    </div>

    <!-- Recursive children -->
    <div v-if="node.type === 'directory' && expanded" class="node-children">
      <FileTree
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :active-path="activePath"
        @select-file="emit('select-file', $event)"
        @create-node="emit('create-node', $event, false)"
        @delete-node="emit('delete-node', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.file-tree-node {
  font-size: 13px;
  color: var(--text);
}

.node-row {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  gap: 8px;
  transition: background 0.2s;
  position: relative;
}

.node-row:hover {
  background: rgba(255, 255, 255, 0.05);
}

.node-row.is-active {
  background: rgba(157, 140, 255, 0.15);
  color: var(--accent);
  font-weight: 500;
}

.icon-holder {
  display: flex;
  align-items: center;
  color: var(--muted);
}

.is-active .icon-holder {
  color: var(--accent);
}

.node-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-actions {
  display: none;
  align-items: center;
  gap: 4px;
}

.node-row:hover .node-actions {
  display: flex;
}

.node-actions button {
  background: transparent;
  border: none;
  color: var(--muted);
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-actions button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text);
}

.node-actions button.delete-btn:hover {
  color: #ff6b6b;
}

.node-children {
  padding-left: 16px;
  border-left: 1px solid rgba(255, 255, 255, 0.05);
  margin-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
