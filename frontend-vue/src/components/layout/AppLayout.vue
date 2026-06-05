<template>
  <div class="flex h-screen bg-terminal-bg overflow-hidden">
    <!-- 侧边栏 -->
    <aside
      class="flex flex-col w-56 bg-terminal-surface border-r border-terminal-border shrink-0"
      :class="{ '-translate-x-full': !sidebarOpen, 'translate-x-0': sidebarOpen }"
    >
      <!-- Logo -->
      <div class="flex items-center gap-2 px-4 py-4 border-b border-terminal-border">
        <div class="w-6 h-6 bg-accent-blue rounded flex items-center justify-center text-white text-xs font-bold">D</div>
        <span class="font-mono font-semibold text-terminal-text text-sm tracking-wider">DLQI</span>
        <span class="ml-auto text-terminal-dim text-xs">v1.0</span>
      </div>

      <!-- 导航 -->
      <nav class="flex-1 py-2 overflow-y-auto">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-4 py-2.5 text-sm text-terminal-muted hover:text-terminal-text hover:bg-terminal-card transition-colors"
          active-class="text-accent-blue bg-terminal-card border-r-2 border-accent-blue"
        >
          <component :is="item.icon" :size="15" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <!-- 运行 Pipeline 按钮 -->
      <div class="p-3 border-t border-terminal-border">
        <button
          class="w-full t-btn-primary text-xs py-2 flex items-center justify-center gap-2"
          :disabled="pipelineRunning"
          @click="runPipeline"
        >
          <span v-if="pipelineRunning" class="animate-spin">⟳</span>
          <span>{{ pipelineRunning ? '运行中...' : '▶ 运行 Pipeline' }}</span>
        </button>
        <div v-if="pipelineStatus" class="mt-1.5 text-xs text-terminal-dim text-center font-mono truncate">
          {{ pipelineStatus }}
        </div>
      </div>
    </aside>

    <!-- 主内容 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶栏 -->
      <header class="flex items-center gap-3 px-4 py-3 border-b border-terminal-border bg-terminal-surface shrink-0">
        <button class="text-terminal-muted hover:text-terminal-text md:hidden" @click="sidebarOpen = !sidebarOpen">
          ☰
        </button>
        <span class="font-mono text-xs text-terminal-dim">{{ currentTitle }}</span>
        <div class="ml-auto flex items-center gap-2">
          <span class="text-xs text-terminal-dim font-mono">{{ now }}</span>
          <!-- 日间/夜间切换 -->
          <button
            class="w-7 h-7 flex items-center justify-center rounded text-terminal-muted hover:text-terminal-text hover:bg-terminal-card transition-colors text-base"
            :title="themeStore.isDark ? '切换日间模式' : '切换夜间模式'"
            @click="themeStore.toggle()"
          >
            {{ themeStore.isDark ? '☀' : '🌙' }}
          </button>
          <span
            class="w-2 h-2 rounded-full"
            :class="backendOk ? 'bg-gain' : 'bg-loss'"
            :title="backendOk ? '后端在线' : '后端离线'"
          />
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="flex-1 overflow-y-auto p-4">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  LayoutDashboard, TrendingUp, Brain, BarChart2,
  Briefcase, ShieldAlert, Database, SlidersHorizontal
} from 'lucide-vue-next'
import { useBacktestStore } from '@/stores/backtest'
import { useThemeStore } from '@/stores/theme'
import { api } from '@/composables/api'

const route = useRoute()
const backtestStore = useBacktestStore()
const themeStore = useThemeStore()
const sidebarOpen = ref(true)
const backendOk = ref(false)
const now = ref('')

const navItems = [
  { to: '/',           label: '概览',     icon: LayoutDashboard },
  { to: '/strategies', label: '策略分析', icon: TrendingUp },
  { to: '/models',     label: '模型对比', icon: Brain },
  { to: '/backtest',   label: '回测结果', icon: BarChart2 },
  { to: '/trading',    label: '模拟交易', icon: Briefcase },
  { to: '/risk',       label: '风险监控', icon: ShieldAlert },
  { to: '/data',       label: '数据管理', icon: Database },
  { to: '/tuning',     label: '参数调优', icon: SlidersHorizontal },
]

const titleMap: Record<string, string> = {
  '/': 'DLQI / 概览',
  '/strategies': 'DLQI / 策略分析',
  '/models': 'DLQI / 模型对比',
  '/backtest': 'DLQI / 回测结果',
  '/trading': 'DLQI / 模拟交易',
  '/risk': 'DLQI / 风险监控',
  '/data': 'DLQI / 数据管理',
  '/tuning': 'DLQI / 参数调优',
}

const currentTitle = computed(() => titleMap[route.path] ?? 'DLQI')
const pipelineRunning = computed(() => backtestStore.pipelineRunning)
const pipelineStatus = computed(() => backtestStore.pipelineStatus)

async function runPipeline() {
  await backtestStore.runPipeline()
}

async function checkBackend() {
  try {
    await api.getPipelineStatus()
    backendOk.value = true
  } catch {
    backendOk.value = false
  }
}

function updateClock() {
  now.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

let statusTimer: ReturnType<typeof setInterval>
let clockTimer: ReturnType<typeof setInterval>

onMounted(() => {
  checkBackend()
  updateClock()
  statusTimer = setInterval(() => backtestStore.checkStatus(), 3000)
  clockTimer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  clearInterval(statusTimer)
  clearInterval(clockTimer)
})
</script>
