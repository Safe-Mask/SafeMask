const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
const goToUploadBtn = document.getElementById('goToUploadBtn');
const docsList = document.getElementById('docsList');
const docsEmptyState = document.getElementById('docsEmptyState');
const docsCountPill = document.getElementById('docsCountPill');
const currentUserLabel = document.getElementById('currentUserLabel');
const detailEmptyState = document.getElementById('detailEmptyState');
const detailShell = document.getElementById('detailShell');
const detailTitle = document.getElementById('detailTitle');
const detailTeam = document.getElementById('detailTeam');
const detailDate = document.getElementById('detailDate');
const detailSecurity = document.getElementById('detailSecurity');
const detailCryptoKey = document.getElementById('detailCryptoKey');
const detailPreviewFrame = document.getElementById('detailPreviewFrame');
const detailPreviewFallback = document.getElementById('detailPreviewFallback');
const undoRedactionBtn = document.getElementById('undoRedactionBtn');
const closeDetailsBtn = document.getElementById('closeDetailsBtn');
const loadingStep = document.getElementById('loadingStep');
const loadingStepLabel = document.getElementById('loadingStepLabel');
const loadingFileName = document.getElementById('loadingFileName');
const loadingBadgeRedaction = document.getElementById('loadingBadgeRedaction');
const loadingBadgeTeams = document.getElementById('loadingBadgeTeams');

const API_DOCUMENTS = 'https://safemask-3.onrender.com/documentos/censurados';
const initialDocId = Number(new URLSearchParams(window.location.search).get('doc_id'));

const storedName = localStorage.getItem('userName') || 'Usuario';
userNameElement.textContent = storedName;
userIcon.textContent = storedName.charAt(0).toUpperCase();
currentUserLabel.textContent = storedName;

