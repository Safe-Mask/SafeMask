const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');

const teamNameHeader = document.getElementById('teamNameHeader');
const teamSubtitle = document.getElementById('teamSubtitle');
const detailTeamName = document.getElementById('detailTeamName');
const detailTeamDescription = document.getElementById('detailTeamDescription');
const detailCreatedAt = document.getElementById('detailCreatedAt');
const detailTotalMembers = document.getElementById('detailTotalMembers');
const detailTotalDocs = document.getElementById('detailTotalDocs');
const detailMemberList = document.getElementById('detailMemberList');
const detailDocumentList = document.getElementById('detailDocumentList');
const teamDocsCount = document.getElementById('teamDocsCount');

const API_BASE = 'https://safemask-3.onrender.com/equipes';
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

function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) {
        return '0 KB';
    }

    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
    }

    return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function documentAccessLabel(canAccess) {
    return canAccess
        ? { label: 'Com acesso', css: 'ok', action: 'Descensurar' }
        : { label: 'Sem acesso', css: 'alert', action: 'Bloqueado' };
}

function openDocumentRedaction(docId) {
    window.location.href = `../documentos/descensura.html?doc_id=${docId}`;
}

function getTeamId() {
    const params = new URLSearchParams(window.location.search);
    const teamId = Number(params.get('team_id'));
    return Number.isFinite(teamId) ? teamId : null;
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
        detailDocumentList.innerHTML = `
            <li class="empty-state">
                <strong>Sem documentos</strong>
                <span>Os documentos desta equipe nao puderam ser exibidos.</span>
            </li>
        `;
        teamDocsCount.textContent = '0 documentos';
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
    } else {
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

    const documentos = Array.isArray(team.documentos_lista) ? team.documentos_lista : [];
    teamDocsCount.textContent = `${documentos.length} documento(s)`;

    if (!documentos.length) {
        detailDocumentList.innerHTML = `
            <li class="empty-state">
                <strong>Nenhum documento encontrado</strong>
                <span>Esta equipe ainda nao possui documentos cadastrados.</span>
            </li>
        `;
        return;
    }

    detailDocumentList.innerHTML = documentos
        .map((documento) => {
            const access = documentAccessLabel(Boolean(documento.tem_acesso));
            const docClasses = `team-doc-item ${documento.tem_acesso ? 'allowed' : 'denied'}`;
            const actionMarkup = documento.tem_acesso
                ? `<button type="button" class="team-doc-action" data-doc-redaction="${documento.doc_id}">${access.action}</button>`
                : `<button type="button" class="team-doc-action disabled" disabled>${access.action}</button>`;

            return `
                <li class="${docClasses}">
                    <div class="team-doc-top">
                        <div>
                            <strong>${escapeHtml(documento.nome_original)}</strong>
                            <p>${escapeHtml(documento.autor_nome || 'Autor desconhecido')} · ${escapeHtml(formatDate(documento.criado_em))}</p>
                        </div>
                        <span class="pill ${access.css}">${escapeHtml(access.label)}</span>
                    </div>

                    <div class="team-doc-meta">
                        <span class="pill wait">Extensao ${escapeHtml(documento.extensao || '-')}</span>
                        <span class="pill wait">${escapeHtml(formatBytes(documento.tamanho_bytes))}</span>
                        <span class="pill wait">Nivel ${escapeHtml(String(documento.nivel_seguranca ?? '-'))}</span>
                    </div>

                    <div class="team-doc-footer">
                        <span>${escapeHtml(documento.status_processamento || 'status indisponivel')}</span>
                        ${actionMarkup}
                    </div>
                </li>
            `;
        })
        .join('');
}

detailDocumentList.addEventListener('click', (event) => {
    const target = event.target.closest('[data-doc-redaction]');
    if (target) {
        openDocumentRedaction(target.dataset.docRedaction);
        return;
    }

    const docCard = event.target.closest('.team-doc-item');
    if (!docCard) {
        return;
    }

    const docId = docCard.querySelector('[data-doc-redaction]')?.dataset.docRedaction || null;
    const isAllowed = docCard.classList.contains('allowed');

    if (!isAllowed) {
        alert('Você não tem permissão para descensurar este documento.');
        return;
    }

    if (docId) {
        openDocumentRedaction(docId);
    }
});

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

loadTeam();