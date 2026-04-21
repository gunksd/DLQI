<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-terminal-text tracking-wide">数据管理</h1>
    </div>

    <!-- Toast 提示 -->
    <div v-if="toast.show" class="fixed top-4 right-4 z-50 px-4 py-2 rounded text-sm font-medium shadow-lg transition-all"
      :class="toast.type === 'success' ? 'bg-gain/20 border border-gain/40 text-gain' : 'bg-loss/20 border border-loss/40 text-loss'">
      {{ toast.message }}
    </div>

    <!-- 数据源状态 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div v-if="sourcesLoading" class="t-card col-span-3 text-terminal-muted text-xs">加载数据源...</div>
      <div v-else v-for="src in sources" :key="src.name" class="t-card">
        <div class="flex items-center justify-between mb-1">
          <span class="text-terminal-text text-sm font-semibold">{{ src.name }}</span>
          <span class="t-badge" :class="['connected','available','healthy'].includes(src.status) ? 'text-gain border-gain/30' : 'text-loss border-loss/30'">
            {{ ['connected','available','healthy'].includes(src.status) ? 'ONLINE' : src.status?.toUpperCase() ?? 'ERROR' }}
          </span>
        </div>
        <div class="text-terminal-dim text-xs">{{ src.description ?? src.message ?? '—' }}</div>
        <div v-if="src.last_sync" class="text-terminal-dim text-xs mt-1 font-mono">
          最后同步: {{ fmtTime(src.last_sync) }}
        </div>
      </div>
    </div>

    <!-- 批量同步操作栏 -->
    <div class="t-card space-y-4">
      <div class="text-terminal-muted text-xs font-semibold uppercase tracking-wider">批量同步</div>
      <div class="flex flex-wrap gap-3">
        <label v-for="sym in allSymbols" :key="sym" class="flex items-center gap-1.5 cursor-pointer">
          <input type="checkbox" v-model="selectedSymbols" :value="sym" class="accent-accent-blue" />
          <span class="font-mono text-terminal-text text-xs">{{ sym }}</span>
        </label>
      </div>
      <div class="flex flex-wrap gap-3 items-end">
        <div>
          <label class="block text-terminal-muted text-xs mb-1">开始日期</label>
          <input type="date" v-model="syncStart"
            class="bg-terminal-bg border border-terminal-border text-terminal-text font-mono text-xs px-3 py-1.5 rounded focus:outline-none focus:border-accent-blue" />
        </div>
        <div>
          <label class="block text-terminal-muted text-xs mb-1">结束日期</label>
          <input type="date" v-model="syncEnd"
            class="bg-terminal-bg border border-terminal-border text-terminal-text font-mono text-xs px-3 py-1.5 rounded focus:outline-none focus:border-accent-blue" />
        </div>
        <button class="t-btn-primary text-xs" :disabled="syncing || !selectedSymbols.length" @click="handleSync">
          <span v-if="syncing" class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            同步中...
          </span>
          <span v-else>同步数据</span>
        </button>
        <button class="t-btn-ghost text-xs" :disabled="batchSyncing" @click="handleBatchDownload">
          <span v-if="batchSyncing" class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            批量下载中...
          </span>
          <span v-else>S&amp;P 500 批量下载</span>
        </button>
      </div>
    </div>

    <!-- 数据质量 & 存储统计 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="t-card">
        <div class="text-terminal-muted text-xs font-semibold uppercase tracking-wider mb-3">数据质量</div>
        <div v-if="qualityLoading" class="text-terminal-dim text-xs">加载中...</div>
        <div v-else-if="quality" class="grid grid-cols-2 gap-3 text-xs">
          <div>
            <div class="text-terminal-dim">文件数</div>
            <div class="font-mono text-terminal-text text-lg">{{ quality.file_count ?? 0 }}</div>
          </div>
          <div>
            <div class="text-terminal-dim">总记录数</div>
            <div class="font-mono text-terminal-text text-lg">{{ (quality.total_rows ?? 0).toLocaleString() }}</div>
          </div>
          <div>
            <div class="text-terminal-dim">完整度</div>
            <div class="font-mono text-gain text-lg">{{ ((quality.completeness ?? 0) * 100).toFixed(1) }}%</div>
          </div>
          <div>
            <div class="text-terminal-dim">日期范围</div>
            <div class="font-mono text-terminal-text text-sm">{{ quality.date_range ?? '-' }}</div>
          </div>
        </div>
      </div>
      <div class="t-card">
        <div class="text-terminal-muted text-xs font-semibold uppercase tracking-wider mb-3">存储统计</div>
        <div v-if="storageLoading" class="text-terminal-dim text-xs">加载中...</div>
        <div v-else-if="storage" class="grid grid-cols-2 gap-3 text-xs">
          <div>
            <div class="text-terminal-dim">原始数据</div>
            <div class="font-mono text-terminal-text text-lg">{{ storage.raw_size ?? '-' }}</div>
          </div>
          <div>
            <div class="text-terminal-dim">模型文件</div>
            <div class="font-mono text-terminal-text text-lg">{{ storage.models_size ?? '-' }}</div>
          </div>
          <div>
            <div class="text-terminal-dim">回测结果</div>
            <div class="font-mono text-terminal-text text-lg">{{ storage.results_size ?? '-' }}</div>
          </div>
          <div>
            <div class="text-terminal-dim">总计</div>
            <div class="font-mono text-accent-blue text-lg">{{ storage.total_size ?? '-' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 股票数据列表 -->
    <div class="t-card">
      <div class="flex items-center justify-between mb-3">
        <div class="text-terminal-muted text-xs font-semibold uppercase tracking-wider">股票数据</div>
        <input v-model="search" type="text" placeholder="搜索股票代码..."
          class="bg-terminal-bg border border-terminal-border text-terminal-text text-xs px-3 py-1.5 rounded w-40 focus:outline-none focus:border-accent-blue font-mono" />
      </div>

      <div v-if="stocksLoading" class="text-terminal-muted text-xs">加载中...</div>
      <div v-else-if="filteredStocks.length" class="overflow-x-auto">
        <table class="t-table w-full text-xs">
          <thead>
            <tr>
              <th>股票代码</th>
              <th class="text-right">数据点数</th>
              <th class="text-right">最新日期</th>
              <th class="text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in filteredStocks" :key="s.symbol">
              <td class="font-mono text-accent-blue font-semibold">{{ s.symbol }}</td>
              <td class="font-mono text-right text-terminal-text">{{ (s as any).records ?? (s as any).data_points ?? '—' }}</td>
              <td class="font-mono text-right text-terminal-muted">{{ (s as any).last_update ?? (s as any).last_date ?? '—' }}</td>
              <td class="text-right">
                <button class="text-xs px-2 py-0.5 rounded border border-accent-blue/30 text-accent-blue hover:bg-accent-blue/10 transition-colors"
                  :disabled="syncingSingle === s.symbol"
                  @click="syncSingle(s.symbol)">
                  {{ syncingSingle === s.symbol ? '...' : '同步' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="text-terminal-dim text-xs py-4 text-center">
        {{ search ? '未找到匹配的股票' : '暂无股票数据' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/composables/api'
import { useDataStore } from '@/stores/data'

const allSymbols = ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'NVDA']
const selectedSymbols = ref<string[]>([...allSymbols])

const today = new Date().toISOString().slice(0, 10)
const oneYearAgo = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10)
const syncStart = ref(oneYearAgo)
const syncEnd = ref(today)

const syncing = ref(false)
const syncingSingle = ref<string | null>(null)
const batchSyncing = ref(false)
const search = ref('')
const toast = ref({ show: false, type: 'success', message: '' })
const quality = ref<any>(null)
const qualityLoading = ref(false)
const storage = ref<any>(null)
const storageLoading = ref(false)

const dataStore = useDataStore()
const sources = computed(() => dataStore.sources)
const sourcesLoading = computed(() => dataStore.sourcesLoading)
const stocks = computed(() => dataStore.stocks)
const stocksLoading = computed(() => dataStore.stocksLoading)

const filteredStocks = computed(() => {
  if (!search.value.trim()) return stocks.value
  return stocks.value.filter(s => s.symbol.toLowerCase().includes(search.value.toLowerCase()))
})

const fmtTime = (ts: string) => {
  try { return new Date(ts).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }) }
  catch { return ts }
}

function showToast(type: 'success' | 'error', message: string) {
  toast.value = { show: true, type, message }
  setTimeout(() => { toast.value.show = false }, 3000)
}

async function handleSync() {
  if (!selectedSymbols.value.length) return
  syncing.value = true
  try {
    await api.syncData({ symbols: selectedSymbols.value, start_date: syncStart.value, end_date: syncEnd.value })
    showToast('success', `已同步 ${selectedSymbols.value.join(', ')}`)
    await dataStore.loadStocks(true)
  } catch (e: any) {
    showToast('error', e.message ?? '同步失败')
  } finally {
    syncing.value = false
  }
}

async function syncSingle(symbol: string) {
  syncingSingle.value = symbol
  try {
    await api.syncData({ symbols: [symbol], start_date: syncStart.value, end_date: syncEnd.value })
    showToast('success', `${symbol} 同步成功`)
    await dataStore.loadStocks(true)
  } catch (e: any) {
    showToast('error', `${symbol} 同步失败: ${e.message}`)
  } finally {
    syncingSingle.value = null
  }
}

const sp500Core = [
  'AAPL','MSFT','AMZN','NVDA','GOOGL','META','TSLA','BRK-B','LLY','AVGO',
  'JPM','UNH','XOM','V','PG','MA','COST','JNJ','HD','MRK',
  'ABBV','WMT','NFLX','BAC','CRM','CVX','KO','AMD','PEP','LIN',
  'TMO','ORCL','ACN','MCD','CSCO','ADBE','ABT','WFC','DHR','GE',
  'TXN','PM','QCOM','INTU','CMCSA','DIS','VZ','AMGN','IBM','CAT',
]

async function handleBatchDownload() {
  batchSyncing.value = true
  try {
    await api.syncData({ symbols: sp500Core, start_date: '2016-01-01', end_date: today })
    showToast('success', `已提交 ${sp500Core.length} 只股票批量下载`)
    await dataStore.loadStocks(true)
    await loadQualityAndStorage()
  } catch (e: any) {
    showToast('error', `批量下载失败: ${e.message}`)
  } finally {
    batchSyncing.value = false
  }
}

async function loadQualityAndStorage() {
  qualityLoading.value = true
  storageLoading.value = true
  try {
    const [q, s] = await Promise.all([api.getDataQuality(), api.getStorageStats()])
    quality.value = q
    storage.value = s
  } catch { /* 静默 */ }
  finally {
    qualityLoading.value = false
    storageLoading.value = false
  }
}

onMounted(() => {
  dataStore.loadSources()
  dataStore.loadStocks()
  loadQualityAndStorage()
})
</script>
