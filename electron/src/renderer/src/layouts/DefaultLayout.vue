<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElAside, ElContainer, ElHeader, ElMain, ElMenu, ElMenuItem } from 'element-plus'
import { useRouter } from 'vue-router'
import GlobalLoading from '../components/GlobalLoading.vue'

const router = useRouter()
const route = useRoute()

interface NavItem {
  path: string
  title: string
}

const navItems = computed<NavItem[]>(() =>
  router
    .getRoutes()
    .filter(
      (record): record is typeof record & { meta: { nav: boolean; title: string } } =>
        record.meta.nav === true && typeof record.meta.title === 'string'
    )
    .map((record) => ({
      path: record.path,
      title: record.meta.title
    }))
)
</script>

<template>
  <el-container class="app-layout">
    <el-header class="app-header">
      <span class="app-title">Weekly Report</span>
    </el-header>
    <el-container class="app-body">
      <el-aside width="200px" class="app-aside">
        <el-menu :default-active="route.path" router>
          <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
            {{ item.title }}
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
    <GlobalLoading />
  </el-container>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
}

.app-title {
  font-size: 16px;
  font-weight: 600;
}

.app-body {
  align-items: stretch;
}

.app-aside {
  border-right: 1px solid var(--el-border-color-light);
}

.app-main {
  background: var(--el-fill-color-light);
}
</style>
