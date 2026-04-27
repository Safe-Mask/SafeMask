const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
const btnAddDocument = document.getElementById('btnAddDocument');
const btnOpenDocumentModal = document.getElementById('btnOpenDocumentModal');
const documentModal = document.getElementById('documentModal');
const closeDocumentModal = document.getElementById('closeDocumentModal');
const cancelDocumentModal = document.getElementById('cancelDocumentModal');
const confirmDocumentModal = document.getElementById('confirmDocumentModal');

const teamNameHeader = document.getElementById('teamNameHeader');
const teamSubtitle = document.getElementById('teamSubtitle');
const detailTeamName = document.getElementById('detailTeamName');
const detailTeamDescription = document.getElementById('detailTeamDescription');
const detailCreatedAt = document.getElementById('detailCreatedAt');
const detailTotalMembers = document.getElementById('detailTotalMembers');
const detailTotalDocs = document.getElementById('detailTotalDocs');
const detailMemberList = document.getElementById('detailMemberList');

const API_BASE = 'http://127.0.0.1:8000/equipes';
const storedName = localStorage.getItem('userName') || 'Usuario';
userNameElement.textContent = storedName;
userIcon.textContent = storedName.charAt(0).toUpperCase();

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function roleLabel(role) {
    if (!role) {
        return { label: 'Sem cargo', css: 'wait' };
    }

    if (role.toLowerCase() === 'lider') {
        return { label: 'Lider', css: 'ok' };
    }

    return { label: role, css: 'wait' };
}

function formatDate(value) {
    if (!value) {
        return '-';
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return '-';
    }

    return date.toLocaleString('pt-BR');
}

function getTeamId() {
    const params = new URLSearchParams(window.location.search);
    const teamId = Number(params.get('team_id'));
    return Number.isFinite(teamId) ? teamId : null;
}

function openDocumentModal() {
    documentModal.classList.add('open');
    documentModal.setAttribute('aria-hidden', 'false');
}

function closeDocumentFlow() {
    documentModal.classList.remove('open');
    documentModal.setAttribute('aria-hidden', 'true');
}

function renderTeam(team) {
    if (!team) {
        teamNameHeader.textContent = 'Equipe nao encontrada';
        teamSubtitle.textContent = 'Nao foi possivel carregar a equipe solicitada';
        detailTeamName.textContent = 'Equipe nao encontrada';
        detailTeamDescription.textContent = 'Verifique se voce tem acesso a esta equipe.';
        detailCreatedAt.textContent = '-';
        detailTotalMembers.textContent = '0';
        detailTotalDocs.textContent = '0';
        detailMemberList.innerHTML = `
            <li class="empty-state">
                <strong>Sem membros</strong>
                <span>A equipe nao pode ser exibida.</span>
            </li>
        `;
        return;
    }

    teamNameHeader.textContent = team.nome;
    teamSubtitle.textContent = `${team.membros} membro(s) · ${team.documentos} documento(s)`;
    detailTeamName.textContent = team.nome;
    detailTeamDescription.textContent = team.descricao || 'Sem descricao cadastrada.';
    detailCreatedAt.textContent = formatDate(team.criado_em);
    detailTotalMembers.textContent = team.membros ?? 0;
    detailTotalDocs.textContent = team.documentos ?? 0;

    const members = (team.membros_lista || []).slice().sort((a, b) => {
        const cargoDiff = (b.cargo_nivel || 0) - (a.cargo_nivel || 0);
        if (cargoDiff !== 0) {
            return cargoDiff;
        }
        return String(a.nome || '').localeCompare(String(b.nome || ''), 'pt-BR');
    });

    if (!members.length) {
        detailMemberList.innerHTML = `
            <li class="empty-state">
                <strong>Nenhum membro encontrado</strong>
                <span>Essa equipe ainda nao possui integrantes vinculados.</span>
            </li>
        `;
        return;
    }

    detailMemberList.innerHTML = members
        .map((member) => {
            const role = roleLabel(member.cargo_nome);
            return `
                <li>
                    <div class="member-body">
                        <strong>${escapeHtml(member.nome)}</strong>
                        <p class="member-email">${escapeHtml(member.email)}</p>
                        <p>${escapeHtml(role.label)}</p>
                    </div>
                    <span class="pill ${role.css} member-role">${escapeHtml(role.label)}</span>
                </li>
            `;
        })
        .join('');
}

async function loadTeam() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    const teamId = getTeamId();
    if (!teamId) {
        renderTeam(null);
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/${teamId}`, {
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
            throw new Error('Falha ao carregar equipe.');
        }

        const data = await response.json();
        const backendUser = data?.usuario;
        if (backendUser?.nome) {
            localStorage.setItem('userName', backendUser.nome);
            localStorage.setItem('userId', String(backendUser.user_id));
            userNameElement.textContent = backendUser.nome;
            userIcon.textContent = backendUser.nome.charAt(0).toUpperCase();
        }

        renderTeam(data);
    } catch (error) {
        console.error(error);
        renderTeam(null);
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

btnAddDocument.addEventListener('click', openDocumentModal);
btnOpenDocumentModal.addEventListener('click', openDocumentModal);
closeDocumentModal.addEventListener('click', closeDocumentFlow);
cancelDocumentModal.addEventListener('click', closeDocumentFlow);

documentModal.addEventListener('click', (event) => {
    if (event.target === documentModal) {
        closeDocumentFlow();
    }
});

confirmDocumentModal.addEventListener('click', () => {
    closeDocumentFlow();
    alert('Fluxo de adicao de documento ainda sera ligado ao backend.');
});

loadTeam();