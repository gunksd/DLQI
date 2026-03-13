import dynamic from "next/dynamic";

// Lazy-loaded chart components (ECharts bundle only loaded when needed)
export const KLineChart = dynamic(() => import("./KLineChart").then(m => m.KLineChart), { ssr: false });
export const EquityCurve = dynamic(() => import("./EquityCurve").then(m => m.EquityCurve), { ssr: false });
export const DrawdownChart = dynamic(() => import("./DrawdownChart").then(m => m.DrawdownChart), { ssr: false });
export const DistributionChart = dynamic(() => import("./DistributionChart").then(m => m.DistributionChart), { ssr: false });
export const ROCCurve = dynamic(() => import("./ROCCurve").then(m => m.ROCCurve), { ssr: false });
export const VaRChart = dynamic(() => import("./VaRChart").then(m => m.VaRChart), { ssr: false });
export const OptimizationProgress = dynamic(() => import("./OptimizationProgress").then(m => m.OptimizationProgress), { ssr: false });
export const RadarChart = dynamic(() => import("./RadarChart").then(m => m.RadarChart), { ssr: false });
export const HeatmapChart = dynamic(() => import("./HeatmapChart").then(m => m.HeatmapChart), { ssr: false });
