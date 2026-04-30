<template>
  <div class="p-6 flex flex-col gap-4 h-full overflow-y-auto">

    <!-- 策略推荐面板 -->
    <div class="t-card border-accent-blue/40">
      <div class="flex items-center justify-between mb-3">
        <div>
          <span class="text-terminal-text font-semibold text-sm">策略评估与推荐</span>
          <span class="text-terminal-dim text-xs ml-2">综合评分 = Sharpe×40% + 年化收益×30% + 最大回撤×20% + 方向准确率×10%</span>
        </div>
        <button class="t-btn-ghost text-xs px-3 py-1" @click="loadRecommend" :disabled="recLoading">
          {{ recLoading ? '评估中...' : '重新评估' }}
        </button>
      </div>

      <div v-if="recLoading" class="text-terminal-muted text-xs py-4 text-center">评估中...</div>
      <div v-else-if="recError" class="text-loss text-xs py-2">{{ recError }}</div>
      <div v-else-if="recommend" class="flex gap-3">
        <!-- Top 3 卡片 -->
        <div
          v-for="(item, idx) in recommend.top"
          :key="item.model_id"
          class="flex-1 rounded border p-3 cursor-pointer transition-colors"
          :class="idx === 0
            ? 'border-accent-blue bg-accent-blue/5'
            : 'border-terminal-border hover:border-terminal-text'"
          @click="selectStrategy(item)"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs font-bold" :class="idx === 0 ? 'text-accent-blue' : 'text-terminal-dim'">
              #{{ (idx as number) + 1 }}
            </span>
            <span v-if="idx === 0" class="text-xs bg-accent-blue/20 text-accent-blue px-1.5 py-0.5 rounded font-semibold">主策略</span>
            <span class="t-badge ml-auto">{{ item.model_type }}</span>
          </div>
          <div class="font-mono text-xs text-terminal-text truncate mb-1">{{ item.model_id }}</div>
          <div class="text-accent-blue font-mono text-xs mb-2">{{ item.symbol }}</div>
          <div class="flex items-center justify-between mb-2">
            <span class="text-terminal-dim text-xs">综合评分</span>
            <span class="font-mono text-sm font-bold" :class="idx === 0 ? 'text-accent-blue' : 'text-terminal-text'">
              {{ ((item.composite_score ?? 0) * 100).toFixed(1) }}
            </span>
          </div>
          <!-- 评分条 -->
          <div class="space-y-1">
            <div v-for="bar in scoreBars(item)" :key="bar.label" class="flex items-center gap-2">
              <span class="text-terminal-dim text-xs w-16 shrink-0">{{ bar.label }}</span>
              <div class="flex-1 bg-terminal-border rounded-full h-1">
                <div class="h-1 rounded-full" :class="bar.color" :style="{ width: bar.pct + '%' }"></div>
              </div>
              <span class="font-mono text-xs w-10 text-right" :class="bar.textColor">{{ bar.display }}</span>
            </div>
          </div>
          <!-- 一键部署按钮（仅 #1） -->
          <button
            v-if="idx === 0"
            class="t-btn-primary w-full mt-3 text-xs py-1.5"
            :disabled="deploying"
            @click.stop="deployBest"
          >
            {{ deploying ? '部署中...' : '一键部署为主策略' }}
          </button>
        </div>
      </div>

      <!-- 部署成功提示 -->
      <div v-if="deployMsg" class="mt-3 text-xs px-3 py-2 rounded border"
        :class="deployMsg.ok ? 'border-gain/40 text-gain bg-gain/5' : 'border-loss/40 text-loss bg-loss/5'">
        {{ deployMsg.text }}
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="flex items-center gap-3">
      <select v-model="filterSymbol" class="bg-terminal-surface border border-terminal-border text-terminal-text text-xs rounded px-3 py-1.5 font-mono focus:outline-none focus:border-accent-blue">
        <option value="">全部股票</option>
        <option v-for="s in symbols" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filterType" class="bg-terminal-surface border border-terminal-border text-terminal-text text-xs rounded px-3 py-1.5 font-mono focus:outline-none focus:border-accent-blue">
        <option value="">全部类型</option>
        <option value="lightgbm">lightgbm</option>
        <option value="xgboost">xgboost</option>
        <option value="lstm">lstm</option>
        <option value="transformer">transformer</option>
      </select>
      <span class="text-terminal-dim text-xs ml-2">{{ filteredBacktests.length }} 条策略</span>
    </div>

    <!-- Main Content -->
    <div class="flex gap-4 flex-1 min-h-0" style="min-height: 400px;">
      <!-- Left: Strategy List -->
      <div class="w-72 flex-shrink-0 flex flex-col gap-2 overflow-y-auto pr-1">
        <div v-if="loading" class="text-terminal-muted text-sm text-center py-8">加载中...</div>
        <div v-else-if="error" class="text-loss text-sm text-center py-8">{{ error }}</div>
        <div
          v-for="b in filteredBacktests"
          :key="b.model_id"
          class="t-card cursor-pointer transition-colors"
          :class="selected?.model_id === b.model_id ? 'border-accent-blue' : 'hover:border-terminal-text'"
          @click="selectStrategy(b)"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="font-mono text-xs text-terminal-text truncate max-w-[140px]">{{ b.model_id }}</span>
            <span class="t-badge">{{ b.model_type }}</span>
          </div>
          <div class="flex items-center gap-2 mb-2">
            <span class="text-accent-blue font-mono text-xs">{{ b.symbol }}</span>
            <span v-if="recommend?.best?.model_id === b.model_id"
              class="text-xs bg-accent-blue/20 text-accent-blue px-1.5 py-0.5 rounded">主策略</span>
          </div>
          <div class="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <div class="text-terminal-dim">Sharpe</div>
            <div class="font-mono text-right" :class="b.sharpe_ratio >= 0 ? 'text-gain' : 'text-loss'">{{ fmtNum(b.sharpe_ratio) }}</div>
            <div class="text-terminal-dim">年化收益</div>
            <div class="font-mono text-right" :class="b.annual_return >= 0 ? 'text-gain' : 'text-loss'">{{ fmtPct(b.annual_return) }}</div>
            <div class="text-terminal-dim">最大回撤</div>
            <div class="font-mono text-right text-loss">{{ fmtPct(b.max_drawdown) }}</div>
          </div>
        </div>
      </div>

      <!-- Right: Detail -->
      <div class="flex-1 flex flex-col gap-4 min-w-0">
        <div v-if="!selected" class="flex-1 flex items-center justify-center">
          <div class="text-terminal-dim text-sm">请从左侧选择策略</div>
        </div>
        <template v-else>
          <!-- Key Metrics -->
          <div class="grid grid-cols-3 gap-3">
            <div v-for="m in detailMetrics" :key="m.label" class="t-card">
              <div class="text-terminal-dim text-xs mb-1">{{ m.label }}</div>
              <div class="font-mono text-lg" :class="m.colorClass">{{ m.value }}</div>
            </div>
          </div>

          <!-- Equity Curve -->
          <div class="t-card flex-1 flex flex-col" style="min-height: 200px;">
            <div class="text-terminal-text text-xs font-semibold mb-2 border-b border-terminal-border pb-2">
              权益曲线 · {{ selected.model_id }}
            </div>
            <div v-if="curveLoading" class="flex-1 flex items-center justify-center text-terminal-muted text-sm">加载中...</div>
            <v-chart v-else class="flex-1" style="min-height: 200px;" :option="chartOption" autoresize />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { api } from '@/composables/api'
