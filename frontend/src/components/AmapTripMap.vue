<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";
import type { DayPlan, SpotItem } from "../types";
import { useAppStore } from "../stores/app";
import { spotHasCoords } from "../utils";
import { getCityCoords } from "../utils/cities";
import { fetchAmapKey } from "../services/api";

const props = defineProps<{
  days: DayPlan[];
}>();

const emit = defineEmits<{
  "marker-click": [spot: SpotItem, dayIndex: number];
}>();

const store = useAppStore();
const amapKey = ref("");
const mapError = ref("");
const mapContainer = ref<HTMLDivElement>();
const mapLoaded = ref(false);
const hasValidCoords = ref(false);
const missingCoordsHint = ref("");

let mapInstance: any = null;
let AMapLib: any = null;

// Store marker refs keyed by "dayIndex-spotIndex" for external locate calls
const markerMap = new Map<string, any>();

const DAY_COLORS = [
  "#1677ff", "#52c41a", "#fa8c16", "#eb2f96",
  "#722ed1", "#13c2c2", "#f5222d", "#faad14",
];

function dayColor(dayIndex: number): string {
  return DAY_COLORS[dayIndex % DAY_COLORS.length];
}

/** Collect all valid coordinates from days */
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

/** Build InfoWindow HTML for a spot */
function buildInfoContent(spot: SpotItem): string {
  const missing = !spotHasCoords(spot);
  const imgEl = spot.image_url
    ? `<br/><img src="${spot.image_url}" style="max-width:200px;max-height:150px;margin-top:6px;border-radius:6px" />`
    : "";
  const coordsInfo = missing
    ? `<br/><span style="color:#ff4d4f;font-size:12px">⚠️ 位置信息暂缺</span>`
    : "";
  return `
    <div style="max-width:260px;font-size:13px;line-height:1.6">
      <strong style="font-size:14px">${spot.name}</strong>
      ${spot.visit_duration ? `<br/>⏱ ${spot.visit_duration}` : ""}
      ${spot.description ? `<br/>${spot.description}` : ""}
      ${spot.address ? `<br/>📍 ${spot.address}` : ""}
      ${coordsInfo}
      ${imgEl}
    </div>`;
}

async function initMap() {
  if (!amapKey.value) {
    try {
      amapKey.value = await fetchAmapKey();
    } catch {
      mapError.value = "无法获取地图配置，请检查后端服务是否运行";
      return;
    }
  }
  if (!amapKey.value) {
    mapError.value = "地图 Key 未配置，请在 backend/.env 中设置 AMAP_JS_API_KEY";
    return;
  }
  if (!mapContainer.value) return;

  try {
    AMapLib = await AMapLoader.load({
      key: amapKey.value,
      version: "2.0",
      plugins: ["AMap.Marker", "AMap.Polyline", "AMap.InfoWindow"],
    });

    // Determine initial center
    const { points, total } = collectValidPoints();
    hasValidCoords.value = points.length > 0;
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
      }
    }

    mapInstance = new AMapLib.Map(mapContainer.value, {
      zoom,
      center,
    });

    renderTrips();
    mapLoaded.value = true;
  } catch (err: any) {
    console.error("AMap load failed:", err);
    mapError.value = "地图加载失败，请检查网络或 API Key 是否正确";
  }
}

function renderTrips() {
  if (!mapInstance || !AMapLib) return;

  mapInstance.clearMap();
  markerMap.clear();

  const allMarkers: any[] = [];
  const infoWindow = new AMapLib.InfoWindow({ offset: new AMapLib.Pixel(0, -30) });
  const allPoints: [number, number][] = [];

  for (const day of props.days) {
    const color = dayColor(day.day_index);
    const dayPoints: [number, number][] = [];

    for (let si = 0; si < day.spots.length; si++) {
      const spot = day.spots[si];
      const key = `${day.day_index}-${si}`;
      let lng: number, lat: number;
      let hasCoords = spotHasCoords(spot);

      if (hasCoords) {
        lng = spot.location!.lng;
        lat = spot.location!.lat;
      } else {
        // If no coords, skip drawing marker but still could be listed
        continue;
      }

      const pt: [number, number] = [lng, lat];
      dayPoints.push(pt);
      allPoints.push(pt);

      const content = `
        <div style="padding:4px 10px;background:${color};color:#fff;border-radius:6px;font-size:12px;white-space:nowrap;cursor:pointer;font-weight:500;box-shadow:0 2px 6px rgba(0,0,0,0.2)">
          ${spot.name}
        </div>`;

      const marker = new AMapLib.Marker({
        position: pt,
        content,
        zIndex: 100,
      });

      marker.on("click", () => {
        infoWindow.setContent(buildInfoContent(spot));
        infoWindow.open(mapInstance, marker.getPosition());
        emit("marker-click", spot, day.day_index);
      });

      marker.setMap(mapInstance);
      allMarkers.push(marker);
      markerMap.set(key, marker);
    }

    // Draw polylines
    if (dayPoints.length >= 2) {
      const polyline = new AMapLib.Polyline({
        path: dayPoints,
        strokeColor: color,
        strokeWeight: 4,
        strokeOpacity: 0.6,
        strokeStyle: "solid",
        showDir: true,
      });
      polyline.setMap(mapInstance);
    }
  }

  // Fit view
  if (allPoints.length > 0) {
    mapInstance.setFitView(allPoints, false, [60, 60, 60, 60]);
  }
}

/** Exposed: locate and trigger marker click for a spot */
function locateSpot(dayIndex: number, spotIndex: number) {
  if (!mapInstance || !AMapLib) return;
  const key = `${dayIndex}-${spotIndex}`;
  const marker = markerMap.get(key);
  if (marker) {
    const pos = marker.getPosition();
    mapInstance.setZoomAndCenter(16, pos);
    // Simulate click
    marker.emit("click");
  }
}

function destroyMap() {
  if (mapInstance) {
    mapInstance.destroy();
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
    if (key === "result" && mapInstance) {
      setTimeout(() => mapInstance?.resize?.(), 200);
    }
  }
);

onMounted(() => initMap());
onUnmounted(() => destroyMap());

defineExpose({ locateSpot, hasValidCoords, missingCoordsHint });
</script>

<template>
  <div class="amap-container">
    <div v-if="mapError" class="map-placeholder map-error">
      <p>{{ mapError }}</p>
    </div>
    <div v-else-if="!amapKey" class="map-placeholder">
      <p>正在加载地图配置...</p>
    </div>
    <div v-else ref="mapContainer" class="map-box"></div>
    <div v-if="missingCoordsHint" class="coords-hint">
      ⚠️ {{ missingCoordsHint }}
    </div>
  </div>
</template>

<style scoped>
.amap-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  border-radius: 14px;
  overflow: hidden;
  background: #f5f5f5;
}
.map-box {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
.map-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  color: #999;
}
.map-error p {
  color: #ff4d4f;
  font-weight: 500;
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
</style>
