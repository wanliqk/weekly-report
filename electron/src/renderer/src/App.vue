<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import StartupView from '@renderer/views/StartupView.vue'
import { useSidecarStore } from '@renderer/stores/sidecar'

const sidecarStore = useSidecarStore()

onMounted(() => {
  void sidecarStore.init()
})
</script>

<template>
  <StartupView v-if="sidecarStore.serviceState !== 'ready'" />
  <RouterView v-else />
</template>