import type { BacktestResult } from '@/types'
import { fmtPct, fmtNum } from '@/types'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const backtests = ref<BacktestResult[]>([])
const loading = ref(true)
const error = ref('')
const filterSymbol = ref('')
const filterType = ref('')
const selected = ref<BacktestResult | null>(null)
const curveLoading = ref(false)
const equityDates = ref<string[]>([])
const equityValues = ref<number[]>([])

// 推荐相关
const recommend = ref<any>(null)
const recLoading = ref(false)
const recError = ref('')
const deploying = ref(false)
const deployMsg = ref<{ ok: boolean; text: string } | null>(null)

const symbols = ['600519', '601318', '600036', '300750', '002594']

const filteredBacktests = computed(() => {
  return [...backtests.value]
    .filter(b => (!filterSymbol.value || b.symbol === filterSymbol.value))
    .filter(b => (!filterType.value || b.model_type === filterType.value))
    .sort((a, b) => (b.sharpe_ratio ?? 0) - (a.sharpe_ratio ?? 0))
})

const detailMetrics = computed(() => {
  if (!selected.value) return []
  const s = selected.value
  return [
    { label: '总收益', value: fmtPct(s.total_return), colorClass: (s.total_return ?? 0) >= 0 ? 'text-gain' : 'text-loss' },
    { label: '年化收益', value: fmtPct(s.annual_return), colorClass: (s.annual_return ?? 0) >= 0 ? 'text-gain' : 'text-loss' },
    { label: 'Sharpe', value: fmtNum(s.sharpe_ratio), colorClass: (s.sharpe_ratio ?? 0) >= 0 ? 'text-gain' : 'text-loss' },
    { label: '最大回撤', value: fmtPct(s.max_drawdown), colorClass: 'text-loss' },
    { label: '胜率', value: fmtPct(s.win_rate), colorClass: 'text-accent-blue' },
    { label: '交易次数', value: String(s.n_trades ?? '-'), colorClass: 'text-terminal-text' },
  ]
})

