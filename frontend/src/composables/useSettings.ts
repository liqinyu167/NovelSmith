import { ref, computed, watch } from "vue";
import type { ProviderConfig } from "../types";

export function useSettings() {
  const provider = ref<ProviderConfig>({
    base_url: "https://opencode.ai/zen/go/v1",
    model: "deepseek-v4-flash",
    api_key: ""
  });
  const projectBrief = ref("长篇连载悬疑小说。近未来都市，主线围绕雾城档案、失忆调查员与灰塔组织展开。");
  const configOpen = ref(false);
  const providerReady = computed(
    () =>
      Boolean(
        provider.value.base_url.trim() &&
        provider.value.model.trim() &&
        provider.value.api_key.trim()
      )
  );

  function loadSettings() {
    const savedProvider = localStorage.getItem("novelsmith.provider");
    const savedBrief = localStorage.getItem("novelsmith.projectBrief");
    if (savedProvider) provider.value = JSON.parse(savedProvider);
    if (savedBrief) projectBrief.value = savedBrief;
  }

  watch(
    provider,
    (value) => localStorage.setItem("novelsmith.provider", JSON.stringify(value)),
    { deep: true }
  );
  watch(projectBrief, (value) => localStorage.setItem("novelsmith.projectBrief", value));

  return {
    provider,
    projectBrief,
    configOpen,
    providerReady,
    loadSettings
  };
}
