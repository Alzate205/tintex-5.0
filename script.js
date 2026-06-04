// Definición global de variables
let currentUser = null;
let currentFilter = '';
let searchTerm = '';
let currentQuickFilter = 'todos';
let editingProductId = null;
let editingProveedorId = null;
let editingPrototypeId = null;
let loading = null;
let tableBody = null;
let checklistBody = null;
let proveedoresTable = null;
let modalOverlay = null; // Modal para agregar productos
let editProductModalOverlay = null; // Modal para editar productos
let proveedorModalOverlay = null;
let reportOutput = null;
let tipoModalOverlay = null;
let lotesTable = null;
let loteModalOverlay = null;
let prototypesTable = null;
let prototypeModalOverlay = null;
const BASE_URL = 'http://127.0.0.1:5000';
let timers = {}; // Objeto para almacenar los intervalos de temporizadores

// Función para normalizar cadenas (eliminar tildes y convertir a minúsculas)
function normalizeString(str) {
    return str
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();
}

// Función para extraer el número de quantity (maneja números y cadenas)
function extractQuantity(quantityStr) {
    if (quantityStr === null || quantityStr === undefined) return 0;
    const strValue = typeof quantityStr === 'number' ? quantityStr.toString() : quantityStr;
    const match = strValue.match(/([\d\.]+)/);
    return match ? parseFloat(match[0]) : 0;
}

// Función para registrar un movimiento
function registerMovement(productId, productName, tipoMovimiento, cantidad, detalle) {
    const movementData = {
        id_producto: productId,
        producto: productName,
        tipo_movimiento: tipoMovimiento,
        cantidad_movimiento: cantidad,
        fecha_movimiento: new Date().toISOString().split('T')[0],
        usuario: currentUser ? currentUser.nombre : 'Usuario desconocido',
        detalle: detalle || ''
    };

    fetch(`${BASE_URL}/api/movimientos`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(movementData)
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => console.log('Movimiento registrado:', data))
        .catch(error => console.error('Error al registrar movimiento:', error.message));
}

// Función para configurar los enlaces de navegación
function setupNavLinks() {
    const dashboardLink = document.getElementById('dashboardLink');
    const prototypeLink = document.getElementById('prototypeLink');
    const reportLink = document.getElementById('reportLink');
    const proveedoresLink = document.getElementById('proveedoresLink');
    const addTipoBtn = document.getElementById('addTipoBtn');
    const filterBtn = document.getElementById('filterBtn');

    const setActiveLink = (link) => {
        document.querySelectorAll('.nav a').forEach(a => a.classList.remove('active'));
        link.classList.add('active');
    };

    // Obtener el rol del usuario desde localStorage (almacenado tras el login)
    const userRole = currentUser ? currentUser.rol : null;

    // Ocultar el enlace de prototipos para todos los roles
    if (prototypeLink) {
        prototypeLink.style.display = 'none';
    }

    // Mostrar/Ocultar enlaces según el rol
    if (userRole === 'Administrador') {
        // Administrador ve todo excepto prototipos
    } else if (userRole === 'Líder') {
        reportLink.style.display = 'none';    // Ocultar Reportes
        // Líder puede filtrar y agregar tipo
        filterBtn.style.display = 'block';
        addTipoBtn.style.display = 'block';
    } else if (userRole === 'Bodeguero') {
        reportLink.style.display = 'none';    // Ocultar Reportes
        proveedoresLink.style.display = 'none'; // Ocultar Proveedores
        // Bodeguero puede filtrar pero no agregar tipo
        filterBtn.style.display = 'block';
        addTipoBtn.style.display = 'none';
    }

    // Configurar eventos de navegación
    if (dashboardLink) {
        dashboardLink.addEventListener('click', () => {
            setActiveLink(dashboardLink);
            window.location.href = 'dashboard.html';
        });
    }
    if (reportLink && userRole === 'Administrador') {
        reportLink.addEventListener('click', () => {
            setActiveLink(reportLink);
            window.location.href = 'reportes.html';
        });
    }
    if (proveedoresLink && (userRole === 'Administrador' || userRole === 'Líder')) {
        proveedoresLink.addEventListener('click', () => {
            setActiveLink(proveedoresLink);
            window.location.href = 'proveedores.html';
        });
    }
}

// Nueva función para cargar productos verificados

function loadVerifiedProductsIntoSelect(selectElement) {
    fetch(`${BASE_URL}/api/inventario`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log('Productos recibidos de /api/inventario:', data);
            selectElement.innerHTML = '<option value="">Seleccionar producto</option>';
            const verifiedProducts = data.filter(item => item.estado_verificacion === 'Verificado');
            console.log('Productos verificados:', verifiedProducts);
            if (verifiedProducts.length === 0) {
                console.warn('No hay productos verificados disponibles');
                selectElement.innerHTML += '<option value="">No hay productos disponibles</option>';
                return;
            }
            verifiedProducts.forEach(product => {
                if (!product.id || !product.product) {
                    console.error('Producto inválido:', product);
                    return;
                }
                const option = document.createElement('option');
                option.value = product.id;
                option.textContent = `${product.product} (Disponible: ${product.quantity} ${product.unit ? product.unit : ''})`;
                option.dataset.quantity = product.quantity;
                selectElement.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error al cargar productos verificados:', error);
            selectElement.innerHTML = '<option value="">Error al cargar productos</option>';
        });
}

// Nueva función para cargar procesos en el select
function loadProcessesIntoSelect(selectElement) {
    fetch(`${BASE_URL}/api/procesos_guardados`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            selectElement.innerHTML = '<option value="">Seleccionar proceso</option>';
            data.forEach(process => {
                const option = document.createElement('option');
                option.value = process.id_proceso_guardado;
                option.textContent = process.nombre_proceso;
                selectElement.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error al cargar procesos:', error);
            selectElement.innerHTML = '<option value="">Error al cargar procesos</option>';
        });
}

// Función para agregar una fila de etapa para lotes
function addEtapaRow(num, nombre = '', tiempo = '', maquina = '', productos = {}) {
    const etapasContainer = document.getElementById('etapasContainer');
    if (!etapasContainer) return;

    const etapaRow = document.createElement('div');
    etapaRow.className = 'etapa-row';
    etapaRow.innerHTML = `
        <label>Etapa ${num}:</label>
        <input type="text" class="etapa-nombre" value="${nombre}" placeholder="Nombre de la etapa" required>
        <input type="number" class="etapa-tiempo" value="${tiempo}" placeholder="Tiempo (min)" required min="1">
        <input type="text" class="etapa-maquina" value="${maquina}" placeholder="Máquina" required>
        <div class="product-selection">
            <label>Productos requeridos:</label>
            <select class="product-select"></select>
            <input type="number" class="product-quantity" placeholder="Cantidad" step="0.01" min="0">
            <button type="button" class="add-product-btn">Agregar Producto</button>
            <div class="selected-products"></div>
        </div>
        <div class="timer-container" style="margin-top: 10px; display: none;">
            <span id="timer-${num}" class="timer">0</span> min
            <progress id="progress-${num}" value="0" max="100" style="width: 100%; margin-top: 5px;"></progress>
        </div>
        <button type="button" class="remove-etapa-btn">Eliminar</button>
    `;
    etapasContainer.appendChild(etapaRow);

    const productSelect = etapaRow.querySelector('.product-select');
    loadVerifiedProductsIntoSelect(productSelect);

    const addProductBtn = etapaRow.querySelector('.add-product-btn');
    const selectedProductsDiv = etapaRow.querySelector('.selected-products');
    const productsMap = new Map(Object.entries(productos));

    productsMap.forEach((quantity, productName) => {
        const productDiv = document.createElement('p');
        productDiv.textContent = `${productName}: ${quantity}`;
        productDiv.dataset.productName = productName;
        productDiv.dataset.quantity = quantity;
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-product-btn';
        removeBtn.textContent = 'Eliminar';
        removeBtn.onclick = () => {
            productsMap.delete(productName);
            productDiv.remove();
        };
        productDiv.appendChild(removeBtn);
        selectedProductsDiv.appendChild(productDiv);
    });

    addProductBtn.onclick = () => {
        const selectedOption = productSelect.options[productSelect.selectedIndex];
        const productId = productSelect.value;
        const productName = selectedOption.textContent.split(' (')[0];
        const availableQuantity = parseFloat(selectedOption.dataset.quantity);
        const quantityInput = etapaRow.querySelector('.product-quantity');
        const quantity = parseFloat(quantityInput.value);

        if (!productId) {
            alert('Por favor, selecciona un producto.');
            return;
        }
        if (!quantity || quantity <= 0) {
            alert('Por favor, ingresa una cantidad válida mayor que 0.');
            return;
        }
        if (quantity > availableQuantity) {
            alert(`La cantidad solicitada (${quantity}) excede la cantidad disponible (${availableQuantity}).`);
            return;
        }

        productsMap.set(productName, quantity);
        const productDiv = document.createElement('p');
        productDiv.textContent = `${productName}: ${quantity}`;
        productDiv.dataset.productName = productName;
        productDiv.dataset.quantity = quantity;
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-product-btn';
        removeBtn.textContent = 'Eliminar';
        removeBtn.onclick = () => {
            productsMap.delete(productName);
            productDiv.remove();
        };
        productDiv.appendChild(removeBtn);
        selectedProductsDiv.appendChild(productDiv);

        productSelect.value = '';
        quantityInput.value = '';
    };

    etapaRow.querySelector('.remove-etapa-btn').addEventListener('click', () => etapaRow.remove());
    etapaRow.productsMap = productsMap;
    etapaRow.dataset.etapaNum = num;
}

// Función para agregar una fila de etapa para prototipos
function addStageRow(num, processId = '', productId = '', quantity = '', time = '') {
    const stagesContainer = document.getElementById('stagesContainer');
    if (!stagesContainer) return;

    const stageRow = document.createElement('div');
    stageRow.className = 'stage-row';
    stageRow.innerHTML = `
        <label>Etapa ${num}:</label>
        <select class="stage-process" required></select>
        <select class="stage-product" required></select>
        <input type="number" class="stage-quantity" value="${quantity}" placeholder="Dosis (g/kg)" step="0.01" min="0" required>
        <input type="number" class="stage-time" value="${time}" placeholder="Tiempo (min)" min="1" required>
        <button type="button" class="remove-stage-btn">Eliminar</button>
    `;
    stagesContainer.appendChild(stageRow);

    const processSelect = stageRow.querySelector('.stage-process');
    const productSelect = stageRow.querySelector('.stage-product');
    loadProcessesIntoSelect(processSelect);
    loadVerifiedProductsIntoSelect(productSelect);

    if (processId) processSelect.value = processId;
    if (productId) productSelect.value = productId;

    stageRow.querySelector('.remove-stage-btn').addEventListener('click', () => stageRow.remove());
}

// Función para cargar y mostrar lotes
function fetchAndUpdateLotes() {
    if (!lotesTable || !loading) return;

    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    loading.style.display = 'block';
    lotesTable.innerHTML = '';

    fetch(`${BASE_URL}/api/lotes`, {
        headers: { 'Authorization': `Bearer ${token}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (!data || data.length === 0) {
                lotesTable.innerHTML = '<div class="inventory-item">No hay lotes disponibles</div>';
                return;
            }

            const lotePromises = data.map(lote => {
                const card = document.createElement('div');
                card.className = 'inventory-item';
                card.innerHTML = `
                    <h3>Lote #${lote.numero_lote}</h3>
                    <p><strong>Estado:</strong> ${lote.estado_actual}</p>
                    <div id="etapas-lote-${lote.id_lote}" class="etapa-progress"></div>
                    <button class="edit-btn" data-id="${lote.id_lote}">Ver/Editar</button>
                `;
                lotesTable.appendChild(card);

                return fetch(`${BASE_URL}/api/lotes/${lote.id_lote}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                })
                    .then(response => response.json())
                    .then(loteData => {
                        const etapasContainer = document.getElementById(`etapas-lote-${lote.id_lote}`);
                        if (!etapasContainer) return;

                        etapasContainer.innerHTML = '<h4>Etapas:</h4><div class="timeline"></div>';
                        const timeline = etapasContainer.querySelector('.timeline');
                        if (!loteData.etapas || loteData.etapas.length === 0) {
                            timeline.innerHTML = '<p>No hay etapas definidas para este lote.</p>';
                            return;
                        }

                        loteData.etapas.forEach((etapa, index) => {
                            const etapaDiv = document.createElement('div');
                            etapaDiv.className = 'etapa-item';
                            const statusClass = etapa.estado_etapa.replace(' ', '-').toLowerCase();
                            etapaDiv.innerHTML = `
                                <div class="timeline-dot ${statusClass}"></div>
                                <div class="timeline-content">
                                    <p>Etapa ${etapa.numero_etapa}: ${etapa.nombre_etapa} (${etapa.estado_etapa})</p>
                                    <span id="timer-${etapa.id_etapa_lote}" class="timer">${etapa.tiempo_restante || etapa.tiempo_estimado || 0}</span> min
                                    <progress id="progress-${etapa.id_etapa_lote}" value="0" max="100" style="width: 100%; margin-top: 5px;"></progress>
                                    <div class="etapa-buttons">
                                        ${etapa.estado_etapa === 'Pendiente' ? `<button class="start-btn" data-id="${etapa.id_etapa_lote}" data-lote="${lote.id_lote}">Iniciar</button>` : ''}
                                        ${etapa.estado_etapa === 'En progreso' ? `
                                            <button class="pause-btn" data-id="${etapa.id_etapa_lote}" data-lote="${lote.id_lote}">Pausar</button>
                                            <button class="complete-btn" data-id="${etapa.id_etapa_lote}" data-lote="${lote.id_lote}">Finalizar</button>
                                        ` : ''}
                                        ${etapa.estado_etapa === 'Pausado' ? `
                                            <button class="start-btn" data-id="${etapa.id_etapa_lote}" data-lote="${lote.id_lote}">Reanudar</button>
                                            <button class="complete-btn" data-id="${etapa.id_etapa_lote}" data-lote="${lote.id_lote}">Finalizar</button>
                                        ` : ''}
                                    </div>
                                </div>
                            `;
                            timeline.appendChild(etapaDiv);

                            if (etapa.estado_etapa === 'En progreso') {
                                startTimer(etapa.id_etapa_lote, etapa.tiempo_restante || etapa.tiempo_estimado || 0);
                            }
                        });
                    });
            });

            Promise.all(lotePromises).then(() => {
                document.querySelectorAll('.edit-btn').forEach(btn => btn.addEventListener('click', handleEditLote));
                document.querySelectorAll('.start-btn').forEach(btn => btn.addEventListener('click', handleStartEtapa));
                document.querySelectorAll('.pause-btn').forEach(btn => btn.addEventListener('click', handlePauseEtapa));
                document.querySelectorAll('.complete-btn').forEach(btn => btn.addEventListener('click', handleCompleteEtapa));
            });
        })
        .catch(error => {
            console.error('Error al cargar lotes:', error.message);
            lotesTable.innerHTML = `<div class="inventory-item">Error al cargar lotes: ${error.message}</div>`;
        })
        .finally(() => loading.style.display = 'none');
}

