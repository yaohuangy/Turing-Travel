<script setup lang="ts">
import { onMounted, ref } from "vue";
import { message, Modal } from "ant-design-vue";
import { DeleteOutlined, EyeOutlined, CalendarOutlined } from "@ant-design/icons-vue";
import { listTrips, getTrip, deleteTrip } from "../services/api";
import type { TripSummary } from "../types";
import { useAppStore } from "../stores/app";

const store = useAppStore();

const trips = ref<TripSummary[]>([]);
const loading = ref(false);

async function loadTrips() {
  loading.value = true;
  try {
    trips.value = await listTrips();
  } catch (err: any) {
    message.error("加载历史记录失败");
  } finally {
    loading.value = false;
  }
}

async function handleView(tripId: string) {
  try {
    const data = await getTrip(tripId);
    store.setItinerary(data);
    store.switchTab("result");
  } catch (err: any) {
    message.error("加载行程详情失败");
  }
}

function handleDelete(tripId: string, e: Event) {
  e.stopPropagation();
  Modal.confirm({
    title: "确认删除",
    content: "删除后将无法恢复，确定要删除这个行程吗？",
    okText: "删除",
    okType: "danger",
    cancelText: "取消",
    async onOk() {
      try {
        await deleteTrip(tripId);
        message.success("已删除");
        await loadTrips();
      } catch (err: any) {
        message.error("删除失败");
      }
    },
  });
}

onMounted(loadTrips);
</script>

<template>
  <div class="history-page">
    <div class="history-header">
      <h3>已保存的旅行计划</h3>
      <a-button size="small" @click="loadTrips" :loading="loading">刷新</a-button>
    </div>

    <a-spin :spinning="loading">
      <div v-if="trips.length > 0" class="trip-grid">
        <div
          v-for="trip in trips"
          :key="trip.trip_id"
          class="trip-card"
          @click="handleView(trip.trip_id)"
        >
          <div class="trip-card-inner">
            <div class="card-top">
              <span class="card-city">{{ trip.destination }}</span>
              <a-button
                type="text"
                danger
                size="small"
                shape="circle"
                class="card-delete"
                @click="(e: Event) => handleDelete(trip.trip_id, e)"
              >
                <DeleteOutlined />
              </a-button>
            </div>

            <h4 class="card-title">{{ trip.name }}</h4>

            <div class="card-meta">
              <span><CalendarOutlined /> {{ trip.start_date }} ~ {{ trip.end_date }}</span>
            </div>

            <div class="card-footer">
              <span class="card-budget">¥{{ trip.total_budget }}</span>
              <span class="card-saved">
                保存于 {{ new Date(trip.saved_at).toLocaleDateString() }}
              </span>
            </div>

            <div class="card-action">
              <EyeOutlined /> 查看详情
            </div>
          </div>
        </div>
      </div>

      <a-empty
        v-else
        description="还没有保存过行程"
        style="margin-top: 60px"
      >
        <template #children>
          <a-button type="primary" @click="store.switchTab('home')">
            去规划行程
          </a-button>
        </template>
      </a-empty>
    </a-spin>
  </div>
</template>

<style scoped>
.history-page {
  padding: 8px 0 16px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.history-header h3 {
  margin: 0;
  font-size: 18px;
}

.trip-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.trip-card {
  cursor: pointer;
  transition: all 0.25s ease;
}

.trip-card:hover {
  transform: translateY(-4px);
}

.trip-card-inner {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #eee;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.25s ease;
  position: relative;
  overflow: hidden;
}

.trip-card-inner::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #1a936f, #52c41a, #fa8c16);
  opacity: 0;
  transition: opacity 0.25s;
}

.trip-card:hover .trip-card-inner {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.trip-card:hover .trip-card-inner::before {
  opacity: 1;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-city {
  font-size: 13px;
  font-weight: 600;
  color: #1a936f;
  background: #e8f5e9;
  padding: 2px 10px;
  border-radius: 10px;
}

.card-delete {
  opacity: 0;
  transition: opacity 0.2s;
}

.trip-card:hover .card-delete {
  opacity: 1;
}

.card-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  line-height: 1.4;
}

.card-meta {
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}

.card-budget {
  font-size: 18px;
  font-weight: 700;
  color: #1a936f;
}

.card-saved {
  font-size: 12px;
  color: #bbb;
}

.card-action {
  margin-top: 12px;
  text-align: center;
  color: #1a936f;
  font-size: 13px;
  font-weight: 500;
  opacity: 0;
  transition: opacity 0.25s;
}

.trip-card:hover .card-action {
  opacity: 1;
}

/* Responsive */
@media (max-width: 992px) {
  .trip-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 576px) {
  .trip-grid { grid-template-columns: 1fr; }
}
</style>
