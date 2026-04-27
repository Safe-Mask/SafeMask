const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
const btnOpenCreateTeam = document.getElementById('btnOpenCreateTeam');
const btnOpenCreateTeamInline = document.getElementById('btnOpenCreateTeamInline');
const btnBackDashboard = document.getElementById('btnBackDashboard');
const menuLinks = document.querySelectorAll('.menu-link');
const API_BASE = 'http://127.0.0.1:8000/equipes';

const metricTotalEquipes = document.getElementById('metricTotalEquipes');
const metricTotalMembros = document.getElementById('metricTotalMembros');
const metricTotalDocumentos = document.getElementById('metricTotalDocumentos');
const metricEquipeMaiorNome = document.getElementById('metricEquipeMaiorNome');
const metricEquipeMaior = document.getElementById('metricEquipeMaior');

const heroTeamName = document.getElementById('heroTeamName');
const heroTeamMembers = document.getElementById('heroTeamMembers');
const heroSuggestedCount = document.getElementById('heroSuggestedCount');
const teamList = document.getElementById('teamList');
const teamChart = document.getElementById('teamChart');

const createTeamModal = document.getElementById('createTeamModal');
const closeCreateTeamModal = document.getElementById('closeCreateTeamModal');
const cancelCreateTeam = document.getElementById('cancelCreateTeam');
const createTeamForm = document.getElementById('createTeamForm');
const teamNameInput = document.getElementById('teamNameInput');
const teamDescriptionInput = document.getElementById('teamDescriptionInput');
const userSearchInput = document.getElementById('userSearchInput');
const suggestedMembersList = document.getElementById('suggestedMembersList');
const availableUsersList = document.getElementById('availableUsersList');
const selectedMembersList = document.getElementById('selectedMembersList');
const selectedMemberCount = document.getElementById('selectedMemberCount');

const storedName = localStorage.getItem('userName') || 'Usuario';
userNameElement.textContent = storedName;
userIcon.textContent = storedName.charAt(0).toUpperCase();

const state = {
    overview: null,
    suggestedMembers: [],
    availableUsers: [],
    selectedMembers: new Map(),
    searchTimer: null,
};

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function openModal() {
    createTeamModal.classList.add('open');
    createTeamModal.setAttribute('aria-hidden', 'false');
    loadFormData();
}

function closeModal() {
    createTeamModal.classList.remove('open');
    createTeamModal.setAttribute('aria-hidden', 'true');
    createTeamForm.reset();
    state.selectedMembers.clear();
    renderSelectedMembers();
}

function renderOverview(overview) {
    metricTotalEquipes.textContent = overview?.metrics?.total_equipes ?? 0;
    metricTotalMembros.textContent = overview?.metrics?.total_membros ?? 0;
    metricTotalDocumentos.textContent = overview?.metrics?.total_documentos ?? 0;

    const topTeamName = overview?.metrics?.equipe_maior_nome || 'Nenhuma equipe';
    const topTeamMembers = overview?.metrics?.equipe_maior_membros ?? 0;
    metricEquipeMaiorNome.textContent = topTeamName;
    metricEquipeMaior.textContent = `${topTeamMembers} membro(s)`;

    heroTeamName.textContent = topTeamName;
    heroTeamMembers.textContent = topTeamMembers;
    heroSuggestedCount.textContent = state.suggestedMembers.length;
}

function renderTeams(teams) {
    if (!teams.length) {
        teamList.innerHTML = `
            <li class="empty-state">
                <strong>Nenhuma equipe encontrada</strong>
                <span>adicione a primeira equipe para visualizar os detalhes</span>
            </li>
        `;
        teamChart.innerHTML = '<p class="empty-message">Sem dados para exibir.</p>';
        return;
    }

    teamList.innerHTML = teams
        .map((team) => {
            const description = team.descricao ? escapeHtml(team.descricao) : 'Sem descricao cadastrada';
            return `
                <li class="team-card">
                    <a class="team-card-link" href="detalhe.html?team_id=${team.team_id}">
                        <div class="team-card-top">
                            <div>
                                <strong>${escapeHtml(team.nome)}</strong>
                                <p>${description}</p>
                            </div>
                            <span class="pill ok">Abrir</span>
                        </div>
                        <div class="team-card-meta">
                            <span class="pill wait">${team.membros} membro(s)</span>
                            <span class="pill wait">${team.documentos} documento(s)</span>
                        </div>
                    </a>
                </li>
            `;
        })
        .join('');

    const maxMembers = Math.max(...teams.map((team) => team.membros), 1);
    teamChart.innerHTML = teams
        .slice(0, 8)
        .map((team) => {
            const width = Math.max(8, Math.round((team.membros / maxMembers) * 100));
            return `
                <div class="bar-item">
                    <span class="label">${escapeHtml(team.nome)}</span>
                    <div class="bar-track"><div class="bar" style="width: ${width}%;"></div></div>
                    <span class="value">${team.membros}</span>
                </div>
            `;
        })
        .join('');
}

