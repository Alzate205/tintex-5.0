// lotes.js — Lotes / Producción
(function () {
    const BASE_URL = 'http://127.0.0.1:5000';
    const token = localStorage.getItem('token');
    if (!token) { window.location.href = 'index.html'; return; }
    const headers = { 'Authorization': `Bearer ${token}` };
    const jsonHeaders = { ...headers, 'Content-Type': 'application/json' };
    const fmt = (n, d = 1) => (n === null || n === undefined) ? '—' : Number(n).toLocaleString('es', { maximumFractionDigits: d });
    const esc = (s) => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

    let procesos = [];
    let productos = [];
    let lotes = [];
    let searchLote = '';

    const badgeEstado = (estado) => {
        const c = estado === 'Completado' ? 'badge-optimo' : (estado === 'En Progreso' ? 'badge-leve' : 'badge-sinref');
        return `<span class="badge-estado ${c}">${esc(estado)}</span>`;
    };

    const procesoOptions = (sel = '') =>
        ['<option value="">Selecciona proceso…</option>']
            .concat(procesos.map(p => {
                const n = p.nombre_proceso || p.nombre || '';
                return `<option value="${esc(n)}" ${n === sel ? 'selected' : ''}>${esc(n)}</option>`;
            })).join('');

    const productoOptions = (sel = '') =>
        ['<option value="">Producto…</option>']
            .concat(productos.map(p =>
                `<option value="${p.id}" ${String(p.id) === String(sel) ? 'selected' : ''}>${esc(p.product)} (${esc(p.unit || '')})</option>`
            )).join('');

    async function init() {
        const [pr, pd] = await Promise.all([
            fetch(`${BASE_URL}/api/procesos_guardados`, { headers }).then(r => r.json()).catch(() => []),
            fetch(`${BASE_URL}/api/inventario`, { headers }).then(r => r.json()).catch(() => [])
        ]);
        procesos = Array.isArray(pr) ? pr : [];
        productos = Array.isArray(pd) ? pd : [];

        document.getElementById('addLoteBtn').onclick = () => abrirModal();
        document.getElementById('closeLoteModalBtn').onclick = cerrarModal;
        document.getElementById('addEtapaBtn').onclick = () => agregarEtapa();
        document.getElementById('loteForm').onsubmit = guardarLote;
        const s = document.getElementById('searchLote');
        if (s) s.oninput = () => { searchLote = s.value.trim().toLowerCase(); render(); };
        cargarLotes();
    }

    async function cargarLotes() {
        lotes = await fetch(`${BASE_URL}/api/lotes`, { headers }).then(r => r.json());
        render();
    }

    function render() {
        const grid = document.getElementById('lotes-grid');
        const lista = lotes.filter(l => !searchLote || (l.numero_lote || '').toLowerCase().includes(searchLote));
        if (!lista.length) {
            grid.innerHTML = '<div class="inventory-item">No hay lotes. Crea uno para empezar.</div>';
            return;
        }
        grid.innerHTML = lista.map(l => `
            <div class="proto-card">
                <div class="proto-head">
                    <h3>${esc(l.numero_lote)}</h3>
                    ${badgeEstado(l.estado_actual)}
                </div>
                <div class="proto-meta">
                    <span><i class="fas fa-weight-hanging"></i> ${fmt(l.peso_tela_kg)} kg de tela</span>
                    <span><i class="fas fa-layer-group"></i> ${l.num_etapas} etapa(s)</span>
                </div>
                <div class="proto-actions">
                    <a class="proto-btn editar" href="optimizador.html?lote=${l.id_lote}" style="text-decoration:none"><i class="fas fa-flask"></i> Optimizar</a>
                    <button class="proto-btn aprobar lote-edit" data-id="${l.id_lote}"><i class="fas fa-edit"></i> Editar</button>
                    <button class="proto-btn eliminar lote-del" data-id="${l.id_lote}"><i class="fas fa-trash"></i> Eliminar</button>
                </div>
            </div>`).join('');
        grid.querySelectorAll('.lote-edit').forEach(b => b.onclick = () => editarLote(b.dataset.id));
        grid.querySelectorAll('.lote-del').forEach(b => b.onclick = () => eliminarLote(b.dataset.id));
    }

    function abrirModal() {
        document.getElementById('loteModalTitle').textContent = 'Crear Lote';
        document.getElementById('loteId').value = '';
        document.getElementById('loteNumero').value = '';
        document.getElementById('lotePeso').value = '';
        document.getElementById('loteEtapas').innerHTML = '';
        agregarEtapa();
        document.getElementById('loteModalOverlay').style.display = 'flex';
    }
    function cerrarModal() { document.getElementById('loteModalOverlay').style.display = 'none'; }

    function agregarEtapa(nombre = '', maquina = '', prods = []) {
        const cont = document.getElementById('loteEtapas');
        const block = document.createElement('div');
        block.className = 'etapa-block';
        block.innerHTML = `
            <div class="etapa-head">
                <select class="etapa-nombre" required>${procesoOptions(nombre)}</select>
                <input class="etapa-maquina" placeholder="Máquina (opcional)" value="${esc(maquina)}">
                <button type="button" class="rm-etapa" title="Quitar etapa"><i class="fas fa-times"></i></button>
            </div>
            <div class="etapa-prods"></div>
            <button type="button" class="add-prod"><i class="fas fa-plus"></i> producto</button>`;
        cont.appendChild(block);
        block.querySelector('.rm-etapa').onclick = () => block.remove();
        const prodsCont = block.querySelector('.etapa-prods');
        block.querySelector('.add-prod').onclick = () => agregarProducto(prodsCont);
        if (prods.length) prods.forEach(p => agregarProducto(prodsCont, p.id_producto, p.cantidad_usada));
        else agregarProducto(prodsCont);
    }

    function agregarProducto(cont, id = '', cant = '') {
        const row = document.createElement('div');
        row.className = 'prod-row';
        row.innerHTML = `
            <select class="prod-id">${productoOptions(id)}</select>
            <input class="prod-cant" type="number" step="0.01" min="0" placeholder="Cant. usada" value="${cant}">
            <button type="button" class="rm-prod" title="Quitar producto"><i class="fas fa-times"></i></button>`;
        cont.appendChild(row);
        row.querySelector('.rm-prod').onclick = () => row.remove();
    }

    function recolectarEtapas() {
        return [...document.querySelectorAll('#loteEtapas .etapa-block')].map(block => ({
            nombre_etapa: block.querySelector('.etapa-nombre').value,
            maquina_utilizada: block.querySelector('.etapa-maquina').value,
            productos: [...block.querySelectorAll('.prod-row')].map(row => ({
                id_producto: Number(row.querySelector('.prod-id').value),
                cantidad_usada: Number(row.querySelector('.prod-cant').value)
            })).filter(p => p.id_producto && p.cantidad_usada > 0)
        })).filter(e => e.nombre_etapa);
    }

    async function guardarLote(e) {
        e.preventDefault();
        const id = document.getElementById('loteId').value;
        const numero_lote = document.getElementById('loteNumero').value.trim();
        const peso_tela_kg = Number(document.getElementById('lotePeso').value);
        const etapas = recolectarEtapas();
        if (!numero_lote || !peso_tela_kg) { alert('Número de lote y peso de tela son obligatorios.'); return; }
        if (!etapas.length || etapas.every(et => et.productos.length === 0)) {
            alert('Agrega al menos una etapa con un producto y su cantidad usada.'); return;
        }
        const body = JSON.stringify({ numero_lote, peso_tela_kg, etapas });
        const url = id ? `${BASE_URL}/api/lotes/${id}` : `${BASE_URL}/api/lotes`;
        const method = id ? 'PUT' : 'POST';
        try {
            const r = await fetch(url, { method, headers: jsonHeaders, body });
            const d = await r.json();
            if (!r.ok) throw new Error(d.error || 'No se pudo guardar');
            cerrarModal();
            cargarLotes();
        } catch (err) { alert('Error: ' + err.message); }
    }

    async function editarLote(id) {
        try {
            const d = await fetch(`${BASE_URL}/api/lotes/${id}`, { headers }).then(r => r.json());
            document.getElementById('loteModalTitle').textContent = 'Editar Lote';
            document.getElementById('loteId').value = d.lote.id_lote;
            document.getElementById('loteNumero').value = d.lote.numero_lote;
            document.getElementById('lotePeso').value = d.lote.peso_tela_kg;
            document.getElementById('loteEtapas').innerHTML = '';
            (d.etapas || []).forEach(et => agregarEtapa(et.nombre_etapa, et.maquina_utilizada, et.productos || []));
            if (!d.etapas || !d.etapas.length) agregarEtapa();
            document.getElementById('loteModalOverlay').style.display = 'flex';
        } catch (err) { alert('Error: ' + err.message); }
    }

    async function eliminarLote(id) {
        if (!confirm('¿Eliminar este lote? Esta acción no se puede deshacer.')) return;
        try {
            const r = await fetch(`${BASE_URL}/api/lotes/${id}`, { method: 'DELETE', headers });
            const d = await r.json();
            if (!r.ok) throw new Error(d.error || 'No se pudo eliminar');
            cargarLotes();
        } catch (err) { alert('Error: ' + err.message); }
    }

    init();
})();
