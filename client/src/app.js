import { pedir, pedirArquivo, pedirJson, salvarToken, salvarUrlServico, sair, considerarServico, token, trocarSenha, urlServico, login, } from "./api";
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
function tamanho(bytes) {
    if (bytes >= 1_048_576)
        return `${(bytes / 1_048_576).toFixed(1)} MB`;
    if (bytes >= 1024)
        return `${Math.round(bytes / 1024)} KB`;
    return `${bytes} B`;
}
function dataCurta(iso) {
    return iso ? iso.slice(0, 16).replace("T", " ") : "";
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
let raiz;
let usuario = null;
export async function bootstrap() {
    raiz = document.getElementById("app");
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
function telaPrimeiroUso(mensagemErro = "") {
    raiz.replaceChildren(h("div", { class: "tela-centro" }, [
        h("div", { class: "cartao configuracao" }, [
            h("h1", {}, ["SafeMask"]),
            h("p", { class: "mudo" }, [
                "Primeiro uso: informe o endereço do serviço central da sua empresa ",
                "(mesmo do painel de instalação, ex.: http://servidor-da-empresa:8000).",
            ]),
            h("input", {
                id: "url-servico",
                type: "url",
                placeholder: "http://servidor-da-empresa:8000",
                style: "width:100%",
                value: mensagemErro && urlServico() ? urlServico() : "",
            }),
            h("div", { class: "linha-form" }, [
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
            ]),
            h("div", { id: "config-erro", class: "erro" }),
        ]),
    ]));
}
// ---------------------------------------------------------------- login ---
function telaLogin() {
    document.getElementById("shell")?.remove();
    raiz.replaceChildren(h("div", { class: "tela-centro" }, [
        h("div", { class: "cartao login" }, [
            h("h1", {}, ["SafeMask"]),
            h("p", { class: "mudo" }, [urlServico() ?? ""]),
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
                h("input", { id: "login-email", type: "email", placeholder: "E-mail", required: "", style: "width:100%" }),
                h("input", { id: "login-senha", type: "password", placeholder: "Senha", required: "", style: "width:100%" }),
                h("button", { class: "primario", type: "submit", style: "width:100%" }, ["Entrar"]),
            ]),
            h("div", { id: "login-erro", class: "erro" }),
            h("p", { class: "mudo pequeno" }, [
                "Esqueceu a senha? Peça a recuperação ao admin (rota /auth/recuperar-senha do serviço).",
            ]),
        ]),
    ]));
}
// ------------------------------------------------------- troca de senha ---
function telaTrocarSenha(possivelUsuario) {
    document.getElementById("shell")?.remove();
    raiz.replaceChildren(h("div", { class: "tela-centro" }, [
        h("div", { class: "cartao login" }, [
            h("h1", {}, ["Troque sua senha"]),
            h("p", { class: "mudo" }, [
                `${possivelUsuario.email} entrou com uma senha provisória. `,
                "Escolha uma senha definitiva (mínimo 8 caracteres) para continuar.",
            ]),
            h("input", { id: "troca-atual", type: "password", placeholder: "Senha provisória atual", style: "width:100%" }),
            h("input", { id: "troca-nova", type: "password", placeholder: "Nova senha", style: "width:100%" }),
            h("input", { id: "troca-nova2", type: "password", placeholder: "Repetir nova senha", style: "width:100%" }),
            h("button", {
                class: "primario",
                style: "width:100%",
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
function telaShell() {
    const buscaUsuario = usuario ?? { nome: "", email: "" };
    const visoes = [
        ["documentos", "Documentos"],
        ["equipes", "Equipes"],
        ["auditoria", "Auditoria"],
    ];
    const conteudo = h("div", { id: "conteudo" });
    const nav = h("nav", { class: "lateral" }, [
        h("div", { class: "marca" }, ["SafeMask"]),
        h("ul", {}, visoes.map(([nome, rotulo]) => h("li", {}, [
            h("button", {
                "data-visao": nome,
                class: nome === "documentos" ? "ativo" : "",
                onclick: (ev) => {
                    const alvo = ev.target.dataset.visao;
                    document.querySelectorAll(".lateral button").forEach((b) => b.classList.remove("ativo"));
                    ev.target.classList.add("ativo");
                    void carregarVisao(alvo, conteudo);
                },
            }, [rotulo]),
        ]))),
        h("div", { class: "rodape-lateral" }, [
            h("p", {}, [`${buscaUsuario.nome} (${buscaUsuario.email})`]),
            h("button", {
                onclick: () => {
                    sair();
                    telaLogin();
                },
            }, ["Sair"]),
        ]),
    ]);
    raiz.replaceChildren(h("div", { class: "shell", id: "shell" }, [nav, conteudo]));
    void carregarVisao("documentos", conteudo);
}
async function carregarVisao(visao, conteudo) {
    conteudo.replaceChildren(h("p", { class: "mudo" }, ["Carregando..."]));
    try {
        if (visao === "documentos")
            await telaDocumentos(conteudo);
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
async function telaDocumentos(conteudo) {
    const lista = await pedirJson("/documentos/censurados");
    const linhas = lista.documentos.map((doc) => h("tr", {}, [
        h("td", {}, [doc.nome_original]),
        h("td", {}, [doc.equipe_nome]),
        h("td", {}, [`N${doc.nivel_seguranca} · ${nivelNome(doc.nivel_seguranca)}`]),
        h("td", {}, [tamanho(doc.tamanho_bytes)]),
        h("td", {}, [dataCurta(doc.criado_em)]),
        h("td", { class: "acoes" }, [
            h("button", {
                onclick: async () => await baixarProtegido(`/documentos/censurados/${doc.doc_id}/arquivo`, `${doc.nome_original}.${doc.extensao || "pdf"}`),
            }, ["Baixar versão censurada"]),
            h("button", {
                onclick: async (ev) => {
                    const botao = ev.target;
                    botao.disabled = true;
                    try {
                        await baixarProtegido(`/documentos/${doc.doc_id}/parcial`, `${doc.nome_original}_parcial.${doc.extensao || "pdf"}`);
                    }
                    catch (exc) {
                        alert(exc.message);
                    }
                    finally {
                        botao.disabled = false;
                    }
                },
            }, ["Pedir versão parcial"]),
        ]),
    ]));
    conteudo.replaceChildren(h("h2", {}, ["Documentos"]), h("p", { class: "mudo" }, [
        `Você recebe versões no limite do seu cargo (${lista.total} documento(s) nas suas equipes). `,
        "O original nunca sai do servidor.",
    ]), linhas.length
        ? h("table", { class: "tabela" }, [
            h("thead", {}, [h("tr", {}, ["Documento", "Equipe", "Nível", "Tamanho", "Data (UTC)", "Ações"].map((t) => h("th", {}, [t])))]),
            h("tbody", {}, linhas),
        ])
        : h("p", { class: "mudo" }, ["Nenhum documento ainda. Documentos surgem aqui com upload no admin ou ingestão da pasta base."]));
}
// -------------------------------------------------------------- equipes ---
async function telaEquipes(conteudo) {
    const visao = await pedirJson("/equipes/overview");
    const criarEquipe = h("details", { class: "bloco" }, [
        h("summary", {}, ["Criar nova equipe"]),
        h("div", { class: "linha-form" }, [
            h("input", { id: "equipe-nome", placeholder: "Nome da equipe", style: "flex:1" }),
            h("button", {
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
    ]);
    const cartoes = visao.equipes.map((equipe) => {
        const souLider = equipe.cargo_usuario === "lider";
        const membros = equipe.membros_lista.map((m) => h("tr", {}, [
            h("td", {}, [m.nome]),
            h("td", { class: "mudo" }, [m.email]),
            h("td", {}, [h("span", { class: `etiqueta nivel-${m.cargo_nivel}` }, [m.cargo_nome])]),
            souLider
                ? h("td", { class: "acoes" }, [
                    h("button", {
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
                    }, ["Cargo"]),
                    h("button", {
                        class: "perigo",
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
                    }, ["Remover"]),
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
            h("input", { placeholder: "E-mail de quem vai entrar", style: "flex:1" }),
            souLider ? h("button", { type: "submit" }, ["Adicionar membro"]) : h("span"),
        ]);
        const politica = h("details", { class: "bloco" }, [
            h("summary", {}, ["Política de níveis (admin da equipe)"]),
            h("p", { class: "mudo pequeno" }, [
                "Tipo → nível mínimo exigido de quem pede versão mais aberta (só tipos informados mudam).",
            ]),
            h("div", { class: "linha-form" }, [
                h("input", { placeholder: "ex.: TELEFONE", style: "width:40%", id: `politica-tipo-${equipe.team_id}` }),
                h("input", { placeholder: "nível (1-3)", style: "width:25%", id: `politica-nivel-${equipe.team_id}` }),
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
        return h("div", { class: "cartao equipe" }, [
            h("h3", {}, [
                `${equipe.nome} `,
                h("span", { class: "mudo" }, [`· ${equipe.membros} membro(s), ${equipe.documentos} doc(s), seu cargo: ${equipe.cargo_usuario ?? "sem acesso"}`]),
            ]),
            h("table", { class: "tabela" }, [
                h("thead", {}, [h("tr", {}, ["Nome", "E-mail", "Cargo", souLider ? "Ações" : ""].map((t) => h("th", {}, [t])))]),
                h("tbody", {}, membros),
            ]),
            addMembro,
            souLider ? politica : h("span"),
        ]);
    });
    conteudo.replaceChildren(h("h2", {}, ["Equipes"]), criarEquipe, ...cartoes);
}
// ------------------------------------------------------------ auditoria ---
async function telaAuditoria(conteudo, pagina = 1) {
    const dados = await pedirJson(`/auditoria?pagina=${pagina}&por_pagina=20`);
    const linhas = dados.eventos.map((ev) => h("tr", {}, [
        h("td", { class: "mudo" }, [dataCurta(ev.data_hora)]),
        h("td", {}, [ev.acao]),
        h("td", {}, [ev.resultado]),
        h("td", {}, [ev.usuario?.nome ?? ""]),
        h("td", {}, [ev.documento?.nome ?? ""]),
        h("td", { class: "mudo" }, [ev.ip_origem ?? ""]),
    ]));
    conteudo.replaceChildren(h("h2", {}, ["Auditoria"]), h("p", { class: "mudo" }, [`${dados.total} evento(s) nas equipes que você audita — página ${dados.pagina}/${dados.paginas || 1}.`]), h("div", { class: "linha-form" }, [
        h("button", {
            onclick: async () => await baixarProtegido("/auditoria/exportar", "auditoria_safemask.csv"),
        }, ["Exportar CSV"]),
    ]), h("table", { class: "tabela" }, [
        h("thead", {}, [h("tr", {}, ["Quando (UTC)", "Ação", "Resultado", "Usuário", "Documento", "IP"].map((t) => h("th", {}, [t])))]),
        h("tbody", {}, linhas),
    ]), h("div", { class: "linha-form" }, [
        dados.pagina > 1 ? h("button", { onclick: () => void telaAuditoria(conteudo, dados.pagina - 1) }, ["← Anterior"]) : h("span"),
        dados.pagina < dados.paginas ? h("button", { onclick: () => void telaAuditoria(conteudo, dados.pagina + 1) }, ["Próxima →"]) : h("span"),
    ]));
}