function renderCandidates(list, container, emptyTitle, emptyText) {
    if (!list.length) {
        container.innerHTML = `
            <li class="empty-state small">
                <strong>${emptyTitle}</strong>
                <span>${emptyText}</span>
            </li>
        `;
        return;
    }

    container.innerHTML = list
        .map((member) => {
            const isSelected = state.selectedMembers.has(member.user_id);
            return `
                <li class="candidate-item ${isSelected ? 'selected' : ''}">
                    <div>
                        <strong>${escapeHtml(member.nome)}</strong>
                        <p>${escapeHtml(member.email)}</p>
                        ${member.equipes_compartilhadas ? `<span class="muted">${member.equipes_compartilhadas} equipe(s) em comum</span>` : ''}
                    </div>
                    <button type="button" class="candidate-action" data-member-id="${member.user_id}">
                        ${isSelected ? 'Incluido' : 'Adicionar'}
                    </button>
                </li>
            `;
        })
        .join('');
}

function renderSelectedMembers() {
    const selectedMembers = Array.from(state.selectedMembers.values());
    selectedMemberCount.textContent = `${selectedMembers.length} selecionado(s)`;
    heroSuggestedCount.textContent = state.suggestedMembers.length;

    if (!selectedMembers.length) {
        selectedMembersList.innerHTML = '<span class="empty-chip">Nenhum membro selecionado</span>';
        return;
    }

    selectedMembersList.innerHTML = selectedMembers
        .map((member) => `
            <button type="button" class="selected-chip" data-remove-member="${member.user_id}">
                ${escapeHtml(member.nome)}
                <span aria-hidden="true">×</span>
            </button>
        `)
        .join('');
}

function addMember(member) {
    if (!state.selectedMembers.has(member.user_id)) {
        state.selectedMembers.set(member.user_id, member);
        renderSelectedMembers();
        renderCandidates(state.suggestedMembers, suggestedMembersList, 'Nenhum membro sugerido', 'as pessoas aparecerão aqui automaticamente');
        renderCandidates(state.availableUsers, availableUsersList, 'Sem resultados', 'digite para encontrar usuarios cadastrados');
    }
}

function removeMember(memberId) {
    state.selectedMembers.delete(memberId);
    renderSelectedMembers();
    renderCandidates(state.suggestedMembers, suggestedMembersList, 'Nenhum membro sugerido', 'as pessoas aparecerão aqui automaticamente');
    renderCandidates(state.availableUsers, availableUsersList, 'Sem resultados', 'digite para encontrar usuarios cadastrados');
}

