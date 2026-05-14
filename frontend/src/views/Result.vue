<script setup lang="ts">
import { nextTick, ref } from "vue";
import { message } from "ant-design-vue";
import {
  EnvironmentOutlined,
  ClockCircleOutlined,
  SaveOutlined,
  DownloadOutlined,
  EditOutlined,
  PictureOutlined,
  AimOutlined,
  CarOutlined,
} from "@ant-design/icons-vue";
import type { DayPlan, SpotItem } from "../types";
import { editTrip, saveTrip, exportMarkdownUrl, exportPdfUrl, downloadExportedMarkdown, downloadExportedPdf } from "../services/api";
import AmapTripMap from "../components/AmapTripMap.vue";
import { useAppStore } from "../stores/app";
import { spotHasCoords } from "../utils";

const store = useAppStore();
const collapseKeys = ref<string[]>([]);
const saving = ref(false);
const tripId = ref<string | null>(null);
const navSection = ref("overview");
const highlightedSpot = ref<string | null>(null);
const mapRef = ref<InstanceType<typeof AmapTripMap> | null>(null);

const DAY_COLORS = [
  "#E74C3C", "#3498DB", "#2ECC71", "#F39C12",
  "#9B59B6", "#1ABC9C", "#E67E22", "#2980B9",
];
function dayColor(dayIndex: number): string {
  return DAY_COLORS[dayIndex % DAY_COLORS.length];
}

function weatherIcon(condition: string) {
  if (!condition) return "🌤️";
  const c = condition.toLowerCase();
  if (c.includes("晴")) return "☀️";
  if (c.includes("云") || c.includes("阴")) return "☁️";
  if (c.includes("雨")) return "🌧️";
  if (c.includes("雪")) return "❄️";
  return "🌤️";
}

function getMealLabel(day: DayPlan, type: "breakfast" | "lunch" | "dinner") {
  const meal = day.meals?.find((m) => m.type === type);
  return meal ? meal.name : "—";
}

