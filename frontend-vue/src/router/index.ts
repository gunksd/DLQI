import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      { path: '', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
      { path: 'strategies', name: 'strategies', component: () => import('@/views/StrategiesView.vue') },
      { path: 'models', name: 'models', component: () => import('@/views/ModelsView.vue') },
      { path: 'backtest', name: 'backtest', component: () => import('@/views/BacktestView.vue') },
      { path: 'trading', name: 'trading', component: () => import('@/views/TradingView.vue') },
      { path: 'risk', name: 'risk', component: () => import('@/views/RiskView.vue') },
      { path: 'data', name: 'data', component: () => import('@/views/DataView.vue') },
      { path: 'tuning', name: 'tuning', component: () => import('@/views/TuningView.vue') },
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