async function loadOverview() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/overview`, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '../auth/login.html';
            return;
        }

        if (!response.ok) {
            throw new Error('Falha ao carregar equipes.');
        }

        const data = await response.json();
        const backendUser = data?.usuario;
        if (backendUser?.nome) {
            localStorage.setItem('userName', backendUser.nome);
            localStorage.setItem('userId', String(backendUser.user_id));
            userNameElement.textContent = backendUser.nome;
            userIcon.textContent = backendUser.nome.charAt(0).toUpperCase();
        }

        state.overview = data;
        renderOverview(data);
        renderTeams(data.equipes || []);
    } catch (error) {
        console.error(error);
        teamList.innerHTML = `
            <li class="empty-state">
                <strong>Erro ao carregar dados</strong>
                <span>verifique se o backend esta ativo em http://127.0.0.1:8000</span>
            </li>
        `;
    }
}

async function loadFormData(query = '') {
    const token = localStorage.getItem('token');
    if (!token) {
        return;
    }

    const endpoint = new URL(`${API_BASE}/form-data`);
    if (query) {
        endpoint.searchParams.set('query', query);
    }

    try {
        const response = await fetch(endpoint.toString(), {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            throw new Error('Falha ao carregar candidatos.');
        }

        const data = await response.json();
        state.suggestedMembers = data.membros_sugeridos || [];
        state.availableUsers = data.usuarios_disponiveis || [];

        renderCandidates(state.suggestedMembers, suggestedMembersList, 'Nenhum membro sugerido', 'as pessoas aparecerão aqui automaticamente');
        renderCandidates(state.availableUsers, availableUsersList, 'Sem resultados', 'digite para encontrar usuarios cadastrados');
        heroSuggestedCount.textContent = state.suggestedMembers.length;
    } catch (error) {
        console.error(error);
        suggestedMembersList.innerHTML = `
            <li class="empty-state small">
                <strong>Falha ao carregar</strong>
                <span>tente abrir o modal novamente</span>
            </li>
        `;
        availableUsersList.innerHTML = `
            <li class="empty-state small">
                <strong>Falha ao carregar</strong>
                <span>tente pesquisar novamente mais tarde</span>
            </li>
        `;
    }
}

async function handleCreateTeam(event) {
    event.preventDefault();

    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    const payload = {
        nome: teamNameInput.value.trim(),
        descricao: teamDescriptionInput.value.trim(),
        membros_ids: Array.from(state.selectedMembers.keys()),
    };

    try {
        const response = await fetch(API_BASE, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Falha ao criar equipe.');
        }

        const data = await response.json();
        const teamId = data?.equipe?.team_id;
        closeModal();
        await loadOverview();

        if (teamId) {
            window.location.href = `detalhe.html?team_id=${teamId}`;
        }
    } catch (error) {
        console.error(error);
        alert(error.message || 'Falha ao criar equipe.');
    }
}

userTrigger.addEventListener('click', () => {
    const isOpen = userDropdown.classList.toggle('open');
    userTrigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
});

document.addEventListener('click', (event) => {
    if (!userMenu.contains(event.target)) {
        userDropdown.classList.remove('open');
        userTrigger.setAttribute('aria-expanded', 'false');
    }
});

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userName');
    localStorage.removeItem('userId');
    window.location.href = '../../../index.html';
});

menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});

if (btnBackDashboard) {
    btnBackDashboard.addEventListener('click', () => {
        window.location.href = '../dashboard.html';
    });
}

btnOpenCreateTeam.addEventListener('click', openModal);
if (btnOpenCreateTeamInline) {
    btnOpenCreateTeamInline.addEventListener('click', openModal);
}
closeCreateTeamModal.addEventListener('click', closeModal);
cancelCreateTeam.addEventListener('click', closeModal);

createTeamModal.addEventListener('click', (event) => {
    if (event.target === createTeamModal) {
        closeModal();
    }
});

createTeamForm.addEventListener('submit', handleCreateTeam);

userSearchInput.addEventListener('input', () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => {
        loadFormData(userSearchInput.value.trim());
    }, 250);
});

suggestedMembersList.addEventListener('click', (event) => {
    const button = event.target.closest('[data-member-id]');
    if (!button) {
        return;
    }

    const memberId = Number(button.getAttribute('data-member-id'));
    const member = state.suggestedMembers.find((item) => item.user_id === memberId);
    if (member) {
        addMember(member);
    }
});

availableUsersList.addEventListener('click', (event) => {
    const button = event.target.closest('[data-member-id]');
    if (!button) {
        return;
    }

    const memberId = Number(button.getAttribute('data-member-id'));
    const member = state.availableUsers.find((item) => item.user_id === memberId);
    if (member) {
        addMember(member);
    }
});

selectedMembersList.addEventListener('click', (event) => {
    const button = event.target.closest('[data-remove-member]');
    if (!button) {
        return;
    }

    removeMember(Number(button.getAttribute('data-remove-member')));
});

menuLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
        const href = link.getAttribute('href') || '';
        if (!href || href === '#') {
            event.preventDefault();
        }

        if (window.innerWidth <= 860) {
            sidebar.classList.remove('open');
        }
    });
});

loadOverview();