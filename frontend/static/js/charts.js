// CareLink Chart.js Controller
let trendChartInstance = null;
let urgencyChartInstance = null;

function renderAdminCharts(chartsData) {
    // 1. Trend Volume Chart
    const trendCtx = document.getElementById('admin-trend-chart');
    if (trendCtx && chartsData.volume_trend) {
        if (trendChartInstance) trendChartInstance.destroy();
        trendChartInstance = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: chartsData.volume_trend.labels,
                datasets: [{
                    label: 'Monthly Referral Volume',
                    data: chartsData.volume_trend.data,
                    borderColor: '#0d9488',
                    backgroundColor: 'rgba(13, 148, 136, 0.08)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointBackgroundColor: '#0d9488',
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // 2. Urgency Distribution Doughnut Chart
    const urgencyCtx = document.getElementById('admin-urgency-chart');
    if (urgencyCtx && chartsData.urgency_chart) {
        if (urgencyChartInstance) urgencyChartInstance.destroy();
        urgencyChartInstance = new Chart(urgencyCtx, {
            type: 'doughnut',
            data: {
                labels: chartsData.urgency_chart.labels,
                datasets: [{
                    data: chartsData.urgency_chart.data,
                    backgroundColor: ['#0d9488', '#d97706', '#e11d48'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
                },
                cutout: '70%'
            }
        });
    }
}
