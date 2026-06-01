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
    cargarPrediccion();
})();
