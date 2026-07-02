const API = window.location.origin;

let state = {
    worldId: null,
    worldName: null,
    worldProtagonist: null,
    worldEra: null,
    commitId: null,
    parentId: null,
    adapterType: 'ollama',
    history: [],
};

// ── Screens ────────────────────────────────────

function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
}

function backToSetup() {
    state.history = [];
    loadExistingWorlds();
    showScreen('setup-screen');
}

// ── Load Existing Worlds ──────────────────────

async function loadExistingWorlds() {
    const container = document.getElementById('worlds-list');
    try {
        const res = await fetch(`${API}/worlds`);
        if (!res.ok) return;

        const worlds = await res.json();
        if (worlds.length === 0) {
            container.innerHTML = '<p class="no-worlds">No hay mundos creados aun.</p>';
            return;
        }

        container.innerHTML = worlds.map(w => `
            <div class="world-card">
                <div class="world-card-info">
                    <h4>${escapeHtml(w.name)}</h4>
                    <p>${escapeHtml(w.protagonist)} — ${escapeHtml(w.era)}</p>
                </div>
                <div class="world-card-stats">
                    <div class="commits">${w.total_commits} capitulos</div>
                    <div>${escapeHtml(w.tone)}</div>
                    <div class="world-card-actions">
                        <button class="btn-continue" onclick="resumeWorld('${w.world_id}', '${escapeAttr(w.name)}', '${escapeAttr(w.protagonist)}', '${escapeAttr(w.era)}')">Continuar</button>
                        <button class="btn-delete" onclick="deleteWorld(event, '${w.world_id}', '${escapeAttr(w.name)}')">Eliminar</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Error loading worlds:', err);
        container.innerHTML = '<p class="no-worlds">Error cargando mundos.</p>';
    }
}

async function deleteWorld(event, worldId, name) {
    event.stopPropagation();
    if (!confirm(`Eliminar "${name}" y toda su historia? Esta accion no se puede deshacer.`)) {
        return;
    }

    try {
        const res = await fetch(`${API}/worlds/${worldId}`, { method: 'DELETE' });
        if (res.ok || res.status === 204) {
            loadExistingWorlds();
        } else {
            const err = await res.json();
            alert('Error eliminando: ' + (err.detail || 'Error desconocido'));
        }
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

// ── Resume World → Show Chapters ──────────────

async function resumeWorld(worldId, name, protagonist, era) {
    state.worldId = worldId;
    state.worldName = name;
    state.worldProtagonist = protagonist;
    state.worldEra = era;
    state.adapterType = document.getElementById('adapter-type').value;

    document.getElementById('chapters-title').textContent = name;
    document.getElementById('chapters-subtitle').textContent = 'Selecciona un capitulo para continuar.';
    showScreen('chapters-screen');

    await loadChapters(worldId);
}

async function loadChapters(worldId) {
    const container = document.getElementById('chapters-list');
    container.innerHTML = '<p class="no-worlds">Cargando capitulos...</p>';

    try {
        const res = await fetch(`${API}/worlds/${worldId}/commits`);
        if (!res.ok) throw new Error('Error cargando capitulos');

        const commits = await res.json();
        if (commits.length === 0) {
            container.innerHTML = `
                <p class="no-worlds">Este mundo no tiene capitulos aun.</p>
                <button class="btn btn-primary" style="max-width:300px;margin:16px auto;display:block" onclick="startFromWorld()">Iniciar Historia</button>
            `;
            return;
        }

        container.innerHTML = commits.map(c => `
            <div class="chapter-card" onclick="selectChapter('${c.commit_id}')">
                <span class="depth-badge">Cap ${c.depth}</span>
                <div class="chapter-card-info">
                    <div class="summary">${escapeHtml(c.summary)}</div>
                    ${c.choice_text ? `<div class="choice-label">${escapeHtml(c.choice_text)}</div>` : ''}
                </div>
                ${c.is_ending ? '<span class="forced-event-badge">FIN</span>' : ''}
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = '<p class="no-worlds">Error cargando capitulos.</p>';
    }
}

async function startFromWorld() {
    updateWorldInfo({ name: state.worldName, protagonist: state.worldProtagonist, era: state.worldEra });
    showScreen('game-screen');
    showLoading('Generando el inicio de la historia...');

    try {
        const res = await fetch(`${API}/worlds/${state.worldId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ adapter_type: state.adapterType }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error iniciando narrativa');
        }
        const commit = await res.json();
        state.commitId = commit.commit_id;
        state.parentId = commit.parent_id;
        hideLoading();
        renderCommit(commit);
    } catch (err) {
        hideLoading();
        alert('Error: ' + err.message);
        showScreen('chapters-screen');
    }
}

async function selectChapter(commitId) {
    updateWorldInfo({ name: state.worldName, protagonist: state.worldProtagonist, era: state.worldEra });
    showScreen('game-screen');
    showLoading('Cargando capitulo...');

    try {
        const res = await fetch(`${API}/commits/${commitId}/goto`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error cargando capitulo');
        }
        const commit = await res.json();
        state.commitId = commit.commit_id;
        state.parentId = commit.parent_id;
        state.history = [];
        hideLoading();
        renderCommit(commit);
    } catch (err) {
        hideLoading();
        alert('Error: ' + err.message);
        showScreen('chapters-screen');
    }
}

loadExistingWorlds();

// ── Setup ──────────────────────────────────────

document.getElementById('setup-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Creando mundo...';

    state.adapterType = document.getElementById('adapter-type').value;

    try {
        const worldData = {
            name: document.getElementById('world-name').value,
            context: document.getElementById('world-context').value,
            protagonist: document.getElementById('world-protagonist').value,
            era: document.getElementById('world-era').value,
            tone: document.getElementById('world-tone').value,
            initial_entities: getEntities(),
        };

        const worldRes = await fetch(`${API}/worlds`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(worldData),
        });

        if (!worldRes.ok) {
            const err = await worldRes.json();
            throw new Error(err.detail || 'Error creando mundo');
        }

        const world = await worldRes.json();
        state.worldId = world.world_id;
        state.worldName = worldData.name;
        state.worldProtagonist = worldData.protagonist;
        state.worldEra = worldData.era;

        updateWorldInfo(worldData);
        showScreen('game-screen');
        showLoading('Generando el inicio de la historia...');

        const startRes = await fetch(`${API}/worlds/${state.worldId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ adapter_type: state.adapterType }),
        });

        if (!startRes.ok) {
            const err = await startRes.json();
            throw new Error(err.detail || 'Error iniciando narrativa');
        }

        const commit = await startRes.json();
        state.commitId = commit.commit_id;
        state.parentId = commit.parent_id;
        hideLoading();
        renderCommit(commit);

    } catch (err) {
        hideLoading();
        alert('Error: ' + err.message);
        btn.disabled = false;
        btn.textContent = 'Crear Mundo e Iniciar Historia';
    }
});

