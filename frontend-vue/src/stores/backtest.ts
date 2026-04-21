import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/composables/api'
import type { BacktestResult } from '@/types'

export const useBacktestStore = defineStore('backtest', () => {
  const results = ref<BacktestResult[]>([])
  const loading = ref(false)
  const pipelineRunning = ref(false)
  const pipelineStatus = ref<string>('')

  async function fetchResults(params?: { symbol?: string; model_type?: string }) {
    loading.value = true
    try {
      const data = await api.getBacktests(params) as any
      results.value = data.items ?? data ?? []
    } finally {
      loading.value = false
    }
  }

  async function runPipeline() {
    pipelineRunning.value = true
    try {
      await api.runPipeline()
    } finally {
      // 状态由轮询更新
    }
  }

  async function checkStatus() {
    try {
      const data = await api.getPipelineStatus() as any
      pipelineRunning.value = data.running ?? false
      pipelineStatus.value = data.status ?? ''
      if (!pipelineRunning.value && results.value.length === 0) {
        await fetchResults()
      }
    } catch {
      pipelineRunning.value = false
    }
  }

  return { results, loading, pipelineRunning, pipelineStatus, fetchResults, runPipeline, checkStatus }
})
