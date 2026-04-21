<template>
  <div class="p-6 space-y-6">
    <!-- Pipeline 控制栏 -->
    <div class="t-card flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="text-terminal-text text-sm font-semibold">Pipeline</div>
        <div v-if="pipelineRunning" class="flex items-center gap-2 text-accent-blue text-xs">
          <span class="inline-block w-3 h-3 border-2 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin"></span>
          {{ pipelineStep || '运行中...' }}
        </div>
        <div v-else-if="pipelineError" class="text-loss text-xs">{{ pipelineError }}</div>
        <div v-else-if="pipelineLastRun" class="text-terminal-dim text-xs">
          上次运行: {{ fmtTime(pipelineLastRun) }}
        </div>
        <div v-else class="text-terminal-dim text-xs">训练 → 预测 → 回测 → 分析</div>
      </div>
      <button class="t-btn-primary text-xs" :disabled="pipelineRunning" @click="handleRunPipeline">
        {{ pipelineRunning ? '运行中...' : '运行 Pipeline' }}
      </button>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-5 gap-4">
      <div v-for="kpi in kpiCards" :key="kpi.label" class="t-card">
        <div class="text-terminal-muted text-xs mb-1">{{ kpi.label }}</div>
        <div class="font-mono text-xl" :class="kpi.colorClass">{{ kpi.value }}</div>
      </div>
    </div>

    <!-- Top Models Table -->
    <div class="t-card">
      <div class="text-terminal-text text-sm font-semibold mb-3 border-b border-terminal-border pb-2">
        最佳模型排行 TOP 10
      </div>
      <div v-if="loading" class="text-terminal-muted text-sm py-4 text-center">加载中...</div>
      <div v-else-if="error" class="text-loss text-sm py-4 text-center">{{ error }}</div>
      <table v-else class="w-full text-xs">
        <thead>
          <tr class="text-terminal-dim border-b border-terminal-border">
            <th class="text-left py-2 pr-3">模型ID</th>
            <th class="text-left py-2 pr-3">股票</th>
            <th class="text-left py-2 pr-3">类型</th>
            <th class="text-right py-2 pr-3">Sharpe</th>
            <th class="text-right py-2 pr-3">年化收益</th>
            <th class="text-right py-2 pr-3">最大回撤</th>
            <th class="text-right py-2">方向准确率</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="m in topModels"
            :key="m.model_id"
            class="border-b border-terminal-border hover:bg-terminal-card transition-colors"
          >
            <td class="py-2 pr-3 font-mono text-terminal-text truncate max-w-[120px]">{{ m.model_id }}</td>
            <td class="py-2 pr-3 text-accent-blue font-mono">{{ m.symbol }}</td>
            <td class="py-2 pr-3">
              <span class="t-badge">{{ m.model_type }}</span>
            </td>
            <td class="py-2 pr-3 text-right font-mono" :class="m.sharpe_ratio >= 0 ? 'text-gain' : 'text-loss'">
              {{ fmtNum(m.sharpe_ratio) }}
            </td>
            <td class="py-2 pr-3 text-right font-mono" :class="m.annual_return >= 0 ? 'text-gain' : 'text-loss'">
              {{ fmtPct(m.annual_return) }}
            </td>
            <td class="py-2 pr-3 text-right font-mono text-loss">{{ fmtPct(m.max_drawdown) }}</td>
            <td class="py-2 text-right font-mono text-terminal-text">{{ fmtPct(m.direction_accuracy) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Bottom Two Columns -->
    <div class="grid grid-cols-2 gap-4">
      <!-- Symbol Coverage -->
      <div class="t-card">
        <div class="text-terminal-text text-sm font-semibold mb-3 border-b border-terminal-border pb-2">
          股票覆盖
        </div>
        <table class="w-full text-xs">
          <thead>
            <tr class="text-terminal-dim border-b border-terminal-border">
              <th class="text-left py-2 pr-3">股票</th>
              <th class="text-right py-2 pr-3">模型数</th>
              <th class="text-right py-2">最佳 Sharpe</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in symbolCoverage"
              :key="row.symbol"
              class="border-b border-terminal-border hover:bg-terminal-card transition-colors"
            >
              <td class="py-2 pr-3 font-mono text-accent-blue">{{ row.symbol }}</td>
              <td class="py-2 pr-3 text-right font-mono text-terminal-text">{{ row.count }}</td>
              <td class="py-2 text-right font-mono" :class="row.bestSharpe >= 0 ? 'text-gain' : 'text-loss'">
                {{ fmtNum(row.bestSharpe) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Portfolios -->
      <div class="t-card">
        <div class="text-terminal-text text-sm font-semibold mb-3 border-b border-terminal-border pb-2">
          模拟组合
        </div>
        <div v-if="portfolioLoading" class="text-terminal-muted text-sm py-4 text-center">加载中...</div>
        <div v-else-if="portfolios.length === 0" class="text-terminal-dim text-sm py-4 text-center">暂无组合数据</div>
        <div v-else class="space-y-2">
          <div
            v-for="p in portfolios"
            :key="p.id"
            class="flex items-center justify-between p-2 rounded border border-terminal-border hover:bg-terminal-surface transition-colors"
          >
            <div>
              <div class="text-terminal-text text-xs font-mono">{{ p.name || p.id }}</div>
              <div class="text-terminal-dim text-xs mt-0.5">{{ p.symbol }} · {{ p.model_type }}</div>
            </div>
            <div class="text-right">
              <div class="font-mono text-xs" :class="(p.total_return ?? 0) >= 0 ? 'text-gain' : 'text-loss'">
                {{ fmtPct(p.total_return ?? 0) }}
              </div>
              <div class="text-terminal-dim text-xs font-mono">{{ fmtMoney(p.equity ?? 0) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/composables/api'
import type { BacktestResult } from '@/types'
import { fmtPct, fmtNum, fmtMoney } from '@/types'

const backtests = ref<BacktestResult[]>([])
const portfolios = ref<any[]>([])
const loading = ref(true)
const portfolioLoading = ref(true)
const error = ref('')

// Pipeline state
const pipelineRunning = ref(false)
const pipelineStep = ref('')
const pipelineError = ref('')
const pipelineLastRun = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const fmtTime = (ts: string) => {
  try { return new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }
  catch { return ts }
}

async function checkPipelineStatus() {
  try {
    const s = await api.getPipelineStatus() as any
    pipelineRunning.value = s.running ?? false
    pipelineStep.value = s.progress ?? ''
    pipelineError.value = s.error ?? ''
    pipelineLastRun.value = s.last_run ?? ''
    if (!pipelineRunning.value && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
      // 完成后刷新回测数据
      const res = await api.getBacktests({ page_size: 100 })
      backtests.value = res.items ?? []
    }
  } catch { /* 静默 */ }
}

async function handleRunPipeline() {
  pipelineError.value = ''
  try {
    await api.runPipeline()
    pipelineRunning.value = true
    pipelineStep.value = '启动中...'
    if (!pollTimer) {
      pollTimer = setInterval(checkPipelineStatus, 3000)
    }
  } catch (e: any) {
    pipelineError.value = e.message ?? '启动失败'
  }
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const topModels = computed(() =>
  [...backtests.value]
    .sort((a, b) => b.sharpe_ratio - a.sharpe_ratio)
    .slice(0, 10)
)

const kpiCards = computed(() => {
  const items = backtests.value
  if (!items.length) return [
    { label: '已训练模型', value: '0', colorClass: 'text-terminal-text' },
    { label: '平均 Sharpe', value: '-', colorClass: 'text-terminal-text' },
    { label: '最佳 Sharpe', value: '-', colorClass: 'text-terminal-text' },
    { label: '平均方向准确率', value: '-', colorClass: 'text-terminal-text' },
    { label: '平均年化收益', value: '-', colorClass: 'text-terminal-text' },
  ]
  const avg = (fn: (x: BacktestResult) => number) =>
    items.reduce((s, x) => s + fn(x), 0) / items.length
  const bestSharpe = Math.max(...items.map(x => x.sharpe_ratio))
  const avgAnnual = avg(x => x.annual_return)
  return [
    { label: '已训练模型', value: String(items.length), colorClass: 'text-terminal-text' },
    { label: '平均 Sharpe', value: fmtNum(avg(x => x.sharpe_ratio)), colorClass: avg(x => x.sharpe_ratio) >= 0 ? 'text-gain' : 'text-loss' },
    { label: '最佳 Sharpe', value: fmtNum(bestSharpe), colorClass: 'text-gain' },
    { label: '平均方向准确率', value: fmtPct(avg(x => x.direction_accuracy)), colorClass: 'text-accent-blue' },
    { label: '平均年化收益', value: fmtPct(avgAnnual), colorClass: avgAnnual >= 0 ? 'text-gain' : 'text-loss' },
  ]
})

const symbolCoverage = computed(() => {
  const map = new Map<string, { count: number; bestSharpe: number }>()
  for (const b of backtests.value) {
    const cur = map.get(b.symbol) ?? { count: 0, bestSharpe: -Infinity }
    map.set(b.symbol, {
      count: cur.count + 1,
      bestSharpe: Math.max(cur.bestSharpe, b.sharpe_ratio),
    })
  }
  return [...map.entries()]
    .map(([symbol, v]) => ({ symbol, ...v }))
    .sort((a, b) => b.bestSharpe - a.bestSharpe)
})

onMounted(async () => {
  checkPipelineStatus()
  try {
    const res = await api.getBacktests({ page_size: 100 })
    backtests.value = res.items ?? []
  } catch (e: any) {
    error.value = e?.message ?? '加载失败'
  } finally {
    loading.value = false
  }
  try {
    const res = await api.getPortfolios()
    portfolios.value = res.items ?? res ?? []
  } catch {
    // 静默失败
  } finally {
    portfolioLoading.value = false
  }
})
</script>
