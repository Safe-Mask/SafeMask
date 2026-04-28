const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
const goToDashboardBtn = document.getElementById('goToDashboardBtn');
const cancelUploadBtn = document.getElementById('cancelUploadBtn');
const saveCensoredDocBtn = document.getElementById('saveCensoredDocBtn');
const pickFileBtn = document.getElementById('pickFileBtn');
const documentInput = document.getElementById('documentInput');
const dropzone = document.getElementById('dropzone');
const fileSummary = document.getElementById('fileSummary');
const previewFileName = document.getElementById('previewFileName');
const teamPicker = document.getElementById('teamPicker');
const selectedTeamsCount = document.getElementById('selectedTeamsCount');
const selectedTeamsNames = document.getElementById('selectedTeamsNames');
const docTitleInput = document.getElementById('docTitleInput');
const securityLevelInput = document.getElementById('securityLevelInput');
const docNotesInput = document.getElementById('docNotesInput');
const API_DASHBOARD_OVERVIEW = 'http://127.0.0.1:8000/dashboard/overview';

const storedName = localStorage.getItem('userName') || 'Usuario';
userNameElement.textContent = storedName;
userIcon.textContent = storedName.charAt(0).toUpperCase();

const state = {
    selectedTeams: new Set(),
    currentFile: null,
    teams: [],
};

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
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

function normalizeTeams(rawTeams) {
    if (!Array.isArray(rawTeams) || rawTeams.length === 0) {
        return [];
    }

    return rawTeams
        .map((team, index) => ({
            id: team.team_id ?? team.id ?? index + 1,
            nome: team.nome ?? team.team_name ?? team.name ?? `Equipe ${index + 1}`,
            descricao: team.descricao ?? team.description ?? 'Equipe do usuario',
        }))
        .filter((team) => team.nome);
}

function setTeams(teams) {
    state.teams = normalizeTeams(teams);
    try {
        localStorage.setItem('userTeams', JSON.stringify(state.teams));
    } catch (error) {
        console.error('Erro ao salvar equipes no cache:', error);
    }
}

function renderSelectedSummary() {
    const selected = Array.from(state.selectedTeams);
    selectedTeamsCount.textContent = `${selected.length} equipe(s) selecionada(s)`;

    if (!selected.length) {
        selectedTeamsNames.textContent = 'Escolha as equipes para este documento fazer parte.';
        return;
    }

    const teamNames = selected
        .map((teamId) => state.teams.find((item) => String(item.id) === String(teamId))?.nome)
        .filter(Boolean);

    selectedTeamsNames.textContent = teamNames.join(' · ');
}

function renderTeams() {
    const teams = state.teams;

    if (!teams.length) {
        teamPicker.innerHTML = `
            <div class="empty-state small">
                <strong>Nenhuma equipe encontrada</strong>
                <span>Entre em uma equipe para que ela apareca nesta selecao.</span>
            </div>
        `;
        selectedTeamsCount.textContent = '0 equipe(s) selecionada(s)';
        selectedTeamsNames.textContent = 'Voce precisa participar de pelo menos uma equipe.';
        return;
    }

    teamPicker.innerHTML = teams
        .map((team) => `
            <label class="team-option" data-team-id="${escapeHtml(team.id)}">
                <div>
                    <strong>${escapeHtml(team.nome)}</strong>
                    <p>${escapeHtml(team.descricao)}</p>
                </div>
                <input type="checkbox" value="${escapeHtml(team.id)}">
            </label>
        `)
        .join('');

    const options = teamPicker.querySelectorAll('.team-option');
    options.forEach((option) => {
        const checkbox = option.querySelector('input');
        checkbox.addEventListener('change', () => {
            const teamId = checkbox.value;
            if (checkbox.checked) {
                state.selectedTeams.add(teamId);
                option.classList.add('selected');
            } else {
                state.selectedTeams.delete(teamId);
                option.classList.remove('selected');
            }
            renderSelectedSummary();
        });
    });

    if (options[0]) {
        const firstCheckbox = options[0].querySelector('input');
        firstCheckbox.checked = true;
        firstCheckbox.dispatchEvent(new Event('change'));
    }
}

async function loadUserTeams() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    try {
        const response = await fetch(API_DASHBOARD_OVERVIEW, {
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
            throw new Error('Falha ao carregar equipes do usuario.');
        }

        const data = await response.json();
        setTeams(data.equipes || []);
        renderTeams();
        renderSelectedSummary();
    } catch (error) {
        console.error(error);
        state.teams = [];
        renderTeams();
    }
}

function updateFileSummary(file) {
    if (!file) {
        state.currentFile = null;
        previewFileName.textContent = 'Arquivo nao carregado';
        fileSummary.innerHTML = `
            <div class="empty-state small">
                <strong>Nenhum arquivo selecionado</strong>
                <span>Escolha um documento para iniciar o fluxo de censura.</span>
            </div>
        `;
        return;
    }

    state.currentFile = file;
    const sizeLabel = formatBytes(file.size);
    const nameWithoutExt = file.name.replace(/\.[^.]+$/, '');
    previewFileName.textContent = file.name;
    docTitleInput.value = `${nameWithoutExt}_censurado`;

    fileSummary.innerHTML = `
        <div class="file-card">
            <div class="file-card-top">
                <div>
                    <strong>${escapeHtml(file.name)}</strong>
                    <p>${escapeHtml(file.type || 'arquivo selecionado')}</p>
                </div>
                <span class="pill ok">Carregado</span>
            </div>
            <div class="file-meta">
                <span>Tamanho: ${escapeHtml(sizeLabel)}</span>
                <span>Persistencia: somente versao criptografada</span>
                <span>Status: pronto para revisao</span>
            </div>
        </div>
    `;
}

function openFilePicker() {
    documentInput.click();
}

function handleFileChange(fileList) {
    const file = fileList && fileList[0];
    updateFileSummary(file || null);
}

function setDragState(active) {
    dropzone.classList.toggle('dragover', active);
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

goToDashboardBtn.addEventListener('click', () => {
    window.location.href = '../dashboard.html';
});

cancelUploadBtn.addEventListener('click', () => {
    window.location.href = '../dashboard.html';
});

pickFileBtn.addEventListener('click', openFilePicker);
dropzone.addEventListener('click', (event) => {
    if (event.target === documentInput || event.target === pickFileBtn) {
        return;
    }
    openFilePicker();
});

documentInput.addEventListener('change', (event) => {
    handleFileChange(event.target.files);
});

dropzone.addEventListener('dragover', (event) => {
    event.preventDefault();
    setDragState(true);
});

dropzone.addEventListener('dragleave', () => {
    setDragState(false);
});

dropzone.addEventListener('drop', (event) => {
    event.preventDefault();
    setDragState(false);
    handleFileChange(event.dataTransfer.files);
});

saveCensoredDocBtn.addEventListener('click', () => {
    if (!state.currentFile) {
        alert('Selecione um arquivo para continuar.');
        return;
    }

    if (!state.selectedTeams.size) {
        alert('Selecione ao menos uma equipe para vincular o documento.');
        return;
    }

    const selectedTeams = Array.from(state.selectedTeams).join(', ');
    alert(`Fluxo visual pronto. O backend vai salvar a versao criptografada e associar o documento as equipes selecionadas: ${selectedTeams}.`);
});

docTitleInput.addEventListener('input', () => {
    if (!docTitleInput.value.trim() && state.currentFile) {
        docTitleInput.value = `${state.currentFile.name.replace(/\.[^.]+$/, '')}_censurado`;
    }
});

updateFileSummary(null);
loadUserTeams();
