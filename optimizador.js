// optimizador.js — lógica de la pantalla Optimizador
(function () {
    const BASE_URL = 'http://127.0.0.1:5000';
    const token = localStorage.getItem('token');
    if (!token) { window.location.href = 'index.html'; return; }
    const headers = { 'Authorization': `Bearer ${token}` };

    const fmt = (n, d = 2) => (n === null || n === undefined) ? '—' : Number(n).toLocaleString('es', { maximumFractionDigits: d });
    const badgeClass = { optimo: 'badge-optimo', sobredosis: 'badge-sobredosis', leve: 'badge-leve', sin_referencia: 'badge-sinref' };
    const badgeText = { optimo: 'Óptimo', sobredosis: 'Sobredosis', leve: 'Leve', sin_referencia: 'Sin ref.' };

    async function init() {
        const sel = document.getElementById('loteSelect');
        const lotes = await fetch(`${BASE_URL}/api/lotes`, { headers }).then(r => r.json());
        sel.innerHTML = lotes.map(l => `<option value="${l.id_lote}">${l.numero_lote}</option>`).join('');
        sel.onchange = () => cargarLote(sel.value);
        if (lotes.length) cargarLote(lotes[0].id_lote);
        cargarAcumulado();
    }

    async function cargarLote(idLote) {
        const data = await fetch(`${BASE_URL}/api/optimizador/lote/${idLote}`, { headers }).then(r => r.json());
        document.getElementById('pesoTela').textContent = `Peso de tela: ${fmt(data.peso_tela_kg)} kg`;
        const t = data.totales;
        document.getElementById('resultCards').innerHTML = `
            <div class="kpi-card"><h3>Exceso de químico</h3><div class="val">${fmt(t.excedente_kg)} kg</div></div>
            <div class="kpi-card"><h3>Agua evitable 💧</h3><div class="val">${fmt(t.agua_evitable_l)} L</div><div class="sub">estimación</div></div>
            <div class="kpi-card"><h3>CO₂ evitable 🌍</h3><div class="val">${fmt(t.co2_evitable_kg)} kg</div><div class="sub">estimación</div></div>
            <div class="kpi-card"><h3>Ahorro estimado</h3><div class="val">$${fmt(t.ahorro)}</div></div>`;
        document.getElementById('detalleBody').innerHTML = data.detalle.map(d => `
            <tr>
                <td>${d.etapa}</td><td>${d.producto}</td>
                <td>${fmt(d.dosis_real_g_kg, 2)}</td><td>${fmt(d.dosis_ref_g_kg, 2)}</td>
                <td>${d.desviacion_pct === null ? '—' : fmt(d.desviacion_pct, 1) + '%'}</td>
                <td>${d.excedente_kg ? fmt(d.excedente_kg) + ' kg' : '—'}</td>
                <td><span class="badge-estado ${badgeClass[d.estado]}">${badgeText[d.estado]}</span></td>
            </tr>`).join('');
    }

    let chart;
    async function cargarAcumulado() {
        const g = await fetch(`${BASE_URL}/api/optimizador/acumulado`, { headers }).then(r => r.json());
        document.getElementById('acumuladoTotales').innerHTML =
            `<strong>${fmt(g.lotes_analizados, 0)}</strong> lotes analizados · ` +
            `Excedente total: <strong>${fmt(g.excedente_kg)} kg</strong> · ` +
            `Agua evitable: <strong>${fmt(g.agua_evitable_l)} L</strong> · ` +
            `CO₂ evitable: <strong>${fmt(g.co2_evitable_kg)} kg</strong>`;
        const ctx = document.getElementById('acumuladoChart');
        if (chart) chart.destroy();
        chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Químico (kg)', 'Agua (L)', 'CO₂ (kg)'],
                datasets: [{ label: 'Evitable (acumulado planta)',
                    data: [g.excedente_kg, g.agua_evitable_l, g.co2_evitable_kg],
                    backgroundColor: ['#0b7a4f', '#2a6fb0', '#1f9d6b'] }]
            },
            options: { responsive: true, plugins: { legend: { display: false } } }
        });
    }

    init();
})();
