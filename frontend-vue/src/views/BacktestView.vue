<template>
  <div class="p-6 space-y-6">
    <!-- Filter Bar -->
    <div class="flex items-center gap-3 flex-wrap">
      <select v-model="filterSymbol" class="bg-terminal-surface border border-terminal-border text-terminal-text text-xs rounded px-3 py-1.5 font-mono focus:outline-none focus:border-accent-blue">
        <option value="">全部股票</option>
        <option v-for="s in symbols" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="filterType" class="bg-terminal-surface border border-terminal-border text-terminal-text text-xs rounded px-3 py-1.5 font-mono focus:outline-none focus:border-accent-blue">
        <option value="">全部类型</option>
        <option value="lightgbm">lightgbm</option>
        <option value="xgboost">xgboost</option>
        <option value="lstm">lstm</option>
      </select>
      <select v-model="sortField" class="bg-terminal-surface border border-terminal-border text-terminal-text text-xs rounded px-3 py-1.5 font-mono focus:outline-none focus:border-accent-blue">
        <option value="sharpe_ratio">排序: Sharpe</option>
        <option value="annual_return">排序: 年化收益</option>
        <option value="max_drawdown">排序: 最大回撤</option>
      </select>
      <span class="text-terminal-dim text-xs ml-2">{{ filteredBacktests.length }} 条记录</span>
    </div>

    <!-- Full Backtest Table -->
    <div class="t-card overflow-x-auto">
      <div class="text-terminal-text text-sm font-semibold mb-3 border-b border-terminal-border pb-2">
        回测结果
      </div>
      <div v-if="loading" class="text-terminal-muted text-sm text-center py-8">加载中...</div>
      <div v-else-if="error" class="text-loss text-sm text-center py-8">{{ error }}</div>
      <table v-else class="w-full text-xs whitespace-nowrap">
        <thead>
          <tr class="text-terminal-dim border-b border-terminal-border">
            <th class="text-left py-2 pr-3 sticky left-0 bg-terminal-card">模型ID</th>
            <th class="text-left py-2 pr-3">股票</th>
            <th class="text-left py-2 pr-3">类型</th>
            <th class="text-right py-2 pr-3">总收益</th>
            <th class="text-right py-2 pr-3">年化收益</th>
            <th class="text-right py-2 pr-3">波动率</th>
            <th class="text-right py-2 pr-3">最大回撤</th>
            <th class="text-right py-2 pr-3">Sharpe</th>
            <th class="text-right py-2 pr-3">Sortino</th>
            <th class="text-right py-2 pr-3">Calmar</th>
            <th class="text-right py-2 pr-3">方向准确率</th>
            <th class="text-right py-2 pr-3">胜率</th>
            <th class="text-right py-2 pr-3">盈亏比</th>
            <th class="text-right py-2">交易次数</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="b in filteredBacktests"
            :key="b.model_id"
            class="border-b border-terminal-border hover:bg-terminal-surface transition-colors"
          >
            <td class="py-2 pr-3 font-mono text-terminal-text sticky left-0 bg-terminal-card truncate max-w-[120px]">{{ b.model_id }}</td>
            <td class="py-2 pr-3 font-mono text-accent-blue">{{ b.symbol }}</td>
            <td class="py-2 pr-3"><span class="t-badge">{{ b.model_type }}</span></td>
            <td class="py-2 pr-3 text-right font-mono" :class="b.total_return >= 0 ? 'text-gain' : 'text-loss'">{{ fmtPct(b.total_return) }}</td>
            <td class="py-2 pr-3 text-right font-mono" :class="b.annual_return >= 0 ? 'text-gain' : 'text-loss'">{{ fmtPct(b.annual_return) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-terminal-text">{{ fmtPct(b.volatility) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-loss">{{ fmtPct(b.max_drawdown) }}</td>
            <td class="py-2 pr-3 text-right font-mono" :class="b.sharpe_ratio >= 0 ? 'text-gain' : 'text-loss'">{{ fmtNum(b.sharpe_ratio) }}</td>
            <td class="py-2 pr-3 text-right font-mono" :class="(b.sortino_ratio ?? 0) >= 0 ? 'text-gain' : 'text-loss'">{{ fmtNum(b.sortino_ratio ?? 0) }}</td>
            <td class="py-2 pr-3 text-right font-mono" :class="(b.calmar_ratio ?? 0) >= 0 ? 'text-gain' : 'text-loss'">{{ fmtNum(b.calmar_ratio ?? 0) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-terminal-text">{{ fmtPct(b.direction_accuracy) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-terminal-text">{{ fmtPct(b.win_rate) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-terminal-text">{{ fmtNum(b.profit_factor ?? 0) }}</td>
            <td class="py-2 text-right font-mono text-terminal-text">{{ b.n_trades ?? b.total_trades ?? '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Correlation Heatmap -->
    <div class="t-card">
      <div class="text-terminal-text text-sm font-semibold mb-3 border-b border-terminal-border pb-2">
        相关性矩阵
      </div>
      <div v-if="corrLoading" class="text-terminal-muted text-sm text-center py-8">加载中...</div>
      <div v-else-if="corrError" class="text-terminal-dim text-sm text-center py-8">{{ corrError }}</div>
      <v-chart v-else class="w-full h-72" :option="heatmapOption" autoresize />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
import { api } from '@/composables/api'
import type { BacktestResult } from '@/types'
import { fmtPct, fmtNum } from '@/types'

use([CanvasRenderer, HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent])

const backtests = ref<BacktestResult[]>([])
const loading = ref(true)
const error = ref('')
const filterSymbol = ref('')
const filterType = ref('')
const sortField = ref<'sharpe_ratio' | 'annual_return' | 'max_drawdown'>('sharpe_ratio')

const corrLoading = ref(true)
const corrError = ref('')
const corrSymbols = ref<string[]>([])
const corrMatrix = ref<[number, number, number][]>([])

const symbols = ['600519', '601318', '600036', '300750', '002594']

const filteredBacktests = computed(() => {
  const field = sortField.value
  return [...backtests.value]
    .filter(b => !filterSymbol.value || b.symbol === filterSymbol.value)
    .filter(b => !filterType.value || b.model_type === filterType.value)
    .sort((a, b) => {
      const av = (a as any)[field] ?? 0
      const bv = (b as any)[field] ?? 0
      return field === 'max_drawdown' ? av - bv : bv - av
    })
})

const heatmapOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    backgroundColor: '#1a1a1a',
    borderColor: '#2a2a2a',
    textStyle: { color: '#e5e7eb', fontSize: 11 },
    formatter: (p: any) => `${corrSymbols.value[p.data[1]]} / ${corrSymbols.value[p.data[0]]}: ${fmtNum(p.data[2])}`,
  },
  grid: { top: 20, right: 20, bottom: 60, left: 60 },
  xAxis: {
    type: 'category',
    data: corrSymbols.value,
    axisLabel: { color: '#9ca3af', fontSize: 11 },
    axisLine: { lineStyle: { color: '#2a2a2a' } },
  },
  yAxis: {
    type: 'category',
    data: corrSymbols.value,
    axisLabel: { color: '#9ca3af', fontSize: 11 },
    axisLine: { lineStyle: { color: '#2a2a2a' } },
  },
  visualMap: {
    min: -1,
    max: 1,
    calculable: true,
    orient: 'horizontal',
    left: 'center',
    bottom: 0,
    inRange: { color: ['#ef4444', '#1a1a1a', '#10b981'] },
    textStyle: { color: '#9ca3af' },
  },
  series: [{
    type: 'heatmap',
    data: corrMatrix.value,
    label: { show: true, color: '#e5e7eb', fontSize: 10 },
  }],
}))

onMounted(async () => {
  try {
    const res = await api.getBacktests({ page_size: 200 })
    backtests.value = res.items ?? []
  } catch (e: any) {
    error.value = e?.message ?? '加载失败'
  } finally {
    loading.value = false
  }

  try {
    const data = await (api as any).getCorrelation()
    corrSymbols.value = data.xLabels ?? data.symbols ?? []
    // backend returns values as [x, y, value] triples already
    if (data.values) {
      corrMatrix.value = data.values.map((v: any[]) => [v[0], v[1], parseFloat((v[2] ?? 0).toFixed(2))])
    } else {
      const matrix: number[][] = data.matrix ?? []
      const flat: [number, number, number][] = []
      for (let y = 0; y < matrix.length; y++) {
        for (let x = 0; x < (matrix[y]?.length ?? 0); x++) {
          flat.push([x, y, parseFloat((matrix[y][x] ?? 0).toFixed(2))])
        }
      }
      corrMatrix.value = flat
    }
  } catch (e: any) {
    corrError.value = '相关性数据暂不可用'
  } finally {
    corrLoading.value = false
  }
})
</script>
