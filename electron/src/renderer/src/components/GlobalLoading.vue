<script setup lang="ts">
import { useUiStore } from '../stores/ui'

const ui = useUiStore()
</script>

<template>
  <Transition name="loading-fade">
    <div v-if="ui.isLoading" class="global-loading" role="status" aria-label="加载中" />
  </Transition>
</template>

<style scoped>
.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  z-index: 3000;
  background: linear-gradient(90deg, var(--el-color-primary-light-5), var(--el-color-primary));
  animation: loading-pulse 1s ease-in-out infinite;
}

@keyframes loading-pulse {
  0% {
    opacity: 0.4;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.4;
  }
}

.loading-fade-enter-active,
.loading-fade-leave-active {
  transition: opacity 0.2s ease;
}

.loading-fade-enter-from,
.loading-fade-leave-to {
  opacity: 0;
}
</style>
