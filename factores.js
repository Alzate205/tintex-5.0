// factores.js — administración de coeficientes ambientales (solo Administrador)
(function () {
    const BASE_URL = 'http://127.0.0.1:5000';
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    if (!token || !user) { window.location.href = 'index.html'; return; }
    const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

    if (user.rol !== 'Administrador') {
        document.getElementById('adminGate').innerHTML =
            '<div class="eco-card">Solo el rol <strong>Administrador</strong> puede editar coeficientes.</div>';
        return;
    }
    document.getElementById('factoresWrap').style.display = 'block';

    async function cargar() {
        const productos = await fetch(`${BASE_URL}/api/inventario`, { headers }).then(r => r.json());
        const factores = await fetch(`${BASE_URL}/api/factores_ambientales`, { headers }).then(r => r.json());
        const mapa = {};
        factores.forEach(f => mapa[f.id_producto] = f);
        document.getElementById('factoresBody').innerHTML = productos.map(p => {
            const f = mapa[p.id] || {};
            return `<tr data-id="${p.id}">
                <td>${p.product}</td>
                <td><input type="number" step="0.1" class="agua" value="${f.agua_l_por_kg ?? 0}" style="width:80px"></td>
                <td><input type="number" step="0.1" class="co2" value="${f.co2_kg_por_kg ?? 0}" style="width:80px"></td>
                <td><input type="text" class="score" value="${f.eco_score ?? 'C'}" style="width:50px"></td>
                <td><input type="text" class="fuente" value="${f.fuente ?? ''}" style="width:160px"></td>
                <td><button class="add-btn guardar">Guardar</button></td>
            </tr>`;
        }).join('');
        document.querySelectorAll('.guardar').forEach(btn => btn.onclick = guardar);
    }

    async function guardar(e) {
        const tr = e.target.closest('tr');
        const payload = {
            id_producto: Number(tr.dataset.id),
            agua_l_por_kg: Number(tr.querySelector('.agua').value),
            co2_kg_por_kg: Number(tr.querySelector('.co2').value),
            eco_score: tr.querySelector('.score').value,
            fuente: tr.querySelector('.fuente').value,
            es_estimacion: 1
        };
        const r = await fetch(`${BASE_URL}/api/factores_ambientales`, {
            method: 'POST', headers, body: JSON.stringify(payload)
        });
        e.target.textContent = r.ok ? 'Guardado ✓' : 'Error';
        setTimeout(() => { e.target.textContent = 'Guardar'; }, 1500);
    }

    cargar();
})();
