<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";
import type { DayPlan, SpotItem } from "../types";
import { useAppStore } from "../stores/app";
import { spotHasCoords } from "../utils";
import { getCityCoords } from "../utils/cities";

const props = defineProps<{
  days: DayPlan[];
}>();

const emit = defineEmits<{
  "marker-click": [spot: SpotItem, dayIndex: number];
}>();

const store = useAppStore();
const AMAP_KEY = import.meta.env.VITE_AMAP_JS_KEY || "";
const AMAP_SECRET = import.meta.env.VITE_AMAP_SECRET || "";
const mapContainer = ref<HTMLDivElement>();
const mapLoaded = ref(false);
const mapError = ref("");
const hasValidCoords = ref(false);
const missingCoordsHint = ref("");

let mapInstance: any = null;
let AMapLib: any = null;

const markerMap = new Map<string, any>();

const DAY_COLORS = [
  "#E74C3C", "#3498DB", "#2ECC71", "#F39C12",
  "#9B59B6", "#1ABC9C", "#E67E22", "#2980B9",
];

function dayColor(dayIndex: number): string {
  return DAY_COLORS[dayIndex % DAY_COLORS.length];
}

function collectValidPoints(): { points: [number, number][]; count: number; total: number } {
  const points: [number, number][] = [];
  let total = 0;
  for (const day of props.days) {
    for (const spot of day.spots) {
      total++;
      if (spotHasCoords(spot)) {
        points.push([spot.location!.lng, spot.location!.lat]);
      }
    }
  }
  return { points, count: points.length, total };
}

function buildInfoContent(spot: SpotItem, dayIdx: number, spotIdx: number): string {
  const imgEl = spot.image_url
    ? `<br/><img src="${spot.image_url}" style="max-width:200px;max-height:150px;margin-top:6px;border-radius:6px" onerror="this.style.display='none'" />`
    : "";
  return `
    <div style="max-width:260px;font-size:13px;line-height:1.6">
      <span style="font-size:11px;color:#999;background:#f0f0f0;padding:1px 6px;border-radius:4px">D${dayIdx + 1} · 第${spotIdx + 1}站</span>
      <br/>
      <strong style="font-size:14px">${spot.name}</strong>
      ${spot.visit_duration ? `<br/>⏱ 建议游玩：${spot.visit_duration}` : ""}
      ${spot.address ? `<br/>📍 ${spot.address}` : ""}
      ${spot.description ? `<br/><span style="color:#666">${spot.description}</span>` : ""}
      ${imgEl}
    </div>`;
}

function buildMarkerContent(spotName: string, dayIdx: number, color: string): string {
  const d = dayIdx + 1;
  return `
    <div style="display:flex;align-items:center;gap:4px;padding:3px 8px;background:${color};color:#fff;border-radius:20px;font-size:11px;white-space:nowrap;cursor:pointer;font-weight:500;box-shadow:0 2px 6px rgba(0,0,0,0.25)">
      <span style="background:rgba(255,255,255,0.25);border-radius:50%;width:16px;height:16px;display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:700">${d}</span>
      ${spotName}
    </div>`;
}

async function initMap() {
  if (!AMAP_KEY) {
    mapError.value = "地图 JS Key 未配置，请在 frontend/.env 中设置 VITE_AMAP_JS_KEY";
    return;
  }
  if (!mapContainer.value) return;

  if (mapInstance) {
    destroyMap();
  }

  try {
    if (AMAP_SECRET) {
      (window as any)._AMapSecurityConfig = {
        securityJsCode: AMAP_SECRET,
      };
    }

    AMapLib = await AMapLoader.load({
      key: AMAP_KEY,
      version: "2.0",
      plugins: ["AMap.Marker", "AMap.Polyline", "AMap.InfoWindow"],
    });

    const { points, total } = collectValidPoints();
    hasValidCoords.value = points.length > 0;
    missingCoordsHint.value = "";

    let center: [number, number] = [116.397, 39.909];
    let zoom = 12;

    if (points.length > 0) {
      const lngs = points.map((p) => p[0]);
      const lats = points.map((p) => p[1]);
      center = [
        (Math.min(...lngs) + Math.max(...lngs)) / 2,
        (Math.min(...lats) + Math.max(...lats)) / 2,
      ];
    } else {
      const dest = store.itinerary?.destination;
      const fallback = dest ? getCityCoords(dest) : null;
      if (fallback) {
        center = fallback;
      }
      if (total > 0) {
        missingCoordsHint.value = `${total} 个景点坐标缺失，地图已定位到城市中心`;
      } else if (props.days.length > 0) {
        missingCoordsHint.value = "暂无景点坐标数据，地图已定位到城市中心";
      }
    }

    mapInstance = new AMapLib.Map(mapContainer.value, {
      zoom,
      center: new AMapLib.LngLat(center[0], center[1]),
    });

    mapLoaded.value = true;
    mapError.value = "";

    mapInstance.on("complete", () => {
      renderTrips();
    });
  } catch (err: any) {
    const msg = err?.message || String(err);
    console.error("[AmapTripMap] 地图加载失败:", msg);
    if (msg.includes("security")) {
      mapError.value = "安全密钥错误，请检查 frontend/.env 中的 VITE_AMAP_SECRET";
    } else if (msg.includes("key") || msg.includes("Key")) {
      mapError.value = "JS Key 无效，请检查 frontend/.env 中的 VITE_AMAP_JS_KEY";
    } else {
      mapError.value = "地图加载失败，请检查网络或高德 JS API Key / 安全密钥是否正确";
    }
  }
}

