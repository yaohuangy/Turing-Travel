<script setup lang="ts">
import { ref } from "vue";
import { message } from "ant-design-vue";
import {
  SearchOutlined,
  CalendarOutlined,
  TeamOutlined,
  EditOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons-vue";
import { generateTrip, isTimeoutError } from "../services/api";
import type { TripRequest } from "../types";
import { useAppStore } from "../stores/app";
import { CITIES } from "../utils/cities";

const store = useAppStore();

const destination = ref("");
const dateRange = ref<[string, string] | null>(null);
const budgetLevel = ref<"economy" | "comfort" | "luxury">("comfort");
const travelers = ref(2);
const preferences = ref<string[]>([]);
const extraRequirements = ref("");
const loading = ref(false);

const cityOptions = CITIES.map((c) => ({ value: c.name }));

const preferenceOptions = [
  { label: "🌲 自然风光", value: "自然风光" },
  { label: "📜 历史文化", value: "历史文化" },
  { label: "🍜 美食探店", value: "美食探店" },
  { label: "👨‍👩‍👧 亲子乐园", value: "亲子乐园" },
  { label: "🏖️ 休闲度假", value: "休闲度假" },
  { label: "🏔️ 户外运动", value: "户外运动" },
];

function disabledDate(current: any) {
  return current && current.isBefore(new Date(), "day");
}

async function handleSubmit() {
  console.log("[Home] handleSubmit called");

  if (!destination.value.trim()) {
    message.warning("请输入目的地");
    return;
  }
  if (!dateRange.value || dateRange.value.length !== 2) {
    message.warning("请选择出发和结束日期");
    return;
  }

  loading.value = true;
  const request: TripRequest = {
    destination: destination.value.trim(),
    start_date: dateRange.value[0],
    end_date: dateRange.value[1],
    budget_level: budgetLevel.value,
    travelers: travelers.value,
    preferences: preferences.value,
    extra_requirements: extraRequirements.value || null,
  };

  console.log("[Home] POST /api/trip/generate body:", JSON.stringify(request, null, 2));

  try {
    const response = await generateTrip(request);
    console.log("[Home] generateTrip response:", response);
    store.setItinerary(response.itinerary);
    message.success("行程生成成功！");
    store.switchTab("result");
  } catch (err: any) {
    console.error("[Home] generateTrip error:", err);
    if (isTimeoutError(err)) {
      message.error("行程生成超时，请重试（LLM 处理较慢，建议减少天数或简化需求）", 5);
    } else if (err?.response?.data?.detail) {
      message.error(err.response.data.detail);
    } else if (err?.message) {
      message.error(`网络错误: ${err.message}`);
    } else {
      message.error("生成失败，请重试");
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="home-page">
    <!-- Hero section -->
    <div class="hero-banner">
      <p class="hero-text">填写以下信息，AI 将为您生成专属旅行计划</p>
    </div>

    <a-card class="form-card" :body-style="{ padding: '32px' }">
      <a-form layout="vertical">
        <!-- Destination -->
        <a-form-item label="目的地" required>
          <a-auto-complete
            v-model:value="destination"
            :options="cityOptions"
            placeholder="输入目的地城市，如：大理、三亚、成都"
            size="large"
            style="width: 100%"
            :filter-option="(input: string, option: any) =>
              option.value.toLowerCase().includes(input.toLowerCase())"
          >
            <template #prefix>
              <SearchOutlined style="color: #1a936f" />
            </template>
          </a-auto-complete>
        </a-form-item>

        <!-- Date range -->
        <a-form-item label="出发 / 结束日期" required>
          <a-range-picker
            v-model:value="dateRange"
            :disabled-date="disabledDate"
            style="width: 100%"
            size="large"
            value-format="YYYY-MM-DD"
          >
            <template #prefix>
              <CalendarOutlined style="color: #1a936f" />
            </template>
          </a-range-picker>
        </a-form-item>

        <!-- Budget -->
        <a-form-item label="预算档位">
          <a-segmented
            v-model:value="budgetLevel"
            :options="[
              { label: '💰 经济型', value: 'economy' },
              { label: '💎 舒适型', value: 'comfort' },
              { label: '👑 豪华型', value: 'luxury' },
            ]"
            block
            size="large"
            style="width: 100%"
          />
        </a-form-item>

        <!-- Travelers -->
        <a-form-item label="出行人数">
          <a-input-number
            v-model:value="travelers"
            :min="1"
            :max="20"
            size="large"
            style="width: 100%"
          >
            <template #prefix>
              <TeamOutlined style="color: #1a936f" />
            </template>
          </a-input-number>
        </a-form-item>

        <!-- Preferences -->
        <a-form-item label="兴趣偏好">
          <a-checkbox-group v-model:value="preferences" style="width: 100%">
            <a-row :gutter="[8, 8]">
              <a-col
                v-for="opt in preferenceOptions"
                :key="opt.value"
                :xs="12" :sm="8" :md="8"
              >
                <a-checkbox :value="opt.value" class="pref-checkbox">
                  {{ opt.label }}
                </a-checkbox>
              </a-col>
            </a-row>
          </a-checkbox-group>
        </a-form-item>

        <!-- Extra requirements -->
        <a-form-item label="额外需求">
          <a-textarea
            v-model:value="extraRequirements"
            placeholder="例如：希望多安排一些洱海边的景点、需要无障碍设施、适合老人小孩..."
            :rows="3"
            size="large"
          >
            <template #prefix>
              <EditOutlined style="color: #1a936f" />
            </template>
          </a-textarea>
        </a-form-item>

        <!-- Submit -->
        <a-form-item style="margin-bottom: 0">
          <a-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleSubmit"
            class="submit-btn"
          >
            <template #icon>
              <ThunderboltOutlined />
            </template>
            {{ loading ? "AI 正在为您规划行程..." : "开始生成行程" }}
          </a-button>
          <p v-if="loading" class="loading-hint">
            ⏳ AI 正在根据您的需求生成个性化行程，可能需要 <strong>10-90 秒</strong>，请耐心等待...
          </p>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<style scoped>
.home-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 8px 0 16px;
}

.hero-banner {
  text-align: center;
  padding: 8px 0 20px;
}

.hero-text {
  color: #666;
  font-size: 15px;
  margin: 0;
}

.form-card {
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border: 1px solid #e8e8e8;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #1a936f, #168a5f);
  border: none;
  box-shadow: 0 4px 14px rgba(26, 147, 111, 0.35);
  transition: all 0.3s ease;
}

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(26, 147, 111, 0.45);
}

.submit-btn:active {
  transform: translateY(0);
}

.loading-hint {
  text-align: center;
  color: #888;
  font-size: 13px;
  margin-top: 10px;
  margin-bottom: 0;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.pref-checkbox {
  margin: 0 !important;
}

/* Larger touch targets on mobile */
@media (max-width: 576px) {
  .form-card :deep(.ant-card-body) {
    padding: 20px 16px !important;
  }
}
</style>
