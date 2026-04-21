<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold text-terminal-text tracking-wide">风险监控</h1>
      <button class="t-btn-ghost text-xs" @click="reload">刷新</button>
    </div>

    <div v-if="error" class="bg-red-900/20 border border-loss/40 text-loss px-4 py-2 text-sm rounded">
      {{ error }}
    </div>

    <div v-if="loading" class="text-terminal-muted text-sm">加载中...</div>

    <template v-else>
      <!-- 风险概览 4卡片 -->
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <div class="t-card">
          <div class="text-terminal-muted text-xs mb-1">平均 Sharpe</div>
          <div class="font-mono text-2xl" :class="(overview?.portfolio_risk?.avg_sharpe ?? 0) >= 1 ? 'text-gain' : 'text-terminal-text'">
            {{ fmtNum(overview?.portfolio_risk.avg_sharpe) }}
          </div>
        </div>
        <div class="t-card">
          <div class="text-terminal-muted text-xs mb-1">最大回撤</div>
          <div class="font-mono text-2xl text-loss">
            {{ fmtPct(overview?.portfolio_risk.worst_drawdown) }}
          </div>
        </div>
        <div class="t-card">
          <div class="text-terminal-muted text-xs mb-1">平均波动率</div>
          <div class="font-mono text-2xl text-terminal-text">
            {{ fmtPct(overview?.portfolio_risk.avg_volatility) }}
          </div>
        </div>
        <div class="t-card">
          <div class="text-terminal-muted text-xs mb-1">方向准确率</div>
          <div class="font-mono text-2xl" :class="(overview?.portfolio_risk.avg_direction_accuracy ?? 0) >= 0.55 ? 'text-gain' : 'text-terminal-text'">
            {{ fmtPct(overview?.portfolio_risk.avg_direction_accuracy) }}
          </div>
        </div>
      </div>

      <!-- VaR 指标 3卡片 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="t-card border-loss/20">
          <div class="text-terminal-muted text-xs mb-1">VaR 95%</div>
          <div class="font-mono text-2xl text-loss">
            {{ fmtPct(varMetrics?.var_95) }}
          </div>
          <div class="text-terminal-dim text-xs mt-1">单日最大损失（95%置信）</div>
        </div>
        <div class="t-card border-loss/20">
          <div class="text-terminal-muted text-xs mb-1">VaR 99%</div>
          <div class="font-mono text-2xl text-loss">
            {{ fmtPct(varMetrics?.var_99) }}
          </div>
          <div class="text-terminal-dim text-xs mt-1">单日最大损失（99%置信）</div>
        </div>
        <div class="t-card border-loss/20">
          <div class="text-terminal-muted text-xs mb-1">CVaR 95%</div>
          <div class="font-mono text-2xl text-loss">
            {{ fmtPct(varMetrics?.cvar_95) }}
          </div>
          <div class="text-terminal-dim text-xs mt-1">条件风险价值（尾部期望损失）</div>
        </div>
      </div>

      <!-- 风险预警 -->
      <div class="t-card">
        <div class="text-terminal-muted text-xs mb-3">风险预警</div>
        <div v-if="alerts.length" class="space-y-2">
          <div v-for="a in alerts" :key="a.id"
            class="flex items-start gap-3 px-3 py-2 rounded border"
            :class="alertRowClass(a.level)">
            <span class="t-badge mt-0.5 shrink-0" :class="alertBadgeClass(a.level)">
              {{ alertLabel(a.level) }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="text-terminal-text text-xs font-semibold">{{ a.title }}</div>
              <div class="text-terminal-muted text-xs mt-0.5">{{ a.message }}</div>
            </div>
            <div class="text-terminal-dim text-xs shrink-0 font-mono">{{ fmtTime(a.created_at) }}</div>
          </div>
        </div>
        <div v-else class="text-terminal-dim text-xs py-4 text-center">暂无风险预警</div>
      </div>

      <!-- 压力测试 -->
      <div class="t-card">
        <div class="text-terminal-muted text-xs mb-3">压力测试</div>
        <div class="flex flex-wrap gap-4 mb-4">
          <label v-for="s in scenarios" :key="s.value" class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="selectedScenarios" :value="s.value"
              class="accent-accent-blue" />
            <span class="text-terminal-text text-xs">{{ s.label }}</span>
          </label>
        </div>
        <button class="t-btn-primary text-xs" :disabled="stressTesting || !selectedScenarios.length"
          @click="runStress">
          {{ stressTesting ? '测试中...' : '运行压力测试' }}
        </button>

        <!-- 结果表格 -->
        <div v-if="stressResults.length" class="mt-4 overflow-x-auto">
          <table class="t-table w-full text-xs">
            <thead>
              <tr>
                <th>场景</th>
                <th class="text-right">最大回撤</th>
                <th class="text-right">总收益</th>
                <th class="text-right">Sharpe</th>
                <th class="text-right">波动率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in stressResults" :key="r.scenario">
                <td class="text-terminal-text">{{ r.scenario }}</td>
                <td class="font-mono text-right text-loss">{{ fmtPct(r.max_drawdown) }}</td>
                <td class="font-mono text-right" :class="r.total_return >= 0 ? 'text-gain' : 'text-loss'">
                  {{ fmtPct(r.total_return) }}
                </td>
                <td class="font-mono text-right">{{ fmtNum(r.sharpe, 2) }}</td>
                <td class="font-mono text-right text-terminal-muted">{{ fmtPct(r.volatility) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="stressRan" class="text-terminal-dim text-xs mt-3">测试完成，暂无结果数据。</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/composables/api'
import type { RiskOverview, RiskAlert } from '@/types'
import { fmtPct, fmtNum } from '@/types'

const overview = ref<RiskOverview | null>(null)
const varMetrics = ref<any>(null)
const alertsList = ref<any[]>([])
const loading = ref(false)
const error = ref('')

const alerts = computed(() => alertsList.value)

const scenarios = [
  { value: '市场暴跌', label: '市场暴跌 (-20%)' },
  { value: '利率上升', label: '利率上升 (+100bp)' },
  { value: '科技股回调', label: '科技股回调 (-15%)' },
  { value: '流动性危机', label: '流动性危机' },
  { value: '黑天鹅事件', label: '黑天鹅事件 (-30%)' },
]
const selectedScenarios = ref<string[]>(['市场暴跌', '科技股回调'])
const stressTesting = ref(false)
const stressRan = ref(false)
const stressResults = ref<any[]>([])

const fmtTime = (ts: string) => {
  try { return new Date(ts).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }
  catch { return ts }
}

const alertLabel = (level: string) => ({ info: 'INFO', warning: 'WARN', critical: 'CRIT' }[level] ?? level.toUpperCase())

const alertBadgeClass = (level: string) => ({
  info: 'text-accent-blue border-accent-blue/30',
  warning: 'text-yellow-400 border-yellow-400/30',
  critical: 'text-loss border-loss/30',
}[level] ?? 'text-terminal-muted border-terminal-border')

const alertRowClass = (level: string) => ({
  info: 'bg-accent-blue/5 border-accent-blue/20',
  warning: 'bg-yellow-400/5 border-yellow-400/20',
  critical: 'bg-loss/5 border-loss/20',
}[level] ?? 'bg-terminal-surface border-terminal-border')

async function reload() {
  loading.value = true
  error.value = ''
  try {
    const [ov, vr, al] = await Promise.all([
      api.getRiskOverview(),
      api.getVaR({ confidence: 0.95, window: 252 }),
      (api as any).getRiskAlerts(),
    ]) as any[]
    overview.value = ov
    varMetrics.value = vr?.current_var ?? vr ?? null
    // normalize 'danger' → 'critical' for badge display
    alertsList.value = (al?.alerts ?? []).map((a: any) => ({
      ...a,
      level: a.level === 'danger' ? 'critical' : a.level,
    }))
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function runStress() {
  if (!selectedScenarios.value.length) return
  stressTesting.value = true
  stressRan.value = false
  try {
    const res = await api.runStressTest({ strategy_id: 0, scenarios: selectedScenarios.value }) as any
    // backend returns { scenarios: { "市场暴跌": { portfolio_impact, shock, ... }, ... } }
    const scenariosMap = res?.scenarios ?? {}
    stressResults.value = Object.entries(scenariosMap).map(([name, data]: [string, any]) => ({
      scenario: name,
      max_drawdown: data.portfolio_impact ?? 0,
      total_return: data.portfolio_impact ?? 0,
      sharpe: 0,
      volatility: Math.abs(data.var_impact ?? 0),
      description: data.description ?? '',
    }))
  } catch {
    stressResults.value = []
  } finally {
    stressTesting.value = false
    stressRan.value = true
  }
}

onMounted(reload)
</script>
