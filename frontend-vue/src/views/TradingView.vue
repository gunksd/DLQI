<template>
  <div class="p-6 space-y-6">
    <!-- 顶部操作栏 -->
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-terminal-text tracking-wide">模拟交易</h1>
      <button class="t-btn-primary" @click="showCreate = true">+ 新建组合</button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="bg-red-900/20 border border-loss/40 text-loss px-4 py-2 text-sm rounded">
      {{ error }}
    </div>

    <!-- 创建组合弹窗 -->
    <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div class="t-card w-full max-w-md space-y-4">
        <h2 class="text-terminal-text font-semibold text-base">新建模拟组合</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-terminal-muted text-xs mb-1">组合名称</label>
            <input v-model="form.name" type="text" placeholder="My Portfolio"
              class="w-full bg-terminal-bg border border-terminal-border text-terminal-text text-sm px-3 py-2 rounded focus:outline-none focus:border-accent-blue" />
          </div>
          <div>
            <label class="block text-terminal-muted text-xs mb-1">初始资金 (USD)</label>
            <input v-model.number="form.initial_capital" type="number" min="1000"
              class="w-full bg-terminal-bg border border-terminal-border text-terminal-text font-mono text-sm px-3 py-2 rounded focus:outline-none focus:border-accent-blue" />
          </div>
          <div>
            <label class="block text-terminal-muted text-xs mb-1">选择模型</label>
            <select v-model="form.model_id" @change="onModelSelect"
              class="w-full bg-terminal-bg border border-terminal-border text-terminal-text text-sm px-3 py-2 rounded focus:outline-none focus:border-accent-blue">
              <option value="">— 不绑定模型 —</option>
              <option v-for="m in availableModels" :key="m.id" :value="m.id">
                {{ m.name }} ({{ m.symbol }} · {{ m.model_type }})
              </option>
            </select>
            <div v-if="modelsLoading" class="text-terminal-dim text-xs mt-1">加载模型列表...</div>
          </div>
          <div v-if="form.model_id">
            <label class="block text-terminal-muted text-xs mb-1">股票代码</label>
            <div class="w-full bg-terminal-bg/50 border border-terminal-border text-accent-blue font-mono text-sm px-3 py-2 rounded">
              {{ form.symbol || '—' }}
            </div>
            <div class="text-terminal-dim text-xs mt-1">自动从所选模型获取</div>
          </div>
          <div>
            <label class="block text-terminal-muted text-xs mb-1">模拟天数</label>
            <select v-model.number="form.days"
              class="w-full bg-terminal-bg border border-terminal-border text-terminal-text text-sm px-3 py-2 rounded focus:outline-none focus:border-accent-blue">
              <option :value="30">30 天</option>
              <option :value="60">60 天</option>
              <option :value="90">90 天</option>
              <option :value="120">120 天</option>
            </select>
          </div>
        </div>
        <div class="flex gap-3 pt-2">
          <button class="t-btn-primary flex-1" :disabled="creating" @click="handleCreate">
            {{ creating ? '创建中...' : '确认创建' }}
          </button>
          <button class="t-btn-ghost flex-1" @click="closeCreate">取消</button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-terminal-muted text-sm">加载中...</div>

    <!-- 组合卡片网格 -->
    <div v-else-if="portfolios.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div v-for="p in portfolios" :key="p.id"
        class="t-card cursor-pointer transition-colors hover:border-accent-blue/50"
        :class="{ 'border-accent-blue': selectedId === p.id }"
        @click="selectPortfolio(p.id)">
        <div class="flex items-start justify-between mb-3">
          <span class="text-terminal-text font-semibold text-sm">{{ p.name }}</span>
          <span class="t-badge" :class="statusClass(p.status)">{{ p.status }}</span>
        </div>
        <div class="space-y-1 text-xs mb-4">
          <div class="flex justify-between">
            <span class="text-terminal-muted">初始资金</span>
            <span class="font-mono text-terminal-text">{{ fmtMoney(p.initial_capital) }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-terminal-muted">当前总值</span>
            <span class="font-mono" :class="p.total_value >= p.initial_capital ? 'text-gain' : 'text-loss'">
              {{ fmtMoney(p.total_value) }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-terminal-muted">持仓数量</span>
            <span class="font-mono text-terminal-text">{{ Object.keys(p.positions || {}).length }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-terminal-muted">收益率</span>
            <span class="font-mono" :class="returnRate(p) >= 0 ? 'text-gain' : 'text-loss'">
              {{ fmtPct(returnRate(p) / 100) }}
            </span>
          </div>
        </div>
        <div class="flex gap-2 border-t border-terminal-border pt-3">
          <button class="t-btn-ghost text-xs flex-1" :disabled="simulating === p.id"
            @click.stop="handleSimulate(p.id)">
            {{ simulating === p.id ? '模拟中...' : '模拟(90天)' }}
          </button>
          <button class="text-xs px-3 py-1 rounded border border-loss/40 text-loss hover:bg-loss/10 transition-colors"
            :disabled="deleting === p.id"
            @click.stop="handleDelete(p.id)">
            {{ deleting === p.id ? '...' : '删除' }}
          </button>
        </div>
      </div>
    </div>

    <div v-else class="text-terminal-muted text-sm">暂无模拟组合，点击"新建组合"开始。</div>

    <!-- 详情面板 -->
    <div v-if="selectedId && detail" class="space-y-4">
      <div class="border-t border-terminal-border pt-4">
        <h2 class="text-terminal-text font-semibold text-sm mb-4">
          组合详情 — {{ detail.name }}
        </h2>

        <!-- 权益曲线 -->
        <div class="t-card mb-4">
          <div class="text-terminal-muted text-xs mb-3">权益曲线</div>
          <div v-if="equityLoading" class="text-terminal-muted text-xs">加载中...</div>
          <v-chart v-else-if="equityOption" :option="equityOption" style="height:240px" autoresize />
          <div v-else class="text-terminal-dim text-xs">暂无权益数据</div>
        </div>

        <!-- 交易记录 -->
        <div class="t-card">
          <div class="text-terminal-muted text-xs mb-3">交易记录</div>
          <div v-if="tradesLoading" class="text-terminal-muted text-xs">加载中...</div>
          <div v-else-if="trades.length" class="overflow-x-auto">
            <table class="t-table w-full text-xs">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>股票</th>
                  <th>方向</th>
                  <th class="text-right">数量</th>
                  <th class="text-right">价格</th>
                  <th class="text-right">手续费</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in trades" :key="t.id">
                  <td class="font-mono text-terminal-dim">{{ fmtTime(t.timestamp) }}</td>
                  <td class="font-mono text-accent-blue">{{ t.symbol }}</td>
                  <td>
                    <span class="t-badge" :class="t.side === 'buy' ? 'text-gain border-gain/30' : 'text-loss border-loss/30'">
                      {{ t.side === 'buy' ? '买入' : '卖出' }}
                    </span>
                  </td>
                  <td class="font-mono text-right">{{ t.quantity }}</td>
                  <td class="font-mono text-right">{{ fmtMoney(t.price) }}</td>
                  <td class="font-mono text-right text-terminal-muted">{{ fmtMoney(t.commission) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-terminal-dim text-xs">暂无交易记录</div>
        </div>
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
import type { PaperPortfolio, PaperTrade } from '@/types'
import { fmtPct, fmtNum, fmtMoney } from '@/types'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const portfolios = ref<PaperPortfolio[]>([])
const loading = ref(false)
const error = ref('')
const showCreate = ref(false)
const creating = ref(false)
const simulating = ref<string | null>(null)
const deleting = ref<string | null>(null)

const selectedId = ref<string | null>(null)
const detail = computed(() => portfolios.value.find(p => p.id === selectedId.value) ?? null)

const equityData = ref<{ date: string; equity: number }[]>([])
const equityLoading = ref(false)
const trades = ref<PaperTrade[]>([])
const tradesLoading = ref(false)

interface ModelOption { id: string; name: string; symbol: string; model_type: string }
const availableModels = ref<ModelOption[]>([])
const modelsLoading = ref(false)

const form = ref({ name: '', initial_capital: 100000, model_id: '', symbol: '', days: 90 })

function onModelSelect() {
  const m = availableModels.value.find(m => m.id === form.value.model_id)
  form.value.symbol = m?.symbol ?? ''
}

async function loadModels() {
  modelsLoading.value = true
  try {
    const res = await api.getModels() as any
    const list = Array.isArray(res) ? res : (res?.items ?? res?.models ?? [])
    availableModels.value = list.map((m: any) => ({
      id: String(m.model_id ?? m.id ?? ''),
      name: m.name ?? m.model_id ?? String(m.id),
      symbol: m.symbol ?? '',
      model_type: m.model_type ?? '',
    }))
  } catch {
    availableModels.value = []
  } finally {
    modelsLoading.value = false
  }
}

const returnRate = (p: PaperPortfolio) =>
  p.initial_capital > 0 ? ((p.total_value - p.initial_capital) / p.initial_capital) * 100 : 0

const statusClass = (s: string) => {
  if (s === 'active') return 'text-gain border-gain/30'
  if (s === 'simulated') return 'text-accent-blue border-accent-blue/30'
  return 'text-terminal-muted border-terminal-border'
}

const fmtTime = (ts: string) => {
  try { return new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }
  catch { return ts }
}

const equityOption = computed(() => {
  if (!equityData.value.length) return null
  const dates = equityData.value.map(d => d.date)
  const values = equityData.value.map(d => d.equity)
  return {
    backgroundColor: 'transparent',
    grid: { top: 16, right: 16, bottom: 32, left: 64 },
    tooltip: { trigger: 'axis', backgroundColor: '#1a1a1a', borderColor: '#2a2a2a', textStyle: { color: '#e5e7eb', fontSize: 11 } },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#2a2a2a' } }, axisLabel: { color: '#6b7280', fontSize: 10 } },
    yAxis: { type: 'value', axisLine: { lineStyle: { color: '#2a2a2a' } }, splitLine: { lineStyle: { color: '#1a1a1a' } }, axisLabel: { color: '#6b7280', fontSize: 10, formatter: (v: number) => `$${(v / 1000).toFixed(0)}k` } },
    series: [{ type: 'line', data: values, smooth: true, symbol: 'none', lineStyle: { color: '#3b82f6', width: 2 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.25)' }, { offset: 1, color: 'rgba(59,130,246,0)' }] } } }],
  }
})

async function loadPortfolios() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getPortfolios() as any
    portfolios.value = Array.isArray(res) ? res : (res?.items ?? res?.portfolios ?? [])
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function selectPortfolio(id: string) {
  if (selectedId.value === id) { selectedId.value = null; return }
  selectedId.value = id
  equityLoading.value = true
  tradesLoading.value = true
  try {
    const [eq, tr] = await Promise.all([api.getPortfolioEquity(id), api.getPortfolioTrades(id)]) as any[]
    const rawEquity = Array.isArray(eq) ? eq : (eq?.data ?? eq?.equity_curve ?? [])
    equityData.value = rawEquity.map((d: any) => ({ date: d.date, equity: d.value ?? d.equity ?? 0 }))
    trades.value = Array.isArray(tr) ? tr : (tr?.items ?? tr?.trades ?? [])
  } catch {
    equityData.value = []
    trades.value = []
  } finally {
    equityLoading.value = false
    tradesLoading.value = false
  }
}

async function handleCreate() {
  if (!form.value.name.trim()) return
  creating.value = true
  try {
    const payload: any = { name: form.value.name, initial_capital: form.value.initial_capital }
    if (form.value.model_id.trim()) payload.model_id = form.value.model_id.trim()
    if (form.value.symbol.trim()) payload.symbol = form.value.symbol.trim()
    const created = await api.createPortfolio(payload) as any
    const newId = created?.id
    const modelIdForSim = form.value.model_id
    const daysForSim = form.value.days
    await loadPortfolios()
    closeCreate()
    // 创建后自动触发模拟
    if (newId && modelIdForSim) {
      simulating.value = newId
      try {
        await api.simulatePortfolio(newId, daysForSim)
        await loadPortfolios()
        selectPortfolio(newId)
      } catch (e: any) {
        error.value = '模拟失败: ' + e.message
      } finally {
        simulating.value = null
      }
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    creating.value = false
  }
}

function closeCreate() {
  showCreate.value = false
  form.value = { name: '', initial_capital: 100000, model_id: '', symbol: '', days: 90 }
}

async function handleSimulate(id: string) {
  simulating.value = id
  try {
    await api.simulatePortfolio(id, 90)
    await loadPortfolios()
    if (selectedId.value === id) await selectPortfolio(id)
  } catch (e: any) {
    error.value = e.message
  } finally {
    simulating.value = null
  }
}

async function handleDelete(id: string) {
  if (!confirm('确认删除该组合？')) return
  deleting.value = id
  try {
    await api.deletePortfolio(id)
    if (selectedId.value === id) selectedId.value = null
    await loadPortfolios()
  } catch (e: any) {
    error.value = e.message
  } finally {
    deleting.value = null
  }
}

onMounted(() => { loadPortfolios(); loadModels() })
</script>
