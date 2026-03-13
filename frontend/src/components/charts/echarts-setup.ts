/**
 * Centralized ECharts module registration.
 * Import this once — all chart components share the same registration.
 */
import * as echarts from "echarts/core";
import {
  LineChart,
  BarChart,
  CandlestickChart,
  ScatterChart,
  RadarChart,
  HeatmapChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  // Charts
  LineChart,
  BarChart,
  CandlestickChart,
  ScatterChart,
  RadarChart,
  HeatmapChart,
  // Components
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
  VisualMapComponent,
  // Renderer
  CanvasRenderer,
]);

export { echarts };
