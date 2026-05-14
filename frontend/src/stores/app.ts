import { defineStore } from "pinia";
import { ref, watch } from "vue";
import type { Itinerary } from "../types";

export const useAppStore = defineStore("app", () => {
  const activeKey = ref("home");
  const itinerary = ref<Itinerary | null>(null);

  // Persist to sessionStorage
  const savedActiveKey = sessionStorage.getItem("tt_activeKey");
  if (savedActiveKey) activeKey.value = savedActiveKey;

  const savedItinerary = sessionStorage.getItem("tt_itinerary");
  if (savedItinerary) {
    try {
      itinerary.value = JSON.parse(savedItinerary);
    } catch {
      sessionStorage.removeItem("tt_itinerary");
    }
  }

  watch(activeKey, (v) => sessionStorage.setItem("tt_activeKey", v));
  watch(itinerary, (v) => {
    if (v) {
      sessionStorage.setItem("tt_itinerary", JSON.stringify(v));
    } else {
      sessionStorage.removeItem("tt_itinerary");
    }
  }, { deep: true });

  function switchTab(key: string) {
    activeKey.value = key;
  }

  function setItinerary(data: Itinerary) {
    itinerary.value = data;
  }

  function clearItinerary() {
    itinerary.value = null;
    sessionStorage.removeItem("tt_itinerary");
  }

  return { activeKey, itinerary, switchTab, setItinerary, clearItinerary };
});
