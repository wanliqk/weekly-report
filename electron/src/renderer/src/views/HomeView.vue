<script setup lang="ts">
import { computed } from 'vue'

import { formatServiceState } from '@renderer/utils/status-message'

const platformName = computed(() => window.desktop.platform)
const serviceMessage = formatServiceState('pending')
</script>

<template>
  <main class="baseline-shell">
    <section>
      <span class="baseline-eyebrow">WEEKLY REPORT</span>
      <h1>工程基线已就绪</h1>
      <p>Electron、Vue 和 FastAPI 已接入统一工作区，下一步将连接本地后端启动链路。</p>
    </section>

    <section class="baseline-grid" aria-label="工程状态">
      <article>
        <span>桌面运行环境</span>
        <strong>{{ platformName }}</strong>
      </article>
      <article>
        <span>后端服务</span>
        <strong>{{ serviceMessage }}</strong>
      </article>
      <article>
        <span>业务模块</span>
        <strong>待逐步接入</strong>
      </article>
    </section>
  </main>
</template>

<style scoped>
.baseline-shell {
  width: min(1080px, calc(100% - 64px));
  margin: 0 auto;
  padding: 96px 0;
}

.baseline-shell > section:first-child {
  max-width: 720px;
}

.baseline-eyebrow {
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

h1 {
  margin: 16px 0;
  font-size: clamp(40px, 6vw, 72px);
  line-height: 1.05;
}

p {
  color: #52605f;
  font-size: 18px;
  line-height: 1.8;
}

.baseline-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 64px;
}

.baseline-grid article {
  display: grid;
  gap: 12px;
  padding: 24px;
  border: 1px solid rgb(15 118 110 / 12%);
  border-radius: 18px;
  background: rgb(255 255 255 / 78%);
}

.baseline-grid span {
  color: #6b7776;
  font-size: 13px;
}

.baseline-grid strong {
  font-size: 18px;
}

@media (max-width: 760px) {
  .baseline-shell {
    width: min(100% - 32px, 1080px);
    padding: 56px 0;
  }

  .baseline-grid {
    grid-template-columns: 1fr;
  }
}
</style>
