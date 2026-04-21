<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-terminal-text tracking-wide">参数调优</h1>
      <div class="flex gap-2">
        <button class="t-btn-ghost text-xs" @click="resetDefaults">重置默认值</button>
        <button class="t-btn-primary text-xs" @click="applyBest" :disabled="!topResults.length">
          应用最优参数
        </button>
      </div>
    </div>

    <div class="flex flex-col xl:flex-row gap-6">
      <!-- 左侧参数配置面板 -->
      <div class="xl:w-80 shrink-0 space-y-3">
        <!-- 训练模式选择 -->
        <div class="t-card space-y-3">
          <div class="text-terminal-text text-xs font-semibold uppercase tracking-wider">训练配置</div>
          <div class="space-y-2">
            <label class="text-terminal-muted text-xs">训练模式</label>
            <div class="flex gap-2">
              <button class="flex-1 text-xs py-1.5 rounded border transition-colors"
                :class="trainMode === 'single' ? 'border-accent-blue bg-accent-blue/10 text-accent-blue' : 'border-terminal-border text-terminal-dim hover:border-terminal-muted'"
                @click="trainMode = 'single'">单股票</button>
              <button class="flex-1 text-xs py-1.5 rounded border transition-colors"
                :class="trainMode === 'multi' ? 'border-accent-blue bg-accent-blue/10 text-accent-blue' : 'border-terminal-border text-terminal-dim hover:border-terminal-muted'"
                @click="trainMode = 'multi'">多股票联合</button>
            </div>
          </div>
          <div v-if="trainMode === 'single'" class="space-y-2">
            <label class="text-terminal-muted text-xs">股票</label>
            <select v-model="trainSymbol"
              class="w-full bg-terminal-bg border border-terminal-border text-terminal-text text-xs px-2 py-1.5 rounded focus:outline-none focus:border-accent-blue font-mono">
              <option v-for="s in trainSymbols" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>
          <div class="space-y-2">
            <label class="text-terminal-muted text-xs">模型类型</label>
            <select v-model="trainModelType"
              class="w-full bg-terminal-bg border border-terminal-border text-terminal-text text-xs px-2 py-1.5 rounded focus:outline-none focus:border-accent-blue font-mono">
              <option value="transformer">Transformer</option>
              <option value="lstm">LSTM</option>
              <option value="lightgbm">LightGBM</option>
              <option value="xgboost">XGBoost</option>
            </select>
          </div>
          <button class="t-btn-primary w-full text-xs" :disabled="training" @click="startTraining">
            <span v-if="training" class="flex items-center justify-center gap-2">
              <span class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              训练中 {{ trainProgress }}%
            </span>
            <span v-else>{{ trainMode === 'multi' ? '开始多股票联合训练' : '开始训练' }}</span>
          </button>
          <!-- 训练进度 -->
          <div v-if="training || trainResult" class="space-y-2">
            <div v-if="training" class="space-y-1">
              <div class="w-full bg-terminal-border rounded-full h-1.5">
                <div class="bg-accent-blue h-1.5 rounded-full transition-all duration-300"
                  :style="{ width: trainProgress + '%' }"></div>
              </div>
              <div class="text-terminal-dim text-xs font-mono">{{ trainStep }}</div>
            </div>
            <div v-if="trainResult" class="text-xs space-y-1">
              <div class="text-gain font-semibold">训练完成</div>
              <div class="text-terminal-muted font-mono">模型: {{ trainResult.model_id }}</div>
              <div class="text-terminal-muted font-mono">Val Loss: {{ trainResult.val_loss?.toFixed(6) }}</div>
            </div>
            <div v-if="trainError" class="text-xs text-loss">{{ trainError }}</div>
          </div>
        </div>

        <div v-for="group in paramGroups" :key="group.key" class="t-card">
          <button class="w-full flex items-center justify-between text-left"
            @click="toggleGroup(group.key)">
            <span class="text-terminal-text text-xs font-semibold uppercase tracking-wider">{{ group.label }}</span>
            <span class="text-terminal-dim text-xs">{{ collapsed[group.key] ? '▶' : '▼' }}</span>
          </button>
          <div v-show="!collapsed[group.key]" class="mt-3 space-y-4">
            <div v-for="p in group.params" :key="p.key">
              <div class="flex justify-between items-center mb-1">
                <label class="text-terminal-muted text-xs">{{ p.label }}</label>
                <span class="font-mono text-accent-blue text-xs">{{ formatParamVal(p, params[p.key]) }}</span>
              </div>
              <input type="range" :min="p.min" :max="p.max" :step="p.step"
                v-model.number="params[p.key]"
                class="w-full h-1 accent-accent-blue cursor-pointer" />
              <div class="flex justify-between text-terminal-dim text-xs mt-0.5">
                <span class="font-mono">{{ p.min }}</span>
                <span class="font-mono">{{ p.max }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧结果展示 -->
      <div class="flex-1 space-y-4">
        <div class="t-card">
          <div class="text-terminal-muted text-xs mb-3">模型 Sharpe 分布（真实回测结果）</div>
          <v-chart :option="scatterOption" style="height:260px" autoresize />
        </div>

        <div class="t-card">
          <div class="text-terminal-muted text-xs mb-3">
            最优模型 Top 5（按 Sharpe 排序）
            <span v-if="resultsLoading" class="ml-2 text-terminal-dim">加载中...</span>
          </div>
          <div class="overflow-x-auto">
            <table class="t-table w-full text-xs">
              <thead>
                <tr>
                  <th class="text-center">排名</th>
                  <th>模型</th>
                  <th>股票</th>
                  <th class="text-right">Sharpe</th>
                  <th class="text-right">年化收益</th>
                  <th class="text-right">最大回撤</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in topResults" :key="i"
                  :class="i === 0 ? 'bg-accent-blue/5' : ''">
                  <td class="text-center font-mono">
                    <span v-if="i === 0" class="text-gain font-bold">#1</span>
                    <span v-else class="text-terminal-muted">#{{ i + 1 }}</span>
                  </td>
                  <td class="font-mono text-terminal-dim text-xs truncate max-w-[120px]">{{ r.model_id }}</td>
                  <td class="font-mono text-accent-blue">{{ r.symbol }}</td>
                  <td class="font-mono text-right" :class="r.sharpe >= 1 ? 'text-gain' : 'text-terminal-text'">
                    {{ r.sharpe.toFixed(3) }}
                  </td>
                  <td class="font-mono text-right" :class="r.annual_return >= 0 ? 'text-gain' : 'text-loss'">
                    {{ (r.annual_return * 100).toFixed(1) }}%
                  </td>
                  <td class="font-mono text-right text-loss">
                    {{ (r.max_drawdown * 100).toFixed(1) }}%
                  </td>
                </tr>
                <tr v-if="!topResults.length && !resultsLoading">
                  <td colspan="6" class="text-center text-terminal-dim py-4">暂无回测数据</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { api } from '@/composables/api'

use([CanvasRenderer, ScatterChart, GridComponent, TooltipComponent])

// 训练配置
const trainMode = ref<'single' | 'multi'>('single')
const trainSymbol = ref('AAPL')
const trainModelType = ref('transformer')
const trainSymbols = ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'NVDA']

