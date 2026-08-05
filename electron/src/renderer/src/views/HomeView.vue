<script setup lang="ts">
import { computed } from 'vue'

import { useAuthStore } from '@renderer/stores/auth'

const authStore = useAuthStore()
const greeting = computed(() => authStore.currentUser?.display_name || '你好')
</script>

<template>
  <main class="workspace-page">
    <header class="page-heading dashboard-heading">
      <div>
        <span class="eyebrow">TODAY'S WORKSPACE</span>
        <h1>{{ greeting }}，今天也留下清晰的一笔。</h1>
        <p>认证与用户管理已经接通。日报闭环将在下一阶段从这里展开。</p>
      </div>
      <span class="date-chip">本地 · Asia/Shanghai</span>
    </header>
    <section class="dashboard-grid">
      <article class="feature-card feature-card-primary">
        <span>日报</span>
        <h2>记录今日进展</h2>
        <p>模板、草稿、提交与归档能力将在阶段 5 接入。</p>
        <el-button type="primary" disabled>即将开放</el-button>
      </article>
      <article class="feature-card">
        <span>周报</span>
        <h2>汇总一周脉络</h2>
        <p>只汇总已归档日报，并保留来源追溯。</p>
      </article>
      <article class="feature-card">
        <span>安全状态</span>
        <h2>本机加密登录</h2>
        <p>Token 已由 Electron safeStorage 加密保存，页面仅持有运行期副本。</p>
      </article>
    </section>
  </main>
</template>