function scoreBars(item: any) {
  const bd = item.score_breakdown ?? {}
  return [
    {
      label: 'Sharpe',
      pct: Math.min((bd.sharpe_score / 0.40) * 100, 100),
      display: fmtNum(item.sharpe_ratio),
      color: 'bg-accent-blue',
      textColor: (item.sharpe_ratio ?? 0) >= 0 ? 'text-gain' : 'text-loss',
    },
    {
      label: '年化',
      pct: Math.min((bd.return_score / 0.30) * 100, 100),
      display: fmtPct(item.annual_return),
      color: 'bg-gain',
      textColor: (item.annual_return ?? 0) >= 0 ? 'text-gain' : 'text-loss',
    },
    {
      label: '回撤',
      pct: Math.min((bd.drawdown_score / 0.20) * 100, 100),
      display: fmtPct(item.max_drawdown),
      color: 'bg-yellow-500',
      textColor: 'text-loss',
    },
    {
      label: '准确率',
      pct: Math.min((bd.accuracy_score / 0.10) * 100, 100),
      display: fmtPct(item.direction_accuracy),
      color: 'bg-purple-500',
      textColor: 'text-terminal-text',
    },
  ]
}

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 20, right: 20, bottom: 30, left: 60 },
  xAxis: {
    type: 'category',
    data: equityDates.value,
    axisLine: { lineStyle: { color: '#2a2a2a' } },
    axisLabel: { color: '#6b7280', fontSize: 10 },
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      color: '#6b7280',
      fontSize: 10,
      formatter: (v: number) => '¥' + v.toLocaleString(),
    },
    splitLine: { lineStyle: { color: '#1a1a1a' } },
  },
  series: [{
    type: 'line',
    data: equityValues.value,
    smooth: true,
    lineStyle: { color: '#3b82f6', width: 2 },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(59,130,246,0.3)' },
          { offset: 1, color: 'rgba(59,130,246,0)' },
        ],
      },
    },
    symbol: 'none',
  }],
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#1a1a1a',
    borderColor: '#2a2a2a',
    textStyle: { color: '#e5e7eb', fontSize: 11 },
  },
}))

async function selectStrategy(b: BacktestResult) {
  selected.value = b
  curveLoading.value = true
  equityDates.value = []
  equityValues.value = []
  try {
    const data = await api.getEquityCurve(b.model_id)
    equityDates.value = data.dates ?? data.map((d: any) => d.date)
    equityValues.value = data.portfolio_values ?? data.equities ?? data.map((d: any) => d.equity ?? d.value)
  } catch {
    // 静默失败
  } finally {
    curveLoading.value = false
  }
}

async function loadRecommend() {
  recLoading.value = true
  recError.value = ''
  try {
    recommend.value = await api.getRecommendedStrategy()
  } catch (e: any) {
    recError.value = e?.message ?? '评估失败'
  } finally {
    recLoading.value = false
  }
}

async function deployBest() {
  if (!recommend.value?.best) return
  deploying.value = true
  deployMsg.value = null
  try {
    const res = await api.deployStrategy({
      model_id: recommend.value.best.model_id,
      initial_capital: 1000000,
      days: 120,
    })
    deployMsg.value = {
      ok: true,
      text: `主策略已部署为模拟组合「${res.portfolio?.name}」，最终净值 ¥${res.simulation?.final_value?.toLocaleString() ?? '-'}`,
    }
  } catch (e: any) {
    deployMsg.value = { ok: false, text: e?.message ?? '部署失败' }
  } finally {
    deploying.value = false
  }
}

onMounted(async () => {
  loadRecommend()
  try {
    const res = await api.getBacktests()
    backtests.value = res.items ?? []
  } catch (e: any) {
    error.value = e?.message ?? '加载失败'
  } finally {
    loading.value = false
  }
})
</script>
