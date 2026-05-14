<script setup lang="ts">
import { ref } from "vue";
import { message } from "ant-design-vue";
import { UserOutlined, LockOutlined } from "@ant-design/icons-vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const emit = defineEmits<{ loggedIn: [] }>();

const isRegister = ref(false);
const username = ref("");
const password = ref("");
const loading = ref(false);

async function handleSubmit() {
  if (!username.value.trim() || !password.value.trim()) {
    message.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    if (isRegister.value) {
      await auth.register(username.value.trim(), password.value);
      message.success("注册成功！");
    } else {
      await auth.login(username.value.trim(), password.value);
      message.success("登录成功！");
    }
    emit("loggedIn");
  } catch (err: any) {
    message.error(err?.response?.data?.detail || "操作失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h2>途灵旅行</h2>
      <p class="login-sub">AI 驱动的智能旅行规划助手</p>

      <a-form layout="vertical" @submit.prevent="handleSubmit">
        <a-form-item label="用户名">
          <a-input v-model:value="username" size="large" placeholder="请输入用户名">
            <template #prefix><UserOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item label="密码">
          <a-input-password v-model:value="password" size="large" placeholder="请输入密码">
            <template #prefix><LockOutlined /></template>
          </a-input-password>
        </a-form-item>

        <a-form-item>
          <a-button
            type="primary"
            size="large"
            :loading="loading"
            block
            @click="handleSubmit"
          >
            {{ isRegister ? "注册" : "登录" }}
          </a-button>
        </a-form-item>
      </a-form>

      <div class="login-toggle">
        <a-button type="link" @click="isRegister = !isRegister">
          {{ isRegister ? "已有账号？去登录" : "没有账号？去注册" }}
        </a-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 160px);
  padding: 24px;
}
.login-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}
.login-card h2 {
  text-align: center;
  font-size: 24px;
  color: #1a936f;
  margin: 0 0 4px;
}
.login-sub {
  text-align: center;
  color: #999;
  font-size: 13px;
  margin: 0 0 28px;
}
.login-toggle {
  text-align: center;
}
</style>