// 训练状态
const training = ref(false)
const trainProgress = ref(0)
const trainStep = ref('')
const trainResult = ref<any>(null)
const trainError = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

async function startTraining() {
  training.value = true
  trainProgress.value = 0
  trainStep.value = '提交训练任务...'
  trainResult.value = null
  trainError.value = ''

  try {
    let res: any
    if (trainMode.value === 'multi') {
      res = await api.trainMultiStock({
        model_type: trainModelType.value,
        epochs: params.epochs,
      })
    } else {
      res = await api.trainModel({
        symbol: trainSymbol.value,
        model_type: trainModelType.value,
        epochs: params.epochs,
      })
    }

    const jobId = res.job_id
    trainStep.value = '训练已提交，等待执行...'

    pollTimer = setInterval(async () => {
      try {
        const job: any = await api.getJob(jobId)
        trainProgress.value = Math.round((job.progress ?? 0) * 100)
        trainStep.value = job.current_step ?? job.message ?? '训练中...'

        if (job.status === 'completed') {
          clearInterval(pollTimer!)
          pollTimer = null
          training.value = false
          trainResult.value = job.result ?? {}
          // 刷新回测数据
          const btRes = await api.getBacktests({ page_size: 200 }) as any
          allResults.value = btRes.items ?? []
        } else if (job.status === 'failed') {
          clearInterval(pollTimer!)
          pollTimer = null
          training.value = false
          trainError.value = job.error ?? '训练失败'
        }
      } catch {
        // 轮询出错时继续等待
      }
    }, 2000)
  } catch (e: any) {
    training.value = false
    trainError.value = e.message ?? '提交失败'
  }
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 参数分组定义
const paramGroups = [
  {
    key: 'model',
    label: '模型参数',
    params: [
      { key: 'lr', label: '学习率', min: 0.001, max: 0.1, step: 0.001, fmt: 'float4' },
      { key: 'hidden', label: '隐藏层大小', min: 32, max: 512, step: 32, fmt: 'int' },
      { key: 'layers', label: '层数', min: 1, max: 6, step: 1, fmt: 'int' },
      { key: 'dropout', label: 'Dropout', min: 0, max: 0.5, step: 0.05, fmt: 'float2' },
    ],
  },
  {
    key: 'train',
    label: '训练参数',
    params: [
      { key: 'batch_size', label: '批次大小', min: 16, max: 256, step: 16, fmt: 'int' },
      { key: 'epochs', label: 'Epochs', min: 10, max: 200, step: 10, fmt: 'int' },
      { key: 'lookback', label: '回望窗口', min: 20, max: 120, step: 5, fmt: 'int' },
    ],
  },
  {
    key: 'strategy',
    label: '策略参数',
    params: [
      { key: 'hold_period', label: '持仓周期', min: 1, max: 20, step: 1, fmt: 'int' },
      { key: 'stop_loss', label: '止损', min: 0.01, max: 0.1, step: 0.01, fmt: 'pct' },
      { key: 'take_profit', label: '止盈', min: 0.05, max: 0.3, step: 0.01, fmt: 'pct' },
      { key: 'position_size', label: '仓位大小', min: 0.1, max: 1.0, step: 0.1, fmt: 'float2' },
    ],
  },
]

const defaults: Record<string, number> = {
  lr: 0.01, hidden: 128, layers: 2, dropout: 0.1,
  batch_size: 64, epochs: 50, lookback: 60,
  hold_period: 5, stop_loss: 0.03, take_profit: 0.1, position_size: 0.5,
}

const params = reactive<Record<string, number>>({ ...defaults })
const collapsed = reactive<Record<string, boolean>>({ model: false, train: false, strategy: false })

function toggleGroup(key: string) { collapsed[key] = !collapsed[key] }
function resetDefaults() { Object.assign(params, defaults) }

function formatParamVal(p: any, v: number): string {
  if (p.fmt === 'int') return String(Math.round(v))
  if (p.fmt === 'pct') return `${(v * 100).toFixed(0)}%`
  if (p.fmt === 'float4') return v.toFixed(4)
  return v.toFixed(2)
}

// 真实回测结果
const allResults = ref<any[]>([])
const resultsLoading = ref(false)

const topResults = computed(() =>
  [...allResults.value]
    .sort((a, b) => (b.sharpe_ratio ?? 0) - (a.sharpe_ratio ?? 0))
    .slice(0, 5)
    .map(r => ({
      sharpe: r.sharpe_ratio ?? 0,
      annual_return: r.annual_return ?? 0,
      max_drawdown: r.max_drawdown ?? 0,
      lr: 0.01,
      hidden: 128,
      epochs: 50,
      model_id: r.model_id ?? '',
      symbol: r.symbol ?? '',
      model_type: r.model_type ?? '',
    }))
)

const historyData = computed(() =>
  allResults.value.map((r, i) => [i + 1, parseFloat((r.sharpe_ratio ?? 0).toFixed(3))])
)

const scatterOption = computed(() => ({
  backgroundColor: 'transparent',
  grid: { top: 16, right: 24, bottom: 36, left: 56 },
  tooltip: {
    trigger: 'item',
    backgroundColor: '#1a1a1a',
    borderColor: '#2a2a2a',
    textStyle: { color: '#e5e7eb', fontSize: 11 },
    formatter: (p: any) => {
      const r = allResults.value[p.data[0] - 1]
      return `${r?.model_id ?? ''}<br/>Sharpe: <b>${p.data[1]}</b>`
    },
  },
  xAxis: {
    type: 'value', name: '模型序号', nameTextStyle: { color: '#6b7280', fontSize: 10 },
    axisLine: { lineStyle: { color: '#2a2a2a' } },
    splitLine: { lineStyle: { color: '#1a1a1a' } },
    axisLabel: { color: '#6b7280', fontSize: 10 },
  },
  yAxis: {
    type: 'value', name: 'Sharpe', nameTextStyle: { color: '#6b7280', fontSize: 10 },
    axisLine: { lineStyle: { color: '#2a2a2a' } },
    splitLine: { lineStyle: { color: '#1a1a1a' } },
    axisLabel: { color: '#6b7280', fontSize: 10 },
  },
  series: [{
    type: 'scatter',
    data: historyData.value,
    symbolSize: 6,
    itemStyle: {
      color: (p: any) => p.data[1] >= 1.5 ? '#10b981' : p.data[1] >= 1.0 ? '#3b82f6' : '#6b7280',
      opacity: 0.8,
    },
  }],
}))

function applyBest() {
  if (!topResults.value.length) return
  const best = topResults.value[0]
  params.lr = best.lr
  params.hidden = best.hidden
  params.epochs = best.epochs
}

onMounted(async () => {
  resultsLoading.value = true
  try {
    const res = await api.getBacktests({ page_size: 200 }) as any
    allResults.value = res.items ?? []
  } catch {
    allResults.value = []
  } finally {
    resultsLoading.value = false
  }
})
</script>
