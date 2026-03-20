let riskStreamChart = null;
let statusChart = null;

async function fetchJSON(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
}

function renderKpis(metrics) {
    const cards = document.getElementById('kpi-cards');
    const counters = metrics.counters || {};
    const rates = metrics.rates || {};
    const avg = metrics.averages_ms || {};

    const items = [
        { label: 'Approval Rate', value: `${((rates.transaction_approval_rate || 0) * 100).toFixed(1)}%`, icon: 'fa-circle-check', color: 'text-emerald-300' },
        { label: 'Liveness Failure', value: `${((rates.liveness_failure_rate || 0) * 100).toFixed(1)}%`, icon: 'fa-face-frown', color: 'text-amber-300' },
        { label: 'Settlement Failure', value: `${((rates.settlement_failure_rate || 0) * 100).toFixed(2)}%`, icon: 'fa-triangle-exclamation', color: 'text-rose-300' },
        { label: 'Avg Pipeline Time', value: `${Math.round((avg.transaction || 0) + (avg.liveness || 0))} ms`, icon: 'fa-stopwatch', color: 'text-sky-300' }
    ];

    cards.innerHTML = items.map(item => `
        <div class="glass rounded-2xl p-4">
            <div class="flex justify-between items-center mb-2">
                <span class="text-sm text-slate-300">${item.label}</span>
                <i class="fas ${item.icon} ${item.color}"></i>
            </div>
            <div class="text-2xl font-black">${item.value}</div>
        </div>
    `).join('');
}

function renderAlerts(alertData) {
    const container = document.getElementById('alerts');
    const alerts = alertData.active_alerts || [];

    if (!alerts.length) {
        container.innerHTML = '<div class="text-sm text-emerald-300">Sem alertas ativos. Sistema estável.</div>';
        return;
    }

    container.innerHTML = alerts.map(a => `
        <div class="rounded-xl p-3 border ${a.severity === 'critical' ? 'border-rose-500 bg-rose-900/30' : 'border-amber-500 bg-amber-900/20'}">
            <div class="text-xs uppercase tracking-wide mb-1">${a.type}</div>
            <div class="font-semibold">${a.message}</div>
        </div>
    `).join('');
}

function renderFeed(feedData) {
    const feed = feedData.feed || [];
    const container = document.getElementById('fraud-feed');

    if (!feed.length) {
        container.innerHTML = '<div class="text-sm text-slate-300">Sem transações recentes.</div>';
        return;
    }

    container.innerHTML = feed.map(item => {
        const statusColor = item.status === 'approved' ? 'text-emerald-300' : item.status === 'pending' ? 'text-amber-300' : 'text-rose-300';
        const anomalyBadge = item.anomaly_detected
            ? `<span class="px-2 py-1 rounded-full text-xs bg-rose-700/40 text-rose-200">IF ${Number(item.anomaly_score || 0).toFixed(1)}%</span>`
            : '<span class="px-2 py-1 rounded-full text-xs bg-emerald-700/30 text-emerald-200">Normal</span>';

        return `
            <div class="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
                <div class="flex justify-between items-start gap-3 mb-2">
                    <div>
                        <div class="font-semibold">TX ${String(item.transaction_id).slice(-8)}</div>
                        <div class="text-xs text-slate-400">${new Date(item.created_at).toLocaleString('pt-PT')}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-lg font-black">€${Number(item.amount || 0).toFixed(2)}</div>
                        <div class="text-xs ${statusColor}">${String(item.status).toUpperCase()}</div>
                    </div>
                </div>
                <div class="flex flex-wrap items-center gap-2 mb-2">
                    ${anomalyBadge}
                    <span class="px-2 py-1 rounded-full text-xs bg-sky-700/30 text-sky-200">Risco ${Number(item.risk_score || 0).toFixed(1)}</span>
                    <span class="px-2 py-1 rounded-full text-xs bg-indigo-700/30 text-indigo-200">${String(item.risk_level).toUpperCase()}</span>
                    <span class="px-2 py-1 rounded-full text-xs bg-purple-700/30 text-purple-200">Liveness ${item.liveness_performed ? (item.liveness_success ? 'PASS' : 'FAIL') : 'N/A'}</span>
                </div>
                <div class="text-xs text-slate-300">${item.risk_reason || item.anomaly_reason || 'Sem explicação adicional'}</div>
            </div>
        `;
    }).join('');
}

function renderCharts(feedData) {
    const feed = (feedData.feed || []).slice().reverse();

    const labels = feed.map((_, idx) => `#${idx + 1}`);
    const riskScores = feed.map(item => Number(item.risk_score || 0));
    const statuses = feed.map(item => String(item.status || '').toLowerCase());

    const approved = statuses.filter(s => s === 'approved').length;
    const pending = statuses.filter(s => s === 'pending').length;
    const rejected = statuses.filter(s => s === 'rejected' || s === 'blocked').length;

    const riskCtx = document.getElementById('risk-stream-chart');
    if (riskCtx && typeof Chart !== 'undefined') {
        if (riskStreamChart) riskStreamChart.destroy();
        riskStreamChart = new Chart(riskCtx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Risk Score',
                        data: riskScores,
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.2)',
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { color: '#cbd5e1' },
                        grid: { color: 'rgba(148,163,184,0.15)' }
                    },
                    x: {
                        ticks: { color: '#cbd5e1' },
                        grid: { color: 'rgba(148,163,184,0.1)' }
                    }
                },
                plugins: { legend: { labels: { color: '#e2e8f0' } } }
            }
        });
    }

    const statusCtx = document.getElementById('status-chart');
    if (statusCtx && typeof Chart !== 'undefined') {
        if (statusChart) statusChart.destroy();
        statusChart = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Approved', 'Pending', 'Rejected'],
                datasets: [{ data: [approved, pending, rejected], backgroundColor: ['#22c55e', '#f59e0b', '#ef4444'] }]
            },
            options: {
                plugins: { legend: { labels: { color: '#e2e8f0' } } },
                cutout: '65%'
            }
        });
    }
}

async function refreshDashboard() {
    try {
        const [metrics, alerts, feed] = await Promise.all([
            fetchJSON('/api/observability/metrics'),
            fetchJSON('/api/observability/alerts'),
            fetchJSON('/api/observability/fraud-feed?limit=30')
        ]);

        renderKpis(metrics);
        renderAlerts(alerts);
        renderFeed(feed);
        renderCharts(feed);

        document.getElementById('last-update').textContent = new Date().toLocaleTimeString('pt-PT');
    } catch (error) {
        console.error('Fraud dashboard refresh failed:', error);
    }
}

window.addEventListener('DOMContentLoaded', async () => {
    await refreshDashboard();
    setInterval(refreshDashboard, 4000);
});
