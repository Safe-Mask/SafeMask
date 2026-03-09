const userTrigger = document.getElementById('userTrigger');
const userDropdown = document.getElementById('userDropdown');
const userMenu = document.getElementById('userMenu');
const logoutBtn = document.getElementById('logoutBtn');
const userNameElement = document.getElementById('userName');
const userIcon = document.querySelector('.user-icon');
const menuToggle = document.getElementById('menuToggle');
const btnCensurarDocumento = document.getElementById('btnCensurarDocumento');
const sidebar = document.getElementById('sidebar');
const menuLinks = document.querySelectorAll('.menu-link');
const API_URL = 'http://127.0.0.1:8000/dashboard/overview';

const metricTotalEquipes = document.getElementById('metricTotalEquipes');
const metricTotalDocs = document.getElementById('metricTotalDocs');
const metricDocsCensurados = document.getElementById('metricDocsCensurados');
const metricTaxaCensura = document.getElementById('metricTaxaCensura');
const metricNivelSeguranca = document.getElementById('metricNivelSeguranca');
const metricNivelAlto = document.getElementById('metricNivelAlto');

const highlightTotalCensurados = document.getElementById('highlightTotalCensurados');
const highlightTaxaCensura = document.getElementById('highlightTaxaCensura');
const highlightNivelAlto = document.getElementById('highlightNivelAlto');

const teamList = document.getElementById('teamList');
const docList = document.getElementById('docList');
const barChartTeams = document.getElementById('barChartTeams');
const processingDonut = document.getElementById('processingDonut');
const processingLegend = document.getElementById('processingLegend');
const docsPanel = document.getElementById('docs-enviados');

const storedName = localStorage.getItem('userName') || 'Usuario';
userNameElement.textContent = storedName;
userIcon.textContent = storedName.charAt(0).toUpperCase();

userTrigger.addEventListener('click', () => {
    const isOpen = userDropdown.classList.toggle('open');
    userTrigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
});

// Fecha o dropdown ao clicar fora da area do menu do usuario.
document.addEventListener('click', (event) => {
    if (!userMenu.contains(event.target)) {
        userDropdown.classList.remove('open');
        userTrigger.setAttribute('aria-expanded', 'false');
    }
});

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userName');
    window.location.href = '../../index.html';
});

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatRelativeDate(isoString) {
    if (!isoString) {
        return 'data indisponivel';
    }

    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;

    if (Number.isNaN(date.getTime())) {
        return 'data invalida';
    }

    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return 'agora';
    if (minutes < 60) return `ha ${minutes} minuto(s)`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `ha ${hours} hora(s)`;

    const days = Math.floor(hours / 24);
    return `ha ${days} dia(s)`;
}

function statusBySecurityLevel(level) {
    if (level >= 4) {
        return { label: 'Censura Forte', css: 'ok' };
    }
    if (level >= 2) {
        return { label: 'Censurado', css: 'ok' };
    }
    return { label: 'Baixa Protecao', css: 'alert' };
}

function renderTeams(teams) {
    if (!teams.length) {
        teamList.innerHTML = `
            <li>
                <strong>Nenhuma equipe encontrada</strong>
                <span>cadastre ou associe equipes para visualizar</span>
            </li>
        `;
        barChartTeams.innerHTML = '<p class="empty-message">Sem dados para exibir.</p>';
        return;
    }

    teamList.innerHTML = teams
        .slice(0, 6)
        .map((team) => `
            <li>
                <strong>${escapeHtml(team.nome)}</strong>
                <span>${team.documentos} documento(s) ativo(s)</span>
            </li>
        `)
        .join('');

    const maxDocs = Math.max(...teams.map((team) => team.documentos), 1);

    barChartTeams.innerHTML = teams
        .slice(0, 6)
        .map((team) => {
            const width = Math.max(8, Math.round((team.documentos / maxDocs) * 100));
            return `
                <div class="bar-item">
                    <span class="label">${escapeHtml(team.nome)}</span>
                    <div class="bar-track"><div class="bar" style="width: ${width}%;"></div></div>
                    <span class="value">${team.documentos}</span>
                </div>
            `;
        })
        .join('');
}