function renderTrips() {
  if (!mapInstance || !AMapLib) return;

  mapInstance.clearMap();
  markerMap.clear();

  const infoWindow = new AMapLib.InfoWindow({ offset: new AMapLib.Pixel(0, -36) });
  const allPoints: any[] = [];
  let totalValidSpots = 0;

  for (const day of props.days) {
    const color = dayColor(day.day_index);
    const dayPoints: any[] = [];
    let skipped = 0;

    for (let si = 0; si < day.spots.length; si++) {
      const spot = day.spots[si];
      const key = `${day.day_index}-${si}`;

      if (!spotHasCoords(spot)) {
        skipped++;
        continue;
      }

      const pt = new AMapLib.LngLat(spot.location!.lng, spot.location!.lat);
      dayPoints.push(pt);
      allPoints.push(pt);
      totalValidSpots++;

      const marker = new AMapLib.Marker({
        position: pt,
        content: buildMarkerContent(spot.name, day.day_index, color),
        zIndex: 100,
        offset: new AMapLib.Pixel(0, -10),
      });

      marker.on("click", () => {
        infoWindow.setContent(buildInfoContent(spot, day.day_index, si));
        infoWindow.open(mapInstance, marker.getPosition());
        emit("marker-click", spot, day.day_index);
      });

      marker.setMap(mapInstance);
      markerMap.set(key, marker);
    }

    if (skipped > 0) {
      console.warn(
        `[AmapTripMap] D${day.day_index + 1}：${skipped} 个景点坐标缺失，已跳过`
      );
    }

    if (dayPoints.length === 0) {
      console.warn(
        `[AmapTripMap] D${day.day_index + 1}：无有效坐标，不绘制路线`
      );
    } else if (dayPoints.length >= 2) {
      const polyline = new AMapLib.Polyline({
        path: dayPoints,
        strokeColor: color,
        strokeWeight: 5,
        strokeOpacity: 0.65,
        strokeStyle: "solid",
        showDir: true,
        dirColor: color,
      });
      polyline.setMap(mapInstance);
    }
  }

  if (allPoints.length > 0) {
    mapInstance.setFitView(allPoints, false, [70, 70, 70, 70]);
  }
}

function locateSpot(dayIndex: number, spotIndex: number) {
  if (!mapInstance || !AMapLib) return;
  const key = `${dayIndex}-${spotIndex}`;
  const marker = markerMap.get(key);
  if (marker) {
    const pos = marker.getPosition();
    mapInstance.setZoomAndCenter(16, pos);
    marker.emit("click");
  }
}

function destroyMap() {
  if (mapInstance) {
    try { mapInstance.destroy(); } catch (e) { /* ignore */ }
    mapInstance = null;
  }
  markerMap.clear();
  mapLoaded.value = false;
}

watch(
  () => props.days,
  () => {
    if (mapInstance) {
      destroyMap();
      setTimeout(initMap, 150);
    }
  },
  { deep: true }
);

watch(
  () => store.activeKey,
  (key) => {
    if (key === "result") {
      nextTick(() => {
        setTimeout(() => mapInstance?.resize?.(), 300);
      });
    }
  }
);

onMounted(() => {
  nextTick(() => initMap());
});

onUnmounted(() => destroyMap());

defineExpose({ locateSpot, hasValidCoords, missingCoordsHint });
</script>

<template>
  <div class="amap-container">
    <div v-if="mapError" class="map-placeholder map-error">
      <p>{{ mapError }}</p>
    </div>
    <div v-else-if="!mapLoaded && !AMAP_KEY" class="map-placeholder">
      <p>地图 Key 未配置</p>
    </div>
    <div ref="mapContainer" class="map-box"></div>
    <div v-if="missingCoordsHint && !mapError" class="coords-hint">
      ⚠️ {{ missingCoordsHint }}
    </div>
  </div>
</template>

<style scoped>
.amap-container {
  position: relative;
  width: 100%;
  height: 500px;
  border-radius: 14px;
  overflow: hidden;
  background: #f5f5f5;
}
.map-box {
  width: 100%;
  height: 500px;
}
.map-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 500px;
  color: #999;
}
.map-error p {
  color: #ff4d4f;
  font-weight: 500;
  text-align: center;
  padding: 0 24px;
  line-height: 1.6;
}
.coords-hint {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  background: rgba(255, 77, 79, 0.92);
  color: #fff;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  pointer-events: none;
  white-space: nowrap;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .amap-container {
    height: 380px;
    border-radius: 10px;
  }
  .map-box {
    height: 380px;
  }
  .map-placeholder {
    height: 380px;
  }
}
</style>
