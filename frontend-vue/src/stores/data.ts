import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/composables/api'
import type { StockInfo } from '@/types'

export const useDataStore = defineStore('data', () => {
  const stocks = ref<StockInfo[]>([])
  const sources = ref<any[]>([])
  const stocksLoaded = ref(false)
  const sourcesLoaded = ref(false)
  const stocksLoading = ref(false)
  const sourcesLoading = ref(false)

  async function loadStocks(force = false) {
    if (stocksLoaded.value && !force) return
    stocksLoading.value = true
    try {
      const res = await api.getStocks({ page_size: 100 }) as any
      stocks.value = Array.isArray(res) ? res : (res?.stocks ?? res?.items ?? [])
      stocksLoaded.value = true
    } catch {
      stocks.value = []
    } finally {
      stocksLoading.value = false
    }
  }

  async function loadSources(force = false) {
    if (sourcesLoaded.value && !force) return
    sourcesLoading.value = true
    try {
      const res = await api.getDataSources() as any
      sources.value = Array.isArray(res) ? res : (res?.sources ?? [])
      sourcesLoaded.value = true
    } catch {
      sources.value = []
    } finally {
      sourcesLoading.value = false
    }
  }

  function invalidate() {
    stocksLoaded.value = false
    sourcesLoaded.value = false
  }

  return { stocks, sources, stocksLoading, sourcesLoading, loadStocks, loadSources, invalidate }
})