function renderRecentDocs(docs) {
    if (!docs.length) {
        docList.innerHTML = `
            <li>
                <div>
                    <strong>Nenhum documento recente</strong>
                    <p>os uploads aparecerao aqui</p>
                </div>
                <span class="status wait">Vazio</span>
            </li>
        `;
        return;
    }

    docList.innerHTML = docs
        .slice(0, 8)
        .map((doc) => {
            const status = statusBySecurityLevel(doc.nivel_seguranca);
            return `
                <li>
                    <div>
                        <strong>${escapeHtml(doc.nome_original)}</strong>
                        <p>${escapeHtml(doc.equipe_nome || 'Sem equipe')} · ${formatRelativeDate(doc.criado_em)}</p>
                    </div>
                    <span class="status ${status.css}">${status.label}</span>
                </li>
            `;
        })
        .join('');
}

function renderProcessingChart(metrics) {
    const totalDocs = metrics.total_documentos || 0;
    const censurados = metrics.documentos_censurados || 0;
    const nivelAlto = metrics.documentos_nivel_alto || 0;
    const outros = Math.max(0, totalDocs - censurados);

    const censuradosPct = totalDocs ? Math.round((censurados / totalDocs) * 100) : 0;
    const nivelAltoPct = totalDocs ? Math.round((nivelAlto / totalDocs) * 100) : 0;
    const outrosPct = Math.max(0, 100 - censuradosPct - nivelAltoPct);

    processingDonut.style.background = `conic-gradient(
        #00c853 0 ${censuradosPct}%,
        #ff9f1a ${censuradosPct}% ${censuradosPct + nivelAltoPct}%,
        #7a7a7a ${censuradosPct + nivelAltoPct}% 100%
    )`;

    processingLegend.innerHTML = `
        <li><span class="dot done"></span> Censurados: ${censuradosPct}% (${censurados})</li>
        <li><span class="dot review"></span> Nivel alto: ${nivelAltoPct}% (${nivelAlto})</li>
        <li><span class="dot queue"></span> Demais docs: ${outrosPct}% (${outros})</li>
    `;
}

function applyMetrics(metrics) {
    metricTotalEquipes.textContent = metrics.total_equipes ?? 0;
    metricTotalDocs.textContent = metrics.total_documentos ?? 0;
    metricDocsCensurados.textContent = metrics.documentos_censurados ?? 0;
    metricTaxaCensura.textContent = `${metrics.taxa_censura ?? 0}% de censura aplicada`;
    metricNivelSeguranca.textContent = metrics.media_nivel_seguranca ?? 0;
    metricNivelAlto.textContent = `${metrics.documentos_nivel_alto ?? 0} docs com nivel alto`;

    highlightTotalCensurados.textContent = metrics.documentos_censurados ?? 0;
    highlightTaxaCensura.textContent = `${metrics.taxa_censura ?? 0}%`;
    highlightNivelAlto.textContent = metrics.documentos_nivel_alto ?? 0;
}

async function loadDashboardData() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'auth/login.html';
        return;
    }

    try {
        const response = await fetch(API_URL, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = 'auth/login.html';
            return;
        }

        if (!response.ok) {
            throw new Error('Falha ao carregar dashboard.');
        }

        const data = await response.json();
        const backendUserName = data?.usuario?.nome;
        if (backendUserName) {
            localStorage.setItem('userName', backendUserName);
            userNameElement.textContent = backendUserName;
            userIcon.textContent = backendUserName.charAt(0).toUpperCase();
        }

        applyMetrics(data.metrics || {});
        renderTeams(data.equipes || []);
        renderRecentDocs(data.documentos_recentes || []);
        renderProcessingChart(data.metrics || {});
    } catch (error) {
        console.error(error);
        docList.innerHTML = `
            <li>
                <div>
                    <strong>Erro ao carregar dados</strong>
                    <p>verifique se o backend esta ativo em http://127.0.0.1:8000</p>
                </div>
                <span class="status alert">Erro</span>
            </li>
        `;
    }
}

menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});

btnCensurarDocumento.addEventListener('click', () => {
    docsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });

    menuLinks.forEach((item) => item.classList.remove('active'));
    const docsMenuItem = document.querySelector('.menu-link[data-section="upload-documento"]');
    if (docsMenuItem) {
        docsMenuItem.classList.add('active');
    }
});

// Marca visualmente a secao selecionada no menu lateral.
menuLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
        event.preventDefault();
        menuLinks.forEach((item) => item.classList.remove('active'));
        link.classList.add('active');

        if (window.innerWidth <= 860) {
            sidebar.classList.remove('open');
        }
    });
});

loadDashboardData();
