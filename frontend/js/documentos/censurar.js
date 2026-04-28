const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
const goToDashboardBtn = document.getElementById('goToDashboardBtn');
const goToDashboardBtnInline = document.getElementById('goToDashboardBtnInline');
const cancelUploadBtn = document.getElementById('cancelUploadBtn');
const cancelReviewBtn = document.getElementById('cancelReviewBtn');
const censorStartBtn = document.getElementById('censorStartBtn');
const saveCensoredDocBtn = document.getElementById('saveCensoredDocBtn');
const pickFileBtn = document.getElementById('pickFileBtn');
const documentInput = document.getElementById('documentInput');
const dropzone = document.getElementById('dropzone');
const fileSummary = document.getElementById('fileSummary');
const fileSummaryReview = document.getElementById('fileSummaryReview');
const dropzonePrompt = document.getElementById('dropzonePrompt');
const previewFileName = document.getElementById('previewFileName');
const teamPicker = document.getElementById('teamPicker');
const selectedTeamsCount = document.getElementById('selectedTeamsCount');
const selectedTeamsNames = document.getElementById('selectedTeamsNames');
const docTitleInput = document.getElementById('docTitleInput');
const securityLevelInput = document.getElementById('securityLevelInput');
const docNotesInput = document.getElementById('docNotesInput');
const uploadStep = document.getElementById('uploadStep');
const loadingStep = document.getElementById('loadingStep');
const reviewStep = document.getElementById('reviewStep');
const loadingStepLabel = document.getElementById('loadingStepLabel');
const loadingFileName = document.getElementById('loadingFileName');
const loadingBadgeRedaction = document.getElementById('loadingBadgeRedaction');
const loadingBadgeTeams = document.getElementById('loadingBadgeTeams');
const API_DASHBOARD_OVERVIEW = 'http://127.0.0.1:8000/dashboard/overview';

const storedName = localStorage.getItem('userName') || 'Usuario';
userNameElement.textContent = storedName;
userIcon.textContent = storedName.charAt(0).toUpperCase();

const state = {
    selectedTeams: new Set(),
    currentFile: null,
    teams: [],
    currentStep: 'upload',
    loadingTimeoutId: null,
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

function setStep(step) {
    clearTimeout(state.loadingTimeoutId);
    state.currentStep = step;
    uploadStep.hidden = step !== 'upload';
    loadingStep.hidden = step !== 'loading';
    reviewStep.hidden = step !== 'review';

    if (step === 'loading') {
        loadingStepLabel.textContent = '0%';
        loadingBadgeRedaction.classList.remove('active');
        loadingBadgeTeams.classList.remove('active');
    }
}

function setFileSummaryMarkup(target, file) {
    if (!target) {
        return;
    }

    if (!file) {
        target.innerHTML = `
            <div class="empty-state small">
                <strong>Nenhum arquivo selecionado</strong>
                <span>Escolha um documento para iniciar o fluxo de censura.</span>
            </div>
        `;
        return;
    }

    const sizeLabel = formatBytes(file.size);

    target.innerHTML = `
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

function updateDropzoneState(hasFile) {
    dropzone.classList.toggle('is-filled', hasFile);
    if (dropzonePrompt) {
        dropzonePrompt.hidden = hasFile;
    }
    fileSummary.hidden = !hasFile;
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
            const teamId = Number(checkbox.value);
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
        censorStartBtn.disabled = true;
        updateDropzoneState(false);
        setFileSummaryMarkup(fileSummary, null);
        setFileSummaryMarkup(fileSummaryReview, null);
        return;
    }

    state.currentFile = file;
    const nameWithoutExt = file.name.replace(/\.[^.]+$/, '');
    previewFileName.textContent = file.name;
    docTitleInput.value = `${nameWithoutExt}_censurado`;
    censorStartBtn.disabled = false;

    updateDropzoneState(true);
    setFileSummaryMarkup(fileSummary, file);
    setFileSummaryMarkup(fileSummaryReview, file);
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

function openReviewStep() {
    if (!state.currentFile) {
        alert('Selecione um arquivo para continuar.');
        return;
    }

    clearTimeout(state.loadingTimeoutId);
    loadingFileName.textContent = state.currentFile.name;
    setStep('loading');

    const progressMarks = [
        { delay: 5000, value: '25%', redaction: false, teams: false },
        { delay: 10000, value: '50%', redaction: true, teams: false },
        { delay: 17000, value: '85%', redaction: true, teams: true },
        { delay: 20000, value: '100%', redaction: true, teams: true },
    ];

    progressMarks.forEach((mark) => {
        setTimeout(() => {
            if (state.currentStep !== 'loading') {
                return;
            }

            loadingStepLabel.textContent = mark.value;
            loadingBadgeRedaction.classList.toggle('active', mark.redaction);
            loadingBadgeTeams.classList.toggle('active', mark.teams);
        }, mark.delay);
    });

    state.loadingTimeoutId = setTimeout(() => {
        if (state.currentStep === 'loading') {
            setStep('review');
        }
    }, 20500);
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

goToDashboardBtnInline.addEventListener('click', () => {
    window.location.href = '../dashboard.html';
});

cancelUploadBtn.addEventListener('click', () => {
    clearTimeout(state.loadingTimeoutId);
    setStep('upload');
});

cancelReviewBtn.addEventListener('click', () => {
    clearTimeout(state.loadingTimeoutId);
    setStep('upload');
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

censorStartBtn.addEventListener('click', openReviewStep);

saveCensoredDocBtn.addEventListener('click', async () => {
    if (!state.currentFile) {
        alert('Selecione um arquivo para continuar.');
        return;
    }

    if (!state.selectedTeams.size) {
        alert('Selecione ao menos uma equipe para vincular o documento.');
        return;
    }

    saveCensoredDocBtn.disabled = true;
    saveCensoredDocBtn.textContent = 'Salvando...';

    try {
        const formData = new FormData();
        formData.append('file', state.currentFile);
        formData.append('titulo', docTitleInput.value);
        formData.append('nivel_seguranca', securityLevelInput.value);
        formData.append('observacoes', docNotesInput.value);
        formData.append('teams', JSON.stringify(Array.from(state.selectedTeams).map((teamId) => Number(teamId))));

        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = '../auth/login.html';
            return;
        }

        const response = await fetch('http://127.0.0.1:8000/documentos/salvar-censurado', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '../auth/login.html';
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            alert(`Erro ao salvar: ${data.detail || 'Erro desconhecido'}`);
            return;
        }

        alert(`Documento censurado salvo com sucesso em ${data.documentos_criados} equipe(s)!`);
        
        // Limpar e voltar ao upload
        documentInput.value = '';
        updateFileSummary(null);
        setStep('upload');
        state.selectedTeams.clear();
        renderSelectedSummary();

    } catch (error) {
        console.error('Erro ao salvar documento:', error);
        alert('Erro ao salvar documento. Verifique o console.');
    } finally {
        saveCensoredDocBtn.disabled = false;
        saveCensoredDocBtn.textContent = 'Salvar documento censurado';
    }
});

docTitleInput.addEventListener('input', () => {
    if (!docTitleInput.value.trim() && state.currentFile) {
        docTitleInput.value = `${state.currentFile.name.replace(/\.[^.]+$/, '')}_censurado`;
    }
});

updateFileSummary(null);
setStep('upload');
loadUserTeams();

window.addEventListener('beforeunload', () => {
    clearTimeout(state.loadingTimeoutId);
    clearPreviewUrl();
});
