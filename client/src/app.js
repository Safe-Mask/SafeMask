import { enviarLote, pedir, pedirArquivo, pedirJson, salvarToken, salvarUrlServico, sair, considerarServico, token, trocarSenha, urlServico, login, } from "./api";
import { USUARIO_DEMO, ativarDemo, desativarDemo, emModoDemo, visaoInicialDemo } from "./demo";
const CAMINHOS = {
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1 1 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    dashboard: '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    files: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    history: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "arrow-up-right": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
    lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    cloud: '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>',
    database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "chevron-left": '<path d="m15 18-6-6 6-6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M8 2v4"/><path d="M16 2v4"/><path d="M3 10h18"/>',
    scan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
    "eye-off": '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><path d="m2 2 20 20"/>',
    alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    building: '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    "panel-left": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/>',
    maximize: '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>',
    refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/>',
};
function icone(nome, tamanho = 17) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "icone");
    svg.setAttribute("width", String(tamanho));
    svg.setAttribute("height", String(tamanho));
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = CAMINHOS[nome];
    return svg;
}
function h(tag, props = {}, filhos = []) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
        if (k === "class")
            el.className = v;
        else if (k.startsWith("on"))
            el.addEventListener(k.slice(2), v);
        else if (v !== null && v !== undefined)
            el.setAttribute(k, String(v));
    }
    for (const f of filhos)
        if (f !== null && f !== undefined)
            el.append(f);
    return el;
}
function mostrarErro(caixa, mensagem) {
    caixa.textContent = mensagem;
    caixa.style.display = mensagem ? "block" : "none";
}
function nivelNome(nivel) {
    return ["Publico", "Interno", "Sensivel", "Restrito"][Math.min(3, Math.max(1, nivel))];
}
function riscoInfo(nivel) {
    if (nivel >= 4)
        return { rotulo: "Crítico", classe: "risco-critico" };
    if (nivel === 3)
        return { rotulo: "Alto", classe: "risco-alto" };
    if (nivel === 2)
        return { rotulo: "Médio", classe: "risco-medio" };
    return { rotulo: "Baixo", classe: "risco-baixo" };
}
function statusInfo(status) {
    const mapa = {
        AGUARDANDO: { rotulo: "Aguardando revisão", classe: "pill-ambar" },
        PROCESSANDO: { rotulo: "Processando", classe: "pill-azul" },
        CONCLUIDO: { rotulo: "Protegido", classe: "pill-verde" },
        ERRO: { rotulo: "Erro", classe: "pill-vermelho" },
    };
    return mapa[status] ?? { rotulo: status, classe: "pill-cinza" };
}
function resultadoClasse(resultado) {
    if (resultado === "negado")
        return "pill-vermelho";
    if (resultado === "falha")
        return "pill-ambar";
    return "pill-verde";
}
function tamanho(bytes) {
    if (bytes >= 1_048_576)
        return `${(bytes / 1_048_576).toFixed(1)} MB`;
    if (bytes >= 1024)
        return `${Math.round(bytes / 1024)} KB`;
    return `${bytes} B`;
}
function dataRelativa(iso) {
    if (!iso)
        return "";
    const data = new Date(iso);
    if (Number.isNaN(data.getTime()))
        return iso.slice(0, 16).replace("T", " ");
    const agora = new Date();
    const hora = data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    const mesmoDia = data.toDateString() === agora.toDateString();
    const ontem = new Date(agora);
    ontem.setDate(agora.getDate() - 1);
    if (mesmoDia)
        return `Hoje, ${hora}`;
    if (data.toDateString() === ontem.toDateString())
        return `Ontem, ${hora}`;
    return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}