// Función para cargar y mostrar prototipos
async function fetchAndUpdatePrototypes() {
    if (!prototypesTable) {
        console.warn('prototypesTable no está definido.');
        return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    if (loading) loading.style.display = 'block';
    prototypesTable.innerHTML = '';

    try {
        const response = await fetch(`${BASE_URL}/api/prototipos`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (response.status === 401) {
                localStorage.removeItem('token');
                window.location.href = 'index.html';
                return;
            }
            throw new Error(errorData.error || `HTTP error: ${response.status}`);
        }

        const data = await response.json();
        if (!Array.isArray(data) || data.length === 0) {
            prototypesTable.innerHTML = '<div class="inventory-item">No hay prototipos disponibles</div>';
            return;
        }

        const filteredPrototypes = data.filter(prototype =>
            searchTerm === '' || normalizeString(prototype.nombre).includes(normalizeString(searchTerm))
        );

        if (filteredPrototypes.length === 0) {
            prototypesTable.innerHTML = '<div class="inventory-item">No se encontraron prototipos</div>';
            return;
        }

        const badgeEstado = (estado) => {
            const c = estado === 'Aprobado' ? 'badge-optimo' : (estado === 'Rechazado' ? 'badge-sobredosis' : 'badge-leve');
            return `<span class="badge-estado ${c}">${sanitizeHTML(estado)}</span>`;
        };

        filteredPrototypes.forEach((prototype) => {
            const card = document.createElement('div');
            card.className = 'proto-card';
            const h = prototype.huella || {};
            const etapasHtml = (prototype.etapas && prototype.etapas.length)
                ? `<ol class="proto-etapas">${prototype.etapas.map(e => {
                        const sc = e.stock_suficiente ? 'stock-ok' : 'stock-low';
                        return `<li><span class="pe-proc">${sanitizeHTML(e.nombre_proceso)}</span>
                            <span class="pe-prod">${sanitizeHTML(e.nombre_producto)} · ${e.cantidad_requerida} g/kg · ${e.tiempo} min</span>
                            <span class="pe-stock ${sc}">stock ${e.stock_disponible}</span></li>`;
                    }).join('')}</ol>`
                : '<p class="eco-note">Sin etapas definidas.</p>';
            const stockBadge = prototype.stock_suficiente
                ? '<span class="stock-ok"><i class="fas fa-check-circle"></i> Stock suficiente</span>'
                : '<span class="stock-low"><i class="fas fa-exclamation-circle"></i> Stock insuficiente</span>';
            const ultimo = (prototype.historial && prototype.historial.length)
                ? `<div class="proto-hist"><i class="fas fa-history"></i> ${sanitizeHTML(prototype.historial[prototype.historial.length - 1].estado_nuevo)} · ${sanitizeHTML(prototype.historial[prototype.historial.length - 1].usuario_cambio || '')}</div>`
                : '';
            const accionesEstado = prototype.estado === 'En espera'
                ? `<button class="proto-btn aprobar" data-id="${prototype.id_prototipo}"><i class="fas fa-check"></i> Aprobar</button>
                   <button class="proto-btn rechazar" data-id="${prototype.id_prototipo}"><i class="fas fa-ban"></i> Rechazar</button>`
                : '';
            card.innerHTML = `
                <div class="proto-head">
                    <h3>${sanitizeHTML(prototype.nombre)}</h3>
                    ${badgeEstado(prototype.estado)}
                </div>
                <div class="proto-meta">
                    <span><i class="fas fa-user"></i> ${sanitizeHTML(prototype.responsable || '—')}</span>
                    <span><i class="fas fa-calendar-alt"></i> ${new Date(prototype.fecha_creacion).toLocaleDateString()}</span>
                    ${stockBadge}
                </div>
                <div class="proto-huella"><i class="fas fa-tint"></i> ${h.agua_l_por_kg_tela ?? 0} L/kg · <i class="fas fa-globe-americas"></i> ${h.co2_kg_por_kg_tela ?? 0} kg CO₂/kg <em>(estimado)</em></div>
                <h4 class="proto-sub">Receta (etapas)</h4>
                ${etapasHtml}
                ${ultimo}
                <div class="proto-actions">
                    <button class="proto-btn editar" data-id="${prototype.id_prototipo}"><i class="fas fa-edit"></i> Editar</button>
                    ${accionesEstado}
                    <button class="proto-btn eliminar" data-id="${prototype.id_prototipo}"><i class="fas fa-trash"></i> Eliminar</button>
                </div>
            `;
            prototypesTable.appendChild(card);
        });

        document.querySelectorAll('.proto-btn.editar').forEach(b => b.addEventListener('click', () => loadPrototypeForEdit(b.dataset.id)));
        document.querySelectorAll('.proto-btn.aprobar').forEach(b => b.addEventListener('click', () => cambiarEstadoPrototipo(b.dataset.id, 'Aprobado')));
        document.querySelectorAll('.proto-btn.rechazar').forEach(b => b.addEventListener('click', () => cambiarEstadoPrototipo(b.dataset.id, 'Rechazado')));
        document.querySelectorAll('.proto-btn.eliminar').forEach(b => b.addEventListener('click', () => eliminarPrototipo(b.dataset.id)));
    } catch (error) {
        console.error('Error al cargar prototipos:', error.message);
        prototypesTable.innerHTML = `<div class="inventory-item">Error: ${sanitizeHTML(error.message)}</div>`;
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

// Cargar prototipo para edición
async function loadPrototypeForEdit(prototypeId) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/api/prototipos/${prototypeId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (response.status === 401) {
                localStorage.removeItem('token');
                window.location.href = 'index.html';
                return;
            }
            throw new Error(errorData.error || `HTTP error: ${response.status}`);
        }

        const data = await response.json();
        if (!data.prototipo) throw new Error('Estructura de datos inválida');

        document.getElementById('prototypeModalTitle').textContent = 'Editar Prototipo';
        document.getElementById('prototypeName').value = data.prototipo.nombre || '';
        document.getElementById('responsible').value = data.prototipo.responsable || '';
        document.getElementById('notes').value = data.prototipo.notas || '';
        document.getElementById('prototypeState').value = data.prototipo.estado || '';

        const stagesContainer = document.getElementById('stagesContainer');
        stagesContainer.innerHTML = '';
        if (data.etapas && data.etapas.length > 0) {
            await Promise.all([
                loadProcessesIntoSelect(document.createElement('select')),
                loadVerifiedProductsIntoSelect(document.createElement('select'))
            ]); // Precargar opciones
            data.etapas.forEach((etapa, index) =>
                addStageRow(index + 1, etapa.id_proceso, etapa.id_producto, etapa.cantidad_requerida, etapa.tiempo)
            );
        } else {
            addStageRow(1);
        }

        editingPrototypeId = prototypeId;
        prototypeModalOverlay.style.display = 'flex';
    } catch (error) {
        console.error('Error al cargar prototipo:', error);
        alert('Error: ' + error.message);
    }
}

// Función auxiliar para manejar el evento de edición
function handleEditPrototype(e) {
    const prototypeId = e.target.dataset.id;
    if (prototypeId) {
        loadPrototypeForEdit(prototypeId);
    } else {
        console.error('ID de prototipo no encontrado en el botón de edición');
    }
}

async function cambiarEstadoPrototipo(id, estado) {
    if (!confirm(`¿Cambiar el estado del prototipo a "${estado}"?`)) return;
    const token = localStorage.getItem('token');
    try {
        const r = await fetch(`${BASE_URL}/api/prototipos/${id}/estado`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado })
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'No se pudo cambiar el estado');
        fetchAndUpdatePrototypes();
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

async function eliminarPrototipo(id) {
    if (!confirm('¿Eliminar este prototipo? Esta acción no se puede deshacer.')) return;
    const token = localStorage.getItem('token');
    try {
        const r = await fetch(`${BASE_URL}/api/prototipos/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'No se pudo eliminar');
        fetchAndUpdatePrototypes();
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

async function loadPrototypeForEdit(prototypeId) {
    const token = localStorage.getItem('token');
    if (!token) {
        alert('No se encontró un token de autenticación. Por favor, inicia sesión nuevamente.');
        window.location.href = 'index.html';
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/api/prototipos/${prototypeId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (response.status === 401) {
                localStorage.removeItem('token');
                alert('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
                window.location.href = 'index.html';
                return;
            }
            throw new Error(errorData.error || `Error al cargar el prototipo: ${response.status}`);
        }

        const data = await response.json();
        console.log('Datos del prototipo:', data); // Para depuración

        // Verificar que data.prototipo exista
        if (!data.prototipo) {
            throw new Error('Estructura de datos inválida: prototipo no encontrado');
        }

        // Rellenar el formulario con manejo de valores nulos/undefined
        document.getElementById('prototypeModalTitle').textContent = 'Editar Prototipo';
        document.getElementById('prototypeName').value = data.prototipo.nombre || '';
        document.getElementById('responsible').value = data.prototipo.responsable || '';
        document.getElementById('notes').value = data.prototipo.notas || '';
        document.getElementById('prototypeState').value = data.prototipo.estado || '';

        // Cargar las etapas
        const stagesContainer = document.getElementById('stagesContainer');
        stagesContainer.innerHTML = ''; // Limpiar etapas existentes
        if (data.etapas && data.etapas.length > 0) {
            data.etapas.forEach((etapa, index) => {
                addStageRow(index + 1, etapa.id_proceso, etapa.id_producto, etapa.cantidad_requerida, etapa.tiempo);
            });
        } else {
            addStageRow(1); // Agregar una etapa vacía si no hay etapas
        }

        // Mostrar el formulario y almacenar el ID del prototipo que se está editando
        editingPrototypeId = prototypeId;
        prototypeModalOverlay.style.display = 'flex';
    } catch (error) {
        console.error('Error al cargar prototipo para edición:', error);
        alert('Error al cargar el prototipo: ' + error.message);
    }
}

// Función para sanitizar HTML y prevenir XSS
function sanitizeHTML(str) {
    const temp = document.createElement('div');
    temp.textContent = str || '';
    return temp.innerHTML;
}

// Temporizador para las etapas
function startTimer(idEtapa, initialTime) {
    const timerElement = document.getElementById(`timer-${idEtapa}`);
    const progressElement = document.getElementById(`progress-${idEtapa}`);
    if (!timerElement || !progressElement) return;

    let tiempo = parseInt(initialTime, 10) || 0;
    timerElement.textContent = tiempo;
    progressElement.value = 100;

    if (timers[idEtapa]) clearInterval(timers[idEtapa]);

    timers[idEtapa] = setInterval(() => {
        if (tiempo <= 0) {
            clearInterval(timers[idEtapa]);
            delete timers[idEtapa];
            const etapaDiv = timerElement.closest('.etapa-item');
            if (etapaDiv) {
                const completeBtn = etapaDiv.querySelector('.complete-btn');
                if (completeBtn) completeBtn.click();
            }
            return;
        }
        tiempo--;
        timerElement.textContent = tiempo;
        progressElement.value = (tiempo / initialTime) * 100;
    }, 1000);
}

function handleStartEtapa(e) {
    const idEtapa = e.target.dataset.id;
    const idLote = e.target.dataset.lote;
    const timerElement = document.getElementById(`timer-${idEtapa}`);
    if (timerElement) {
        const initialTime = parseInt(timerElement.textContent) || 0;
        startTimer(idEtapa, initialTime);
    }
    updateEtapa(idLote, idEtapa, 'En progreso', getTiempoRestante(idEtapa));
}

function handlePauseEtapa(e) {
    const idEtapa = e.target.dataset.id;
    if (timers[idEtapa]) {
        clearInterval(timers[idEtapa]);
        delete timers[idEtapa];
    }
    const idLote = e.target.dataset.lote;
    updateEtapa(idLote, idEtapa, 'Pausado', parseInt(document.getElementById(`timer-${idEtapa}`).textContent) || 0);
}

function handleCompleteEtapa(e) {
    const idEtapa = e.target.dataset.id;
    const idLote = e.target.dataset.lote;
    if (timers[idEtapa]) {
        clearInterval(timers[idEtapa]);
        delete timers[idEtapa];
    }

    fetch(`${BASE_URL}/api/lotes/${idLote}/etapas/${idEtapa}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => response.json())
        .then(etapaData => {
            const productosRequeridos = etapaData.productos_requeridos || {};
            const updates = [];
            for (const [productName, quantity] of Object.entries(productosRequeridos)) {
                fetch(`${BASE_URL}/api/inventario`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                })
                    .then(response => response.json())
                    .then(inventario => {
                        const product = inventario.find(p => p.product === productName);
                        if (product && product.quantity >= quantity) {
                            updates.push(
                                fetch(`${BASE_URL}/api/inventario/${product.id}`, {
                                    method: 'PUT',
                                    headers: {
                                        'Content-Type': 'application/json',
                                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                                    },
                                    body: JSON.stringify({ cantidad: product.quantity - quantity })
                                })
                            );
                            registerMovement(product.id, productName, 'Salida', quantity, `Uso en etapa ${idEtapa} del lote ${idLote}`);
                        } else {
                            alert(`No hay suficiente ${productName} en inventario para completar la etapa.`);
                        }
                    });
            }
            return Promise.all(updates);
        })
        .then(() => updateEtapa(idLote, idEtapa, 'Completado', 0))
        .catch(error => {
            console.error('Error al actualizar inventario:', error.message);
            alert('Error al actualizar inventario: ' + error.message);
        });
}

function updateEtapa(idLote, idEtapa, estado, tiempoRestante) {
    const token = localStorage.getItem('token');
    fetch(`${BASE_URL}/api/lotes/${idLote}/etapas/${idEtapa}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            estado_etapa: estado,
            tiempo_restante: tiempoRestante,
            productos_requeridos: {}
        })
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            alert(data.message || 'Etapa actualizada correctamente');
            fetchAndUpdateLotes();
        })
        .catch(error => {
            console.error('Error al actualizar etapa:', error.message);
            alert('Error al actualizar etapa: ' + error.message);
        });
}

function getTiempoRestante(idEtapa) {
    const timerElement = document.getElementById(`timer-${idEtapa}`);
    return timerElement ? parseInt(timerElement.textContent) || 0 : 0;
}

function handleEditLote(e) {
    const idLote = e.target.getAttribute('data-id');
    fetch(`${BASE_URL}/api/lotes/${idLote}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(loteData => {
            document.getElementById('loteNumber').value = loteData.lote.numero_lote || '';
            const etapasContainer = document.getElementById('etapasContainer');
            etapasContainer.innerHTML = '';
            if (loteData.etapas && loteData.etapas.length > 0) {
                loteData.etapas.forEach((etapa, index) => {
                    addEtapaRow(
                        index + 1,
                        etapa.nombre_etapa || '',
                        etapa.tiempo_estimado || '',
                        etapa.maquina_utilizada || '',
                        etapa.productos_requeridos || {}
                    );
                });
            } else {
                addEtapaRow(1);
            }
            document.getElementById('loteModalTitle').textContent = 'Editar Lote';
            document.getElementById('loteForm').dataset.id = idLote;
            loteModalOverlay.style.display = 'flex';
        })
        .catch(error => {
            console.error('Error al cargar lote:', error.message);
            alert('Error al cargar lote: ' + error.message);
        });
}



// Funciones relacionadas con tipos de producto
function loadTiposIntoForm() {
    const typeSelect = document.getElementById('productType');
    const editTypeSelect = document.getElementById('editProductType');
    if (!typeSelect || !editTypeSelect) return;

    fetch(`${BASE_URL}/api/tipos_producto`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            typeSelect.innerHTML = '';
            editTypeSelect.innerHTML = '';
            data.forEach(tipo => {
                const option = document.createElement('option');
                option.value = tipo.id_tipo;
                option.textContent = tipo.nombre;
                typeSelect.appendChild(option.cloneNode(true));
                editTypeSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error al cargar tipos:', error);
            typeSelect.innerHTML = '<option value="">Error al cargar tipos</option>';
            editTypeSelect.innerHTML = '<option value="">Error al cargar tipos</option>';
        });
}

function loadTiposIntoFilter() {
    const filterTypeSelect = document.getElementById('filterType');
    if (!filterTypeSelect) return;

    filterTypeSelect.innerHTML = '<option value="">Todos</option>';
    fetch(`${BASE_URL}/api/tipos_producto`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            data.forEach(tipo => {
                const option = document.createElement('option');
                option.value = tipo.id_tipo;
                option.textContent = tipo.nombre;
                filterTypeSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error al cargar tipos en el filtro:', error);
            filterTypeSelect.innerHTML = '<option value="">Error al cargar tipos</option>';
        });
}

// Funciones relacionadas con proveedores
function loadProveedoresIntoForm() {
    const providerSelect = document.getElementById('productProvider');
    const editProviderSelect = document.getElementById('editProductProvider');
    if (!providerSelect || !editProviderSelect) return;

    providerSelect.innerHTML = '<option value="">Sin proveedor</option>';
    editProviderSelect.innerHTML = '<option value="">Sin proveedor</option>';

    const token = localStorage.getItem('token');
    if (!token) {
        alert('No se encontró un token de autenticación. Por favor, inicia sesión nuevamente.');
        window.location.href = 'index.html';
        return;
    }

    fetch(`${BASE_URL}/api/proveedores`, { // Cambiado de /api/v2/proveedores a /api/proveedores para consistencia
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        credentials: 'include' // Añadido para soportar credenciales (CORS con cookies si es necesario)
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            data.forEach(proveedor => {
                const option = document.createElement('option');
                option.value = proveedor.id_proveedor;
                option.textContent = sanitizeHTML(proveedor.nombre);
                providerSelect.appendChild(option.cloneNode(true));
                editProviderSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error al cargar proveedores en el formulario:', error.message);
            providerSelect.innerHTML = '<option value="">Error al cargar proveedores</option>';
            editProviderSelect.innerHTML = '<option value="">Error al cargar proveedores</option>';
            alert('No se pudieron cargar los proveedores: ' + error.message);
        });
}

async function loadProveedores() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            alert('No se encontró un token de autenticación. Por favor, inicia sesión nuevamente.');
            window.location.href = 'index.html';
            return;
        }

        const response = await fetch(`${BASE_URL}/api/proveedores`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error al cargar proveedores: ${response.status}`);
        }

        const proveedores = await response.json();

        const table = document.getElementById('proveedores-table');
        table.innerHTML = `
            <div class="grid-header">
                <div>Nombre</div>
                <div>Contacto</div>
                <div>Teléfono</div>
                <div>Email</div>
                <div>Acciones</div>
            </div>
        `;

        if (proveedores.length === 0) {
            const row = document.createElement('div');
            row.className = 'grid-row';
            row.innerHTML = `<div colspan="5">No hay proveedores disponibles.</div>`;
            table.appendChild(row);
            return;
        }

        proveedores.forEach(proveedor => {
            const row = document.createElement('div');
            row.className = 'grid-row';
            row.innerHTML = `
                <div>${sanitizeHTML(proveedor.nombre)}</div>
                <div>${sanitizeHTML(proveedor.contacto)}</div>
                <div>${sanitizeHTML(proveedor.telefono)}</div>
                <div>${sanitizeHTML(proveedor.email)}</div>
                <div>
                    <button class="action-btn edit-btn" onclick="editProveedor(${proveedor.id_proveedor})">Editar</button>
                    <button class="action-btn delete-btn" onclick="deleteProveedor(${proveedor.id_proveedor})">Eliminar</button>
                </div>
            `;
            table.appendChild(row);
        });
    } catch (error) {
        console.error('Error al cargar proveedores:', error.message);
        alert('Error al cargar proveedores: ' + error.message);
        const table = document.getElementById('proveedores-table');
        table.innerHTML = `
            <div class="grid-header">
                <div>Nombre</div>
                <div>Contacto</div>
                <div>Teléfono</div>
                <div>Email</div>
                <div>Acciones</div>
            </div>
            <div class="grid-row">
                <div colspan="5">Error al cargar proveedores: ${sanitizeHTML(error.message)}</div>
            </div>
        `;
    }
}

async function editProveedor(id) {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            alert('No se encontró un token de autenticación. Por favor, inicia sesión nuevamente.');
            window.location.href = 'index.html';
            return;
        }

        const response = await fetch(`${BASE_URL}/api/proveedores/${id}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error al cargar proveedor: ${response.status}`);
        }

        const proveedor = await response.json();

        document.getElementById('proveedorModalTitle').textContent = 'Editar Proveedor';
        document.getElementById('proveedorNombre').value = sanitizeHTML(proveedor.nombre);
        document.getElementById('proveedorContacto').value = sanitizeHTML(proveedor.contacto);
        document.getElementById('proveedorTelefono').value = sanitizeHTML(proveedor.telefono);
        document.getElementById('proveedorEmail').value = sanitizeHTML(proveedor.email);
        document.getElementById('proveedorForm').dataset.id = id;
        document.getElementById('proveedorModalOverlay').style.display = 'flex';
    } catch (error) {
        console.error('Error al cargar proveedor para editar:', error.message);
        alert('Error al cargar proveedor para editar: ' + error.message);
    }
}

async function deleteProveedor(id) {
    if (!confirm('¿Estás seguro de que deseas eliminar este proveedor?')) {
        return;
    }

    try {
        const token = localStorage.getItem('token');
        if (!token) {
            alert('No se encontró un token de autenticación. Por favor, inicia sesión nuevamente.');
            window.location.href = 'index.html';
            return;
        }

        const response = await fetch(`${BASE_URL}/api/proveedores/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al eliminar el proveedor');
        }

        const data = await response.json();
        alert(data.message);
        loadProveedores();
    } catch (error) {
        console.error('Error al eliminar proveedor:', error.message);
        alert('Error al eliminar el proveedor: ' + error.message);
    }
}

async function saveProveedor() {
    try {
        const idProveedor = document.getElementById('proveedorForm').dataset.id;
        const nombre = document.getElementById('proveedorNombre').value.trim();
        const contacto = document.getElementById('proveedorContacto').value.trim();
        const telefono = document.getElementById('proveedorTelefono').value.trim();
        const email = document.getElementById('proveedorEmail').value.trim();

        if (!nombre || !contacto || !telefono || !email) {
            alert('Todos los campos son obligatorios.');
            return;
        }

        const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
        if (!emailRegex.test(email)) {
            alert('Por favor, ingresa un email válido.');
            return;
        }

        const telefonoRegex = /^\+?\d{9,15}$/;
        if (!telefonoRegex.test(telefono)) {
            alert('Por favor, ingresa un teléfono válido (entre 9 y 15 dígitos, opcionalmente con un "+" al inicio).');
            return;
        }

        const data = { nombre, contacto, telefono, email };

        const token = localStorage.getItem('token');
        if (!token) {
            alert('No se encontró un token de autenticación. Por favor, inicia sesión nuevamente.');
            window.location.href = 'index.html';
            return;
        }

        const method = idProveedor ? 'PUT' : 'POST';
        const url = idProveedor ? `${BASE_URL}/api/proveedores/${idProveedor}` : `${BASE_URL}/api/proveedores`;

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            credentials: 'include',
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error al guardar proveedor: ${response.status}`);
        }

        const result = await response.json();
        alert(result.message || 'Proveedor guardado exitosamente');
        document.getElementById('proveedorModalOverlay').style.display = 'none';
        loadProveedores();
        loadProveedoresIntoForm(); // Actualizar los selectores de proveedores en los formularios
    } catch (error) {
        console.error('Error al guardar proveedor:', error.message);
        alert('Error al guardar proveedor: ' + error.message);
    }
}

function saveTipoProducto() {
    const nombre = document.getElementById('tipoNombre').value.trim();
    if (!nombre) {
        alert('El campo "Nombre" es obligatorio.');
        return;
    }

    fetch(`${BASE_URL}/api/tipos_producto`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ nombre: nombre })
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            alert('Tipo de producto agregado');
            tipoModalOverlay.style.display = 'none';
            loadTiposIntoForm();
            loadTiposIntoFilter();
        })
        .catch(error => {
            console.error('Error al agregar tipo de producto:', error);
            alert('Error al agregar: ' + error.message);
        });
}

function verifyProduct(id, button, estado = 'Verificado') {
    fetch(`${BASE_URL}/api/verificar`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
            id_producto: id,
            estado_verificacion: estado
        })
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            alert(`Producto actualizado correctamente (estado: ${estado})`);
            const productName = data.producto || 'Producto desconocido';
            registerMovement(id, productName, 'Verificación', 0, `Producto marcado como ${estado}`);
            fetchAndUpdateTable();
        })
        .catch(error => {
            console.error('Error al verificar producto:', error);
            alert('Error al verificar: ' + error.message);
        });
}

function markAsBad(id, button) {
    verifyProduct(id, button, 'En mal estado');
}

function handleEdit(e) {
    const productId = e.target.getAttribute('data-id');
    if (!productId || isNaN(parseInt(productId))) {
        alert('ID de producto no válido.');
        return;
    }
    fetch(`${BASE_URL}/api/inventario/${productId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(product => {
            document.getElementById('editProductId').value = product.id || '';
            document.getElementById('editProductName').value = product.product || '';
            document.getElementById('editProductQuantity').value = extractQuantity(product.quantity) || 0;
            document.getElementById('editProductType').value = product.type_id || '';
            document.getElementById('editProductUnit').value = product.unit_id || '';
            document.getElementById('editProductStockMin').value = product.stock_minimo || 0;
            document.getElementById('editProductStockMax').value = product.stock_maximo || '';
            document.getElementById('editProductPrice').value = product.precio || 0;
            document.getElementById('editProductState').value = product.estado_verificacion || 'Pendiente';
            document.getElementById('editProductProvider').value = product.id_proveedor ? product.id_proveedor.toString() : '';
            document.getElementById('editProductLote').value = product.lote || '';
            document.getElementById('editProductEsToxico').checked = product.es_toxico || false;
            document.getElementById('editProductEsCorrosivo').checked = product.es_corrosivo || false;
            document.getElementById('editProductEsInflamable').checked = product.es_inflamable || false;
            editingProductId = product.id;
            editProductModalOverlay.style.display = 'flex';
        })
        .catch(error => {
            console.error('Error al cargar producto:', error);
            alert('Error al cargar: ' + error.message);
        });
}

function resetForm() {
    const productForm = document.getElementById('productForm');
    if (productForm) productForm.reset();
    editingProductId = null;
    document.getElementById('modalTitle').textContent = 'Agregar Producto';
}

function applyQuickFilter(data, qf) {
    const q = (it) => extractQuantity(it.quantity);
    switch (qf) {
        case 'bajo': return data.filter(it => q(it) < (Number(it.stock_minimo) || 0));
        case 'sin': return data.filter(it => q(it) <= 0);
        case 'sobre': return data.filter(it => Number(it.stock_maximo) > 0 && q(it) > Number(it.stock_maximo));
        case 'peligrosos': return data.filter(it => it.es_toxico || it.es_corrosivo || it.es_inflamable);
        case 'pendientes': return data.filter(it => it.estado_verificacion === 'Pendiente');
        default: return data;
    }
}

function updateQuickFilterCounts(data) {
    const labels = { todos: 'Todos', bajo: 'Bajo stock', sin: 'Sin stock', sobre: 'Sobrestock', peligrosos: 'Peligrosos', pendientes: 'Pendientes' };
    document.querySelectorAll('.qf-chip').forEach(chip => {
        const k = chip.dataset.qf;
        const n = applyQuickFilter(data, k).length;
        chip.textContent = `${labels[k] || k} (${n})`;
    });
}

function fetchAndUpdateTable() {
    if (!loading || !tableBody || !checklistBody) return;

    loading.style.display = 'block';
    fetch(`${BASE_URL}/api/inventario`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            tableBody.innerHTML = '';
            checklistBody.innerHTML = '';
            if (!data || data.length === 0) {
                tableBody.innerHTML = '<div class="inventory-item">No hay productos</div>';
                return;
            }
            updateQuickFilterCounts(data);
            let filteredData = currentFilter ? data.filter(item => parseInt(item.type_id) === parseInt(currentFilter)) : data;
            if (searchTerm) {
                const normalizedSearchTerm = normalizeString(searchTerm);
                filteredData = filteredData.filter(item => normalizeString(item.product).includes(normalizedSearchTerm));
            }
            filteredData = applyQuickFilter(filteredData, currentQuickFilter);
            if (filteredData.length === 0) {
                tableBody.innerHTML = '<div class="inventory-item">No se encontraron productos</div>';
            } else {
                filteredData.forEach(item => {
                    const quantityValue = extractQuantity(item.quantity);
                    const stockMaximo = item.stock_maximo || 0;
                    const stockMinimo = Number(item.stock_minimo) || 0;
                    let stockClass = quantityValue < stockMinimo ? 'expire-soon' : (quantityValue < stockMinimo * 1.5 ? 'expire-warning' : 'expire-safe');

                    const card = document.createElement('div');
                    card.className = `inventory-item ${stockClass}`;
                    card.innerHTML = `
                        <h3>${item.product || 'Sin nombre'}</h3>
                        <p><strong>Cantidad:</strong> ${quantityValue || '0'} ${item.unit || ''}</p>
                        <p><strong>Tipo:</strong> ${item.type || 'Sin tipo'}</p>
                        <p><strong>Unidad:</strong> ${item.unit || 'Sin unidad'}</p>
                        <p><strong>Stock Mínimo:</strong> ${item.stock_minimo || '0'}</p>
                        <p><strong>Stock Máximo:</strong> ${stockMaximo || 'N/A'}</p>
                        <p><strong>Precio:</strong> $${item.precio ? item.precio.toFixed(2) : '0.00'}</p>
                        <p><strong>Propiedades:</strong> 
                            ${item.es_toxico ? 'Tóxico ' : ''}${item.es_corrosivo ? 'Corrosivo ' : ''}${item.es_inflamable ? 'Inflamable' : ''}
                        </p>
                        <button class="edit-btn" data-id="${item.id || ''}" ${currentUser.rol === 'bodeguero' ? 'style="display:none;"' : ''}>Editar</button>
                    `;
                    tableBody.appendChild(card);
                });
                document.querySelectorAll('.edit-btn').forEach(btn => btn.addEventListener('click', handleEdit));

                if (currentUser.rol.toLowerCase() === 'bodeguero') {
                    const pendingProducts = filteredData.filter(item => item.estado_verificacion === 'Pendiente');
                    if (pendingProducts.length === 0) {
                        checklistBody.innerHTML = '<div class="inventory-item">No hay productos por verificar</div>';
                    } else {
                        pendingProducts.forEach(item => {
                            const quantityValue = extractQuantity(item.quantity);
                            const stockMaximo = item.stock_maximo || 0;
                            const stockMinimo = Number(item.stock_minimo) || 0;
                            let stockClass = quantityValue < stockMinimo ? 'expire-soon' : (quantityValue < stockMinimo * 1.5 ? 'expire-warning' : 'expire-safe');

                            const card = document.createElement('div');
                            card.className = `inventory-item ${stockClass}`;
                            card.innerHTML = `
                                <h3>${item.product || 'Sin nombre'}</h3>
                                <p><strong>Cantidad:</strong> ${quantityValue || '0'} ${item.unit || ''}</p>
                                <p><strong>Tipo:</strong> ${item.type || 'Sin tipo'}</p>
                                <p><strong>Unidad:</strong> ${item.unit || 'Sin unidad'}</p>
                                <p><strong>Stock Mínimo:</strong> ${item.stock_minimo || '0'}</p>
                                <p><strong>Stock Máximo:</strong> ${stockMaximo || 'N/A'}</p>
                                <p><strong>Precio:</strong> $${item.precio ? item.precio.toFixed(2) : '0.00'}</p>
                                <p><strong>Propiedades:</strong> 
                                    ${item.es_toxico ? 'Tóxico ' : ''}${item.es_corrosivo ? 'Corrosivo ' : ''}${item.es_inflamable ? 'Inflamable' : ''}
                                </p>
                                <button class="verify-btn" data-id="${item.id || ''}">Verificar</button>
                                <button class="bad-btn" data-id="${item.id || ''}">Marcar como mal estado</button>
                            `;
                            checklistBody.appendChild(card);
                        });
                        document.querySelectorAll('.verify-btn').forEach(btn => btn.addEventListener('click', (e) => verifyProduct(e.target.getAttribute('data-id'), e.target)));
                        document.querySelectorAll('.bad-btn').forEach(btn => btn.addEventListener('click', (e) => markAsBad(e.target.getAttribute('data-id'), e.target)));
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error al cargar inventario:', error);
            tableBody.innerHTML = '<div class="inventory-item">Error al cargar inventario</div>';
            if (currentUser.rol.toLowerCase() === 'bodeguero') {
                checklistBody.innerHTML = '<div class="inventory-item">Error al cargar productos por verificar</div>';
            }
        })
        .finally(() => loading.style.display = 'none');
}

async function loadReport() {
    const token = localStorage.getItem('token');

    if (!token) {
        console.error('No se encontró token');
        window.location.href = 'index.html';
        return;
    }

    try {
        const url = `${BASE_URL}/api/reportes`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Resumen del Inventario
        document.getElementById('totalProductos').textContent = data?.resumen_inventario?.total_productos || 0;
        document.getElementById('valorTotal').textContent = `$${data?.resumen_inventario?.valor_total ? data.resumen_inventario.valor_total.toFixed(2) : '0.00'}`;
        document.getElementById('bajoStockCount').textContent = data?.resumen_inventario?.productos_bajo_stock?.length || 0;

        const bajoStockTable = document.getElementById('bajoStockTable');
        bajoStockTable.innerHTML = '';
        if (data?.resumen_inventario?.productos_bajo_stock?.length > 0) {
            data.resumen_inventario.productos_bajo_stock.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${sanitizeHTML(item.nombre)}</td>
                    <td>${item.cantidad}</td>
                    <td>${item.stock_minimo}</td>
                `;
                bajoStockTable.appendChild(row);
            });
        } else {
            bajoStockTable.innerHTML = '<tr><td colspan="3">No hay productos bajo stock.</td></tr>';
        }

        const especialesTable = document.getElementById('especialesTable');
        especialesTable.innerHTML = '';
        if (data?.resumen_inventario?.productos_especiales?.length > 0) {
            data.resumen_inventario.productos_especiales.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${sanitizeHTML(item.nombre)}</td>
                    <td>${item.toxico ? 'Sí' : 'No'}</td>
                    <td>${item.corrosivo ? 'Sí' : 'No'}</td>
                    <td>${item.inflamable ? 'Sí' : 'No'}</td>
                `;
                especialesTable.appendChild(row);
            });
        } else {
            especialesTable.innerHTML = '<tr><td colspan="4">No hay productos con características especiales.</td></tr>';
        }

        // Productos con Más Stock
        const productosMasStockTable = document.getElementById('productosMasStockTable');
        productosMasStockTable.innerHTML = '';
        if (data?.resumen_inventario?.productos?.length > 0) {
            const productosOrdenados = [...data.resumen_inventario.productos]
                .sort((a, b) => b.cantidad - a.cantidad)
                .slice(0, 5);
            productosOrdenados.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${sanitizeHTML(item.nombre)}</td>
                    <td>${item.cantidad}</td>
                `;
                productosMasStockTable.appendChild(row);
            });
        } else {
            productosMasStockTable.innerHTML = '<tr><td colspan="2">No hay datos disponibles.</td></tr>';
        }

        // Actualizar fechas y usuario
        document.getElementById('reportDate').textContent = new Date().toLocaleDateString('es-ES');
        document.getElementById('reportUser').textContent = currentUser?.nombre || 'Usuario';
        document.getElementById('footerDate').textContent = new Date().toLocaleDateString('es-ES');

    } catch (error) {
        console.error('Error al cargar el reporte:', error);
        const reportContainer = document.getElementById('reportContainer');
        if (reportContainer) {
            reportContainer.innerHTML = `<p>Error al cargar el reporte: ${sanitizeHTML(error.message)}</p>`;
        }
    }
}




// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    const isLoginPage = document.getElementById('loginForm') !== null;
    const isDashboardPage = document.getElementById('inventory-table') !== null;
    const isProcessPage = document.getElementById('lotes-table') !== null;
    const isPrototypePage = document.getElementById('prototypes-table') !== null;
    const isReportPage = document.getElementById('reportContainer') !== null;
    const isProveedoresPage = document.getElementById('proveedores-section') !== null;

    if (isLoginPage) {
        document.getElementById('loginForm').onsubmit = (e) => {
            e.preventDefault();
            console.log('Formulario de login enviado'); // Depuración
        
            const btn = document.getElementById('loginBtn');
            btn.disabled = true;
            btn.textContent = 'Cargando...';
        
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
        
            console.log('Usuario:', username); // Depuración
            console.log('Contraseña:', password); // Depuración
            console.log('URL de la solicitud:', `${BASE_URL}/api/login`); // Depuración
        
            fetch(`${BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nombre: username, contrasena: password })
            })
                .then(response => {
                    console.log('Respuesta recibida:', response.status); // Depuración
                    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    console.log('Datos recibidos:', data); // Depuración
                    if (data.user && data.token) {
                        localStorage.setItem('user', JSON.stringify(data.user));
                        localStorage.setItem('token', data.token);
                        currentUser = data.user;
                        window.location.href = '/dashboard.html';
                    } else {
                        alert(data.error || 'Error al iniciar sesión');
                    }
                })
                .catch(error => {
                    console.error('Error en login:', error); // Depuración
                    alert('Error: ' + error.message);
                })
                .finally(() => {
                    btn.disabled = false;
                    btn.textContent = 'Iniciar sesión';
                });
        };
    } else {
        currentUser = JSON.parse(localStorage.getItem('user'));
        if (!currentUser || !localStorage.getItem('token')) {
            window.location.href = 'index.html';
            return;
        }

        document.getElementById('loggedInUser').textContent = currentUser.nombre || 'Usuario';
        loading = document.getElementById('loading');
        const logoutBtn = document.getElementById('logoutBtn');
        const menuToggle = document.querySelector('.menu-toggle');
        const nav = document.querySelector('.nav');

        if (!logoutBtn || !menuToggle || !nav) return;

        logoutBtn.onclick = () => {
            Object.values(timers).forEach(timer => clearInterval(timer));
            timers = {};
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            window.location.href = 'index.html';
        };

        menuToggle.onclick = () => nav.classList.toggle('active');

        if (isDashboardPage) {
            tableBody = document.getElementById('inventory-table');
            checklistBody = document.getElementById('checklist-body');
            modalOverlay = document.getElementById('modalOverlay');
            editProductModalOverlay = document.getElementById('editProductModalOverlay');
            proveedorModalOverlay = document.getElementById('proveedorModalOverlay');
            tipoModalOverlay = document.getElementById('tipoModalOverlay');
            reportOutput = document.getElementById('report-output');
        
            const addProductBtn = document.getElementById('addProductBtn');
            const reportSection = document.getElementById('report-section');
            const adminSection = document.getElementById('admin-section');
            const filterBtn = document.getElementById('filterBtn');
            const reportLink = document.getElementById('reportLink');
            const adminLink = document.getElementById('adminLink');
            const searchInput = document.getElementById('searchInput');
            const clearSearchBtn = document.getElementById('clearSearchBtn');
            const addTipoBtn = document.getElementById('addTipoBtn');
        
            loadTiposIntoForm();
            loadProveedoresIntoForm();
            fetchAndUpdateTable();
        
            function loadPageBasedOnRole(rol) {
                const rolLower = rol.toLowerCase();
                if (addProductBtn) addProductBtn.style.display = rolLower === 'bodeguero' || rolLower === 'administrador' ? 'block' : 'none';
                if (filterBtn) filterBtn.style.display = rolLower !== 'bodeguero' ? 'block' : 'none';
                if (addTipoBtn) addTipoBtn.style.display = rolLower === 'administrador' ? 'block' : 'none';
                if (prototypeLink) prototypeLink.style.display = 'block';
                if (reportLink) reportLink.style.display = rolLower === 'administrador' || rolLower === 'lider' ? 'block' : 'none';
                if (adminLink) adminLink.style.display = rolLower === 'administrador' ? 'block' : 'none';
            }
        
            loadPageBasedOnRole(currentUser.rol);
        
            addProductBtn.onclick = () => {
                resetForm();
                loadTiposIntoForm();
                loadProveedoresIntoForm();
                modalOverlay.style.display = 'flex';
            };
        
            filterBtn.onclick = () => {
                if (filterBtn.classList.contains('clear-filter')) {
                    currentFilter = '';
                    filterBtn.classList.remove('clear-filter');
                    filterBtn.innerHTML = '<i class="fas fa-filter"></i> Filtrar';
                    fetchAndUpdateTable();
                } else {
                    loadTiposIntoFilter();
                    document.getElementById('filterModalOverlay').style.display = 'flex';
                }
            };
        

        
            addTipoBtn.onclick = () => {
                document.getElementById('tipoForm').reset();
                tipoModalOverlay.style.display = 'flex';
            };
        
            document.getElementById('closeModalBtn').onclick = () => modalOverlay.style.display = 'none';
            document.getElementById('closeEditModalBtn').onclick = () => editProductModalOverlay.style.display = 'none';
            document.getElementById('closeProveedorModalBtn').onclick = () => proveedorModalOverlay.style.display = 'none';
            document.getElementById('closeTipoModalBtn').onclick = () => tipoModalOverlay.style.display = 'none';
            document.getElementById('closeFilterModalBtn').onclick = () => document.getElementById('filterModalOverlay').style.display = 'none';

            document.querySelectorAll('.qf-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    currentQuickFilter = chip.dataset.qf;
                    document.querySelectorAll('.qf-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    fetchAndUpdateTable();
                });
            });
        
            document.getElementById('productForm').onsubmit = async (e) => {
                e.preventDefault();
            
                // Recolectar datos del formulario con los IDs correctos de tu HTML
                const nombre = document.getElementById('productName').value.trim();
                const cantidad = parseFloat(document.getElementById('productQuantity').value) || NaN;
                const idTipo = parseInt(document.getElementById('productType').value) || null;
                const idUnidad = parseInt(document.getElementById('productUnit').value) || null;
                const stockMinimo = parseFloat(document.getElementById('productStockMin').value) || NaN;
                const stockMaximo = parseFloat(document.getElementById('productStockMax').value) || NaN;
                const precio = parseFloat(document.getElementById('productPrice').value) || NaN;
                const idProveedor = parseInt(document.getElementById('productProvider').value) || null;
                const estadoVerificacion = document.getElementById('productState').value || 'Pendiente';
                const esToxico = document.getElementById('isToxic').checked;
                const esCorrosivo = document.getElementById('isCorrosive').checked;
                const esInflamable = document.getElementById('isFlammable').checked; 
        
                // Validación de campos obligatorios
                if (!nombre || isNaN(cantidad) || cantidad <= 0 || !idTipo || !idUnidad || 
                isNaN(stockMinimo) || isNaN(stockMaximo) || stockMaximo <= stockMinimo || 
                isNaN(precio)) {
                alert('Por favor, completa todos los campos obligatorios con valores válidos.');
                return;
                }
        
                const data = {
                    nombre,
                    id_tipo: idTipo, // Añadido porque tu formulario tiene productType
                    id_unidad: idUnidad,
                    cantidad,
                    precio,
                    stock_minimo: stockMinimo,
                    stock_maximo: stockMaximo,
                    id_proveedor: idProveedor,
                    lote: '', // No hay campo de lote en este formulario, se envía vacío
                    es_toxico: esToxico,
                    es_corrosivo: esCorrosivo,
                    es_inflamable: esInflamable,
                    estado_verificacion: estadoVerificacion
                };
            
                try {
                    const response = await fetch(`${BASE_URL}/api/inventario`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('token')}`
                        },
                        body: JSON.stringify(data)
                    });
            
                    const result = await response.json();
            
                    if (!response.ok) {
                        throw new Error(result.error || `Error al agregar el producto: ${response.status}`);
                    }
        
                    alert(result.message || 'Producto agregado correctamente');
                    modalOverlay.style.display = 'none'; // Cierra el modal
                    fetchAndUpdateTable(); // Actualiza la tabla
                    productForm.reset(); // Limpia el formulario
        
                    // Opcional: registrar movimiento si tienes esta función
                    if (result.id && typeof registerMovement === 'function') {
                        registerMovement(result.id, nombre, 'Entrada', cantidad, 'Producto agregado al inventario');
        }
        
                } catch (error) {
                    console.error('Error al agregar producto:', error);
                    alert('Error al agregar el producto: ' + error.message);
                }
            };

            document.getElementById('editProductForm').onsubmit = (e) => {
                e.preventDefault();
                const nombre = document.getElementById('editProductName').value.trim();
                const cantidad = parseFloat(document.getElementById('editProductQuantity').value);
                const stockMinimo = parseFloat(document.getElementById('editProductStockMin').value);
                const stockMaximo = parseFloat(document.getElementById('editProductStockMax').value);

                if (!nombre || isNaN(cantidad) || cantidad <= 0 || isNaN(stockMinimo) || isNaN(stockMaximo) || stockMaximo <= stockMinimo) {
                    alert('Por favor, completa todos los campos correctamente.');
                    return;
                }

                const data = {
                    nombre,
                    id_tipo: parseInt(document.getElementById('editProductType').value) || null,
                    id_unidad: parseInt(document.getElementById('editProductUnit').value) || null,
                    cantidad,
                    stock_minimo: stockMinimo,
                    stock_maximo: stockMaximo,
                    precio: parseFloat(document.getElementById('editProductPrice').value) || 0,
                    estado_verificacion: document.getElementById('editProductState').value || 'Pendiente',
                    id_proveedor: parseInt(document.getElementById('editProductProvider').value) || null,
                    lote: document.getElementById('editProductLote').value.trim() || null,
                    es_toxico: document.getElementById('editProductEsToxico').checked,
                    es_corrosivo: document.getElementById('editProductEsCorrosivo').checked,
                    es_inflamable: document.getElementById('editProductEsInflamable').checked
                };

                fetch(`${BASE_URL}/api/inventario/${editingProductId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(data)
                })
                    .then(response => {
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        return response.json();
                    })
                    .then(data => {
                        alert(data.message || 'Producto actualizado exitosamente');
                        editProductModalOverlay.style.display = 'none';
                        fetchAndUpdateTable();
                        registerMovement(editingProductId, nombre, 'Actualización', cantidad, 'Producto actualizado');
                    })
                    .catch(error => {
                        console.error('Error al actualizar producto:', error);
                        alert('Error al actualizar: ' + error.message);
                    });
            };

            document.getElementById('filterForm').onsubmit = (e) => {
                e.preventDefault();
                currentFilter = document.getElementById('filterType').value;
                document.getElementById('filterModalOverlay').style.display = 'none';
                filterBtn.classList.add('clear-filter');
                filterBtn.innerHTML = '<i class="fas fa-times"></i> Limpiar Filtro';
                fetchAndUpdateTable();
            };

            document.getElementById('tipoForm').onsubmit = (e) => {
                e.preventDefault();
                saveTipoProducto();
            };
        }

        if (isProcessPage) {
            lotesTable = document.getElementById('lotes-table');
            loteModalOverlay = document.getElementById('loteModalOverlay');
            const addLoteBtn = document.getElementById('addLoteBtn');

            fetchAndUpdateLotes();

            addLoteBtn.onclick = () => {
                document.getElementById('loteForm').reset();
                document.getElementById('loteModalTitle').textContent = 'Agregar Lote';
                document.getElementById('etapasContainer').innerHTML = '';
                addEtapaRow(1);
                delete document.getElementById('loteForm').dataset.id;
                loteModalOverlay.style.display = 'flex';
            };

            document.getElementById('closeLoteModalBtn').onclick = () => {
                loteModalOverlay.style.display = 'none';
                Object.values(timers).forEach(timer => clearInterval(timer));
                timers = {};
            };

            document.getElementById('loteForm').onsubmit = (e) => {
                e.preventDefault();
                const numeroLote = document.getElementById('loteNumber').value.trim();
                if (!numeroLote) {
                    alert('El número de lote es obligatorio.');
                    return;
                }

                const etapasRows = document.querySelectorAll('.etapa-row');
                if (etapasRows.length === 0) {
                    alert('Debes agregar al menos una etapa.');
                    return;
                }

                const etapas = Array.from(etapasRows).map((row, index) => {
                    const nombre = row.querySelector('.etapa-nombre').value.trim();
                    const tiempo = parseInt(row.querySelector('.etapa-tiempo').value);
                    const maquina = row.querySelector('.etapa-maquina').value.trim();
                    const productosMap = row.productsMap || new Map();
                    const productosRequeridos = Object.fromEntries(productosMap);

                    if (!nombre || isNaN(tiempo) || tiempo <= 0 || !maquina) {
                        alert(`Por favor, completa todos los campos de la etapa ${index + 1}.`);
                        throw new Error('Campos incompletos');
                    }

                    return {
                        numero_etapa: index + 1,
                        nombre_etapa: nombre,
                        tiempo_estimado: tiempo,
                        maquina_utilizada: maquina,
                        productos_requeridos: productosRequeridos,
                        estado_etapa: 'Pendiente'
                    };
                });

                const data = {
                    numero_lote: numeroLote,
                    etapas: etapas
                };

                const idLote = document.getElementById('loteForm').dataset.id;
                const method = idLote ? 'PUT' : 'POST';
                const url = idLote ? `${BASE_URL}/api/lotes/${idLote}` : `${BASE_URL}/api/lotes`;

                fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(data)
                })
                    .then(response => {
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        return response.json();
                    })
                    .then(data => {
                        alert(data.message || 'Lote guardado exitosamente');
                        loteModalOverlay.style.display = 'none';
                        fetchAndUpdateLotes();
                    })
                    .catch(error => {
                        console.error('Error al guardar lote:', error);
                        alert('Error al guardar lote: ' + error.message);
                    });
            };

            document.getElementById('addEtapaBtn').onclick = () => {
                const etapasContainer = document.getElementById('etapasContainer');
                const numEtapas = etapasContainer.querySelectorAll('.etapa-row').length + 1;
                addEtapaRow(numEtapas);
            };
        }

        if (isPrototypePage) {
            prototypesTable = document.getElementById('prototypes-table');
            prototypeModalOverlay = document.getElementById('prototypeModalOverlay');
            const addPrototypeBtn = document.getElementById('addPrototypeBtn');

            fetchAndUpdatePrototypes();

            addPrototypeBtn.onclick = () => {
                document.getElementById('prototypeForm').reset();
                document.getElementById('prototypeModalTitle').textContent = 'Agregar Prototipo';
                document.getElementById('stagesContainer').innerHTML = '';
                addStageRow(1);
                editingPrototypeId = null;
                prototypeModalOverlay.style.display = 'flex';
            };

            document.getElementById('closePrototypeModalBtn').onclick = () => {
                prototypeModalOverlay.style.display = 'none';
            };

            document.getElementById('addStageBtn').onclick = () => {
                const stagesContainer = document.getElementById('stagesContainer');
                const numStages = stagesContainer.querySelectorAll('.stage-row').length + 1;
                addStageRow(numStages);
            };

            // Guardar o actualizar prototipo
            document.getElementById('prototypeForm').onsubmit = async (e) => {
                e.preventDefault();

                try {
                    const nombre = document.getElementById('prototypeName').value.trim();
                    const responsable = document.getElementById('responsible').value.trim();
                    const notas = document.getElementById('notes').value.trim();
                    const estado = document.getElementById('prototypeState').value;

                    if (!nombre || !responsable || !estado) {
                        alert('Completa todos los campos obligatorios.');
                        return;
                    }

                    const stageRows = document.querySelectorAll('#stagesContainer .stage-row');
                    const etapas = Array.from(stageRows).map(row => {
                        const processSelect = row.querySelector('.stage-process');
                        const productSelect = row.querySelector('.stage-product');
                        const quantityInput = row.querySelector('.stage-quantity');
                        const timeInput = row.querySelector('.stage-time');

                        const quantity = parseFloat(quantityInput.value);
                        const time = parseInt(timeInput.value);

                        if (!processSelect.value || !productSelect.value || isNaN(quantity) || quantity <= 0 || isNaN(time) || time <= 0) {
                            alert('Todos los campos de las etapas son obligatorios y deben ser válidos.');
                            throw new Error('Datos de etapa inválidos');
                        }

                        const productOption = productSelect.options[productSelect.selectedIndex];
                        const availableQuantity = parseFloat(productOption.dataset.quantity);
                        if (quantity > availableQuantity) {
                            alert(`Cantidad (${quantity}) excede el stock disponible (${availableQuantity}) para ${productOption.text}.`);
                            throw new Error('Stock insuficiente');
                        }

                        return {
                            id_proceso: parseInt(processSelect.value),
                            id_producto: parseInt(productSelect.value),
                            cantidad_requerida: quantity,
                            tiempo: time,
                            nombre_proceso: processSelect.options[processSelect.selectedIndex].text,
                            nombre_producto: productOption.text.split(' (')[0]
                        };
                    });

                    if (etapas.length === 0) {
                        alert('Debes agregar al menos una etapa.');
                        return;
                    }

                    const prototypeData = { nombre, responsable, notas, estado, etapas };
                    const url = editingPrototypeId ? `${BASE_URL}/api/prototipos/${editingPrototypeId}` : `${BASE_URL}/api/prototipos`;
                    const method = editingPrototypeId ? 'PUT' : 'POST';

                    const response = await fetch(url, {
                        method,
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('token')}`
                        },
                        body: JSON.stringify(prototypeData)
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `HTTP error: ${response.status}`);
                    }

                    const data = await response.json();
                    alert(data.message || 'Prototipo guardado exitosamente');
                    prototypeModalOverlay.style.display = 'none';
                    document.getElementById('prototypeForm').reset();
                    document.getElementById('stagesContainer').innerHTML = '';
                    editingPrototypeId = null;
                    fetchAndUpdatePrototypes();
                } catch (error) {
                    console.error('Error al guardar prototipo:', error);
                    alert('Error: ' + error.message);
                }
            };

            // Evento para cerrar modal
            document.getElementById('closePrototypeModalBtn').onclick = () => {
                prototypeModalOverlay.style.display = 'none';
                document.getElementById('prototypeForm').reset();
                document.getElementById('stagesContainer').innerHTML = '';
                editingPrototypeId = null;
            };

            // Evento para agregar etapa
            document.getElementById('addStageBtn').onclick = () => {
                const numStages = document.querySelectorAll('#stagesContainer .stage-row').length + 1;
                addStageRow(numStages);
            };

            // Evento para abrir modal de creación
            document.getElementById('addPrototypeBtn').onclick = () => {
                document.getElementById('prototypeForm').reset();
                document.getElementById('prototypeModalTitle').textContent = 'Agregar Prototipo';
                document.getElementById('stagesContainer').innerHTML = '';
                addStageRow(1);
                editingPrototypeId = null;
                prototypeModalOverlay.style.display = 'flex';
            };
        }

        if (isReportPage) {
            
            const exportExcelBtn = document.getElementById('exportExcelBtn');
        
            // Validar la existencia de los botones
            if (!exportExcelBtn) {
                console.error('No se encontraron los botones de exportación:', {  exportExcelBtn });
                return;
            }
        
        
            if (typeof XLSX === 'undefined') {
                console.error('XLSX no está disponible. Asegúrate de incluir la librería.');
                alert('Error: No se puede exportar a Excel porque XLSX no está disponible.');
                exportExcelBtn.disabled = true;
            }
        
            // Cargar el reporte al iniciar
            loadReport();
        
            // Función para mostrar retroalimentación al usuario
            const showExportFeedback = (message, isError = false) => {
                const feedbackElement = document.createElement('div');
                feedbackElement.className = `export-feedback ${isError ? 'error' : 'info'}`;
                feedbackElement.textContent = message;
                document.body.appendChild(feedbackElement);
                setTimeout(() => feedbackElement.remove(), 3000);
            };
        
            // Función para convertir gráficos a imágenes
            const convertChartsToImages = async () => {
                const charts = [
                    { id: 'distribucionTiposChart', parent: null, img: null }
                    // Añade más gráficos aquí si los tienes, por ejemplo: { id: 'otroChart', parent: null, img: null }
                ];
        
                for (const chart of charts) {
                    const canvas = document.getElementById(chart.id);
                    if (canvas) {
                        chart.parent = canvas.parentElement;
                        const imgData = canvas.toDataURL('image/png');
                        const img = document.createElement('img');
                        img.src = imgData;
                        img.style.width = '100%';
                        img.style.maxWidth = '500px'; // Ajusta según el diseño
                        chart.img = img;
                        chart.parent.appendChild(img);
                        canvas.style.display = 'none';
                    }
                }
        
                return charts;
            };
        
            // Función para restaurar gráficos después de exportar
            const restoreCharts = (charts) => {
                charts.forEach(chart => {
                    if (chart.img && chart.parent) {
                        const canvas = chart.parent.querySelector('canvas');
                        if (canvas) {
                            canvas.style.display = 'block';
                            chart.parent.removeChild(chart.img);
                        }
                    }
                });
            };
        
        
            // Exportar a Excel usando la API del backend
            exportExcelBtn.onclick = async function() {
                try {
                    const token = localStorage.getItem('token');
                    if (!token) {
                        showExportFeedback('Error: No hay sesión activa', true);
                        return;
                    }

                    showExportFeedback('Exportando reporte...');

                    const response = await fetch(`${BASE_URL}/api/reportes/export`, {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Error al exportar a Excel');
                    }

                    const blob = await response.blob();
                    const filename = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'Reporte_Avanzado.xlsx';

                    // Intentar usar la API de PyWebView para guardar el archivo
                    try {
                        if (window.pywebview) {
                            const base64Data = await window.blobToBase64(blob);
                            const filePath = await window.pywebview.api.save_file_dialog({
                                save_file: filename,
                                file_types: ['Excel Files (*.xlsx)']
                            });
                            
                            if (filePath) {
                                const success = await window.pywebview.api.save_file(filePath, base64Data);
                                if (success) {
                                    showExportFeedback(`Archivo guardado en: ${filePath}`);
                                } else {
                                    throw new Error('Error al guardar el archivo');
                                }
                            }
                        } else {
                            // Si no está en PyWebView, usar el método normal de descarga
                            window.downloadFile(blob, filename);
                            showExportFeedback('Archivo descargado exitosamente');
                        }
                    } catch (error) {
                        console.error('Error al usar PyWebView API:', error);
                        // Fallback al método normal de descarga
                        window.downloadFile(blob, filename);
                        showExportFeedback('Archivo descargado exitosamente');
                    }
                } catch (error) {
                    console.error('Error al exportar a Excel:', error);
                    showExportFeedback('Error al exportar el reporte', true);
                }
            };

            // Función auxiliar para convertir Blob a Base64
            window.blobToBase64 = function(blob) {
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64data = reader.result.split(',')[1];
                        resolve(base64data);
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            };

            // Función para descargar el archivo
            window.downloadFile = function(blob, filename) {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            };

            // Función para mostrar mensajes de feedback
            window.showExportFeedback = function(message, isError = false) {
                const feedback = document.createElement('div');
                feedback.className = `export-feedback ${isError ? 'error' : 'info'}`;
                feedback.textContent = message;
                document.body.appendChild(feedback);
                
                setTimeout(() => {
                    feedback.remove();
                }, 3000);
            }
        }

        if (isProveedoresPage) {
            const addProveedorBtn = document.getElementById('addProveedorBtn');
            const proveedorModalOverlay = document.getElementById('proveedorModalOverlay');
            const proveedorForm = document.getElementById('proveedorForm');
            const closeProveedorModalBtn = document.getElementById('closeProveedorModalBtn');
            const proveedoresGrid = document.getElementById('proveedores-grid');
            const searchProveedor = document.getElementById('searchProveedor');
            const loading = document.getElementById('loading');
        
            let proveedoresData = []; // Almacenar los datos de los proveedores para el filtro
        
            // Función para cargar proveedores
            async function loadProveedores() {
                const token = localStorage.getItem('token');
                if (!token) {
                    console.error('No se encontró token');
                    window.location.href = 'index.html';
                    return;
                }
        
                try {
                    loading.style.display = 'block';
                    const response = await fetch(`${BASE_URL}/api/proveedores`, {
                        method: 'GET',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });
        
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
        
                    proveedoresData = await response.json();
                    displayProveedores(proveedoresData);
                } catch (error) {
                    console.error('Error al cargar proveedores:', error);
                    proveedoresGrid.innerHTML = `<p>Error al cargar proveedores: ${sanitizeHTML(error.message)}</p>`;
                } finally {
                    loading.style.display = 'none';
                }
            }
        
            // Función para mostrar proveedores en tarjetas
            function displayProveedores(proveedores) {
                proveedoresGrid.innerHTML = '';
                if (proveedores.length === 0) {
                    proveedoresGrid.innerHTML = '<p>No hay proveedores registrados.</p>';
                    return;
                }
        
                proveedores.forEach(proveedor => {
                    const card = document.createElement('div');
                    card.className = 'proveedor-card';
                    card.innerHTML = `
                        <h3>${sanitizeHTML(proveedor.nombre)}</h3>
                        <p><i class="fas fa-user"></i> Contacto: ${sanitizeHTML(proveedor.contacto)}</p>
                        <p><i class="fas fa-phone"></i> Teléfono: ${sanitizeHTML(proveedor.telefono)}</p>
                        <p><i class="fas fa-envelope"></i> Email: ${sanitizeHTML(proveedor.email)}</p>
                        <div class="card-actions">
                            <button class="edit-btn" data-id="${proveedor.id_proveedor}">
                                <i class="fas fa-edit"></i> Editar
                            </button>
                            <button class="delete-btn" data-id="${proveedor.id_proveedor}">
                                <i class="fas fa-trash"></i> Eliminar
                            </button>
                        </div>
                    `;
                    proveedoresGrid.appendChild(card);
                });
        
                // Añadir eventos a los botones de edición y eliminación
                document.querySelectorAll('.edit-btn').forEach(btn => {
                    btn.addEventListener('click', () => editProveedor(btn.dataset.id));
                });
        
                document.querySelectorAll('.delete-btn').forEach(btn => {
                    btn.addEventListener('click', () => deleteProveedor(btn.dataset.id));
                });
            }
        
            // Filtro de búsqueda
            searchProveedor.addEventListener('input', () => {
                const searchTerm = searchProveedor.value.toLowerCase();
                const filteredProveedores = proveedoresData.filter(proveedor =>
                    proveedor.nombre.toLowerCase().includes(searchTerm) ||
                    proveedor.contacto.toLowerCase().includes(searchTerm) ||
                    proveedor.email.toLowerCase().includes(searchTerm)
                );
                displayProveedores(filteredProveedores);
            });
        
            // Abrir modal para agregar proveedor
            addProveedorBtn.addEventListener('click', () => {
                document.getElementById('proveedorModalTitle').textContent = 'Agregar Proveedor';
                proveedorForm.reset();
                proveedorModalOverlay.style.display = 'flex';
            });
        
            // Cerrar modal
            closeProveedorModalBtn.addEventListener('click', () => {
                proveedorModalOverlay.style.display = 'none';
            });
        
            // Guardar proveedor
            proveedorForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const token = localStorage.getItem('token');
                if (!token) {
                    console.error('No se encontró token');
                    window.location.href = 'index.html';
                    return;
                }
        
                const proveedorId = proveedorForm.dataset.id || null;
                const method = proveedorId ? 'PUT' : 'POST';
                const url = proveedorId
                    ? `${BASE_URL}/api/proveedores/${proveedorId}`
                    : `${BASE_URL}/api/proveedores`;
        
                const data = {
                    nombre: document.getElementById('proveedorNombre').value,
                    contacto: document.getElementById('proveedorContacto').value,
                    telefono: document.getElementById('proveedorTelefono').value,
                    email: document.getElementById('proveedorEmail').value
                };
        
                try {
                    loading.style.display = 'block';
                    const response = await fetch(url, {
                        method: method,
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
        
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
        
                    proveedorModalOverlay.style.display = 'none';
                    await loadProveedores();
                } catch (error) {
                    console.error('Error al guardar proveedor:', error);
                    alert(`Error al guardar proveedor: ${error.message}`);
                } finally {
                    loading.style.display = 'none';
                }
            });
        
            // Editar proveedor
            async function editProveedor(id) {
                const proveedor = proveedoresData.find(p => p.id_proveedor == id);
                if (!proveedor) return;
        
                document.getElementById('proveedorModalTitle').textContent = 'Editar Proveedor';
                document.getElementById('proveedorNombre').value = proveedor.nombre;
                document.getElementById('proveedorContacto').value = proveedor.contacto;
                document.getElementById('proveedorTelefono').value = proveedor.telefono;
                document.getElementById('proveedorEmail').value = proveedor.email;
                proveedorForm.dataset.id = id;
                proveedorModalOverlay.style.display = 'flex';
            }
        
            // Eliminar proveedor
            async function deleteProveedor(id) {
                if (!confirm('¿Estás seguro de que deseas eliminar este proveedor?')) return;
        
                const token = localStorage.getItem('token');
                if (!token) {
                    console.error('No se encontró token');
                    window.location.href = 'index.html';
                    return;
                }
        
                try {
                    loading.style.display = 'block';
                    const response = await fetch(`${BASE_URL}/api/proveedores/${id}`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });
        
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                    }
        
                    await loadProveedores();
                } catch (error) {
                    console.error('Error al eliminar proveedor:', error);
                    alert(`Error al eliminar proveedor: ${error.message}`);
                } finally {
                    loading.style.display = 'none';
                }
            }
        
            // Cargar proveedores al iniciar
            loadProveedores();
        }

        setupNavLinks();
    }
});

// Manejador de búsqueda global
const searchInput = document.getElementById('searchInput');
const clearSearchBtn = document.getElementById('clearSearchBtn');

if (searchInput && clearSearchBtn) {
    searchInput.oninput = debounce(() => {
        searchTerm = searchInput.value.trim();
        clearSearchBtn.style.display = searchTerm ? 'block' : 'none';

        const isDashboardPage = document.getElementById('inventory-table') !== null;
        const isPrototypePage = document.getElementById('prototypes-table') !== null;

        if (isDashboardPage) {
            fetchAndUpdateTable();
        } else if (isPrototypePage) {
            fetchAndUpdatePrototypes();
        }
    }, 300);

    clearSearchBtn.onclick = () => {
        searchInput.value = '';
        searchTerm = '';
        clearSearchBtn.style.display = 'none';

        const isDashboardPage = document.getElementById('inventory-table') !== null;
        const isPrototypePage = document.getElementById('prototypes-table') !== null;

        if (isDashboardPage) {
            fetchAndUpdateTable();
        } else if (isPrototypePage) {
            fetchAndUpdatePrototypes();
        }
    };
}


// Función para debounce (evitar múltiples ejecuciones rápidas)
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
