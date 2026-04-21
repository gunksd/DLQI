<template>
  <div class="p-6 space-y-6">
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
      </select>
      <span class="text-terminal-dim text-xs ml-2">{{ comparisonRows.length }} 个模型</span>
    </div>

    <div v-if="loading" class="text-terminal-muted text-sm text-center py-12">加载中...</div>
    <div v-else-if="error" class="text-loss text-sm text-center py-12">{{ error }}</div>

    <!-- Performance Comparison Table -->
    <div v-else class="t-card">
      <div class="text-terminal-text text-sm font-semibold mb-1 border-b border-terminal-border pb-2">
        性能对比
      </div>
      <div class="text-terminal-dim text-xs mb-3">
        Sharpe = 风险调整收益 | 超额收益 = 策略收益 - 买入持有收益 | 交易≤1次的模型本质上等于买入持有
      </div>
      <div class="overflow-x-auto">
      <table class="w-full text-xs">
        <thead>
          <tr class="text-terminal-dim border-b border-terminal-border">
            <th class="text-left py-2 pr-3">模型</th>
            <th class="text-left py-2 pr-3">股票</th>
            <th class="text-left py-2 pr-3">类型</th>
            <th class="text-right py-2 pr-3">Sharpe</th>
            <th class="text-right py-2 pr-3">年化收益</th>
            <th class="text-right py-2 pr-3">超额收益</th>
            <th class="text-right py-2 pr-3">最大回撤</th>
            <th class="text-right py-2 pr-3">方向准确率</th>
            <th class="text-right py-2 pr-3">交易次数</th>
            <th class="text-right py-2">胜率</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="m in comparisonRows"
            :key="m.model_id"
            class="border-b border-terminal-border hover:bg-terminal-card transition-colors"
            :class="(m.n_trades ?? 0) <= 1 ? 'opacity-50' : ''"
          >
            <td class="py-2 pr-3 font-mono text-terminal-text truncate max-w-[120px]">{{ m.model_id }}</td>
            <td class="py-2 pr-3 font-mono" :class="m.symbol === 'MULTI' ? 'text-gain' : 'text-accent-blue'">
              {{ m.symbol === 'MULTI' ? '全股票' : m.symbol }}
            </td>
            <td class="py-2 pr-3"><span class="t-badge">{{ m.model_type }}</span></td>
            <td class="py-2 pr-3 text-right font-mono" :class="(m.sharpe_ratio ?? 0) >= 1 ? 'text-gain' : (m.sharpe_ratio ?? 0) < 0 ? 'text-loss' : 'text-terminal-text'">{{ fmtNum(m.sharpe_ratio) }}</td>
            <td class="py-2 pr-3 text-right font-mono" :class="(m.annual_return ?? 0) >= 0 ? 'text-gain' : 'text-loss'">{{ fmtPct(m.annual_return) }}</td>
            <td class="py-2 pr-3 text-right font-mono" :class="(m.excess_return ?? 0) > 0 ? 'text-gain' : (m.excess_return ?? 0) < -0.01 ? 'text-loss' : 'text-terminal-dim'">{{ fmtPct(m.excess_return) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-loss">{{ fmtPct(m.max_drawdown) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-terminal-text">{{ fmtPct(m.direction_accuracy) }}</td>
            <td class="py-2 pr-3 text-right font-mono text-terminal-text">
              {{ m.n_trades ?? '-' }}
              <span v-if="(m.n_trades ?? 0) <= 1" class="text-terminal-dim">(持有)</span>
            </td>
            <td class="py-2 text-right font-mono text-terminal-text">{{ fmtPct(m.win_rate) }}</td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/composables/api'
import type { ModelInfo } from '@/types'
import { fmtPct, fmtNum } from '@/types'

const models = ref<ModelInfo[]>([])
const comparisonData = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const filterSymbol = ref('')
const filterType = ref('')

const symbols = ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'NVDA']

const filteredModels = computed(() =>
  models.value
    .filter(m => !filterSymbol.value || m.symbol === filterSymbol.value)
    .filter(m => !filterType.value || m.model_type === filterType.value)
)

const comparisonRows = computed(() =>
  [...(comparisonData.value.length ? comparisonData.value : filteredModels.value)]
    .filter(m => !filterSymbol.value || m.symbol === filterSymbol.value)
    .filter(m => !filterType.value || m.model_type === filterType.value)
    .sort((a, b) => (b.sharpe_ratio ?? 0) - (a.sharpe_ratio ?? 0))
)

onMounted(async () => {
  try {
    const [res, cmp] = await Promise.all([api.getModels(), api.compareModels()])
    models.value = res.items ?? []
    comparisonData.value = (cmp as any)?.models ?? []
  } catch (e: any) {
    error.value = e?.message ?? '加载失败'
  } finally {
    loading.value = false
  }
})
</script>