// ---- Navigation ----
function scrollToSection(id: string) {
  navSection.value = id;
  nextTick(() => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

// ---- Save / Export ----
async function handleSave() {
  const it = store.itinerary;
  if (!it) return;
  saving.value = true;
  try {
    const name = `${it.destination}${it.start_date}~${it.end_date}`;
    const { trip_id } = await saveTrip({
      name,
      destination: it.destination,
      start_date: it.start_date,
      end_date: it.end_date,
      itinerary: it,
    });
    tripId.value = trip_id;
    message.success("行程已保存！");
    store.switchTab("history");
  } catch (err: any) {
    message.error(err?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

function handleExportMarkdown() {
  const it = store.itinerary;
  if (!it) return;
  if (tripId.value) {
    window.open(exportMarkdownUrl(tripId.value), "_blank");
  } else {
    downloadExportedMarkdown(it);
  }
}

function handleExportPdf() {
  const it = store.itinerary;
  if (!it) return;
  if (tripId.value) {
    window.open(exportPdfUrl(tripId.value), "_blank");
  } else {
    downloadExportedPdf(it);
  }
}

// ---- Edit modal ----
const editVisible = ref(false);
const editing = ref(false);
const editDayIndex = ref(0);
const editInstruction = ref("");

function handleEdit(dayIndex: number) {
  editDayIndex.value = dayIndex;
  editInstruction.value = "";
  editVisible.value = true;
}

async function handleEditSubmit() {
  if (!editInstruction.value.trim()) { message.warning("请输入修改指令"); return; }
  const id = tripId.value;
  if (!id) { message.warning("请先保存行程再编辑"); return; }
  editing.value = true;
  try {
    const updated = await editTrip(id, editDayIndex.value, editInstruction.value.trim());
    store.setItinerary(updated);
    message.success("编辑成功！");
    editVisible.value = false;
  } catch (err: any) {
    message.error(err?.response?.data?.detail || "编辑失败");
  } finally {
    editing.value = false;
  }
}

// ---- Marker / Spot list / Point-detail interaction ----
function onMarkerClick(spot: SpotItem, dayIndex: number) {
  const day = store.itinerary?.days?.[dayIndex];
  if (!day) return;
  const spotIndex = day.spots.findIndex((s) => s.name === spot.name);
  highlightAndScroll(dayIndex, spotIndex);
}

function highlightAndScroll(dayIndex: number, spotIndex: number) {
  const key = `${dayIndex}-${spotIndex}`;
  highlightedSpot.value = key;
  setTimeout(() => { highlightedSpot.value = null; }, 3000);

  // Expand day panel
  const dayKey = String(dayIndex);
  if (!collapseKeys.value.includes(dayKey)) {
    collapseKeys.value = [...collapseKeys.value, dayKey];
  }

  // Scroll left panel spot card into view
  nextTick(() => {
    const el = document.getElementById(`spot-${dayIndex}-${spotIndex}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  // Scroll right panel point-detail item into view
  nextTick(() => {
    const el = document.getElementById(`pd-${dayIndex}-${spotIndex}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
}

function handleLocateSpot(dayIndex: number, spotIndex: number) {
  mapRef.value?.locateSpot(dayIndex, spotIndex);
  highlightAndScroll(dayIndex, spotIndex);
}

function handlePointDetailClick(dayIndex: number, spotIndex: number) {
  handleLocateSpot(dayIndex, spotIndex);
}

// ---- Budget ----
function getBudgetItems(it: any) {
  if (!it?.budget) return [];
  return [
    { label: "交通", value: it.budget.transportation, color: "#1a936f" },
    { label: "住宿", value: it.budget.accommodation, color: "#52c41a" },
    { label: "餐饮", value: it.budget.meals, color: "#fa8c16" },
    { label: "门票", value: it.budget.tickets, color: "#eb2f96" },
    { label: "其他", value: it.budget.other, color: "#722ed1" },
  ];
}

function maxBudget(items: { value: number }[]) {
  return Math.max(...items.map((x) => x.value), 1);
}

const budgetCols = [
  { title: "项目", dataIndex: "label", key: "label" },
  { title: "金额", dataIndex: "value", key: "value", align: "right" as const,
    customRender: ({ text }: any) => `¥${text}` },
];
</script>

<template>
  <div class="result-page">
    <div v-if="store.itinerary">
      <!-- Header -->
      <div id="overview" class="result-header">
        <div class="header-info">
          <h2>📍 {{ store.itinerary.destination }}</h2>
          <span class="header-dates">{{ store.itinerary.start_date }} ~ {{ store.itinerary.end_date }}</span>
          <div class="header-stats">
            <a-tag color="green">{{ store.itinerary.days.length }} 天行程</a-tag>
            <a-tag color="blue">{{ store.itinerary.days.reduce((acc, d) => acc + (d.spots?.length || 0), 0) }} 个景点</a-tag>
            <a-tag color="orange">¥{{ store.itinerary.budget.total }} 预算</a-tag>
          </div>
        </div>
        <a-space wrap>
          <a-button type="primary" :loading="saving" @click="handleSave">
            <SaveOutlined /> 保存
          </a-button>
          <a-button @click="handleExportMarkdown"><DownloadOutlined /> MD</a-button>
          <a-button @click="handleExportPdf"><DownloadOutlined /> PDF</a-button>
        </a-space>
      </div>

      <!-- Navigation bar -->
      <div class="nav-bar">
        <a-segmented
          v-model:value="navSection"
          :options="[
            { label: '📋 行程概览', value: 'overview' },
            { label: '📅 每日行程', value: 'daily' },
            { label: '💰 预算明细', value: 'budget' },
          ]"
          block
          size="large"
          @change="(val: string) => scrollToSection(val)"
        />
      </div>

      <!-- Content row: left 60% itinerary, right 40% map + point-detail -->
      <a-row :gutter="16" class="content-row">
        <!-- Left: daily itinerary -->
        <a-col :xs="24" :lg="14">
          <div id="daily" class="section-anchor"></div>
          <a-collapse
            v-model:activeKey="collapseKeys"
            class="day-collapse"
            :bordered="false"
          >
            <a-collapse-panel
              v-for="day in store.itinerary.days"
              :key="String(day.day_index)"
              class="day-panel"
            >
              <template #header>
                <div class="day-header">
                  <span class="day-badge">D{{ day.day_index + 1 }}</span>
                  <span class="day-date">{{ day.date }}</span>
                  <span v-if="day.weather" class="day-weather-badge">
                    {{ weatherIcon(day.weather.condition) }}
                    {{ day.weather.temp_low }}° ~ {{ day.weather.temp_high }}°
                  </span>
                  <span class="day-spot-count">{{ day.spots?.length || 0 }} 个景点</span>
                </div>
              </template>

              <template #extra>
                <a-button size="small" type="text" @click.stop="handleEdit(day.day_index)" class="edit-day-btn">
                  <EditOutlined />
                </a-button>
              </template>

              <div class="day-content">
                <div class="spots-list">
                  <div
                    v-for="(spot, si) in day.spots"
                    :key="spot.name || si"
                    :id="`spot-${day.day_index}-${si}`"
                    :class="['spot-card', {
                      'spot-highlighted': highlightedSpot === `${day.day_index}-${si}`
                    }]"
                  >
                    <div class="spot-image-placeholder">
                      <PictureOutlined />
                    </div>
                    <div class="spot-info">
                      <div class="spot-title">
                        <EnvironmentOutlined style="color:#1a936f;margin-right:4px" />
                        <strong>{{ spot.name }}</strong>
                        <a-tag v-if="spot.visit_duration" color="green" size="small">
                          <ClockCircleOutlined /> {{ spot.visit_duration }}
                        </a-tag>
                        <a-tag v-if="!spotHasCoords(spot)" color="red" size="small">无坐标</a-tag>
                      </div>
                      <p v-if="spot.description" class="spot-desc">{{ spot.description }}</p>
                      <span v-if="spot.address" class="spot-addr">📍 {{ spot.address }}</span>
                    </div>
                    <div class="spot-actions">
                      <a-tooltip title="在地图中定位">
                        <a-button
                          size="small"
                          shape="circle"
                          :disabled="!spotHasCoords(spot)"
                          @click.stop="handleLocateSpot(day.day_index, si)"
                        >
                          <AimOutlined />
                        </a-button>
                      </a-tooltip>
                    </div>
                  </div>
                </div>

                <a-divider style="margin:12px 0" />
                <div class="meals-strip">
                  <a-tag color="blue">🍳 {{ getMealLabel(day, 'breakfast') }}</a-tag>
                  <a-tag color="orange">🍜 {{ getMealLabel(day, 'lunch') }}</a-tag>
                  <a-tag color="purple">🍲 {{ getMealLabel(day, 'dinner') }}</a-tag>
                </div>
                <div v-if="day.hotel" class="hotel-line">
                  🏨 <strong>{{ day.hotel.name }}</strong>
                  <span v-if="day.hotel.location"> · {{ day.hotel.location }}</span>
                  <a-tag v-if="day.hotel.estimated_price" color="gold">¥{{ day.hotel.estimated_price }}/晚</a-tag>
                </div>
                <div v-if="day.route_estimate" class="route-line">
                  <a-tag color="green">
                    🚗 {{ day.route_estimate.distance_km }} km / {{ day.route_estimate.duration_min }} min
                  </a-tag>
                </div>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </a-col>

        <!-- Right: map + point-detail list -->
        <a-col :xs="24" :lg="10">
          <div class="right-panel">
            <!-- Map -->
            <div class="map-wrapper">
              <AmapTripMap
                ref="mapRef"
                :days="store.itinerary.days"
                class="map-card"
                @marker-click="onMarkerClick"
              />
            </div>

            <!-- Point detail list -->
            <div class="point-detail-panel">
              <div class="pd-title">📍 点位明细</div>
              <div class="pd-list">
                <template v-for="day in store.itinerary.days" :key="'pd-day-' + day.day_index">
                  <div class="pd-day-header" :style="{ color: dayColor(day.day_index) }">
                    <span class="pd-day-dot" :style="{ background: dayColor(day.day_index) }"></span>
                    D{{ day.day_index + 1 }} · {{ day.date }}
                  </div>
                  <div
                    v-for="(spot, si) in day.spots"
                    :key="'pd-' + day.day_index + '-' + si"
                    :id="`pd-${day.day_index}-${si}`"
                    :class="['pd-item', {
                      'pd-item-active': highlightedSpot === `${day.day_index}-${si}`,
                      'pd-item-nocoord': !spotHasCoords(spot),
                    }]"
                    @click="handlePointDetailClick(day.day_index, si)"
                  >
                    <div class="pd-item-left">
                      <div class="pd-item-name">
                        <span class="pd-item-num" :style="{ background: dayColor(day.day_index) }">{{ si + 1 }}</span>
                        {{ spot.name }}
                      </div>
                      <div v-if="spot.address" class="pd-item-addr">📍 {{ spot.address }}</div>
                      <div v-else class="pd-item-addr pd-no-addr">暂无地址信息</div>
                    </div>
                    <div class="pd-item-right">
                      <div v-if="day.route_estimate" class="pd-item-traffic">
                        <CarOutlined />
                        <span>{{ day.route_estimate.distance_km }}km</span>
                        <span>{{ day.route_estimate.duration_min }}min</span>
                      </div>
                      <div v-else class="pd-item-traffic pd-no-traffic">—</div>
                      <a-button
                        size="small"
                        type="text"
                        :disabled="!spotHasCoords(spot)"
                        class="pd-locate-btn"
                        @click.stop="handleLocateSpot(day.day_index, si)"
                      >
                        <AimOutlined />
                      </a-button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </a-col>
      </a-row>

      <!-- Budget -->
      <div id="budget" class="section-anchor"></div>
      <a-card title="💰 预算明细" class="budget-card" :body-style="{ padding: '20px 24px' }">
        <a-row :gutter="24">
          <a-col :xs="24" :md="12">
            <a-table
              :columns="budgetCols"
              :data-source="getBudgetItems(store.itinerary)"
              :pagination="false"
              size="small"
              row-key="label"
            >
              <template #footer>
                <div style="text-align:right;font-weight:700;font-size:15px">
                  总计：<span style="color:#1a936f">¥{{ store.itinerary.budget.total }}</span>
                </div>
              </template>
            </a-table>
          </a-col>
          <a-col :xs="24" :md="12">
            <div class="budget-chart">
              <div v-for="item in getBudgetItems(store.itinerary)" :key="item.label" class="bar-row">
                <span class="bar-label">{{ item.label }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    :style="{
                      width: (item.value / maxBudget(getBudgetItems(store.itinerary))) * 100 + '%',
                      background: item.color,
                    }"
                  />
                </div>
                <span class="bar-val">¥{{ item.value }}</span>
              </div>
            </div>
          </a-col>
        </a-row>
      </a-card>

      <!-- Edit Modal -->
      <a-modal
        v-model:open="editVisible"
        title="✏️ 编辑行程"
        :confirm-loading="editing"
        ok-text="提交修改"
        cancel-text="取消"
        @ok="handleEditSubmit"
      >
        <p style="margin-bottom:8px">正在编辑 <strong>第 {{ editDayIndex + 1 }} 天</strong></p>
        <a-textarea
          v-model:value="editInstruction"
          placeholder="描述你想怎么修改这一天，例如：
• 把午餐换成火锅
• 下午加一个博物馆
• 删除第三个景点"
          :rows="4"
          :disabled="editing"
        />
      </a-modal>
    </div>

    <a-empty v-else description="暂无行程数据，请先生成行程" style="margin-top:60px" />
  </div>
</template>

<style scoped>
.result-page { padding: 8px 0 16px; }

/* Header */
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #f0faf5, #e8f5e9);
  border-radius: 14px;
}
.header-info h2 { margin: 0 0 6px; font-size: 22px; }
.header-dates { color: #666; font-size: 14px; display: block; }
.header-stats { margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap; }

/* Navigation */
.nav-bar {
  margin-bottom: 16px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: #fff;
  padding: 8px 0;
}
.section-anchor { scroll-margin-top: 80px; }
.content-row { margin-bottom: 16px; }

/* Left: day panels */
.day-collapse { background: transparent; }
.day-panel {
  margin-bottom: 10px !important;
  border-radius: 12px !important;
  overflow: hidden;
  border: 1px solid #eee !important;
  transition: box-shadow 0.2s;
}
.day-panel:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.day-header { display: flex; align-items: center; gap: 10px; flex: 1; }
.day-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 32px; height: 32px; background: #1a936f; color: #fff;
  border-radius: 8px; font-weight: 700; font-size: 13px;
}
.day-date { color: #888; font-size: 13px; }
.day-weather-badge { font-size: 12px; background: #e6f7ff; color: #1677ff; padding: 2px 8px; border-radius: 10px; }
.day-spot-count { font-size: 12px; color: #aaa; margin-left: auto; }
.edit-day-btn { opacity: 0.5; transition: opacity 0.2s; }
.day-panel:hover .edit-day-btn { opacity: 1; }
.day-content { padding: 4px 0; }

/* Spot cards */
.spots-list { scroll-margin-top: 60px; }
.spot-card {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 10px; margin-bottom: 8px;
  background: #fafafa; border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  scroll-margin-top: 80px;
}
.spot-card:hover { background: #f5f5f5; }
.spot-highlighted {
  background: #e6f7ff !important;
  border-color: #1677ff !important;
  box-shadow: 0 0 0 3px rgba(22,119,255,0.15);
}
.spot-image-placeholder {
  flex-shrink: 0; width: 60px; height: 60px;
  background: #f0f0f0; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; color: #ccc;
}
.spot-info { flex: 1; min-width: 0; }
.spot-title { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
.spot-desc { color: #666; font-size: 13px; margin: 2px 0; }
.spot-addr { color: #999; font-size: 12px; }
.spot-actions {
  flex-shrink: 0; display: flex; align-items: center;
  opacity: 0; transition: opacity 0.2s;
}
.spot-card:hover .spot-actions { opacity: 1; }

/* Meals / Hotel / Route */
.meals-strip { display: flex; gap: 8px; flex-wrap: wrap; }
.hotel-line { margin-top: 8px; font-size: 13px; }
.route-line { margin-top: 6px; }

/* Right panel */
.right-panel {
  position: sticky;
  top: 60px;
}
.map-wrapper {
  margin-bottom: 12px;
}
.map-card {
  height: 400px;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 2px 16px rgba(0,0,0,0.06);
  border: 1px solid #eee;
}

/* Point detail panel */
.point-detail-panel {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #eee;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  overflow: hidden;
}
.pd-title {
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}
.pd-list {
  max-height: 380px;
  overflow-y: auto;
  padding: 4px 0;
}
.pd-day-header {
  padding: 10px 16px 4px;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}
.pd-day-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.pd-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
  border-left: 3px solid transparent;
  scroll-margin-top: 60px;
}
.pd-item:hover {
  background: #f5f7fa;
}
.pd-item-active {
  background: #e6f7ff !important;
  border-left-color: #1677ff !important;
}
.pd-item-nocoord {
  opacity: 0.55;
}
.pd-item-left {
  flex: 1;
  min-width: 0;
}
.pd-item-name {
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}
.pd-item-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.pd-item-addr {
  font-size: 11px;
  color: #999;
  margin-left: 24px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pd-no-addr {
  font-style: italic;
  color: #ccc;
}
.pd-item-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  margin-left: 8px;
}
.pd-item-traffic {
  font-size: 11px;
  color: #1a936f;
  display: flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}
.pd-no-traffic {
  color: #ccc;
}
.pd-locate-btn {
  opacity: 0;
  transition: opacity 0.15s;
}
.pd-item:hover .pd-locate-btn {
  opacity: 1;
}

/* Budget */
#budget.section-anchor { scroll-margin-top: 80px; }
.budget-card { border-radius: 14px; margin-top: 16px; }
.budget-chart { padding: 8px 0; }
.bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.bar-label { min-width: 40px; font-size: 13px; color: #555; }
.bar-track { flex: 1; height: 18px; background: #f0f0f0; border-radius: 9px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 9px; transition: width 0.4s ease; }
.bar-val { min-width: 60px; text-align: right; font-size: 13px; font-weight: 500; }

/* Responsive */
@media (max-width: 1200px) {
  .pd-list { max-height: 280px; }
}
@media (max-width: 992px) {
  .right-panel { position: static; margin-top: 16px; }
  .map-card { height: 350px; }
  .pd-list { max-height: 300px; }
}
</style>
