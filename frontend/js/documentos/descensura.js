const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');
const backToDocumentsBtn = document.getElementById('backToDocumentsBtn');
const docTitle = document.getElementById('docTitle');
const docSubtitle = document.getElementById('docSubtitle');
const docAccessLabel = document.getElementById('docAccessLabel');
const docTeamLabel = document.getElementById('docTeamLabel');
const docPreviewFrame = document.getElementById('docPreviewFrame');
const docPreviewFallback = document.getElementById('docPreviewFallback');
const metaTeam = document.getElementById('metaTeam');
const metaAuthor = document.getElementById('metaAuthor');
const metaDate = document.getElementById('metaDate');
const metaSize = document.getElementById('metaSize');
const metaLevel = document.getElementById('metaLevel');
const metaStatus = document.getElementById('metaStatus');
const metaKey = document.getElementById('metaKey');
const openCensoredBtn = document.getElementById('openCensoredBtn');
const startRedactionBtn = document.getElementById('startRedactionBtn');

const API_DOCUMENT = 'https://safemask-3.onrender.com/documentos/censurados';
const docId = Number(new URLSearchParams(window.location.search).get('doc_id'));

const storedName = localStorage.getItem('userName') || 'Usuario';
userNameElement.textContent = storedName;
userIcon.textContent = storedName.charAt(0).toUpperCase();

let previewObjectUrl = null;

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

function securityLabel(level) {
    const map = {
        1: 'Basico',
        2: 'Protecao media',
        3: 'Protecao alta',
        4: 'Protecao maxima',
    };

    return map[Number(level)] || 'Desconhecido';
}

function clearPreviewUrl() {
    if (previewObjectUrl) {
        URL.revokeObjectURL(previewObjectUrl);
        previewObjectUrl = null;
    }
}

function resetPage(message = 'Selecione um documento permitido para iniciar a descensura.') {
    docTitle.textContent = 'Documento indisponivel';
    docSubtitle.textContent = message;
    docAccessLabel.textContent = 'Sem dados';
    docTeamLabel.textContent = 'Equipe';
    metaTeam.textContent = '-';
    metaAuthor.textContent = '-';
    metaDate.textContent = '-';
    metaSize.textContent = '-';
    metaLevel.textContent = '-';
    metaStatus.textContent = '-';
    metaKey.textContent = '-';
    clearPreviewUrl();
    docPreviewFrame.src = 'about:blank';
    docPreviewFallback.hidden = false;
    docPreviewFallback.innerHTML = `
        <strong>Documento indisponível</strong>
        <p>${escapeHtml(message)}</p>
    `;
}

async function loadDocument() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '../auth/login.html';
        return;
    }

    if (!docId) {
        resetPage('Nenhum documento foi informado na URL.');
        return;
    }

    try {
        const response = await fetch(`${API_DOCUMENT}/${docId}`, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '../auth/login.html';
            return;
        }

        if (response.status === 404) {
            alert('Você não tem permissão para acessar este documento.');
            window.location.href = 'censurados.html';
            return;
        }

        if (!response.ok) {
            throw new Error('Falha ao carregar o documento.');
        }

        const documento = await response.json();
        docTitle.textContent = documento.nome_original || 'Documento';
        docSubtitle.textContent = `${documento.equipe?.nome || 'Sem equipe'} · pronto para descensura`;
        docAccessLabel.textContent = 'Com acesso';
        docTeamLabel.textContent = documento.equipe?.nome || 'Sem equipe';
        metaTeam.textContent = documento.equipe?.nome || '-';
        metaAuthor.textContent = documento.autor_nome || storedName;
        metaDate.textContent = formatDate(documento.criado_em);
        metaSize.textContent = formatBytes(documento.tamanho_bytes);
        metaLevel.textContent = securityLabel(documento.nivel_seguranca);
        metaStatus.textContent = documento.status_processamento || '-';
        metaKey.textContent = documento.chave_criptografica || '-';

        clearPreviewUrl();
        docPreviewFallback.hidden = false;
        docPreviewFallback.innerHTML = `
            <strong>Carregando preview</strong>
            <p>Buscando o documento para exibição segura.</p>
        `;
        docPreviewFrame.src = 'about:blank';
        docPreviewFrame.onload = () => {
            docPreviewFallback.hidden = true;
        };

        if (documento.preview_url) {
            const previewResponse = await fetch(`https://safemask-3.onrender.com${documento.preview_url}`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (previewResponse.ok) {
                const blob = await previewResponse.blob();
                previewObjectUrl = URL.createObjectURL(blob);
                docPreviewFrame.src = previewObjectUrl;
            } else {
                docPreviewFallback.innerHTML = `
                    <strong>Preview indisponível</strong>
                    <p>O arquivo foi carregado, mas não pôde ser renderizado neste navegador.</p>
                `;
                docPreviewFallback.hidden = false;
            }
        }
    } catch (error) {
        console.error(error);
        resetPage('Não foi possível carregar o documento selecionado.');
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

backToDocumentsBtn.addEventListener('click', () => {
    window.location.href = 'censurados.html';
});

openCensoredBtn.addEventListener('click', () => {
    window.location.href = `censurados.html?doc_id=${docId}`;
});

startRedactionBtn.addEventListener('click', () => {
    alert('Fluxo de descensura ainda em preparação.');
});

window.addEventListener('beforeunload', clearPreviewUrl);

loadDocument();
