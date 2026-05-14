import { ref } from "vue";
import { defineStore } from "pinia";
import api from "../services/api";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("tt_token") || "");
  const username = ref(localStorage.getItem("tt_username") || "");
  const userId = ref(localStorage.getItem("tt_user_id") || "");

  const isLoggedIn = () => !!token.value;

  async function login(user: string, pass: string) {
    const { data } = await api.post("/auth/login", { username: user, password: pass });
    token.value = data.token;
    username.value = data.username;
    userId.value = data.user_id;
    localStorage.setItem("tt_token", data.token);
    localStorage.setItem("tt_username", data.username);
    localStorage.setItem("tt_user_id", data.user_id);
  }

  async function register(user: string, pass: string) {
    await api.post("/auth/register", { username: user, password: pass });
    // Auto-login after register
    await login(user, pass);
  }

  function logout() {
    token.value = "";
    username.value = "";
    userId.value = "";
    localStorage.removeItem("tt_token");
    localStorage.removeItem("tt_username");
    localStorage.removeItem("tt_user_id");
  }

  return { token, username, userId, isLoggedIn, login, register, logout };
});
