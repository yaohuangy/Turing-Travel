<script setup lang="ts">
import Home from "./views/Home.vue";
import Result from "./views/Result.vue";
import History from "./views/History.vue";
import { useAppStore } from "./stores/app";

const store = useAppStore();
</script>

<template>
  <a-config-provider
    :theme="{
      token: {
        colorPrimary: '#1a936f',
        borderRadius: 8,
        colorSuccess: '#52c41a',
        colorWarning: '#fa8c16',
        colorError: '#ff4d4f',
        fontFamily: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`,
      },
    }"
  >
    <div class="app-wrapper">
      <header class="app-header">
        <div class="header-content">
          <div class="logo-section">
            <span class="logo-icon">🌍</span>
            <h1 class="logo-title">途灵旅行</h1>
          </div>
          <p class="logo-subtitle">AI 驱动的智能旅行规划助手</p>
        </div>
      </header>

      <main class="app-main">
        <a-card class="tab-card" :body-style="{ padding: '0 24px 24px' }">
          <a-tabs
            v-model:activeKey="store.activeKey"
            :tab-bar-style="{ paddingLeft: '24px', marginBottom: '0' }"
            size="large"
          >
            <a-tab-pane key="home" tab="✈️ 规划行程">
              <Home />
            </a-tab-pane>
            <a-tab-pane key="result" tab="📋 行程结果" force-render>
              <Result />
            </a-tab-pane>
            <a-tab-pane key="history" tab="📂 历史记录">
              <History />
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </main>

      <footer class="app-footer">
        <span>途灵旅行 · Turing Travel © 2026</span>
      </footer>
    </div>
  </a-config-provider>
</template>

<style>
/* Global resets & base */
*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
  -webkit-font-smoothing: antialiased;
}

body {
  margin: 0;
  background: #f0f2f5;
  min-height: 100vh;
}

.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Header */
.app-header {
  background: linear-gradient(135deg, #1a936f 0%, #114b5f 100%);
  padding: 36px 24px 28px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.header-content {
  max-width: 600px;
  margin: 0 auto;
}

.logo-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 8px;
}

.logo-icon {
  font-size: 36px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.logo-title {
  color: #fff;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 2px;
  margin: 0;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.logo-subtitle {
  color: rgba(255, 255, 255, 0.85);
  font-size: 15px;
  margin: 0;
  letter-spacing: 1px;
}

/* Main content */
.app-main {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: -8px auto 0;
  padding: 0 16px 32px;
  position: relative;
  z-index: 1;
}

.tab-card {
  border-radius: 12px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.06);
}

/* Footer */
.app-footer {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
  border-top: 1px solid #eee;
  background: #fff;
}

/* Ant Design overrides */
.ant-tabs-nav {
  margin-bottom: 0 !important;
}

.ant-tabs-tab {
  font-size: 15px !important;
  padding: 16px 0 !important;
}

.ant-card {
  border-radius: 12px;
}

.ant-collapse {
  border-radius: 10px;
  overflow: hidden;
}

.ant-collapse-item {
  border-radius: 10px !important;
  overflow: hidden;
  margin-bottom: 8px !important;
  border: 1px solid #e8e8e8 !important;
}

.ant-collapse-content {
  border-top: 1px solid #f0f0f0 !important;
}

/* Responsive */
@media (max-width: 768px) {
  .app-header {
    padding: 24px 16px 20px;
  }
  .logo-title {
    font-size: 24px;
  }
  .logo-subtitle {
    font-size: 13px;
  }
  .app-main {
    padding: 0 8px 20px;
    margin-top: -4px;
  }
}
</style>
