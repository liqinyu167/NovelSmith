import { ref, computed } from "vue";
import type { WorkspaceNode } from "../types";

const apiBase = "";

export function useWorkspace() {
  const workspaceTree = ref<WorkspaceNode | null>(null);
  const activeFile = ref<{ path: string; type: "json" | "text" | "paired"; content: any } | null>(null);
  const isDirty = ref(false);

  const activeFilePath = computed(() => activeFile.value?.path || "");
  
  const activeFileContentString = computed(() => {
    if (!activeFile.value) return "";
    if (activeFile.value.type === "json") {
      return JSON.stringify(activeFile.value.content, null, 2);
    }
    // For paired files, activeFile.content has { json, md }. We stringify the whole pair so agent sees all
    if (activeFile.value.type === "paired") {
      return JSON.stringify(activeFile.value.content, null, 2);
    }
    return activeFile.value.content;
  });

  async function loadWorkspaceTree() {
    try {
      const response = await fetch(`${apiBase}/api/workspace/tree`);
      if (!response.ok) throw new Error("Load tree failed");
      workspaceTree.value = (await response.json()) as WorkspaceNode;
    } catch (e) {
      console.error("Failed to load workspace tree:", e);
    }
  }

  async function openFile(path: string) {
    try {
      const response = await fetch(`${apiBase}/api/workspace/file?path=${encodeURIComponent(path)}`);
      if (!response.ok) throw new Error("Load file failed");
      const fileData = (await response.json()) as { path: string; type: "json" | "text" | "paired"; content: any };
      activeFile.value = fileData;
      isDirty.value = false;
    } catch (e) {
      console.error(`Failed to open file ${path}:`, e);
    }
  }

  async function saveActiveFile(newContent: any) {
    if (!activeFile.value) return;
    try {
      activeFile.value.content = newContent;

      let contentStr = newContent;
      // If it is paired or json, stringify it
      if (activeFile.value.type === "json" || activeFile.value.type === "paired") {
        contentStr = JSON.stringify(newContent, null, 2);
      }

      const response = await fetch(`${apiBase}/api/workspace/file`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: activeFile.value.path,
          content: contentStr
        })
      });
      if (!response.ok) throw new Error("Save file failed");
      isDirty.value = false;
    } catch (e) {
      console.error("Failed to save active file:", e);
    }
  }

  async function createNewFile(parentPath: string, name: string, isDirectory = false) {
    try {
      const slash = parentPath ? "/" : "";
      const path = `${parentPath}${slash}${name}`;
      
      const response = await fetch(`${apiBase}/api/workspace/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path,
          is_directory: isDirectory,
          content: isDirectory ? "" : (name.endsWith(".json") ? "{}" : "")
        })
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Create failed");
      }
      
      await loadWorkspaceTree();
      
      if (!isDirectory) {
        await openFile(path);
      }
    } catch (e) {
      console.error("Failed to create new item:", e);
      alert(e instanceof Error ? e.message : "创建失败");
    }
  }

  async function deleteNode(path: string) {
    if (!confirm(`确定要删除吗？\n路径: ${path}`)) return;
    try {
      const response = await fetch(`${apiBase}/api/workspace/file?path=${encodeURIComponent(path)}`, {
        method: "DELETE"
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Delete failed");
      }
      
      if (activeFile.value?.path === path) {
        activeFile.value = null;
        isDirty.value = false;
      }
      
      await loadWorkspaceTree();
    } catch (e) {
      console.error("Failed to delete node:", e);
      alert(e instanceof Error ? e.message : "删除失败");
    }
  }

  async function openWorkspaceInExplorer() {
    try {
      const response = await fetch(`${apiBase}/api/workspace/open-explorer`, {
        method: "POST"
      });
      if (!response.ok) throw new Error("Open explorer failed");
    } catch (e) {
      console.error("Failed to open workspace in explorer:", e);
    }
  }

  return {
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
  };
}
