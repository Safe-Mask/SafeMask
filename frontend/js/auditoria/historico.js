// Historico de auditoria (GET /auditoria). Lider e supervisor veem os eventos
// das proprias equipes. Trazido do PI-III (CAMPUSCEUB/SafeMask#13).
const filtersPanel = document.getElementById('filtersPanel');
const filtersForm = document.getElementById('filtersForm');
const filterTeam = document.getElementById('filterTeam');
const filterDoc = document.getElementById('filterDoc');
const filterAction = document.getElementById('filterAction');
const filterFrom = document.getElementById('filterFrom');
const filterTo = document.getElementById('filterTo');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');
const totalPill = document.getElementById('totalPill');
const pageLabel = document.getElementById('pageLabel');
const feedback = document.getElementById('feedback');
const emptyState = document.getElementById('emptyState');
const tableWrap = document.getElementById('tableWrap');
const eventsBody = document.getElementById('eventsBody');
const pagination = document.getElementById('pagination');
const prevPageBtn = document.getElementById('prevPageBtn');
const nextPageBtn = document.getElementById('nextPageBtn');

const API_AUDITORIA = `${API_ROOT}/auditoria`;
const POR_PAGINA = 20;
// Mesmo criterio da API (NIVEL_MIN_AUDITORIA): supervisor (2) e lider (3).
const NIVEL_MIN_AUDITORIA = 2;

// Acoes que aparecem na trilha das equipes (eventos com equipe).
const ACOES = {
    upload_documento: 'Enviou documento',
    upload_documento_censurado: 'Salvou versão censurada',
    ver_censurado: 'Visualizou censurado',
    ver_parcial: 'Abriu versão parcial',
    ver_original: 'Abriu original',
    adicionar_membro: 'Adicionou membro',
    remover_membro: 'Removeu membro',
    alterar_cargo: 'Alterou cargo',
    alterar_politica_niveis: 'Alterou níveis da equipe',
};

const state = {
    pagina: 1,
    paginas: 0,
};

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// A API devolve a hora com fuso (UTC); o navegador converte para a hora local.
function formatDate(value) {
    if (!value) {
        return 'data indisponivel';
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'data invalida' : date.toLocaleString('pt-BR');
}

function authHeaders() {
    return { Authorization: `Bearer ${window.AppShell.Sessao.getToken()}` };
}

function redirectToLogin() {
    window.AppShell.Sessao.limpar();
    window.location.href = '../auth/login.html';
}

function showFeedback(message) {
    feedback.textContent = message;
    feedback.hidden = !message;
}

function showEmpty(title, text) {
    emptyState.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(text)}</span>`;
    emptyState.hidden = false;
    tableWrap.hidden = true;
    pagination.hidden = true;
}

// O dia escolhido e o dia LOCAL: 00:00 e 23:59:59.999 locais viram instantes
// UTC, que e como a API compara.
function inicioDoDia(value) {
    return value ? new Date(`${value}T00:00:00`).toISOString() : null;
}

function fimDoDia(value) {
    return value ? new Date(`${value}T23:59:59.999`).toISOString() : null;
}

// Filtros da tela, sem paginacao.
function filterParams() {
    const params = new URLSearchParams();
    const filtros = {
        team_id: filterTeam.value,
        doc_id: filterDoc.value,
        acao: filterAction.value,
        data_inicio: inicioDoDia(filterFrom.value),
        data_fim: fimDoDia(filterTo.value),
    };
    Object.entries(filtros).forEach(([chave, valor]) => {
        if (valor) {
            params.set(chave, valor);
        }
    });
    return params;
}

function buildQuery() {
    const params = filterParams();
    params.set('pagina', state.pagina);
    params.set('por_pagina', POR_PAGINA);
    return params.toString();
}

function describeTarget(evento) {
    if (evento.documento) {
        return `<span>${escapeHtml(evento.documento.nome || 'Documento removido')}<span class="audit-sub">doc #${evento.documento.doc_id}</span></span>`;
    }
    if (evento.alvo) {
        return `<span>${escapeHtml(evento.alvo.nome || '-')}<span class="audit-sub">membro da equipe</span></span>`;
    }
    return '<span>-</span>';
}

