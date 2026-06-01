// sostenibilidad.js — Panel de Sostenibilidad
(function () {
    const BASE_URL = 'http://127.0.0.1:5000';
    const token = localStorage.getItem('token');
    if (!token) { window.location.href = 'index.html'; return; }
    const headers = { 'Authorization': `Bearer ${token}` };
    const fmt = (n, d = 1) => (n === null || n === undefined) ? '—' : Number(n).toLocaleString('es', { maximumFractionDigits: d });

    async function cargarKpis() {
        const k = await fetch(`${BASE_URL}/api/sostenibilidad/kpis`, { headers }).then(r => r.json());
        document.getElementById('kpiGrid').innerHTML = `
            <div class="kpi-card"><h3>Químicos monitoreados</h3><div class="val">${fmt(k.total_productos,0)}</div></div>
            <div class="kpi-card"><h3>% Peligrosos</h3><div class="val">${fmt(k.pct_peligrosos,1)}%</div><div class="sub">${fmt(k.peligrosos,0)} productos</div></div>
            <div class="kpi-card"><h3>Bajo stock</h3><div class="val">${fmt(k.bajo_stock,0)}</div></div>
            <div class="kpi-card"><h3>Agua evitada 💧</h3><div class="val">${fmt(k.agua_evitada_l,0)} L</div><div class="sub">estimación</div></div>
            <div class="kpi-card"><h3>CO₂ evitado 🌍</h3><div class="val">${fmt(k.co2_evitado_kg,1)} kg</div><div class="sub">estimación</div></div>`;
    }

    async function cargarGraficas() {
        const g = await fetch(`${BASE_URL}/api/sostenibilidad/graficas`, { headers }).then(r => r.json());

        new Chart(document.getElementById('consumoChart'), {
            type: 'bar',
            data: {
                labels: g.consumo_por_lote.map(x => x.lote),
                datasets: [{ data: g.consumo_por_lote.map(x => x.total), backgroundColor: '#0b7a4f' }]
            },
            options: { responsive: true, plugins: { legend: { display: false } } }
        });

        const pv = g.peligrosos_vs_seguros;
        new Chart(document.getElementById('donutChart'), {
            type: 'doughnut',
            data: {
                labels: ['Seguros', 'Corrosivos', 'Tóxicos/Inflamables'],
                datasets: [{ data: [pv.seguros, pv.corrosivos, pv.toxicos_inflamables],
                    backgroundColor: ['#1f9d6b', '#e67e22', '#c0392b'] }]
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
        });

        new Chart(document.getElementById('topChart'), {
            type: 'bar',
            data: {
                labels: g.top_quimicos.map(x => x.nombre),
                datasets: [{ data: g.top_quimicos.map(x => x.total), backgroundColor: '#13a06f' }]
            },
            options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } } }
        });

        const icono = { bajo_stock: '🔴', sobredosis: '🟠', sin_coeficiente: '⚪' };
        const box = document.getElementById('alertasBox');
        box.innerHTML = g.alertas.length
            ? g.alertas.map(a => `<div style="padding:8px 10px;margin-bottom:6px;border-radius:8px;background:#f7faf8;font-size:.82rem">${icono[a.tipo] || '•'} ${a.mensaje}</div>`).join('')
            : '<p class="eco-note">Sin alertas activas.</p>';
    }

    async function cargarPrediccion() {
        const items = await fetch(`${BASE_URL}/api/prediccion/consumo`, { headers }).then(r => r.json());
        const conHistorial = items.filter(p => p.historial > 0);
        const lista = (conHistorial.length ? conHistorial : items).slice(0, 12);
        document.getElementById('prediccionBody').innerHTML = lista.map(p => `
            <tr>
                <td>${p.nombre}</td>
                <td>${fmt(p.stock_actual,1)}</td>
                <td>${fmt(p.proyeccion,1)}</td>
                <td>${p.confianza}</td>
                <td>${p.reordenar ? '<span class="badge-estado badge-sobredosis">Reordenar</span>' : '<span class="badge-estado badge-optimo">OK</span>'}</td>
            </tr>`).join('');
    }

    cargarKpis();
    cargarGraficas();
    cargarPrediccion();
})();
