// Array para armazenar pets
let pets = [];
// Array para armazenar eventos
let events = [];

// NAVEGAÇÃO

function showPage(id) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + id).classList.add('active');

    document.querySelectorAll('.top-nav .nav-btn').forEach((n, i) => {
        n.classList.toggle('active', n.textContent.toLowerCase().startsWith(id));
    });

    if (id === 'agenda') renderEvents();
    if (id === 'pets') renderPetsGrid();
    if (id === 'novo') updatePetSelect();
}

//TOAST

function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2600);
}

//UTILITÁRIOS
function calcAge(nasc) {
    if (!nasc) return '';
    const b = new Date(nasc);
    const n = new Date();
    const y = n.getFullYear() - b.getFullYear();
    const m = n.getMonth() - b.getMonth();
    const totalM = y * 12 + m;
    if (totalM < 12) return totalM + ' meses';
    return y + (y === 1 ? ' ano' : ' anos');
}

function fmtDate(d) {
    if (!d) return '';
    const [y, m, day] = d.split('-');
    return `${day}/${m}/${y}`;
}

// PETS 
function addPet() {
    const nome = document.getElementById('pet-nome').value.trim();
    if (!nome) {
        alert('Informe o nome do pet.');
        return;
    }

    const especie = document.getElementById('pet-especie').value;
    const raca = document.getElementById('pet-raca').value.trim();
    const nasc = document.getElementById('pet-nasc').value;

    pets.push({ id: Date.now(), nome, especie, raca, nasc });

    document.getElementById('pet-nome').value = '';
    document.getElementById('pet-raca').value = '';
    document.getElementById('pet-nasc').value = '';

    renderPetsGrid();
    updatePetSelect();
    toast('✅ ' + nome + ' adicionado(a)!');
}

function deletePet(id) {
    if (!confirm('Remover este pet e todos seus eventos?')) return;
    pets = pets.filter(p => p.id !== id);
    events = events.filter(e => e.petId !== id);
    renderPetsGrid();
    renderEvents();
    updatePetSelect();
}

function renderPetsGrid() {
    const el = document.getElementById('pets-grid');
    if (!pets.length) {
        el.innerHTML = '<div class="empty-state"><span class="empty-icon">🐾</span><p>Nenhum pet cadastrado.</p></div>';
        return;
    }

    el.innerHTML = pets.map(p => `
        <div class="pet-card">
            <button class="del-btn pet-card-del" onclick="deletePet(${p.id})">✕</button>
            <div class="pet-avatar">${p.especie}</div>
            <div class="pet-card-name">${p.nome}</div>
            <div class="pet-card-info">${p.raca || 'Raça não informada'}</div>
            ${p.nasc ? `<div class="pet-card-age">${calcAge(p.nasc)}</div>` : ''}
        </div>
    `).join('');
}

function updatePetSelect() {
    const sel = document.getElementById('ev-pet');
    sel.innerHTML = '<option value="">Selecione o pet</option>' + pets.map(p => `<option value="${p.id}">${p.especie} ${p.nome}</option>`).join('');
}

// EVENTOS 
function addEvent() {
    const petId = parseInt(document.getElementById('ev-pet').value);
    const tipo = document.getElementById('ev-tipo').value;
    const desc = document.getElementById('ev-desc').value.trim();
    const data = document.getElementById('ev-data').value;
    const hora = document.getElementById('ev-hora').value;
    const local = document.getElementById('ev-local').value.trim();
    const obs = document.getElementById('ev-obs').value.trim();

    if (!petId) { alert('Selecione um pet.'); return; }
    if (!desc) { alert('Informe uma descrição.'); return; }
    if (!data) { alert('Informe a data.'); return; }

    events.push({ id: Date.now(), petId, tipo, desc, data, hora, local, obs });

    document.getElementById('ev-desc').value = '';
    document.getElementById('ev-data').value = '';
    document.getElementById('ev-hora').value = '';
    document.getElementById('ev-local').value = '';
    document.getElementById('ev-obs').value = '';

    toast('✅ Evento salvo com sucesso!');
    showPage('agenda');
}

function deleteEvent(id) {
    events = events.filter(e => e.id !== id);
    renderEvents();
}

const typeIcon = { consulta: '🏥', vacina: '💉', banho: '🛁', outro: '📌' };

function renderEvents() {
    const today = new Date().toISOString().slice(0, 10);
    const sorted = [...events].sort((a, b) => a.data.localeCompare(b.data));
    const upcoming = sorted.filter(e => e.data >= today);
    const past = sorted.filter(e => e.data < today).reverse();

    const renderList = (list, emptyMsg) => {
        if (!list.length) return `<div class="empty-state"><span class="empty-icon">🐾</span><p>${emptyMsg}</p></div>`;
        return list.map(e => {
            const pet = pets.find(p => p.id === e.petId);
            return `
            <div class="event-card">
                <div class="event-card-header">
                    <div class="event-card-title">${typeIcon[e.tipo] || '📌'} ${e.desc}</div>
                    <button class="del-btn" onclick="deleteEvent(${e.id})">✕</button>
                </div>
                <div><strong>Pet:</strong> ${pet ? pet.nome : 'N/A'}</div>
                <div><strong>Data:</strong> ${fmtDate(e.data)} ${e.hora || ''}</div>
                ${e.local ? `<div><strong>Local:</strong> ${e.local}</div>` : ''}
                ${e.obs ? `<div><strong>Obs:</strong> ${e.obs}</div>` : ''}
            </div>`;
        }).join('');
    };

    document.getElementById('upcoming-events').innerHTML = renderList(upcoming, 'Nenhum evento próximo.');
    document.getElementById('past-events').innerHTML = renderList(past, 'Nenhum evento anterior.');
}

// INIT

showPage('agenda');
//FUNCIONÁRIOS

async function loadFuncionarios() {
    const res = await fetch(API + "/funcionarios");
    const dados = await res.json();

    const div = document.getElementById("lista-funcionarios");
    div.innerHTML = "";

    dados.forEach(f => {
        div.innerHTML += `
            <div>
                <b>${f.nome}</b> - ${f.cargo} - R$${f.salario}
                <button onclick="deleteFuncionario(${f.id})">❌</button>
            </div>
        `;
    });
}

async function addFuncionario() {
    const fd = new FormData();

    fd.append("nome", document.getElementById("f-nome").value);
    fd.append("cargo", document.getElementById("f-cargo").value);
    fd.append("salario", document.getElementById("f-salario").value);
    fd.append("telefone", document.getElementById("f-telefone").value);

    await fetch(API + "/funcionarios", {
        method: "POST",
        body: fd
    });

    alert("Funcionário cadastrado!");
    loadFuncionarios();
}

async function deleteFuncionario(id) {
    await fetch(API + "/funcionarios/" + id, {
        method: "DELETE"
    });

    loadFuncionarios();
}