function renderEvents(data) {
    const eventos = Array.isArray(data.eventos) ? data.eventos : [];
    state.paginas = data.paginas || 0;

    totalPill.textContent = `${data.total || 0} evento(s)`;
    pageLabel.textContent = state.paginas ? `Página ${data.pagina} de ${state.paginas}` : '';

    if (!eventos.length) {
        showEmpty('Nenhum evento encontrado', 'Não há registros para os filtros escolhidos.');
        return;
    }

    eventsBody.innerHTML = eventos
        .map((evento) => {
            const negado = evento.resultado === 'negado';
            // data-label: no celular cada linha vira um cartao e o rotulo da
            // coluna aparece ao lado do valor (ver historico.css).
            return `
                <tr class="${negado ? 'negado' : ''}">
                    <td class="audit-when" data-label="Data e hora"><span>${escapeHtml(formatDate(evento.data_hora))}</span></td>
                    <td data-label="Usuário"><span>${escapeHtml(evento.usuario?.nome || '-')}</span></td>
                    <td data-label="Cargo"><span>${escapeHtml(evento.cargo || 'fora da equipe')}</span></td>
                    <td data-label="Ação"><span>${escapeHtml(ACOES[evento.acao] || evento.acao)}</span></td>
                    <td data-label="Resultado"><span class="audit-result ${negado ? 'negado' : 'sucesso'}">${negado ? '⚠ Negado' : '✓ Sucesso'}</span></td>
                    <td data-label="Documento ou membro">${describeTarget(evento)}</td>
                    <td data-label="Equipe"><span>${escapeHtml(evento.equipe?.nome || '-')}</span></td>
                </tr>
            `;
        })
        .join('');

    emptyState.hidden = true;
    tableWrap.hidden = false;
    pagination.hidden = state.paginas <= 1;
    prevPageBtn.disabled = state.pagina <= 1;
    nextPageBtn.disabled = state.pagina >= state.paginas;
}

async function loadEvents() {
    showFeedback('');
    try {
        const response = await fetch(`${API_AUDITORIA}?${buildQuery()}`, { headers: authHeaders() });

        if (response.status === 401) {
            redirectToLogin();
            return;
        }
        if (response.status === 403) {
            totalPill.textContent = '0 eventos';
            filtersPanel.hidden = true;
            showEmpty(
                'Consulta não permitida',
                'O histórico de auditoria é visível para líder e supervisor, somente das próprias equipes.',
            );
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            // 400 (filtro invalido) e 422 (parametro fora do formato) trazem o motivo em `detail`.
            showFeedback(typeof data.detail === 'string' ? data.detail : 'Verifique os filtros informados.');
            return;
        }
        renderEvents(data);
    } catch (error) {
        console.error(error);
        showEmpty('Erro ao carregar o histórico', 'Verifique se o backend está ativo e se sua sessão continua válida.');
    }
}

function fillSelect(select, options) {
    options.forEach(({ value, label }) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    });
}

// Equipes e documentos do filtro: so os que o usuario pode auditar, para a
// lista nao oferecer uma opcao que a API recusaria com 403.
async function loadFilterOptions() {
    fillSelect(filterAction, Object.entries(ACOES).map(([value, label]) => ({ value, label })));

    const [overviewResponse, docsResponse] = await Promise.all([
        fetch(`${API_ROOT}/equipes/overview`, { headers: authHeaders() }),
        fetch(`${API_ROOT}/documentos/censurados`, { headers: authHeaders() }),
    ]);

    if (overviewResponse.status === 401 || docsResponse.status === 401) {
        redirectToLogin();
        return false;
    }

    if (overviewResponse.ok) {
        const overview = await overviewResponse.json();
        const userId = overview.usuario?.user_id;
        const equipes = (overview.equipes || []).filter((equipe) => {
            const eu = (equipe.membros_lista || []).find((membro) => membro.user_id === userId);
            return eu && eu.cargo_nivel >= NIVEL_MIN_AUDITORIA;
        });
        fillSelect(filterTeam, equipes.map((equipe) => ({ value: equipe.team_id, label: equipe.nome })));
        state.equipesAuditaveis = new Set(equipes.map((equipe) => equipe.team_id));
    }

    if (docsResponse.ok && state.equipesAuditaveis) {
        const docs = await docsResponse.json();
        const documentos = (docs.documentos || []).filter((doc) => state.equipesAuditaveis.has(doc.team_id));
        fillSelect(filterDoc, documentos.map((doc) => ({
            value: doc.doc_id,
            label: `${doc.nome_original} (${doc.equipe_nome})`,
        })));
    }
    return true;
}

filtersForm.addEventListener('submit', (event) => {
    event.preventDefault();
    state.pagina = 1;
    loadEvents();
});

clearFiltersBtn.addEventListener('click', () => {
    filtersForm.reset();
    state.pagina = 1;
    loadEvents();
});

prevPageBtn.addEventListener('click', () => {
    if (state.pagina > 1) {
        state.pagina -= 1;
        loadEvents();
    }
});

nextPageBtn.addEventListener('click', () => {
    if (state.pagina < state.paginas) {
        state.pagina += 1;
        loadEvents();
    }
});

async function init() {
    if (!window.AppShell.Sessao.getToken()) {
        redirectToLogin();
        return;
    }
    try {
        if (!(await loadFilterOptions())) {
            return;
        }
    } catch (error) {
        // Sem as opcoes de filtro a lista ainda funciona; so os selects ficam vazios.
        console.error(error);
    }

    // Vindo de um documento: ja abre filtrado por ele.
    const docInicial = new URLSearchParams(window.location.search).get('doc_id');
    if (docInicial && filterDoc.querySelector(`option[value="${CSS.escape(docInicial)}"]`)) {
        filterDoc.value = docInicial;
    }
    loadEvents();
}

init();