function dataLonga() {
    return new Date()
        .toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })
        .toUpperCase();
}
function primeiroNome(nome) {
    return (nome || "Usuário").trim().split(/\s+/)[0];
}
function iniciais(nome) {
    const partes = (nome || "").trim().split(/\s+/).filter(Boolean);
    if (!partes.length)
        return "SM";
    return `${partes[0][0] ?? ""}${partes.length > 1 ? partes[partes.length - 1][0] : ""}`.toUpperCase();
}
function hostServico() {
    const url = urlServico();
    if (!url)
        return "Serviço local";
    try {
        return new URL(url).host;
    }
    catch {
        return url.replace(/^https?:\/\//, "");
    }
}
function baixar(arquivo, nome) {
    // <a download> funciona no webview do Tauri e também na dev do Vite.
    const url = URL.createObjectURL(arquivo);
    const a = h("a", { href: url, download: nome });
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}
async function baixarProtegido(path, nome) {
    // Bearer vai no header: <a href> puro nao leva o token e o download
    // seria barrado com 401.
    const blob = await pedirArquivo(path);
    baixar(blob, nome);
}
function pilula(rotulo, classe) {
    return h("span", { class: `pill ${classe}` }, [rotulo]);
}
// ------------------------------------------------------------- estado -----
let raiz;
let usuario = null;
let geracaoDocumentos = 0;
let visaoAtual = "documentos";
let conteudoAtual = null;
let caminhoAtualEl = null;
let filtroBusca = "";
let previewUrlAtual = null;
function revogarPreview() {
    if (previewUrlAtual) {
        URL.revokeObjectURL(previewUrlAtual);
        previewUrlAtual = null;
    }
}
export async function bootstrap() {
    raiz = document.getElementById("app");
    if (emModoDemo()) {
        const tela = visaoInicialDemo();
        if (tela === "login") {
            telaLogin();
            return;
        }
        usuario = USUARIO_DEMO;
        telaShell(tela);
        return;
    }
    if (!urlServico()) {
        telaPrimeiroUso();
        return;
    }
    if (!token()) {
        telaLogin();
        return;
    }
    try {
        usuario = await pedirJson("/auth/me");
    }
    catch (exc) {
        const erro = exc;
        if (erro.status === 401) {
            sair();
            telaLogin();
            return;
        }
        telaPrimeiroUso(erro.message);
        return;
    }
    if (usuario.precisa_trocar_senha) {
        telaTrocarSenha(usuario);
        return;
    }
    telaShell();
}
// ------------------------------------------------------------- 1o uso -----
function marcaAuth() {
    return h("div", { class: "marca-auth" }, [
        h("div", { class: "marca-simbolo" }, [icone("shield", 21)]),
        h("span", { class: "marca-nome" }, ["SafeMask"]),
    ]);
}
function telaPrimeiroUso(mensagemErro = "") {
    raiz.replaceChildren(h("div", { class: "tela-centro" }, [
        h("div", { class: "cartao-auth" }, [
            marcaAuth(),
            h("h1", {}, ["Conecte seu workspace"]),
            h("p", { class: "subtitulo" }, [
                "Informe o endereço do serviço central da sua empresa (o mesmo do painel de instalação).",
            ]),
            h("input", {
                id: "url-servico",
                type: "url",
                placeholder: "http://servidor-da-empresa:8000",
                value: mensagemErro && urlServico() ? urlServico() : "",
            }),
            h("button", {
                class: "primario",
                onclick: async (ev) => {
                    const botao = ev.target;
                    const caixaErro = document.getElementById("config-erro");
                    mostrarErro(caixaErro, "");
                    const valor = document.getElementById("url-servico").value;
                    if (!valor.startsWith("http")) {
                        mostrarErro(caixaErro, "Informe a URL completa (http://...:porta).");
                        return;
                    }
                    salvarUrlServico(valor);
                    botao.disabled = true;
                    botao.textContent = "Testando o serviço...";
                    if (await considerarServico()) {
                        telaLogin();
                    }
                    else {
                        mostrarErro(caixaErro, "Serviço não respondeu. Confira endereço/porta e o firewall.");
                        botao.disabled = false;
                        botao.textContent = "Conectar e continuar";
                    }
                },
            }, ["Conectar e continuar"]),
            h("div", { id: "config-erro", class: "erro" }),
            h("button", {
                type: "button",
                class: "botao-demo",
                onclick: () => {
                    ativarDemo();
                    void bootstrap();
                },
            }, ["Entrar em modo demonstração"]),
            h("p", { class: "mudo pequeno", style: "text-align:center;margin:0" }, [
                "Conheça as telas com dados fictícios, sem instalar o serviço.",
            ]),
        ]),
    ]));
}
// ---------------------------------------------------------------- login ---
function telaLogin() {
    document.getElementById("shell")?.remove();
    const demoAtivo = emModoDemo();
    raiz.replaceChildren(h("div", { class: "tela-centro" }, [
        h("div", { class: "cartao-auth" }, [
            marcaAuth(),
            h("h1", {}, ["Entrar no SafeMask"]),
            h("p", { class: "subtitulo" }, [
                demoAtivo ? "Ambiente de demonstração local — dados fictícios" : (urlServico() ?? ""),
            ]),
            demoAtivo ? h("div", { style: "display:flex;justify-content:center" }, [h("span", { class: "etiqueta-demo" }, ["Modo Demonstração"])]) : null,
            h("form", {
                onsubmit: async (ev) => {
                    ev.preventDefault();
                    const caixaErro = document.getElementById("login-erro");
                    mostrarErro(caixaErro, "");
                    const email = document.getElementById("login-email").value;
                    const senha = document.getElementById("login-senha").value;
                    try {
                        const corpo = await login(email, senha);
                        salvarToken(corpo.access_token);
                        usuario = corpo.user;
                        if (corpo.user.precisa_trocar_senha)
                            telaTrocarSenha(corpo.user);
                        else
                            telaShell();
                    }
                    catch (exc) {
                        mostrarErro(caixaErro, exc.message);
                    }
                },
            }, [
                h("input", {
                    id: "login-email",
                    type: "email",
                    placeholder: "E-mail",
                    required: "",
                    value: demoAtivo ? "admin@safemask.demo" : "",
                }),
                h("input", {
                    id: "login-senha",
                    type: "password",
                    placeholder: "Senha",
                    required: "",
                    value: demoAtivo ? "demo1234" : "",
                }),
                h("button", { class: "primario", type: "submit" }, ["Entrar"]),
            ]),
            h("div", { id: "login-erro", class: "erro" }),
            demoAtivo
                ? h("button", {
                    type: "button",
                    class: "link-suave",
                    onclick: () => {
                        desativarDemo();
                        sair();
                        void bootstrap();
                    },
                }, ["Sair do modo demonstração"])
                : null,
            h("p", { class: "mudo pequeno", style: "text-align:center;margin:0" }, [
                demoAtivo
                    ? "Clique em Entrar com qualquer e-mail/senha no modo demo."
                    : "Esqueceu a senha? Peça a recuperação ao admin do serviço.",
            ]),
        ]),
    ]));
}
// ------------------------------------------------------- troca de senha ---
function telaTrocarSenha(possivelUsuario) {
    document.getElementById("shell")?.remove();
    raiz.replaceChildren(h("div", { class: "tela-centro" }, [
        h("div", { class: "cartao-auth" }, [
            marcaAuth(),
            h("h1", {}, ["Troque sua senha"]),
            h("p", { class: "subtitulo" }, [
                `${possivelUsuario.email} entrou com uma senha provisória. Escolha uma senha definitiva (mínimo 8 caracteres).`,
            ]),
            h("input", { id: "troca-atual", type: "password", placeholder: "Senha provisória atual" }),
            h("input", { id: "troca-nova", type: "password", placeholder: "Nova senha" }),
            h("input", { id: "troca-nova2", type: "password", placeholder: "Repetir nova senha" }),
            h("button", {
                class: "primario",
                onclick: async () => {
                    const caixaErro = document.getElementById("troca-erro");
                    mostrarErro(caixaErro, "");
                    const atual = document.getElementById("troca-atual").value;
                    const nova = document.getElementById("troca-nova").value;
                    const nova2 = document.getElementById("troca-nova2").value;
                    if (nova.length < 8) {
                        mostrarErro(caixaErro, "A nova senha precisa ter no mínimo 8 caracteres.");
                        return;
                    }
                    if (nova !== nova2) {
                        mostrarErro(caixaErro, "As duas senhas novas não conferem.");
                        return;
                    }
                    try {
                        const corpo = await trocarSenha(atual, nova);
                        salvarToken(corpo.access_token);
                        usuario = corpo.user;
                        telaShell();
                    }
                    catch (exc) {
                        mostrarErro(caixaErro, exc.message);
                    }
                },
            }, ["Salvar senha e continuar"]),
            h("div", { id: "troca-erro", class: "erro" }),
        ]),
    ]));
}
const METADADOS_VISAO = {
    documentos: { titulo: "Documentos", caminho: "Documentos" },
    painel: { titulo: "Visão geral", caminho: "Visão geral" },
    equipes: { titulo: "Equipes", caminho: "Equipes" },
    auditoria: { titulo: "Trilha de auditoria", caminho: "Trilha de auditoria" },
};
function seletorVisao(visao, rotulo, iconeNome, contagemId) {
    return h("button", {
        class: `nav-item${visao === visaoAtual ? " ativo" : ""}`,
        "data-visao": visao,
        onclick: () => selecionarVisao(visao),
    }, [
        icone(iconeNome),
        h("span", {}, [rotulo]),
        contagemId ? h("span", { class: "nav-contagem", id: contagemId }, [""]) : null,
    ]);
}
function selecionarVisao(visao) {
    visaoAtual = visao;
    revogarPreview();
    document.querySelectorAll(".nav-item").forEach((botao) => {
        botao.classList.toggle("ativo", botao.dataset.visao === visao);
    });
    if (caminhoAtualEl)
        caminhoAtualEl.textContent = METADADOS_VISAO[visao].caminho;
    if (conteudoAtual)
        void carregarVisao(visao, conteudoAtual);
}
function aplicarFiltro() {
    document.querySelectorAll("[data-doc-nome]").forEach((linha) => {
        const nome = (linha.dataset.docNome ?? "").toLowerCase();
        linha.style.display = !filtroBusca || nome.includes(filtroBusca) ? "" : "none";
    });
}
async function atualizarContadores() {
    try {
        const lista = await pedirJson("/documentos/censurados");
        const contador = document.getElementById("contagem-documentos");
        if (contador)
            contador.textContent = String(lista.total);
    }
    catch {
        // contador e enfeite; nao interrompe a tela
    }
    try {
        const visao = await pedirJson("/equipes/overview");
        const contador = document.getElementById("contagem-equipes");
        if (contador)
            contador.textContent = String(visao.equipes.length);
    }
    catch {
        // idem
    }
}
function menuConta() {
    const demoAtivo = emModoDemo();
    const detalhes = h("details", { class: "conta-menu" }, [
        h("summary", {}, [
            h("span", { class: "avatar" }, [iniciais(usuario?.nome ?? "")]),
            h("span", { class: "conta-texto" }, [
                h("span", { class: "conta-nome" }, [usuario?.nome ?? "Usuário"]),
                h("span", { class: "conta-papel" }, [usuario?.email ?? ""]),
            ]),
            icone("chevron-down", 13),
        ]),
        h("div", { class: "conta-popover" }, [
            h("button", {
                onclick: () => {
                    sair();
                    telaLogin();
                },
            }, [icone("logout", 15), "Sair"]),
            demoAtivo
                ? h("button", {
                    onclick: () => {
                        desativarDemo();
                        sair();
                        void bootstrap();
                    },
                }, [icone("shield", 15), "Encerrar demonstração"])
                : null,
        ]),
    ]);
    return detalhes;
}
function telaShell(visaoInicial = "documentos") {
    visaoAtual = visaoInicial;
    filtroBusca = "";
    const demoAtivo = emModoDemo();
    const orgNome = demoAtivo ? "Acme Corporation" : "Sua empresa";
    const orgPlano = demoAtivo ? "Workspace Enterprise" : hostServico();
    const caminhoAtual = h("span", { class: "atual" }, [METADADOS_VISAO[visaoInicial].caminho]);
    caminhoAtualEl = caminhoAtual;
    const busca = h("input", {
        type: "search",
        placeholder: "Buscar no workspace...",
        "aria-label": "Buscar documentos",
        oninput: (ev) => {
            filtroBusca = ev.target.value.trim().toLowerCase();
            aplicarFiltro();
        },
    });
    const topo = h("header", { class: "topo" }, [
        h("div", { class: "topo-menu" }, [
            h("div", { class: "marca" }, [
                h("div", { class: "marca-simbolo" }, [icone("shield", 21)]),
                h("span", { class: "marca-nome" }, ["SafeMask"]),
            ]),
            h("div", { class: "org-seletor" }, [
                h("div", { class: "org-avatar" }, [icone("building", 16)]),
                h("div", { class: "org-texto" }, [
                    h("span", { class: "org-nome" }, [orgNome]),
                    h("span", { class: "org-plano" }, [orgPlano]),
                ]),
                icone("chevron-down", 13),
            ]),
            h("div", { class: "topo-espaco" }),
            h("div", { class: "ambiente" }, [
                h("div", { class: "ambiente-linha" }, [
                    h("span", { class: "ambiente-ponto" }),
                    h("span", { class: "ambiente-titulo" }, [demoAtivo ? "Ambiente de demonstração" : "Ambiente monitorado"]),
                ]),
                h("span", { class: "ambiente-detalhe" }, [
                    demoAtivo ? "Dados fictícios, sem servidor" : "Todas as fontes conectadas",
                ]),
            ]),
            h("div", { class: "topo-acoes" }, [
                demoAtivo ? h("span", { class: "etiqueta-demo" }, ["Modo Demonstração"]) : null,
                h("button", {
                    class: "acao-topo",
                    onclick: () => {
                        if (demoAtivo) {
                            alert("Modo demonstração: as configurações do serviço ficam simuladas.");
                            return;
                        }
                        telaPrimeiroUso();
                    },
                }, [icone("settings", 17), h("span", {}, ["Configurações"])]),
                h("button", {
                    class: "acao-topo",
                    onclick: () => alert("Central de ajuda: consulte docs/instalacao.md no repositório."),
                }, [icone("help", 17), h("span", {}, ["Central de ajuda"])]),
                h("div", { class: "divisor-vertical" }),
                menuConta(),
            ]),
        ]),
        h("div", { class: "topo-nav" }, [
            h("span", { class: "nav-secao" }, ["WORKSPACE"]),
            seletorVisao("painel", "Visão geral", "dashboard"),
            seletorVisao("documentos", "Documentos", "files", "contagem-documentos"),
            seletorVisao("equipes", "Equipes", "users", "contagem-equipes"),
            seletorVisao("auditoria", "Trilha de auditoria", "history"),
        ]),
    ]);
    const barra = h("div", { class: "barra-workspace" }, [
        h("div", { class: "caminho" }, [
            icone("panel-left", 17),
            h("span", {}, ["Workspace"]),
            h("span", { class: "separador" }, ["/"]),
            caminhoAtual,
        ]),
        h("label", { class: "busca-global" }, [
            icone("search", 15),
            busca,
            h("span", { class: "busca-atalho" }, ["⌘ K"]),
        ]),
        h("span", { class: "protecao-ativa" }, [icone("shield", 15), "Proteção ativa"]),
        h("button", {
            class: "icone",
            title: "Notificações",
            onclick: () => alert("Nenhuma notificação pendente."),
        }, [icone("bell", 18)]),
    ]);
    const conteudo = h("div", { class: "conteudo", id: "conteudo" });
    conteudoAtual = conteudo;
    raiz.replaceChildren(h("div", { class: "shell", id: "shell" }, [topo, barra, conteudo]));
    void carregarVisao(visaoInicial, conteudo);
    void atualizarContadores();
}
async function carregarVisao(visao, conteudo) {
    conteudo.replaceChildren(h("div", { class: "carregando" }, ["Carregando..."]));
    try {
        if (visao === "documentos")
            await telaDocumentos(conteudo);
        else if (visao === "painel")
            await telaPainel(conteudo);
        else if (visao === "equipes")
            await telaEquipes(conteudo);
        else
            await telaAuditoria(conteudo);
    }
    catch (exc) {
        const erro = exc;
        if (erro.status === 401) {
            sair();
            telaLogin();
            return;
        }
        if (typeof erro.message === "string" && erro.message.includes("Troque a senha") && usuario) {
            telaTrocarSenha(usuario);
            return;
        }
        conteudo.replaceChildren(h("div", { class: "erro" }, [erro.message]));
    }
}
// ------------------------------------------------------------ documentos ---
function linhaDocumento(doc, aoAbrir) {
    const risco = riscoInfo(doc.nivel_seguranca);
    const status = statusInfo(doc.status_processamento);
    const linha = h("tr", {
        class: "clicavel",
        "data-doc-nome": doc.nome_original.toLowerCase(),
        onclick: aoAbrir,
    }, [
        h("td", {}, [
            h("div", { class: "celula-arquivo" }, [
                h("div", { class: "formato" }, [(doc.extensao || "pdf").toUpperCase()]),
                h("div", { class: "celula-identificacao" }, [
                    h("span", { class: "celula-nome" }, [doc.nome_original]),
                    h("span", { class: "celula-pasta" }, [`${doc.equipe_nome} · Nível ${doc.nivel_seguranca}`]),
                ]),
            ]),
        ]),
        h("td", {}, [doc.equipe_nome]),
        h("td", {}, [
            h("div", { class: "celula-risco" }, [
                h("span", { class: `risco-nivel ${risco.classe}` }, [risco.rotulo]),
                h("span", { class: "risco-ocorrencias" }, [`Requer nível ${doc.nivel_seguranca}`]),
            ]),
        ]),
        h("td", {}, [pilula(status.rotulo, status.classe)]),
        h("td", { class: "celula-atualizado" }, [dataRelativa(doc.criado_em)]),
        h("td", { class: "celula-acao" }, [
            h("button", {
                class: "icone",
                title: "Abrir documento",
                onclick: (ev) => {
                    ev.stopPropagation();
                    aoAbrir();
                },
            }, [icone("arrow-up-right", 17)]),
        ]),
    ]);
    return linha;
}
async function telaDocumentos(conteudo) {
    revogarPreview();
    const geracao = ++geracaoDocumentos;
    const [lista, visao] = await Promise.all([
        pedirJson("/documentos/censurados"),
        pedirJson("/equipes/overview"),
    ]);
    const equipesGestao = visao.equipes.filter((equipe) => (equipe.cargo_nivel_usuario ?? 0) >= 2);
    const pendentes = lista.documentos.some((doc) => doc.status_processamento === "AGUARDANDO" || doc.status_processamento === "PROCESSANDO");
    const abrir = (docId) => {
        if (conteudoAtual)
            void telaRevisao(conteudoAtual, docId);
    };
    const linhas = lista.documentos.map((doc) => linhaDocumento(doc, () => abrir(doc.doc_id)));
    const painelUpload = h("div", { class: "bloco-upload", style: "display:none" }, [
        h("h3", {}, ["Enviar documentos para a fila"]),
        h("p", {}, ["Os PDFs entram na fila do serviço e aparecem na lista com o status do processamento."]),
        h("form", {
            onsubmit: async (ev) => {
                ev.preventDefault();
                const botao = ev.target.querySelector("button[type='submit']");
                const equipe = Number(document.getElementById("upload-equipe").value);
                const nivel = Number(document.getElementById("upload-nivel").value);
                const entrada = document.getElementById("upload-arquivos");
                const arquivos = Array.from(entrada.files ?? []);
                if (!arquivos.length) {
                    alert("Selecione ao menos um PDF.");
                    return;
                }
                botao.disabled = true;
                botao.textContent = "Enviando...";
                try {
                    const resposta = await enviarLote(equipe, nivel, arquivos);
                    alert(`${resposta.mensagem} Aceitos: ${resposta.total_aceito}/${resposta.total_recebido}.`);
                    entrada.value = "";
                    await telaDocumentos(conteudo);
                }
                catch (exc) {
                    alert(exc.message);
                    botao.disabled = false;
                    botao.textContent = "Enviar para a fila";
                }
            },
        }, [
            h("div", { class: "linha-form" }, [
                h("select", { id: "upload-equipe" }, equipesGestao.map((equipe) => h("option", { value: String(equipe.team_id) }, [equipe.nome]))),
                h("select", { id: "upload-nivel" }, [1, 2, 3, 4].map((nivel) => h("option", { value: String(nivel) }, [`N${nivel}`]))),
                h("input", {
                    id: "upload-arquivos",
                    type: "file",
                    accept: "application/pdf",
                    multiple: "",
                    style: "flex:1;min-width:220px",
                }),
                h("button", { class: "primario", type: "submit" }, [icone("plus", 15), "Enviar para a fila"]),
            ]),
        ]),
    ]);
    const barra = h("div", { class: "barra-documentos" }, [
        h("span", { class: "resumo" }, [
            `${lista.total} documento(s) nas suas equipes — o original nunca sai do servidor.`,
        ]),
        equipesGestao.length
            ? h("button", {
                onclick: () => {
                    painelUpload.style.display = painelUpload.style.display === "none" ? "block" : "none";
                },
            }, [icone("plus", 15), "Enviar documentos"])
            : null,
    ]);
    const tabela = h("div", { class: "cartao" }, [
        h("div", { class: "tabela-wrap" }, [
            h("table", { class: "tabela" }, [
                h("thead", {}, [
                    h("tr", {}, [
                        "Nome do documento", "Equipe", "Risco", "Status", "Atualizado", "",
                    ].map((titulo) => h("th", {}, [titulo]))),
                ]),
                h("tbody", {}, linhas),
            ]),
        ]),
        h("div", { class: "tabela-resumo" }, [
            h("span", {}, [`Exibindo ${lista.documentos.length} de ${lista.total} documentos`]),
            h("span", {}, [pendentes ? "Atualizando em tempo real enquanto houver fila" : "Atualizado em tempo real"]),
        ]),
    ]);
    conteudo.replaceChildren(barra, painelUpload, linhas.length
        ? tabela
        : h("div", { class: "cartao vazio" }, [
            icone("files", 26),
            h("strong", {}, ["Nenhum documento ainda"]),
            h("span", {}, ["Os documentos aparecem aqui após upload no admin ou ingestão da pasta base."]),
        ]));
    aplicarFiltro();
    if (pendentes) {
        window.setTimeout(() => {
            const botaoDocumentos = document.querySelector("[data-visao='documentos']");
            if (geracao === geracaoDocumentos && botaoDocumentos?.classList.contains("ativo")) {
                void telaDocumentos(conteudo);
            }
        }, 5000);
    }
}
// --------------------------------------------------------------- revisao ---
async function telaRevisao(conteudo, docId) {
    revogarPreview();
    conteudo.replaceChildren(h("div", { class: "carregando" }, ["Abrindo documento..."]));
    if (caminhoAtualEl)
        caminhoAtualEl.textContent = "Documentos / Revisão";
    const detalhe = await pedirJson(`/documentos/censurados/${docId}`);
    let previewErro = "";
    let url = "";
    try {
        const blob = await pedirArquivo(`/documentos/censurados/${docId}/arquivo`);
        if (blob.size > 0) {
            url = URL.createObjectURL(blob);
            previewUrlAtual = url;
        }
        else {
            previewErro = "O serviço não retornou o arquivo da versão protegida.";
        }
    }
    catch (exc) {
        previewErro = exc.message;
    }
    const risco = riscoInfo(detalhe.nivel_seguranca);
    const status = statusInfo(detalhe.status_processamento);
    const voltar = () => {
        if (conteudoAtual)
            void telaDocumentos(conteudoAtual);
    };
    const acoes = h("div", { class: "revisao-acoes" }, [
        h("button", {
            onclick: async (ev) => {
                const botao = ev.currentTarget;
                botao.disabled = true;
                try {
                    await baixarProtegido(`/documentos/censurados/${detalhe.doc_id}/arquivo`, `${detalhe.nome_original}.${detalhe.extensao || "pdf"}`);
                }
                catch (exc) {
                    alert(exc.message);
                }
                finally {
                    botao.disabled = false;
                }
            },
        }, [icone("download", 16), "Baixar versão protegida"]),
        detalhe.pode_descensura_parcial
            ? h("button", {
                class: "primario",
                onclick: async (ev) => {
                    const botao = ev.currentTarget;
                    botao.disabled = true;
                    try {
                        await baixarProtegido(`/documentos/${detalhe.doc_id}/parcial`, `${detalhe.nome_original}_parcial.${detalhe.extensao || "pdf"}`);
                    }
                    catch (exc) {
                        alert(exc.message);
                    }
                    finally {
                        botao.disabled = false;
                    }
                },
            }, [icone("shield", 16), "Pedir versão parcial"])
            : null,
    ]);
    const cabecalho = h("div", { class: "revisao-cabecalho" }, [
        h("div", {}, [
            h("button", { class: "revisao-voltar", onclick: voltar }, [icone("arrow-left", 13), "Voltar para documentos"]),
            h("h2", {}, [detalhe.nome_original]),
            h("div", { class: "revisao-metadados" }, [
                h("span", {}, [`${detalhe.equipe.nome ?? "Sem equipe"} · Nível ${detalhe.nivel_seguranca} (${nivelNome(detalhe.nivel_seguranca)})`]),
                h("span", { class: "separador" }, ["·"]),
                h("span", {}, [`${tamanho(detalhe.tamanho_bytes)} · ${(detalhe.extensao || "pdf").toUpperCase()}`]),
                pilula(status.rotulo, status.classe),
                pilula(`Risco ${risco.rotulo}`, risco.classe === "risco-critico" ? "pill-vermelho" : risco.classe === "risco-alto" ? "pill-ambar" : "pill-cinza"),
            ]),
        ]),
        acoes,
    ]);
    const etapas = h("div", { class: "etapas" }, [
        h("div", { class: "etapas-lista" }, [
            h("div", { class: "etapa feita" }, [
                h("span", { class: "etapa-marcador" }, [icone("check", 11)]),
                h("span", {}, ["Análise concluída"]),
                h("span", { class: "chevron" }, [icone("chevron-right", 12)]),
            ]),
            h("div", { class: "etapa ativa" }, [
                h("span", { class: "etapa-marcador" }, ["2"]),
                h("span", {}, ["Revisar documento"]),
                h("span", { class: "chevron" }, [icone("chevron-right", 12)]),
            ]),
            h("div", { class: "etapa" }, [
                h("span", { class: "etapa-marcador" }, ["3"]),
                h("span", {}, ["Exportar cópia protegida"]),
            ]),
        ]),
        h("span", { class: "etapas-salvo" }, [icone("cloud", 13), "Somente leitura"]),
    ]);
    const preview = url
        ? h("object", { data: url, type: "application/pdf", "aria-label": "Prévia da versão protegida" }, [
            h("div", { class: "preview-vazio" }, [
                icone("files", 30),
                h("strong", {}, ["Prévia não suportada neste webview"]),
                h("p", {}, ["Use o botão “Baixar versão protegida” para abrir o PDF no leitor do sistema."]),
            ]),
        ])
        : h("div", { class: "preview-vazio" }, [
            icone("alert", 28),
            h("strong", {}, ["Prévia indisponível"]),
            h("p", {}, [previewErro || "Não foi possível carregar a versão protegida."]),
        ]);
    const visualizador = h("div", { class: "visualizador" }, [
        h("div", { class: "visualizador-barra" }, [
            h("div", { class: "abas" }, [
                h("button", { class: "aba ativa" }, ["Prévia protegida"]),
                h("button", { class: "aba", onclick: () => alert("Os metadados completos estão no painel à direita.") }, ["Metadados"]),
            ]),
            h("div", { class: "revisao-metadados" }, [
                h("span", { class: "mono" }, ["100%"]),
                icone("maximize", 15),
            ]),
        ]),
        h("div", { class: "visualizador-corpo" }, [
            h("div", { class: "pagina-preview" }, [preview]),
        ]),
        h("div", { class: "visualizador-rodape" }, [
            h("span", {}, ["Prévia da versão censurada conforme o seu cargo."]),
            h("span", {}, [`Atualizado ${dataRelativa(detalhe.criado_em)}`]),
        ]),
    ]);
    const ficha = h("div", { class: "ficha" }, [
        h("div", { class: "ficha-linha" }, [h("span", { class: "ficha-rotulo" }, ["Equipe"]), h("span", { class: "ficha-valor" }, [detalhe.equipe.nome ?? "—"])]),
        h("div", { class: "ficha-linha" }, [h("span", { class: "ficha-rotulo" }, ["Nível de segurança"]), h("span", { class: "ficha-valor" }, [`N${detalhe.nivel_seguranca} · ${nivelNome(detalhe.nivel_seguranca)}`])]),
        h("div", { class: "ficha-linha" }, [h("span", { class: "ficha-rotulo" }, ["Seu cargo"]), h("span", { class: "ficha-valor" }, [detalhe.cargo_usuario ? `${detalhe.cargo_usuario.nome} (N${detalhe.cargo_usuario.nivel})` : "Sem acesso"])]),
        h("div", { class: "ficha-linha" }, [h("span", { class: "ficha-rotulo" }, ["Autor"]), h("span", { class: "ficha-valor" }, [detalhe.autor_nome ?? "—"])]),
        h("div", { class: "ficha-linha" }, [h("span", { class: "ficha-rotulo" }, ["Tamanho"]), h("span", { class: "ficha-valor" }, [tamanho(detalhe.tamanho_bytes)])]),
        h("div", { class: "ficha-linha" }, [h("span", { class: "ficha-rotulo" }, ["Criado em"]), h("span", { class: "ficha-valor" }, [dataRelativa(detalhe.criado_em)])]),
        h("div", { class: "ficha-linha" }, [h("span", { class: "ficha-rotulo" }, ["Chave"]), h("span", { class: "ficha-valor mono" }, [detalhe.chave_criptografica])]),
    ]);
    const painel = h("div", { class: "cartao painel-protecao" }, [
        h("div", { class: "abas" }, [
            h("button", { class: "aba ativa" }, ["Documento"]),
            h("button", { class: "aba", onclick: voltar }, ["Histórico"]),
        ]),
        h("div", { class: "painel-corpo" }, [
            h("div", { class: "destaque-verde" }, [
                icone("shield", 16),
                h("div", {}, [
                    h("div", { class: "titulo" }, ["Documento protegido no servidor"]),
                    h("div", { class: "detalhe" }, [`Nível ${detalhe.nivel_seguranca} · ${nivelNome(detalhe.nivel_seguranca)}`]),
                ]),
            ]),
            ficha,
            h("div", { class: "painel-divisor" }),
            h("div", {}, [
                h("div", { class: "cabecalho-secao", style: "margin-bottom:9px" }, [
                    h("h3", {}, ["Ações permitidas"]),
                ]),
                h("div", { class: "metodos" }, [
                    h("div", { class: "metodo ativo" }, [
                        h("span", { class: "metodo-radio" }),
                        h("div", { class: "metodo-texto" }, [
                            h("span", { class: "metodo-nome" }, ["Versão protegida"]),
                            h("span", { class: "metodo-detalhe" }, ["Dados acima do seu nível permanecem cobertos"]),
                        ]),
                    ]),
                    detalhe.pode_descensura_parcial
                        ? h("div", { class: "metodo" }, [
                            h("span", { class: "metodo-radio" }),
                            h("div", { class: "metodo-texto" }, [
                                h("span", { class: "metodo-nome" }, ["Versão parcial"]),
                                h("span", { class: "metodo-detalhe" }, ["Revela apenas os dados do seu cargo"]),
                            ]),
                        ])
                        : null,
                    detalhe.pode_descensurar
                        ? h("div", { class: "metodo" }, [
                            h("span", { class: "metodo-radio" }),
                            h("div", { class: "metodo-texto" }, [
                                h("span", { class: "metodo-nome" }, ["Original integral"]),
                                h("span", { class: "metodo-detalhe" }, ["Seu cargo permite ver o original"]),
                            ]),
                        ])
                        : null,
                ]),
            ]),
            h("div", { class: "aviso-privacidade" }, [
                icone("lock", 12),
                h("span", {}, ["O arquivo original permanece no servidor. Você recebe apenas a versão permitida pelo seu cargo."]),
            ]),
        ]),
    ]);
    conteudo.replaceChildren(cabecalho, etapas, h("div", { class: "grade-revisao" }, [visualizador, painel]), h("div", { class: "rodape" }, [
        h("span", { class: "seguranca" }, [icone("shield", 13), "Somente pessoas autorizadas podem visualizar os dados originais."]),
        h("span", {}, ["SafeMask · Seus dados ficam onde devem estar."]),
    ]));
}
// --------------------------------------------------------------- painel ---
function indicador(rotulo, valor, tendencia, classe, iconeNome) {
    return h("div", { class: "indicador" }, [
        h("div", { class: "indicador-titulo" }, [
            h("span", {}, [rotulo]),
            h("span", { style: "color:var(--primario)" }, [icone(iconeNome, 17)]),
        ]),
        h("div", { class: "indicador-valor" }, [
            h("strong", {}, [String(valor)]),
            h("span", { class: `indicador-tendencia ${classe}` }, [tendencia]),
        ]),
    ]);
}
function eventoTexto(evento) {
    const nome = evento.usuario?.nome ?? "Serviço";
    const doc = evento.documento?.nome ?? "documento";
    const equipe = evento.equipe?.nome ?? "Workspace";
    const acoes = {
        ver_original: "tentou abrir o original de",
        ver_censurado: "abriu a versão protegida de",
        ver_parcial: "pediu a versão parcial de",
        upload_documento: "enviou",
        upload_lote: "enviou um lote de documentos",
        processar_documento: "concluiu a varredura de",
        listar_documentos: "consultou a lista de documentos",
    };
    if (evento.acao === "processar_documento") {
        return { titulo: "Varredura de documentos concluída", contexto: `${equipe} · ${evento.resultado}` };
    }
    const acao = acoes[evento.acao] ?? evento.acao;
    if (evento.resultado === "negado") {
        return { titulo: `${nome} teve acesso negado`, contexto: `${equipe} · ${acao} ${doc}` };
    }
    return { titulo: `${nome} ${acao}`, contexto: `${equipe} · ${doc}` };
}
function iconeEvento(evento) {
    if (evento.acao === "processar_documento")
        return "refresh";
    if (evento.resultado === "negado")
        return "alert";
    if (evento.acao === "upload_documento" || evento.acao === "upload_lote")
        return "plus";
    return "shield";
}
async function telaPainel(conteudo) {
    revogarPreview();
    const [visao, lista] = await Promise.all([
        pedirJson("/dashboard/overview"),
        pedirJson("/documentos/censurados"),
    ]);
    let metricas = null;
    try {
        metricas = await pedirJson("/dashboard/metricas");
    }
    catch (exc) {
        if (exc.status !== 403)
            throw exc;
    }
    let eventos = [];
    try {
        const pagina = await pedirJson("/auditoria?pagina=1&por_pagina=3");
        eventos = pagina.eventos;
    }
    catch {
        // membro comum nao audita: o cartao de atividade fica vazio
    }
    const statusPorDoc = new Map(lista.documentos.map((doc) => [doc.doc_id, doc.status_processamento]));
    const pendentes = lista.documentos.filter((doc) => doc.status_processamento === "AGUARDANDO" || doc.status_processamento === "PROCESSANDO").length;
    const totalTipos = metricas ? metricas.top_tipos.reduce((soma, item) => soma + item.quantidade, 0) : 0;
    const apresentacao = h("div", { class: "apresentacao" }, [
        h("div", {}, [
            h("div", { class: "data" }, [dataLonga()]),
            h("h2", {}, [`Tudo sob controle, ${primeiroNome(visao.usuario.nome)}.`]),
            h("p", { class: "descricao" }, ["Acompanhe a proteção dos seus documentos em um só lugar."]),
        ]),
        h("div", { class: "acoes-apresentacao" }, [
            h("button", {}, [icone("calendar", 16), "Últimos 7 dias"]),
            h("button", { class: "primario", onclick: () => selecionarVisao("documentos") }, [icone("plus", 16), "Analisar documentos"]),
        ]),
    ]);
    const indicadores = h("div", { class: "indicadores" }, [
        indicador("Documentos na rede", visao.metrics.total_documentos, `${visao.metrics.total_equipes} equipe(s)`, "neutra", "files"),
        indicador("Documentos protegidos", visao.metrics.documentos_censurados, `${visao.metrics.taxa_censura}% da rede`, "", "shield"),
        indicador("Aguardando revisão", pendentes, `${visao.metrics.documentos_nivel_alto} de alto risco`, "alerta", "scan"),
        indicador("Dados mascarados", metricas ? totalTipos : "—", metricas ? "ocorrências fichadas" : "restrito ao admin", metricas ? "" : "neutra", "eye-off"),
    ]);
    const porNivel = metricas?.documentos.por_nivel ?? {
        "1": lista.documentos.filter((doc) => doc.nivel_seguranca === 1).length,
        "2": lista.documentos.filter((doc) => doc.nivel_seguranca === 2).length,
        "3": lista.documentos.filter((doc) => doc.nivel_seguranca === 3).length,
        "4": lista.documentos.filter((doc) => doc.nivel_seguranca === 4).length,
    };
    const totalNiveis = Object.values(porNivel).reduce((soma, valor) => soma + valor, 0) || 1;
    const coresNivel = ["var(--azul)", "var(--verde)", "var(--ambar)", "var(--vermelho)"];
    const linhasNivel = [1, 2, 3, 4].map((nivel) => {
        const quantidade = Number(porNivel[String(nivel)] ?? 0);
        return h("div", { class: "tipo-linha" }, [
            h("span", { class: "tipo-marcador", style: `background:${coresNivel[nivel - 1]}` }),
            h("span", { class: "tipo-nome" }, [`N${nivel} · ${nivelNome(nivel)}`]),
            h("span", { class: "tipo-quantidade" }, [String(quantidade)]),
            h("span", { class: "tipo-percentual" }, [`${Math.round((quantidade / totalNiveis) * 100)}%`]),
        ]);
    });
    const analise = h("div", { class: "grade-analise" }, [
        h("div", { class: "cartao" }, [
            h("div", { class: "cartao-corpo" }, [
                h("div", { class: "cabecalho-secao" }, [
                    h("div", {}, [
                        h("h3", {}, ["Documentos por nível de proteção"]),
                        h("p", {}, ["Distribuição dos documentos ativos nas equipes que você acessa"]),
                    ]),
                    h("button", { class: "link", onclick: () => selecionarVisao("documentos") }, ["Ver documentos →"]),
                ]),
                h("div", { class: "distribuicao" }, [1, 2, 3, 4].map((nivel) => {
                    const quantidade = Number(porNivel[String(nivel)] ?? 0);
                    return h("span", { style: `width:${(quantidade / totalNiveis) * 100}%;background:${coresNivel[nivel - 1]}` });
                })),
                h("div", { class: "lista-tipos" }, linhasNivel),
            ]),
        ]),
        h("div", { class: "cartao" }, [
            h("div", { class: "cartao-corpo" }, [
                h("div", { class: "cabecalho-secao" }, [
                    h("div", {}, [h("h3", {}, ["Dados sensíveis identificados"])]),
                    icone("help", 15),
                ]),
                metricas
                    ? h("div", { class: "total-sensiveis" }, [
                        h("strong", {}, [String(totalTipos)]),
                        h("span", {}, ["ocorrências na rede"]),
                    ])
                    : h("p", { class: "mudo pequeno" }, ["Métricas administrativas disponíveis para supervisores e líderes."]),
                metricas && metricas.top_tipos.length
                    ? h("div", { class: "lista-tipos" }, metricas.top_tipos.map((item, indice) => {
                        const percentual = totalTipos ? Math.round((item.quantidade / totalTipos) * 100) : 0;
                        return h("div", { class: "tipo-linha" }, [
                            h("span", { class: "tipo-marcador", style: `background:${coresNivel[Math.min(3, indice)]}` }),
                            h("span", { class: "tipo-nome" }, [item.tipo]),
                            h("span", { class: "tipo-quantidade" }, [String(item.quantidade)]),
                            h("span", { class: "tipo-percentual" }, [`${percentual}%`]),
                        ]);
                    }))
                    : h("p", { class: "mudo pequeno" }, ["Nenhum dado sensível fichado ainda."]),
            ]),
        ]),
    ]);
    const recentes = visao.documentos_recentes.slice(0, 5);
    const tabelaRecentes = h("div", { class: "cartao" }, [
        h("div", { class: "cartao-corpo", style: "padding-bottom:0" }, [
            h("div", { class: "cabecalho-secao" }, [
                h("div", { style: "display:flex;align-items:center;gap:9px" }, [
                    h("h3", {}, ["Documentos recentes"]),
                    h("span", { class: "pill pill-cinza sem-ponto" }, [`${pendentes} pendentes`]),
                ]),
                h("div", { style: "display:flex;align-items:center;gap:12px" }, [
                    h("button", { class: "link", onclick: () => selecionarVisao("documentos") }, ["Ver todos os documentos →"]),
                ]),
            ]),
        ]),
        h("div", { class: "tabela-wrap" }, [
            h("table", { class: "tabela" }, [
                h("thead", {}, [
                    h("tr", {}, ["Nome do documento", "Equipe", "Risco", "Status", "Atualizado", ""].map((titulo) => h("th", {}, [titulo]))),
                ]),
                h("tbody", {}, recentes.map((doc) => {
                    const risco = riscoInfo(doc.nivel_seguranca);
                    const status = statusInfo(statusPorDoc.get(doc.doc_id) ?? "CONCLUIDO");
                    return h("tr", {
                        class: "clicavel",
                        onclick: () => {
                            if (conteudoAtual)
                                void telaRevisao(conteudoAtual, doc.doc_id);
                        },
                    }, [
                        h("td", {}, [
                            h("div", { class: "celula-arquivo" }, [
                                h("div", { class: "formato" }, [(doc.extensao || "pdf").toUpperCase()]),
                                h("div", { class: "celula-identificacao" }, [
                                    h("span", { class: "celula-nome" }, [doc.nome_original]),
                                    h("span", { class: "celula-pasta" }, [`Nível ${doc.nivel_seguranca}`]),
                                ]),
                            ]),
                        ]),
                        h("td", {}, [doc.equipe_nome]),
                        h("td", {}, [h("span", { class: `risco-nivel ${risco.classe}` }, [risco.rotulo])]),
                        h("td", {}, [pilula(status.rotulo, status.classe)]),
                        h("td", { class: "celula-atualizado" }, [dataRelativa(doc.criado_em)]),
                        h("td", { class: "celula-acao" }, [icone("arrow-up-right", 17)]),
                    ]);
                })),
            ]),
        ]),
        h("div", { class: "tabela-resumo" }, [
            h("span", {}, [`Exibindo ${recentes.length} de ${visao.metrics.total_documentos} documentos`]),
            h("span", {}, ["Atualizado em tempo real"]),
        ]),
    ]);
    const atividade = h("div", { class: "cartao" }, [
        h("div", { class: "cartao-corpo" }, [
            h("div", { class: "cabecalho-secao" }, [
                h("h3", {}, ["Atividade recente"]),
                h("button", { class: "link", onclick: () => selecionarVisao("auditoria") }, ["Ver auditoria →"]),
            ]),
            eventos.length
                ? h("div", { class: "lista-eventos" }, eventos.map((evento) => {
                    const texto = eventoTexto(evento);
                    return h("div", { class: "evento" }, [
                        h("div", { class: "evento-simbolo" }, [icone(iconeEvento(evento), 14)]),
                        h("div", { class: "evento-detalhes" }, [
                            h("span", { class: "evento-titulo" }, [texto.titulo]),
                            h("span", { class: "evento-contexto" }, [texto.contexto]),
                        ]),
                        h("span", { class: "evento-hora" }, [dataRelativa(evento.data_hora)]),
                    ]);
                }))
                : h("p", { class: "mudo pequeno" }, ["Sem eventos visíveis para o seu cargo."]),
        ]),
    ]);
    const politica = h("div", { class: "politica" }, [
        h("div", { class: "politica-topo" }, [
            icone("shield", 21),
            h("span", { class: "politica-selo" }, ["POLÍTICA ATIVA"]),
        ]),
        h("h3", {}, ["Privacidade por padrão."]),
        h("p", {}, [
            metricas
                ? `Sua política LGPD monitora ${metricas.top_tipos.length} tipos de dados sensíveis em todas as fontes conectadas.`
                : "Sua política LGPD monitora dados sensíveis em todas as fontes conectadas.",
        ]),
        h("button", { class: "link", style: "justify-content:flex-start;color:var(--verde-claro);padding:0", onclick: () => selecionarVisao("equipes") }, ["Gerenciar políticas →"]),
    ]);
    conteudo.replaceChildren(apresentacao, indicadores, analise, tabelaRecentes, h("div", { class: "grade-atividade" }, [atividade, politica]), h("div", { class: "rodape" }, [
        h("span", {}, ["SafeMask · Seus dados ficam onde devem estar. Seguros."]),
        h("span", { class: "seguranca" }, [icone("lock", 10), "Criptografia ponta a ponta"]),
    ]));
}
// -------------------------------------------------------------- equipes ---
async function telaEquipes(conteudo) {
    revogarPreview();
    const visao = await pedirJson("/equipes/overview");
    const criarEquipe = h("div", { class: "cartao" }, [
        h("details", { style: "padding:18px 20px" }, [
            h("summary", { style: "cursor:pointer;font-size:11px;font-weight:600;color:var(--mudo)" }, ["Criar nova equipe"]),
            h("div", { class: "linha-form", style: "margin-top:10px" }, [
                h("input", { id: "equipe-nome", placeholder: "Nome da equipe", style: "flex:1;min-width:220px" }),
                h("button", {
                    class: "primario",
                    onclick: async (ev) => {
                        const botao = ev.target;
                        const nome = document.getElementById("equipe-nome").value.trim();
                        if (!nome)
                            return;
                        botao.disabled = true;
                        try {
                            await pedirJson("/equipes", { corpo: { nome } });
                            await telaEquipes(conteudo);
                        }
                        catch (exc) {
                            alert(exc.message);
                            botao.disabled = false;
                        }
                    },
                }, ["Criar equipe"]),
            ]),
        ]),
    ]);
    const cartoes = visao.equipes.map((equipe) => {
        const souLider = equipe.cargo_usuario === "lider";
        const membros = equipe.membros_lista.map((m) => h("tr", {}, [
            h("td", {}, [m.nome]),
            h("td", { class: "mudo" }, [m.email]),
            h("td", {}, [h("span", { class: `etiqueta nivel-${Math.min(3, m.cargo_nivel)}` }, [m.cargo_nome])]),
            souLider
                ? h("td", { class: "celula-acao" }, [
                    h("button", {
                        class: "icone",
                        title: "Alterar cargo",
                        onclick: async () => {
                            const cargo = prompt(`Novo cargo de ${m.nome} (lider/supervisor/membro):`, m.cargo_nome);
                            if (!cargo)
                                return;
                            try {
                                await pedir(`/equipes/${equipe.team_id}/membros/${m.user_id}`, { metodo: "PATCH", corpo: { cargo } });
                                await telaEquipes(conteudo);
                            }
                            catch (exc) {
                                alert(exc.message);
                            }
                        },
                    }, [icone("settings", 15)]),
                    h("button", {
                        class: "icone perigo",
                        title: "Remover membro",
                        onclick: async () => {
                            if (!confirm(`Remover ${m.nome} de ${equipe.nome}?`))
                                return;
                            try {
                                await pedir(`/equipes/${equipe.team_id}/membros/${m.user_id}`, { metodo: "DELETE" });
                                await telaEquipes(conteudo);
                            }
                            catch (exc) {
                                alert(exc.message);
                            }
                        },
                    }, [icone("logout", 15)]),
                ])
                : h("td"),
        ]));
        const addMembro = h("form", {
            class: "linha-form",
            onsubmit: async (ev) => {
                ev.preventDefault();
                const entrada = ev.target.querySelector("input");
                if (!entrada.value)
                    return;
                try {
                    await pedirJson(`/equipes/${equipe.team_id}/membros`, { corpo: { email: entrada.value } });
                    await telaEquipes(conteudo);
                }
                catch (exc) {
                    alert(exc.message);
                }
            },
        }, [
            h("input", { placeholder: "E-mail de quem vai entrar", style: "flex:1;min-width:220px" }),
            souLider ? h("button", { type: "submit" }, ["Adicionar membro"]) : h("span"),
        ]);
        const politica = h("details", {}, [
            h("summary", {}, ["Política de níveis (admin da equipe)"]),
            h("p", { class: "mudo pequeno", style: "margin:8px 0" }, [
                "Tipo → nível mínimo exigido de quem pede versão mais aberta (só tipos informados mudam).",
            ]),
            h("div", { class: "linha-form" }, [
                h("input", { placeholder: "ex.: TELEFONE", style: "width:40%;min-width:140px", id: `politica-tipo-${equipe.team_id}` }),
                h("input", { placeholder: "nível (1-3)", style: "width:25%;min-width:100px", id: `politica-nivel-${equipe.team_id}` }),
                h("button", {
                    onclick: async () => {
                        const tipo = document.getElementById(`politica-tipo-${equipe.team_id}`).value.trim().toUpperCase();
                        const nivel = Number(document.getElementById(`politica-nivel-${equipe.team_id}`).value);
                        if (!tipo || nivel < 1 || nivel > 3) {
                            alert("Informe o tipo e um nível de 1 a 3.");
                            return;
                        }
                        try {
                            await pedir(`/equipes/${equipe.team_id}/politica-niveis`, { metodo: "PUT", corpo: { niveis: { [tipo]: nivel } } });
                            alert("Política atualizada.");
                        }
                        catch (exc) {
                            alert(exc.message);
                        }
                    },
                }, ["Aplicar"]),
            ]),
        ]);
        return h("div", { class: "cartao cartao-equipe" }, [
            h("div", { class: "equipe-cabecalho" }, [
                h("div", {}, [
                    h("h3", {}, [equipe.nome]),
                    h("p", {}, [equipe.descricao ?? "Equipe da organização"]),
                ]),
                h("div", { class: "equipe-tags" }, [
                    h("span", { class: "pill pill-cinza sem-ponto" }, [`${equipe.membros} membro(s)`]),
                    h("span", { class: "pill pill-cinza sem-ponto" }, [`${equipe.documentos} doc(s)`]),
                    equipe.cargo_usuario
                        ? h("span", { class: "pill pill-verde" }, [`Seu cargo: ${equipe.cargo_usuario}`])
                        : h("span", { class: "pill pill-vermelho" }, ["Sem acesso"]),
                ]),
            ]),
            h("div", { class: "tabela-wrap" }, [
                h("table", { class: "tabela" }, [
                    h("thead", {}, [h("tr", {}, ["Nome", "E-mail", "Cargo", souLider ? "Ações" : ""].map((t) => h("th", {}, [t])))]),
                    h("tbody", {}, membros),
                ]),
            ]),
            addMembro,
            souLider ? politica : h("span"),
        ]);
    });
    conteudo.replaceChildren(criarEquipe, ...cartoes);
}
// ------------------------------------------------------------ auditoria ---
async function telaAuditoria(conteudo, pagina = 1) {
    revogarPreview();
    const dados = await pedirJson(`/auditoria?pagina=${pagina}&por_pagina=20`);
    const linhas = dados.eventos.map((ev) => h("tr", {}, [
        h("td", { class: "mudo" }, [dataRelativa(ev.data_hora)]),
        h("td", {}, [ev.acao]),
        h("td", {}, [pilula(ev.resultado, resultadoClasse(ev.resultado))]),
        h("td", {}, [ev.usuario?.nome ?? "—"]),
        h("td", {}, [ev.documento?.nome ?? "—"]),
        h("td", { class: "mudo mono" }, [ev.ip_origem ?? "—"]),
    ]));
    const cabecalho = h("div", { class: "barra-documentos" }, [
        h("span", { class: "resumo" }, [
            `${dados.total} evento(s) nas equipes que você audita — página ${dados.pagina}/${dados.paginas || 1}.`,
        ]),
        h("button", {
            onclick: async () => await baixarProtegido("/auditoria/exportar", "auditoria_safemask.csv"),
        }, [icone("download", 15), "Exportar CSV"]),
    ]);
    const tabela = h("div", { class: "cartao" }, [
        h("div", { class: "tabela-wrap" }, [
            h("table", { class: "tabela" }, [
                h("thead", {}, [h("tr", {}, ["Quando", "Ação", "Resultado", "Usuário", "Documento", "IP"].map((t) => h("th", {}, [t])))]),
                h("tbody", {}, linhas),
            ]),
        ]),
        h("div", { class: "tabela-resumo" }, [
            h("span", {}, [`Página ${dados.pagina} de ${dados.paginas || 1}`]),
            h("div", { class: "paginacao" }, [
                dados.pagina > 1
                    ? h("button", { onclick: () => void telaAuditoria(conteudo, dados.pagina - 1) }, [icone("chevron-left", 14), "Anterior"])
                    : null,
                dados.pagina < dados.paginas
                    ? h("button", { onclick: () => void telaAuditoria(conteudo, dados.pagina + 1) }, ["Próxima", icone("chevron-right", 14)])
                    : null,
            ]),
        ]),
    ]);
    conteudo.replaceChildren(cabecalho, linhas.length ? tabela : h("div", { class: "cartao vazio" }, [
        icone("history", 26),
        h("strong", {}, ["Nenhum evento ainda"]),
    ]));
}