const state = {
    documentos: [],
    selectedDoc: null,
    previewObjectUrl: null,
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

function formatDate(value) {
    if (!value) {
        return 'data indisponivel';
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return 'data invalida';
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

function securityLabel(level) {
    const map = {
        1: 'Basico',
        2: 'Protecao media',
        3: 'Protecao alta',
        4: 'Protecao maxima',
    };

    return map[Number(level)] || 'Desconhecido';
}

function toggleDetailState(hasDocument) {
    detailEmptyState.hidden = hasDocument;
    detailShell.hidden = !hasDocument;
}

function clearPreviewUrl() {
    if (state.previewObjectUrl) {
        URL.revokeObjectURL(state.previewObjectUrl);
        state.previewObjectUrl = null;
    }
}

function renderDocumentsList() {
    docsCountPill.textContent = `${state.documentos.length} documento(s)`;

    if (!state.documentos.length) {
        docsEmptyState.innerHTML = `
            <strong>Nenhum documento encontrado</strong>
            <span>Você ainda não possui documentos censurados vinculados ao seu usuário.</span>
        `;
        docsList.innerHTML = '';
        toggleDetailState(false);
        return;
    }

    docsEmptyState.hidden = true;
    docsList.innerHTML = state.documentos
        .map((documento) => `
            <article class="doc-card ${state.selectedDoc && state.selectedDoc.doc_id === documento.doc_id ? 'active' : ''}" data-doc-id="${documento.doc_id}">
                <div class="doc-card-top">
                    <div>
                        <strong>${escapeHtml(documento.nome_original)}</strong>
                        <p>${escapeHtml(formatDate(documento.criado_em))}</p>
                    </div>
                    <span class="doc-tag">${escapeHtml(securityLabel(documento.nivel_seguranca))}</span>
                </div>
                <div class="doc-card-meta">
                    <span class="doc-tag">Equipe: ${escapeHtml(documento.equipe_nome || 'Sem equipe')}</span>
                    <span class="doc-tag">Tamanho: ${escapeHtml(formatBytes(documento.tamanho_bytes))}</span>
                </div>
                <div class="doc-actions">
                    <button type="button" class="cta-censor" data-action="redact" data-doc-id="${documento.doc_id}">Ver Arquivo Original</button>
                    <button type="button" class="ghost-button" data-action="details" data-doc-id="${documento.doc_id}">Detalhes</button>
                </div>
            </article>
        `)
        .join('');
}

function renderDocumentDetails(documento) {
    if (!documento) {
        clearPreviewUrl();
        detailPreviewFrame.src = 'about:blank';
        detailPreviewFallback.hidden = false;
        detailPreviewFallback.innerHTML = `
            <strong>Selecione um documento</strong>
            <p>Escolha um item na lista para ver a preview do documento censurado e a chave criptografica correspondente.</p>
        `;
        toggleDetailState(false);
        return;
    }

    state.selectedDoc = documento;
    detailTitle.textContent = documento.nome_original || '-';
    detailTeam.textContent = documento.equipe_nome || '-';
    detailDate.textContent = formatDate(documento.criado_em);
    detailSecurity.textContent = securityLabel(documento.nivel_seguranca);
    detailCryptoKey.textContent = documento.chave_criptografica || '-';

    clearPreviewUrl();
    detailPreviewFallback.hidden = false;
    detailPreviewFallback.innerHTML = `
        <strong>Carregando preview</strong>
        <p>Buscando o arquivo protegido para exibir o documento completo.</p>
    `;
    detailPreviewFrame.src = 'about:blank';
    detailPreviewFrame.onload = () => {
        detailPreviewFallback.hidden = true;
    };

    if (documento.preview_url) {
        const token = localStorage.getItem('token');
        if (token) {
            fetch(`https://safemask-3.onrender.com${documento.preview_url}`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error('Falha ao carregar preview.');
                    }

                    return response.blob();
                })
                .then((blob) => {
                    state.previewObjectUrl = URL.createObjectURL(blob);
                    detailPreviewFrame.src = state.previewObjectUrl;
                })
                .catch((error) => {
                    console.error(error);
                    detailPreviewFallback.innerHTML = `
                        <strong>Preview indisponível</strong>
                        <p>O arquivo existe, mas não pôde ser renderizado no navegador. O documento continua acessível pelos metadados e pela chave criptografica.</p>
                    `;
                    detailPreviewFallback.hidden = false;
                });
        }
    }

    toggleDetailState(true);
    renderDocumentsList();
}

async function loadDocumentDetails(docId) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    const response = await fetch(`${API_DOCUMENTS}/${docId}`, {
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
        throw new Error('Falha ao carregar detalhes do documento.');
    }

    return response.json();
}

async function loadDocuments() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    try {
        const response = await fetch(API_DOCUMENTS, {
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
            throw new Error('Falha ao carregar documentos censurados.');
        }

        const data = await response.json();
        state.documentos = Array.isArray(data.documentos) ? data.documentos : [];
        docsCountPill.textContent = `${data.total || state.documentos.length} documento(s)`;
        currentUserLabel.textContent = `#${data.usuario?.user_id || '-'} ${data.usuario?.nome || storedName}`;
        renderDocumentsList();

        if (state.documentos.length) {
            const initialDocument = state.documentos.find((documento) => Number(documento.doc_id) === initialDocId) || state.documentos[0];
            const detalheInicial = await loadDocumentDetails(initialDocument.doc_id);
            renderDocumentDetails(detalheInicial);
        }
    } catch (error) {
        console.error(error);
        docsEmptyState.innerHTML = `
            <strong>Erro ao carregar documentos</strong>
            <span>Verifique se o backend está ativo e se sua sessão continua válida.</span>
        `;
        docsList.innerHTML = '';
        toggleDetailState(false);
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

goToUploadBtn.addEventListener('click', () => {
    window.location.href = 'censurar.html';
});

docsList.addEventListener('click', (event) => {
    const redactionButton = event.target.closest('[data-action="redact"]');
    if (redactionButton) {
        const docId = Number(redactionButton.dataset.docId);
        window.location.href = `descensura.html?doc_id=${docId}`;
        return;
    }

    const button = event.target.closest('[data-action="details"]');
    if (!button) {
        return;
    }

    const docId = Number(button.dataset.docId);
    const selected = state.documentos.find((documento) => Number(documento.doc_id) === docId);
    if (selected) {
        loadDocumentDetails(docId)
            .then(renderDocumentDetails)
            .catch((error) => {
                console.error(error);
                alert('Nao foi possivel carregar os detalhes do documento.');
            });
    }
});

undoRedactionBtn.addEventListener('click', () => {
    alert('Descensurar ainda nao esta disponivel.');
});

closeDetailsBtn.addEventListener('click', () => {
    clearPreviewUrl();
    detailPreviewFrame.onload = null;
    toggleDetailState(false);
    state.selectedDoc = null;
    renderDocumentsList();
});

window.addEventListener('beforeunload', clearPreviewUrl);

loadDocuments();