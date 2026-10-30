// Modo demonstracao do client: mesmas telas do Tauri, sem backend e sem
// Windows. Ativado por `?demo=1` no Vite; o modo real continua intacto.
//
// A camada `demoFetch` responde aos mesmos endpoints consumidos pelo app.
// O estado vive so em memoria e zera ao recarregar a pagina.
export const USUARIO_DEMO = {
    user_id: 1,
    nome: "Marina Alves",
    email: "admin@safemask.demo",
};
export function emModoDemo() {
    return new URLSearchParams(window.location.search).get("demo") === "1";
}
export function visaoInicialDemo() {
    const tela = new URLSearchParams(window.location.search).get("tela");
    return tela === "login" || tela === "painel" || tela === "equipes" || tela === "auditoria"
        ? tela
        : "documentos";
}
const equipes = [
    {
        team_id: 1,
        nome: "Financeiro",
        descricao: "Contratos, folha e conciliacoes",
        membros_lista: [
            { user_id: 1, nome: "Marina Alves", email: "admin@safemask.demo", cargo_nome: "lider", cargo_nivel: 3 },
            { user_id: 2, nome: "Carlos Menezes", email: "carlos@safemask.demo", cargo_nome: "supervisor", cargo_nivel: 2 },
            { user_id: 3, nome: "Ana Souza", email: "ana@safemask.demo", cargo_nome: "membro", cargo_nivel: 1 },
            { user_id: 4, nome: "Rafael Lima", email: "rafael@safemask.demo", cargo_nome: "membro", cargo_nivel: 1 },
        ],
    },
    {
        team_id: 2,
        nome: "Juridico",
        descricao: "Contratos, pareceres e processos",
        membros_lista: [
            { user_id: 1, nome: "Marina Alves", email: "admin@safemask.demo", cargo_nome: "supervisor", cargo_nivel: 2 },
            { user_id: 5, nome: "Beatriz Nunes", email: "bia@safemask.demo", cargo_nome: "lider", cargo_nivel: 3 },
            { user_id: 3, nome: "Ana Souza", email: "ana@safemask.demo", cargo_nome: "membro", cargo_nivel: 1 },
            { user_id: 6, nome: "Diego Castro", email: "diego@safemask.demo", cargo_nome: "membro", cargo_nivel: 1 },
        ],
    },
];
const documentos = [
    {
        doc_id: 8,
        nome_original: "Contrato de prestacao de servicos - Aurora",
        extensao: "pdf",
        nivel_seguranca: 3,
        tamanho_bytes: 2_480_120,
        status_processamento: "AGUARDANDO",
        criado_em: "2026-10-29T14:18:00+00:00",
        team_id: 2,
        equipe_nome: "Juridico",
    },
    {
        doc_id: 7,
        nome_original: "Relatorio medico - colaborador 4412",
        extensao: "pdf",
        nivel_seguranca: 4,
        tamanho_bytes: 1_204_880,
        status_processamento: "PROCESSANDO",
        criado_em: "2026-10-29T13:42:00+00:00",
        team_id: 1,
        equipe_nome: "Financeiro",
    },
    {
        doc_id: 6,
        nome_original: "Folha de pagamento - outubro 2026",
        extensao: "pdf",
        nivel_seguranca: 3,
        tamanho_bytes: 3_812_004,
        status_processamento: "CONCLUIDO",
        criado_em: "2026-10-28T17:05:00+00:00",
        team_id: 1,
        equipe_nome: "Financeiro",
    },
    {
        doc_id: 5,
        nome_original: "Ata de diretoria - confidencial",
        extensao: "pdf",
        nivel_seguranca: 4,
        tamanho_bytes: 984_320,
        status_processamento: "CONCLUIDO",
        criado_em: "2026-10-28T11:20:00+00:00",
        team_id: 2,
        equipe_nome: "Juridico",
    },
    {
        doc_id: 4,
        nome_original: "Proposta comercial - Banco Norte",
        extensao: "pdf",
        nivel_seguranca: 2,
        tamanho_bytes: 1_760_220,
        status_processamento: "CONCLUIDO",
        criado_em: "2026-10-27T16:48:00+00:00",
        team_id: 1,
        equipe_nome: "Financeiro",
    },
    {
        doc_id: 3,
        nome_original: "Parecer juridico - rescisao 091",
        extensao: "pdf",
        nivel_seguranca: 3,
        tamanho_bytes: 721_400,
        status_processamento: "ERRO",
        criado_em: "2026-10-27T09:31:00+00:00",
        team_id: 2,
        equipe_nome: "Juridico",
    },
    {
        doc_id: 2,
        nome_original: "Cadastro de fornecedores 2026",
        extensao: "pdf",
        nivel_seguranca: 1,
        tamanho_bytes: 640_512,
        status_processamento: "CONCLUIDO",
        criado_em: "2026-10-26T15:12:00+00:00",
        team_id: 1,
        equipe_nome: "Financeiro",
    },
    {
        doc_id: 1,
        nome_original: "Guia de integracao de novos colaboradores",
        extensao: "pdf",
        nivel_seguranca: 1,
        tamanho_bytes: 418_220,
        status_processamento: "CONCLUIDO",
        criado_em: "2026-10-24T10:00:00+00:00",
        team_id: 2,
        equipe_nome: "Juridico",
    },
];
const eventos = [
    { log_id: 12, data_hora: "2026-10-29T14:21:00+00:00", acao: "ver_original", resultado: "negado", usuario: { user_id: 3, nome: "Ana Souza" }, cargo: "membro", documento: { doc_id: 6, nome: "Folha de pagamento - outubro 2026" }, equipe: { team_id: 1, nome: "Financeiro" }, ip_origem: "10.0.4.23" },
    { log_id: 11, data_hora: "2026-10-29T14:19:00+00:00", acao: "upload_lote", resultado: "sucesso", usuario: { user_id: 1, nome: "Marina Alves" }, cargo: "lider", documento: { doc_id: 8, nome: "Contrato de prestacao de servicos - Aurora" }, equipe: { team_id: 2, nome: "Juridico" }, ip_origem: "10.0.4.10" },
    { log_id: 10, data_hora: "2026-10-29T13:55:00+00:00", acao: "ver_parcial", resultado: "sucesso", usuario: { user_id: 2, nome: "Carlos Menezes" }, cargo: "supervisor", documento: { doc_id: 6, nome: "Folha de pagamento - outubro 2026" }, equipe: { team_id: 1, nome: "Financeiro" }, ip_origem: "10.0.4.31" },
    { log_id: 9, data_hora: "2026-10-29T13:48:00+00:00", acao: "ver_censurado", resultado: "sucesso", usuario: { user_id: 5, nome: "Beatriz Nunes" }, cargo: "lider", documento: { doc_id: 5, nome: "Ata de diretoria - confidencial" }, equipe: { team_id: 2, nome: "Juridico" }, ip_origem: "10.0.4.44" },
    { log_id: 8, data_hora: "2026-10-29T12:32:00+00:00", acao: "ver_original", resultado: "negado", usuario: { user_id: 6, nome: "Diego Castro" }, cargo: "membro", documento: { doc_id: 5, nome: "Ata de diretoria - confidencial" }, equipe: { team_id: 2, nome: "Juridico" }, ip_origem: "10.0.4.52" },
    { log_id: 7, data_hora: "2026-10-28T17:08:00+00:00", acao: "upload_documento", resultado: "sucesso", usuario: { user_id: 1, nome: "Marina Alves" }, cargo: "lider", documento: { doc_id: 6, nome: "Folha de pagamento - outubro 2026" }, equipe: { team_id: 1, nome: "Financeiro" }, ip_origem: "10.0.4.10" },
    { log_id: 6, data_hora: "2026-10-28T11:26:00+00:00", acao: "ver_parcial", resultado: "negado", usuario: { user_id: 4, nome: "Rafael Lima" }, cargo: "membro", documento: { doc_id: 4, nome: "Proposta comercial - Banco Norte" }, equipe: { team_id: 1, nome: "Financeiro" }, ip_origem: "10.0.4.19" },
    { log_id: 5, data_hora: "2026-10-27T16:52:00+00:00", acao: "ver_censurado", resultado: "sucesso", usuario: { user_id: 3, nome: "Ana Souza" }, cargo: "membro", documento: { doc_id: 4, nome: "Proposta comercial - Banco Norte" }, equipe: { team_id: 1, nome: "Financeiro" }, ip_origem: "10.0.4.23" },
    { log_id: 4, data_hora: "2026-10-27T09:40:00+00:00", acao: "processar_documento", resultado: "falha", usuario: null, cargo: null, documento: { doc_id: 3, nome: "Parecer juridico - rescisao 091" }, equipe: { team_id: 2, nome: "Juridico" }, ip_origem: null },
    { log_id: 3, data_hora: "2026-10-26T15:16:00+00:00", acao: "upload_documento", resultado: "sucesso", usuario: { user_id: 2, nome: "Carlos Menezes" }, cargo: "supervisor", documento: { doc_id: 2, nome: "Cadastro de fornecedores 2026" }, equipe: { team_id: 1, nome: "Financeiro" }, ip_origem: "10.0.4.31" },
    { log_id: 2, data_hora: "2026-10-24T10:04:00+00:00", acao: "listar_documentos", resultado: "sucesso", usuario: { user_id: 3, nome: "Ana Souza" }, cargo: "membro", documento: null, equipe: { team_id: 2, nome: "Juridico" }, ip_origem: "10.0.4.23" },
    { log_id: 1, data_hora: "2026-10-24T09:58:00+00:00", acao: "ver_original", resultado: "negado", usuario: { user_id: 4, nome: "Rafael Lima" }, cargo: "membro", documento: { doc_id: 1, nome: "Guia de integracao de novos colaboradores" }, equipe: { team_id: 2, nome: "Juridico" }, ip_origem: "10.0.4.19" },
];
const TOP_TIPOS = [
    { tipo: "CPF", quantidade: 18 },
    { tipo: "TELEFONE", quantidade: 11 },
    { tipo: "EMAIL", quantidade: 8 },
    { tipo: "PESSOA", quantidade: 6 },
    { tipo: "ENDERECO", quantidade: 3 },
];
let proximoDocId = 9;
function json(dados, status = 200) {
    return new Response(JSON.stringify(dados), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}
function erro(status, detail) {
    return json({ detail }, status);
}
function corpoObjeto(corpo) {
    return corpo && typeof corpo === "object" ? corpo : {};
}
function equipesAuditaveis() {
    return equipes.filter((equipe) => equipe.membros_lista.some((membro) => membro.user_id === USUARIO_DEMO.user_id && membro.cargo_nivel >= 2));
}
function equipePublica(equipe) {
    const membro = equipe.membros_lista.find((item) => item.user_id === USUARIO_DEMO.user_id);
    return {
        team_id: equipe.team_id,
        nome: equipe.nome,
        descricao: equipe.descricao,
        membros: equipe.membros_lista.length,
        documentos: documentos.filter((doc) => doc.team_id === equipe.team_id).length,
        cargo_usuario: membro?.cargo_nome ?? null,
        cargo_nivel_usuario: membro?.cargo_nivel ?? null,
        membros_lista: equipe.membros_lista.map((item) => ({ ...item })),
    };
}
function visaoEquipes() {
    return {
        usuario: USUARIO_DEMO,
        equipes: equipes.map(equipePublica),
    };
}
function metricas() {
    const permitidas = equipesAuditaveis().map((equipe) => equipe.team_id);
    const docs = documentos.filter((doc) => permitidas.includes(doc.team_id));
    const porNivel = { "1": 0, "2": 0, "3": 0, "4": 0 };
    const porStatus = {
        AGUARDANDO: 0,
        PROCESSANDO: 0,
        CONCLUIDO: 0,
        ERRO: 0,
    };
    for (const doc of docs) {
        porNivel[String(doc.nivel_seguranca)] += 1;
        porStatus[doc.status_processamento] = (porStatus[doc.status_processamento] ?? 0) + 1;
    }
    const negados = eventos.filter((evento) => evento.resultado === "negado" &&
        evento.equipe !== null &&
        permitidas.includes(evento.equipe.team_id));
    const porAcao = {};
    for (const evento of negados)
        porAcao[evento.acao] = (porAcao[evento.acao] ?? 0) + 1;
    return {
        escopo: {
            equipes: equipesAuditaveis().map((equipe) => ({ team_id: equipe.team_id, nome: equipe.nome })),
        },
        documentos: { total: docs.length, por_nivel: porNivel, por_status: porStatus },
        acessos_negados: { total: negados.length, por_acao: porAcao },
        top_tipos: TOP_TIPOS,
    };
}
function arquivoDemo(nome) {
    const conteudo = [
        "%PDF-1.4",
        "% SafeMask - arquivo de demonstracao",
        `% ${nome}`,
        "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj",
        "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj",
        "trailer<</Root 1 0 R>>",
        "%%EOF",
    ].join("\n");
    return new Response(conteudo, {
        status: 200,
        headers: { "Content-Type": "application/pdf" },
    });
}
function adicionarDocumento(teamId, nivel, nome, bytes) {
    const equipe = equipes.find((item) => item.team_id === teamId);
    const documento = {
        doc_id: proximoDocId++,
        nome_original: nome,
        extensao: "pdf",
        nivel_seguranca: nivel,
        tamanho_bytes: bytes,
        status_processamento: "AGUARDANDO",
        criado_em: new Date().toISOString(),
        team_id: teamId,
        equipe_nome: equipe?.nome ?? "Equipe",
    };
    documentos.unshift(documento);
    window.setTimeout(() => {
        documento.status_processamento = "PROCESSANDO";
    }, 1200);
    window.setTimeout(() => {
        documento.status_processamento = "CONCLUIDO";
        eventos.unshift({
            log_id: eventos.length + 100,
            data_hora: new Date().toISOString(),
            acao: "processar_documento",
            resultado: "sucesso",
            usuario: null,
            cargo: null,
            documento: { doc_id: documento.doc_id, nome: documento.nome_original },
            equipe: { team_id: teamId, nome: documento.equipe_nome },
            ip_origem: null,
        });
    }, 3400);
    return documento;
}
export async function demoEnviarLote(teamId, nivelSeguranca, arquivos) {
    await new Promise((resolve) => window.setTimeout(resolve, 500));
    const itens = [];
    for (const arquivo of arquivos) {
        const ehPdf = arquivo.type === "application/pdf" || arquivo.name.toLowerCase().endsWith(".pdf");
        if (!ehPdf) {
            itens.push({
                nome: arquivo.name,
                doc_id: null,
                status: "RECUSADO",
                motivo: "Formato nao aceito. Envie apenas PDFs.",
            });
            continue;
        }
        const titulo = arquivo.name.replace(/\.pdf$/i, "");
        const documento = adicionarDocumento(teamId, nivelSeguranca, titulo, arquivo.size || 512_000);
        itens.push({
            nome: arquivo.name,
            doc_id: documento.doc_id,
            status: "AGUARDANDO",
            motivo: null,
        });
    }
    const aceitos = itens.filter((item) => item.status === "AGUARDANDO").length;
    return {
        mensagem: aceitos
            ? "Lote recebido; processamento em fila (simulado)."
            : "Nenhum arquivo valido foi aceito.",
        total_recebido: arquivos.length,
        total_aceito: aceitos,
        itens,
    };
}
export function demoFetch(path, metodo = "GET", corpo) {
    const [rota, consulta = ""] = path.split("?");
    const query = new URLSearchParams(consulta);
    const dados = corpoObjeto(corpo);
    if (rota === "/auth/me")
        return json(USUARIO_DEMO);
    if (rota === "/auth/login" && metodo === "POST") {
        if (!dados.email || !dados.senha_hash)
            return erro(401, "Email ou senha incorretos.");
        return json({
            access_token: `demo.${Date.now()}.token`,
            token_type: "bearer",
            user: USUARIO_DEMO,
        });
    }
    if (rota === "/auth/trocar-senha" && metodo === "POST") {
        return json({
            access_token: `demo.${Date.now()}.token`,
            token_type: "bearer",
            user: USUARIO_DEMO,
        });
    }
    if (rota === "/documentos/censurados") {
        return json({
            usuario: USUARIO_DEMO,
            total: documentos.length,
            documentos: documentos.map((doc) => ({ ...doc })),
        });
    }
    const censurado = rota.match(/^\/documentos\/censurados\/(\d+)\/arquivo$/);
    if (censurado) {
        const doc = documentos.find((item) => item.doc_id === Number(censurado[1]));
        return doc ? arquivoDemo(`${doc.nome_original} (censurado)`) : erro(404, "Documento nao encontrado.");
    }
    const parcial = rota.match(/^\/documentos\/(\d+)\/parcial$/);
    if (parcial) {
        const doc = documentos.find((item) => item.doc_id === Number(parcial[1]));
        return doc ? arquivoDemo(`${doc.nome_original} (parcial)`) : erro(404, "Documento nao encontrado.");
    }
    if (rota === "/equipes/overview")
        return json(visaoEquipes());
    if (rota === "/dashboard/metricas")
        return json(metricas());
    if (rota === "/auditoria") {
        const pagina = Math.max(1, Number(query.get("pagina") ?? 1));
        const porPagina = Math.max(1, Number(query.get("por_pagina") ?? 20));
        const inicio = (pagina - 1) * porPagina;
        return json({
            total: eventos.length,
            pagina,
            paginas: Math.max(1, Math.ceil(eventos.length / porPagina)),
            eventos: eventos.slice(inicio, inicio + porPagina),
        });
    }
    if (rota === "/auditoria/exportar") {
        const linhas = [
            "data_hora,acao,resultado,usuario,documento,equipe,ip",
            ...eventos.map((evento) => [
                evento.data_hora,
                evento.acao,
                evento.resultado,
                evento.usuario?.nome ?? "",
                evento.documento?.nome ?? "",
                evento.equipe?.nome ?? "",
                evento.ip_origem ?? "",
            ].join(",")),
        ];
        return new Response(linhas.join("\n"), {
            status: 200,
            headers: { "Content-Type": "text/csv; charset=utf-8" },
        });
    }
    if (rota === "/equipes" && metodo === "POST") {
        const nome = String(dados.nome ?? "").trim();
        if (!nome)
            return erro(400, "Informe o nome da equipe.");
        equipes.push({
            team_id: Math.max(...equipes.map((equipe) => equipe.team_id)) + 1,
            nome,
            descricao: "Equipe criada no modo demonstracao",
            membros_lista: [
                { user_id: 1, nome: "Marina Alves", email: "admin@safemask.demo", cargo_nome: "lider", cargo_nivel: 3 },
            ],
        });
        return json({ mensagem: "Equipe criada." }, 201);
    }
    const membro = rota.match(/^\/equipes\/(\d+)\/membros\/(\d+)$/);
    if (membro) {
        const equipe = equipes.find((item) => item.team_id === Number(membro[1]));
        const alvo = equipe?.membros_lista.find((item) => item.user_id === Number(membro[2]));
        if (!equipe || !alvo)
            return erro(404, "Membro nao encontrado.");
        if (metodo === "DELETE") {
            equipe.membros_lista = equipe.membros_lista.filter((item) => item.user_id !== alvo.user_id);
            return json({ mensagem: "Membro removido." });
        }
        if (metodo === "PATCH") {
            const cargo = String(dados.cargo ?? alvo.cargo_nome);
            const niveis = { lider: 3, supervisor: 2, membro: 1 };
            alvo.cargo_nome = cargo;
            alvo.cargo_nivel = niveis[cargo] ?? alvo.cargo_nivel;
            return json({ mensagem: "Cargo atualizado." });
        }
    }
    const novoMembro = rota.match(/^\/equipes\/(\d+)\/membros$/);
    if (novoMembro && metodo === "POST") {
        const equipe = equipes.find((item) => item.team_id === Number(novoMembro[1]));
        const email = String(dados.email ?? "").trim();
        if (!equipe || !email)
            return erro(400, "Informe o e-mail.");
        const nome = email.split("@")[0].replace(/[._-]+/g, " ").replace(/\b\w/g, (letra) => letra.toUpperCase());
        equipe.membros_lista.push({
            user_id: Math.max(...equipes.flatMap((item) => item.membros_lista.map((m) => m.user_id))) + 1,
            nome,
            email,
            cargo_nome: "membro",
            cargo_nivel: 1,
        });
        return json({ mensagem: "Membro adicionado." }, 201);
    }
    if (/^\/equipes\/\d+\/politica-niveis$/.test(rota) && metodo === "PUT") {
        return json({ mensagem: "Politica atualizada (simulada)." });
    }
    return erro(404, `Endpoint de demonstracao nao mapeado: ${metodo} ${rota}`);
}
