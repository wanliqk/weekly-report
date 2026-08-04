<script setup lang="ts">
// DESK-01 占位页：仅证明桌面宿主可运行，不含任何业务逻辑。
// FE-01 将接管本渲染目录（electron/src/renderer）实现真实前端。
const title = 'Weekly Report'
const statusText = '桌面基线就绪（DESK-01）'
</script>

<template>
  <main class="placeholder">
    <h1>{{ title }}</h1>
    <p class="status">{{ statusText }}</p>
    <p class="hint">仅用于启动验证的本地占位页面，不加载任何远程内容。</p>
  </main>
</template>

<style scoped>
.placeholder {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  user-select: none;
}

h1 {
  font-size: 28px;
  font-weight: 700;
}

.status {
  font-size: 16px;
  font-weight: 600;
}

.hint {
  font-size: 13px;
  opacity: 0.6;
}
</style>
