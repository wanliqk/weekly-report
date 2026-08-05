<script setup lang="ts">
// FE-01 占位首页：仅展示基础布局就绪状态，不含业务假数据。
// 业务页面在 FE-AUTH-01 及后续任务中替换。
</script>

<template>
  <section class="home">
    <h1>欢迎使用 Weekly Report</h1>
    <p class="hint">前端基础布局与路由骨架已就绪（FE-01），业务功能将在后续迭代中接入。</p>
  </section>
</template>

<style scoped>
.home {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  user-select: none;
}

h1 {
  font-size: 24px;
  font-weight: 700;
}

.hint {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
</style>
