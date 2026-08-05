<script setup lang="ts">
import { computed } from 'vue'

import { formatServiceState } from '@renderer/utils/status-message'
import { useSidecarStore } from '@renderer/stores/sidecar'

const store = useSidecarStore()

const headline = computed(() => formatServiceState(store.serviceState))
const isFailed = computed(() => store.serviceState === 'failed')
</script>

<template>
  <main class="startup-shell">
    <section>
      <span class="startup-eyebrow">WEEKLY REPORT</span>
      <h1>{{ headline }}</h1>
      <p v-if="!isFailed">正在连接本地后端服务，请稍候…</p>
      <template v-else>
        <p>{{ store.snapshot.reason ?? '未知原因导致启动失败' }}</p>
        <button type="button" class="retry-button" @click="store.retry()">重试</button>
        <details v-if="store.snapshot.recentLogLines.length > 0" class="log-details">
          <summary>详细日志</summary>
          <pre>{{ store.snapshot.recentLogLines.join('\n') }}</pre>
        </details>
      </template>
    </section>
  </main>
</template>

<style scoped>
.startup-shell {
  width: min(720px, calc(100% - 64px));
  margin: 0 auto;
  padding: 120px 0;
  text-align: center;
}

.startup-eyebrow {
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

h1 {
  margin: 16px 0;
  font-size: clamp(28px, 4vw, 44px);
}

p {
  color: #52605f;
  font-size: 16px;
  line-height: 1.6;
}

.retry-button {
  margin-top: 16px;
  padding: 10px 24px;
  border-radius: 999px;
  border: none;
  background: #0f766e;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.log-details {
  margin-top: 24px;
  text-align: left;
}

.log-details pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>
