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
const uploadStep = document.getElementById('uploadStep');
const loadingStep = document.getElementById('loadingStep');
const reviewStep = document.getElementById('reviewStep');
const loadingStepLabel = document.getElementById('loadingStepLabel');
const loadingFileName = document.getElementById('loadingFileName');
const loadingBadgeRedaction = document.getElementById('loadingBadgeRedaction');
const loadingBadgeTeams = document.getElementById('loadingBadgeTeams');
const reviewFeedback = document.getElementById('reviewFeedback');
const API_UPLOAD = `${API_ROOT}/documentos/upload`;
const API_DASHBOARD_OVERVIEW = `${API_ROOT}/dashboard/overview`;

const storedName = localStorage.getItem('userName') || 'Usuario';
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

    // Nenhuma equipe vem marcada: o envio exige a escolha. Vindo do botao
    // "Enviar documento" da pagina da equipe (?equipe=<id>), ela ja vem marcada.
    const equipeDaUrl = Number(new URLSearchParams(window.location.search).get('equipe'));
    options.forEach((option) => {
        const checkbox = option.querySelector('input');
        if (equipeDaUrl && Number(checkbox.value) === equipeDaUrl) {
            checkbox.checked = true;
            checkbox.dispatchEvent(new Event('change'));
        }
    });
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

function showReviewFeedback(message) {
    reviewFeedback.textContent = message;
    reviewFeedback.hidden = false;
}

function hideReviewFeedback() {
    reviewFeedback.hidden = true;
    reviewFeedback.textContent = '';
}

function mensagemPorStatus(status) {
    if (status === 413) return 'Arquivo muito grande para o limite do servidor.';
    if (status === 503) return 'Serviço indisponível no servidor. Tente mais tarde.';
    return 'Erro ao processar documento.';
}

function handleFileChange(fileList) {
    const file = fileList && fileList[0];

    // Conferencia rapida no navegador; a API valida de novo o conteudo,
    // a integridade e o tamanho e explica a recusa (PI-III #18).
    const recusa = !file ? null
        : !file.name.toLowerCase().endsWith('.pdf') ? 'Formato não suportado: envie um arquivo PDF (.pdf).'
        : file.size === 0 ? 'O arquivo está vazio.'
        : null;
    if (recusa) {
        avisar(recusa);
        if (documentInput) {
            documentInput.value = '';
        }
        updateFileSummary(null);
        return;
    }

    updateFileSummary(file || null);
}

function setDragState(active) {
    dropzone.classList.toggle('dragover', active);
}

async function startUpload() {
    if (revisao.analisando) {
        avisar('Aguarde a análise do documento terminar.', 'info');
        return;
    }
    if (!state.currentFile) {
        avisar('Selecione um arquivo para continuar.', 'info');
        return;
    }

    // Sem equipe escolhida nada e enviado (antes ia para a primeira da lista).
    if (!state.selectedTeams.size) {
        avisar('Selecione ao menos uma equipe para vincular o documento.', 'info');
        return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    clearTimeout(state.loadingTimeoutId);
    hideReviewFeedback();
    loadingFileName.textContent = state.currentFile.name;
    setStep('loading');

    const formData = new FormData();
    formData.append('file', state.currentFile);
    formData.append('titulo', docTitleInput.value);
    formData.append('nivel_seguranca', securityLevelInput.value);
    formData.append('teams', JSON.stringify(Array.from(state.selectedTeams).map((teamId) => Number(teamId))));
    // Ajustes da revisao das tarjas.
    formData.append('ignorar', JSON.stringify(Array.from(revisao.ignorados)));
    formData.append('trechos_extras', JSON.stringify(revisao.trechos));

    try {
        loadingStepLabel.textContent = 'Analisando dados sensíveis...';
        loadingBadgeRedaction.classList.add('active');

        const response = await fetch(API_UPLOAD, {
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
            const erro = new Error(data.detail || mensagemPorStatus(response.status));
            erro.recusado = response.status < 500;
            throw erro;
        }

        loadingBadgeTeams.classList.add('active');
        loadingStepLabel.textContent = 'Concluído!';
        if (data.trechos_nao_encontrados) {
            avisarDepois(
                `${data.trechos_nao_encontrados} trecho(s) acrescentado(s) não apareceram no documento e não foram tarjados. Confira a grafia.`,
                'info',
            );
        }

        setTimeout(() => {
            window.location.href = `censurados.html?doc_id=${data.doc_id}`;
        }, 800);
    } catch (error) {
        console.error('Erro ao processar documento:', error);
        // Volta para a revisao, e nao para o inicio: o arquivo e as escolhas
        // continuam ali para uma nova tentativa.
        setStep('review');
        // Recusa do arquivo (4xx) e diferente de falha do servidor: o
        // usuario precisa saber o que corrigir antes de tentar de novo.
        const prefixo = error.recusado ? 'Envio recusado' : 'Erro ao processar documento';
        showReviewFeedback(`${prefixo}: ${error.message || 'verifique o console.'}`);
    }
}

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

// O envio so acontece depois da revisao de equipe, titulo e nivel.
censorStartBtn.addEventListener('click', () => {
    if (!state.currentFile) {
        avisar('Selecione um arquivo para continuar.', 'info');
        return;
    }
    setStep('review');
    analisarDocumento();
});
saveCensoredDocBtn.addEventListener('click', startUpload);

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
});

// ------------------------------------------------------------------
// Revisao das tarjas antes de salvar. A API analisa o arquivo sem
// gravar nada e devolve os achados MASCARADOS, cada um com um id. A pessoa
// desmarca falsos positivos e acrescenta trechos; o envio leva os ids
// desmarcados (`ignorar`) e os trechos (`trechos_extras`).

