/** ECharts 金融终端暗色主题 */
export const terminalTheme = {
  backgroundColor: "transparent",
  textStyle: { color: "#9CA3AF", fontFamily: "Inter, system-ui, sans-serif" },
  title: { textStyle: { color: "#F9FAFB" }, subtextStyle: { color: "#6B7280" } },
  legend: {
    textStyle: { color: "#9CA3AF" },
    inactiveColor: "#374151",
  },
  tooltip: {
    backgroundColor: "#1F2937",
    borderColor: "#374151",
    textStyle: { color: "#F9FAFB", fontSize: 12 },
  },
  xAxis: {
    axisLine: { lineStyle: { color: "#1F2937" } },
    axisTick: { lineStyle: { color: "#1F2937" } },
    axisLabel: { color: "#6B7280", fontSize: 11 },
    splitLine: { lineStyle: { color: "#1F293720" } },
  },
  yAxis: {
    axisLine: { lineStyle: { color: "#1F2937" } },
    axisTick: { lineStyle: { color: "#1F2937" } },
    axisLabel: { color: "#6B7280", fontSize: 11 },
    splitLine: { lineStyle: { color: "#1F293780" } },
  },
  grid: {
    left: 60,
    right: 20,
    top: 20,
    bottom: 30,
    containLabel: false,
  },
  color: ["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B", "#06B6D4", "#EF4444"],
  categoryAxis: {
    axisLine: { lineStyle: { color: "#1F2937" } },
    axisTick: { lineStyle: { color: "#1F2937" } },
    axisLabel: { color: "#6B7280" },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: "#6B7280" },
    splitLine: { lineStyle: { color: "#1F293780" } },
  },
};

/** 涨色 */
export const GAIN_COLOR = "#10B981";
/** 跌色 */
export const LOSS_COLOR = "#EF4444";
/** 蓝色 */
export const BLUE = "#3B82F6";
/** 紫色 */
export const PURPLE = "#8B5CF6";
/** 青色 */
export const CYAN = "#06B6D4";
/** 黄色 */
export const AMBER = "#F59E0B";
