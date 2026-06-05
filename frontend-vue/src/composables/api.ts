import axios, { type AxiosInstance } from "axios";

const http: AxiosInstance = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || "请求失败";
    return Promise.reject(new Error(msg));
  },
);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const r = <T = any>(p: Promise<unknown>): Promise<T> => p as Promise<T>;

export const api = {
  getStocks: (params?: {
    search?: string;
    page?: number;
    page_size?: number;
  }) => r(http.get("/data/stocks", { params })),
  getHistory: (params: {
    symbol: string;
    start_date?: string;
    end_date?: string;
  }) => r(http.get("/data/history", { params })),
  syncData: (data: {
    symbols: string[];
    start_date: string;
    end_date: string;
  }) => r(http.post("/data/sync", data)),
  getDataSources: () => r(http.get("/data/sources")),
  getDataQuality: () => r(http.get("/data/quality")),
  getStorageStats: () => r(http.get("/data/storage")),

  getModels: (params?: { symbol?: string; model_type?: string }) =>
    r(http.get("/models/", { params })),
  getModel: (id: string) => r(http.get(`/models/${id}`)),
  getModelPredictions: (id: string, days = 30, symbol?: string) =>
    r(http.get(`/models/${id}/predictions`, { params: { days, symbol } })),
  getFeatureImportance: (id: string) =>
    r(http.get(`/models/${id}/feature-importance`)),
  compareModels: (symbol?: string) =>
    r(http.get("/models/compare", { params: { symbol } })),
  trainModel: (data: { symbol: string; model_type: string; epochs?: number }) =>
    r(http.post("/models/train", data)),
  trainMultiStock: (data: {
    model_type?: string;
    epochs?: number;
    max_stocks?: number;
  }) => r(http.post("/models/train-multi", data)),

  getBacktests: (params?: {
    symbol?: string;
    model_type?: string;
    page?: number;
    page_size?: number;
  }) => r(http.get("/backtest/", { params })),
  getBacktest: (modelId: string) => r(http.get(`/backtest/${modelId}`)),
  getEquityCurve: (modelId: string) =>
    r(http.get(`/backtest/${modelId}/equity-curve`)),
  getCorrelation: () => r(http.get("/backtest/correlation")),
  runPipeline: () => r(http.post("/backtest/run")),
  getPipelineStatus: () => r(http.get("/backtest/status")),

  getRiskOverview: () => r(http.get("/risk/overview")),
  getVaR: (params?: { confidence?: number; window?: number }) =>
    r(http.get("/risk/var", { params })),
  getRiskAlerts: () => r(http.get("/risk/alerts")),
  runStressTest: (data: { strategy_id: number; scenarios: string[] }) =>
    r(http.post("/risk/stress-test", data)),

  getPortfolios: () => r(http.get("/paper-trading/portfolios")),
  createPortfolio: (data: {
    name: string;
    initial_capital: number;
    model_id?: string;
  }) => r(http.post("/paper-trading/portfolios", data)),
  getPortfolio: (id: string) => r(http.get(`/paper-trading/portfolios/${id}`)),
  runPortfolio: (id: string) =>
    r(http.post(`/paper-trading/portfolios/${id}/run`)),
  simulatePortfolio: (id: string, days = 90) =>
    r(
      http.post(`/paper-trading/portfolios/${id}/simulate`, null, {
        params: { days },
      }),
    ),
  getPortfolioTrades: (id: string) =>
    r(http.get(`/paper-trading/portfolios/${id}/trades`)),
  getPortfolioEquity: (id: string) =>
    r(http.get(`/paper-trading/portfolios/${id}/equity`)),
  deletePortfolio: (id: string) =>
    r(http.delete(`/paper-trading/portfolios/${id}`)),

  getRecommendedStrategy: (symbol?: string) =>
    r(http.get("/backtest/recommend", { params: { symbol } })),
  deployStrategy: (data: {
    model_id: string;
    initial_capital?: number;
    days?: number;
  }) => r(http.post("/paper-trading/portfolios/from-strategy", data)),

  getJobs: () => r(http.get("/jobs/")),
  getJob: (id: string) => r(http.get(`/jobs/${id}`)),
};
