<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome(): void {
  router.push('/')
}
</script>

<template>
  <section class="not-found">
    <h1>404</h1>
    <p class="message">页面不存在或已被移除。</p>
    <button type="button" class="back-button" @click="goHome">返回首页</button>
  </section>
</template>

<style scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  user-select: none;
}

h1 {
  font-size: 56px;
  font-weight: 700;
  margin: 0;
}

.message {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.back-button {
  margin-top: 8px;
  padding: 8px 20px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-bg-color);
  cursor: pointer;
}

.back-button:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
</style>
