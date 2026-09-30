// Shell interno do SafeMask (Fatia 3).
//
// Renderiza sidebar + topbar a partir de uma unica definicao de menu, aplica
// o guarda de cargo e gerencia menu movel e dropdown de usuario. Nao ha build
// step: o script e carregado direto pelas paginas internas.
//
// Uso em uma pagina interna:
//   <script src="../js/config.js"></script>
//   <script src="../js/session.js"></script>
//   <script src="../js/app-shell.js"></script>
//   <main class="content brand-main"> ... </main>
(() => {
    // As paginas vivem em profundidades diferentes (html/, html/documentos/,
    // html/equipes/), entao o menu usa caminhos absolutos. A base antes de
    // "/html/" e deduzida da URL atual porque a raiz de servico muda:
    // no Vercel a raiz e o repo ("/frontend/html/..."), mas servindo a pasta
    // frontend/ direto (dev local) seria "/html/...".
    const RAIZ = (() => {
        const caminho = window.location.pathname;
        const marca = caminho.indexOf('/html/');
        return marca > 0 ? caminho.slice(0, marca) : '';
    })();

    const BASE_HTML = `${RAIZ}/html`;
    const BASE_IMG = `${RAIZ}/images`;
    const LOGIN = `${BASE_HTML}/auth/login.html`;
    // A landing fica na raiz do repo, um nivel acima de frontend/. Servindo a
    // pasta frontend/ como raiz (dev local) ela nao existe, e o logout vai
    // para a propria tela de login.
    const LOGOUT = RAIZ.endsWith('/frontend') ? '/index.html' : LOGIN;

    const MENU = [
        { titulo: 'Documentos', grupo: true },
        { texto: 'Visao Geral', href: `${BASE_HTML}/dashboard.html`, cargo: 'membro' },
        { texto: 'Novo Upload', href: `${BASE_HTML}/documentos/censurar.html`, cargo: 'membro' },
        { texto: 'Documentos Censurados', href: `${BASE_HTML}/documentos/censurados.html`, cargo: 'membro' },
        { texto: 'Historico', href: null, cargo: 'membro' },

        { titulo: 'Equipes', grupo: true },
        { texto: 'Gerenciar Equipes', href: `${BASE_HTML}/equipes/equipes.html`, cargo: 'supervisor' },
        { texto: 'Acessar Equipe', href: `${BASE_HTML}/equipes/detalhe.html`, cargo: 'membro' },

        { titulo: 'Acessos', grupo: true },
        { texto: 'Usuarios da Equipe', href: null, cargo: 'supervisor' },
        { texto: 'Permissoes', href: null, cargo: 'lider' },
        { texto: 'Configuracoes', href: null, cargo: 'supervisor' },
    ];

    function ehAtiva(href) {
        if (!href) return false;
        const alvo = href.replace(/^\//, '');
        const atual = window.location.pathname.replace(/^\//, '');
        return atual === alvo;
    }

    function itemDoMenu(item, sessao) {
        if (item.grupo) {
            return `<p class="menu-title">${item.titulo}</p>`;
        }
        // Guarda de cargo: esconde em vez de apenas desabilitar, para nao
        // expor acoes que o usuario nao pode executar.
        if (!sessao.temCargoMinimo(item.cargo)) return '';

        const classes = ['menu-link'];
        if (ehAtiva(item.href)) classes.push('active');

        if (!item.href) {
            return `<span class="${classes.join(' ')} is-disabled" aria-disabled="true">${item.texto}</span>`;
        }
        return `<a href="${item.href}" class="${classes.join(' ')}">${item.texto}</a>`;
    }

    function sidebarHtml(sessao) {
        const itens = MENU.map((item) => itemDoMenu(item, sessao)).join('\n                    ');

        return `
        <aside class="sidebar" id="sidebar">
            <div class="brand">
                <img src="${BASE_IMG}/safemask-logo-transparente.png" alt="SafeMask" class="brand-logo">
                <div>
                    <p class="brand-kicker">Painel</p>
                    <h1>SafeMask</h1>
                </div>
            </div>
            <nav class="menu" aria-label="Navegacao principal">
                ${itens}
            </nav>
        </aside>`;
    }

    function topbarHtml(tituloPagina) {
        return `
        <header class="topbar">
            <button class="menu-toggle" id="menuToggle" aria-label="Abrir menu" aria-expanded="false">&#9776;</button>
            <nav class="crumb" aria-label="Breadcrumb">
                <span>SafeMask</span>
                <span class="crumb-sep">/</span>
                <span class="crumb-current">${tituloPagina}</span>
            </nav>

            <a href="${BASE_HTML}/documentos/censurar.html" class="cta-censor" id="btnCensurarDocumento">Censurar Documento</a>

            <div class="user-menu" id="userMenu">
                <button class="user-trigger" id="userTrigger" aria-haspopup="true" aria-expanded="false">
                    <span class="user-icon" id="userIcon" aria-hidden="true">U</span>
                    <span id="userName">Usuario</span>
                </button>
                <div class="dropdown" id="userDropdown">
                    <span class="dropdown-cargo" id="userCargo"></span>
                    <button class="dropdown-item" id="logoutBtn">Logout</button>
                </div>
            </div>
        </header>`;
    }

    function nomeDaPagina() {
        const titulo = (document.title || '').replace(/^SafeMask\s*[-–]\s*/, '').trim();
        return titulo || 'Painel';
    }

    function montar(sessao) {
        const shell = document.getElementById('appShell');
        const conteudo = document.getElementById('appContent');
        if (!shell || !conteudo) {
            console.warn('[app-shell] #appShell ou #appContent ausente; shell ignorado.');
            return;
        }

        // O <main> da pagina ja e o container do shell: apenas oinvolve-lo
        // preserva o conteudo e o CSS existentes sem mover o DOM do usuario.
        const wrapper = document.createElement('div');
        wrapper.className = 'dashboard-shell';
        wrapper.innerHTML = `${sidebarHtml(sessao)}
        <div class="main-wrap">${topbarHtml(nomeDaPagina())}</div>`;

        shell.replaceWith(wrapper);

        const mainWrap = wrapper.querySelector('.main-wrap');
        mainWrap.appendChild(conteudo);
    }

    function ligarEventos(sessao) {
        const sidebar = document.getElementById('sidebar');
        const menuToggle = document.getElementById('menuToggle');
        if (sidebar && menuToggle) {
            menuToggle.addEventListener('click', () => {
                const aberto = sidebar.classList.toggle('open');
                menuToggle.setAttribute('aria-expanded', aberto ? 'true' : 'false');
            });
        }

        const userMenu = document.getElementById('userMenu');
        const userTrigger = document.getElementById('userTrigger');
        const userDropdown = document.getElementById('userDropdown');
        if (userMenu && userTrigger && userDropdown) {
            userTrigger.addEventListener('click', (event) => {
                event.stopPropagation();
                const aberto = userDropdown.classList.toggle('open');
                userTrigger.setAttribute('aria-expanded', aberto ? 'true' : 'false');
            });
            document.addEventListener('click', (event) => {
                if (!userMenu.contains(event.target)) {
                    userDropdown.classList.remove('open');
                    userTrigger.setAttribute('aria-expanded', 'false');
                }
            });
        }

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) logoutBtn.addEventListener('click', () => sessao.logout(LOGOUT));

        const nome = document.getElementById('userName');
        const icone = document.getElementById('userIcon');
        const cargoEl = document.getElementById('userCargo');
        const nomeUsuario = sessao.getNome();
        if (nome) nome.textContent = nomeUsuario;
        if (icone) icone.textContent = nomeUsuario.charAt(0).toUpperCase();
        if (cargoEl) cargoEl.textContent = sessao.getCargo();
    }

    function iniciar() {
        const sessao = window.AppShell && window.AppShell.Sessao;
        if (!sessao) {
            console.error('[app-shell] session.js nao carregou antes de app-shell.js.');
            return;
        }
        sessao.exigirLogin(LOGIN);
        montar(sessao);
        ligarEventos(sessao);
    }

    // Monta de imediato quando os alvos ja foram lidos: os scripts das paginas
    // fazem `getElementById('userTrigger')` no topo do arquivo, e esperar o
    // DOMContentLoaded os deixaria null. O fallback so cobre carregamentos
    // tardios, em que o shell ainda nao esta no DOM.
    if (document.getElementById('appShell') && document.getElementById('appContent')) {
        iniciar();
    } else {
        document.addEventListener('DOMContentLoaded', iniciar);
    }
})();