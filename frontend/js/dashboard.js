// Sidebar, topbar e dropdown pertencem ao app-shell.js.
const userNameElement = document.getElementById('userName');
const userIcon = document.getElementById('userIcon');
const API_URL = `${API_ROOT}/dashboard/overview`;





const teamList = document.getElementById('teamList');
const docList = document.getElementById('docList');
const barChartTeams = document.getElementById('barChartTeams');
const processingDonut = document.getElementById('processingDonut');
const processingLegend = document.getElementById('processingLegend');


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


function renderMindmap(data) {
    const metrics = data?.metrics || {};
    const equipes = data?.equipes || [];
    if (!mindmapContainer) return;
    const totalDocs = metrics.total_documentos || 0;
    const censurados = metrics.documentos_censurados || 0;
    const nivelAlto = metrics.documentos_nivel_alto || 0;
    let html = '<div class="mindmap-root">\n';
    html += '  <div class="mindmap-node root">\n';
    html += `    <span class="node-title">SafeMask</span>\n`;
    html += `    <span class="node-meta">${totalDocs} documentos · ${equipes.length} equipes</span>\n`;
    html += '    <div class="node-badges">\n';
    html += `      <span class="badge info">Censurados: ${censurados}</span>\n`;
    html += `      <span class="badge warn">Nivel Alto: ${nivelAlto}</span>\n`;
    html += `      <span class="badge neutral">Taxa: ${metrics.taxa_censura || 0}%</span>\n`;
    html += '    </div>\n  </div>\n';
    html += '  <div class="mindmap-branches">\n';
    if (equipes.length === 0) {
        html += '<div class="mindmap-empty">Nenhuma equipe encontrada</div>\n';
    } else {
        equipes.slice(0, 8).forEach(eq => {
            html += '    <div class="mindmap-branch">\n';
            html += '      <div class="mindmap-node">\n';
            html += `        <span class="node-title">${escapeHtml(eq.nome)}</span>\n`;
            html += `        <span class="node-meta">${eq.documentos} documentos</span>\n`;
            html += '        <div class="node-badges">\n';
            html += eq.documentos > 0 ? '<span class="badge ok">Ativos</span>\n' : '<span class="badge neutral">Vazio</span>\n';
            html += '        </div>\n      </div>\n    </div>\n';
        });
    }
    html += '  </div>\n</div>';
    mindmapContainer.innerHTML = html;
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

        
        renderTeams(data.equipes || []);
        renderRecentDocs(data.documentos_recentes || []);
        renderProcessingChart(data.metrics || {});
        renderMindmap(data);
    } catch (error) {
        console.error(error);
        docList.innerHTML = `
            <li>
                <div>
                    <strong>Erro ao carregar dados</strong>
                    <p>verifique se o backend esta ativo em ${API_ROOT}</p>
                </div>
                <span class="status alert">Erro</span>
            </li>
        `;
    }
}

// Sidebar, dropdown de usuario, logout e CTA sao gerenciados por app-shell.js.
renderMindmap({metrics:{},equipes:[],documentos_recentes:[]});
loadDashboardData();