// ── Advance ────────────────────────────────────

async function makeChoice(choiceText, custom = false) {
    document.querySelectorAll('.choice-btn').forEach(b => b.disabled = true);
    const customInput = document.getElementById('custom-choice-input');
    if (customInput) customInput.disabled = true;

    showLoading('Generando siguiente capitulo...');

    try {
        const res = await fetch(`${API}/commits/${state.commitId}/advance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                choice: choiceText,
                custom: custom,
                adapter_type: state.adapterType,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error avanzando narrativa');
        }

        const commit = await res.json();
        state.commitId = commit.commit_id;
        state.parentId = commit.parent_id;
        hideLoading();
        renderCommit(commit);

    } catch (err) {
        hideLoading();
        alert('Error: ' + err.message);
        document.querySelectorAll('.choice-btn').forEach(b => b.disabled = false);
        if (customInput) customInput.disabled = false;
    }
}

function submitCustomChoice() {
    const input = document.getElementById('custom-choice-input');
    const text = input.value.trim();
    if (!text) return;
    makeChoice(text, true);
}

// ── Navigation ────────────────────────────────

async function goBack() {
    if (!state.parentId) return;

    showLoading('Regresando...');

    try {
        const res = await fetch(`${API}/commits/${state.parentId}/goto`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error regresando');
        }

        const commit = await res.json();
        state.commitId = commit.commit_id;
        state.parentId = commit.parent_id;
        if (state.history.length > 0) state.history.pop();
        hideLoading();
        renderCommit(commit);
    } catch (err) {
        hideLoading();
        alert('Error: ' + err.message);
    }
}

// ── Render ─────────────────────────────────────

function renderCommit(commit) {
    const main = document.getElementById('main-content');

    state.history.push({
        depth: commit.depth,
        summary: commit.summary,
    });

    // Update toolbar
    const btnBack = document.getElementById('btn-back');
    const indicator = document.getElementById('chapter-indicator');
    btnBack.style.display = commit.parent_id ? 'inline-block' : 'none';
    indicator.textContent = `Capitulo ${commit.depth}`;

    let html = '';

    // Chapter header
    html += '<div class="chapter-header">';
    html += `<span class="depth-badge">Capitulo ${commit.depth}</span>`;
    if (commit.forced_event_type) {
        html += `<span class="forced-event-badge">${commit.forced_event_type}</span>`;
    }
    html += '</div>';

    // Narrative
    html += `<div class="narrative-text">${escapeHtml(commit.narrative_text)}</div>`;

    // Summary
    html += `<div class="summary">${escapeHtml(commit.summary)}</div>`;

    // Causal reason
    if (commit.causal_reason) {
        html += `<div class="causal-reason"><strong>Causa:</strong> ${escapeHtml(commit.causal_reason)}</div>`;
    }

    // Ending
    if (commit.is_ending) {
        html += `
            <div class="ending-banner">
                <h2>Fin de la Historia</h2>
                <p>La narrativa ha llegado a su conclusion.</p>
                <button class="btn btn-restart" onclick="backToSetup()">Nueva Historia</button>
            </div>`;
    } else {
        // Choices
        html += '<div class="choices-section"><h3>Elige tu camino</h3>';
        for (const choice of commit.choices) {
            html += `<button class="choice-btn" onclick="makeChoice('${escapeAttr(choice.text)}')">`;
            html += escapeHtml(choice.text);
            if (choice.dramatic_preview) {
                html += '<div class="choice-preview">';
                for (const [key, val] of Object.entries(choice.dramatic_preview)) {
                    if (val !== 0) {
                        const cls = val > 0 ? 'delta-pos' : 'delta-neg';
                        const sign = val > 0 ? '+' : '';
                        html += `<span class="${cls}">${key} ${sign}${val}</span>`;
                    }
                }
                html += '</div>';
            }
            html += '</button>';
        }

        // Custom choice input
        html += `
            <div class="custom-choice">
                <input type="text" id="custom-choice-input" placeholder="Escribe tu propia opcion..."
                    onkeydown="if(event.key==='Enter')submitCustomChoice()">
                <button onclick="submitCustomChoice()">Enviar</button>
            </div>`;

        html += '</div>';

        // Existing paths (already explored branches)
        if (commit.existing_paths && commit.existing_paths.length > 0) {
            html += '<div class="existing-paths-section"><h3>Caminos ya explorados</h3>';
            for (const path of commit.existing_paths) {
                html += `<button class="choice-btn explored" onclick="selectChapter('${path.commit_id}')">`;
                html += `<span class="explored-label">Cap ${path.depth}</span> `;
                html += escapeHtml(path.choice_text);
                html += `<div class="choice-preview"><span class="explored-summary">${escapeHtml(path.summary)}</span></div>`;
                html += '</button>';
            }
            html += '</div>';
        }
    }

    // History
    if (state.history.length > 1) {
        html += '<div class="history-section"><h3>Historia anterior</h3>';
        for (let i = state.history.length - 2; i >= 0; i--) {
            const entry = state.history[i];
            html += `<div class="history-entry"><span class="depth">Cap. ${entry.depth}</span> — ${escapeHtml(entry.summary)}</div>`;
        }
        html += '</div>';
    }

    main.innerHTML = html;
    main.scrollTop = 0;

    // Dramatic meters
    if (commit.dramatic_state) {
        updateMeters(commit.dramatic_state);
    }
}

function updateMeters(dramatic) {
    const meters = ['tension', 'hope', 'chaos', 'rhythm', 'saturation', 'connection', 'mystery'];
    const labels = {
        tension: 'Tension',
        hope: 'Esperanza',
        chaos: 'Caos',
        rhythm: 'Ritmo',
        saturation: 'Saturacion',
        connection: 'Conexion',
        mystery: 'Misterio',
    };

    const container = document.getElementById('meters');
    let html = '';

    for (const m of meters) {
        const val = dramatic[m] || 0;
        html += `
            <div class="meter">
                <div class="meter-label">
                    <span class="meter-name">${labels[m]}</span>
                    <span class="meter-value">${val}/100</span>
                </div>
                <div class="meter-bar">
                    <div class="meter-fill ${m}" style="width: ${val}%"></div>
                </div>
            </div>`;
    }

    container.innerHTML = html;
}

function updateWorldInfo(world) {
    const el = document.getElementById('world-details');
    el.innerHTML = `
        <p><strong>${escapeHtml(world.name)}</strong></p>
        <p>${escapeHtml(world.protagonist)}</p>
        <p>${escapeHtml(world.era)}</p>
    `;
}

// ── Loading ────────────────────────────────────

function showLoading(msg) {
    const el = document.getElementById('loading');
    el.querySelector('.loading-text').textContent = msg || 'Generando...';
    el.classList.add('active');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('active');
}

// ── Entity Management ─────────────────────────

function addEntityField() {
    const list = document.getElementById('entities-list');
    const idx = list.children.length;
    const div = document.createElement('div');
    div.className = 'entity-row';
    div.innerHTML = `
        <input type="text" class="entity-name" placeholder="Nombre (ej: Lyra)" required>
        <select class="entity-type">
            <option value="character">Personaje</option>
            <option value="location">Lugar</option>
            <option value="artifact">Artefacto</option>
            <option value="faction">Faccion</option>
        </select>
        <button type="button" class="btn-remove-entity" onclick="this.parentElement.remove()">x</button>
    `;
    list.appendChild(div);
}

function getEntities() {
    const rows = document.querySelectorAll('.entity-row');
    const entities = [];
    rows.forEach(row => {
        const name = row.querySelector('.entity-name').value.trim();
        const type = row.querySelector('.entity-type').value;
        if (name) {
            entities.push({ name, entity_type: type, attributes: {} });
        }
    });
    return entities;
}

// ── Utils ──────────────────────────────────────

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeAttr(str) {
    if (!str) return '';
    return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
