// F40 — Helpers de construction des configurations chart.js partagées.
import type { ChartTheme } from '~/composables/useChartTheme'
import type { CategorySeries, ChartSeries, PieSeries, RadarSeries } from '~/types/viz/chart'

function pick(theme: ChartTheme, i: number): string {
  return theme.palette[i % theme.palette.length]!
}

export function buildLineConfig(series: ChartSeries[], theme: ChartTheme, fill: 'origin' | false = false): unknown {
  const datasets = series.map((s, i) => ({
    label: s.label,
    data: s.points.map((p) => ({ x: p.x, y: p.y })),
    borderColor: pick(theme, i),
    backgroundColor: fill ? pick(theme, i) + '33' : pick(theme, i),
    fill,
    tension: 0.3,
    pointRadius: 2,
  }))
  return {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' as const } },
      scales: {
        x: { grid: { color: theme.grid.color }, ticks: { color: theme.axis.color } },
        y: { grid: { color: theme.grid.color }, ticks: { color: theme.axis.color }, beginAtZero: true },
      },
    },
  }
}

export function buildBarConfig(series: CategorySeries, theme: ChartTheme, stacked = false): unknown {
  const datasets = series.datasets.map((d, i) => ({
    label: d.label,
    data: d.data,
    backgroundColor: pick(theme, i),
    borderColor: pick(theme, i),
    borderRadius: 4,
  }))
  return {
    type: 'bar',
    data: { labels: series.labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' as const } },
      scales: {
        x: { stacked, grid: { color: theme.grid.color }, ticks: { color: theme.axis.color } },
        y: { stacked, beginAtZero: true, grid: { color: theme.grid.color }, ticks: { color: theme.axis.color } },
      },
    },
  }
}

export function buildRadarConfig(series: RadarSeries, theme: ChartTheme): unknown {
  const datasets = series.datasets.map((d, i) => ({
    label: d.label,
    data: d.data,
    borderColor: pick(theme, i),
    backgroundColor: pick(theme, i) + '33',
    pointRadius: 3,
  }))
  return {
    type: 'radar',
    data: { labels: series.axes, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' as const } },
      scales: {
        r: {
          beginAtZero: true,
          angleLines: { color: theme.grid.color },
          grid: { color: theme.grid.color },
          pointLabels: { color: theme.axis.color },
          ticks: { color: theme.axis.color, backdropColor: 'transparent' },
        },
      },
    },
  }
}

export function buildPieConfig(series: PieSeries, theme: ChartTheme, donut = false): unknown {
  return {
    type: donut ? 'doughnut' : 'pie',
    data: {
      labels: series.labels,
      datasets: [{
        data: series.data,
        backgroundColor: series.data.map((_, i) => pick(theme, i)),
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: donut ? '60%' : 0,
      plugins: { legend: { position: 'bottom' as const } },
    },
  }
}