const API_ANALISAR = `${API_ROOT}/documentos/analisar`;
const findingsList = document.getElementById('findingsList');
const findingsCount = document.getElementById('findingsCount');
const findingsStatus = document.getElementById('findingsStatus');
const extraSnippetInput = document.getElementById('extraSnippetInput');
const addSnippetBtn = document.getElementById('addSnippetBtn');
const extraSnippetList = document.getElementById('extraSnippetList');

const revisao = {
    arquivo: null,
    achados: [],
    ignorados: new Set(),
    trechos: [],
    limites: { trechos: 20, tamanho_min: 3, tamanho_max: 120 },
    analisando: false,
};

function limparRevisao() {
    revisao.arquivo = null;
    revisao.achados = [];
    revisao.ignorados = new Set();
    revisao.trechos = [];
    renderAchados();
    renderTrechos();
}

function renderAchados() {
    const total = revisao.achados.length;
    const marcados = total - revisao.ignorados.size;
    findingsCount.textContent = revisao.analisando ? 'analisando...' : `${marcados} de ${total} marcados`;
    findingsList.innerHTML = revisao.achados
        .map((achado) => {
            const desmarcado = revisao.ignorados.has(achado.id);
            const vezes = achado.ocorrencias > 1 ? ` · ${achado.ocorrencias} vezes` : '';
            return `
                <li class="finding-item ${desmarcado ? 'desmarcado' : ''}">
                    <label>
                        <input type="checkbox" data-achado="${escapeHtml(achado.id)}" aria-label="Tarjar ${escapeHtml(achado.rotulo)} ${escapeHtml(achado.valor_mascarado)}" ${desmarcado ? '' : 'checked'}>
                        <span class="finding-type">${escapeHtml(achado.rotulo)}</span>
                        <span class="finding-value">${escapeHtml(achado.valor_mascarado)}</span>
                        <span class="finding-page">pág. ${escapeHtml(achado.pagina)}${vezes}</span>
                    </label>
                </li>`;
        })
        .join('');
}

function renderTrechos() {
    extraSnippetList.innerHTML = revisao.trechos
        .map((trecho, indice) => `
            <li class="extra-item">
                <span>${escapeHtml(trecho)}</span>
                <button type="button" class="ghost-button" data-remover-trecho="${indice}">Remover</button>
            </li>`)
        .join('');
}

async function analisarDocumento() {
    const arquivo = state.currentFile;
    if (!arquivo || revisao.arquivo === arquivo) {
        return; // ja analisado: voltar para a revisao nao refaz o trabalho
    }
    const token = localStorage.getItem('token');
    limparRevisao();
    revisao.arquivo = arquivo;
    revisao.analisando = true;
    findingsStatus.textContent = 'Analisando o documento...';
    renderAchados();

    try {
        const formData = new FormData();
        formData.append('file', arquivo);
        const response = await fetch(API_ANALISAR, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: formData,
        });
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '../auth/login.html';
            return;
        }
        const data = await response.json().catch(() => ({}));
        if (revisao.arquivo !== arquivo) {
            return; // outro arquivo foi escolhido enquanto este era analisado
        }
        if (!response.ok) {
            throw new Error(data.detail || mensagemPorStatus(response.status));
        }
        revisao.achados = data.achados || [];
        revisao.limites = data.limites || revisao.limites;
        findingsStatus.textContent = revisao.achados.length
            ? 'Tudo o que está marcado será coberto com tarja.'
            : 'Nenhum dado pessoal reconhecido. Se houver algo a cobrir, acrescente o trecho abaixo.';
    } catch (error) {
        console.error('Erro ao analisar documento:', error);
        revisao.arquivo = null;
        findingsStatus.textContent = `Não foi possível analisar: ${error.message}`;
        avisar(`Não foi possível analisar o documento: ${error.message}`);
    } finally {
        revisao.analisando = false;
        renderAchados();
    }
}

function acrescentarTrecho() {
    const trecho = extraSnippetInput.value.split(/\s+/).filter(Boolean).join(' ');
    const { trechos: maximo, tamanho_min: minimo, tamanho_max: tamanhoMaximo } = revisao.limites;
    if (trecho.length < minimo || trecho.length > tamanhoMaximo) {
        avisar(`O trecho precisa ter de ${minimo} a ${tamanhoMaximo} caracteres.`, 'info');
        return;
    }
    if (revisao.trechos.includes(trecho)) {
        avisar('Este trecho já foi acrescentado.', 'info');
        return;
    }
    if (revisao.trechos.length >= maximo) {
        avisar(`No máximo ${maximo} trechos por documento.`, 'info');
        return;
    }
    revisao.trechos.push(trecho);
    extraSnippetInput.value = '';
    renderTrechos();
}

findingsList.addEventListener('change', (event) => {
    const caixa = event.target.closest('[data-achado]');
    if (!caixa) {
        return;
    }
    if (caixa.checked) {
        revisao.ignorados.delete(caixa.dataset.achado);
    } else {
        revisao.ignorados.add(caixa.dataset.achado);
    }
    renderAchados();
});

addSnippetBtn.addEventListener('click', acrescentarTrecho);
extraSnippetInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        acrescentarTrecho();
    }
});
extraSnippetList.addEventListener('click', (event) => {
    const botao = event.target.closest('[data-remover-trecho]');
    if (botao) {
        revisao.trechos.splice(Number(botao.dataset.removerTrecho), 1);
        renderTrechos();
    }
});
