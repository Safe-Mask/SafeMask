// API do servico central. A URL do servico e o token de sessao moram no
// localStorage do webview: 1 client = 1 usuario da mesma empresa e a URL
// nunca muda entre acessos.
import { demoEnviarLote, demoFetch, emModoDemo } from "./demo";
const CHAVE_URL = "servico_url";
const CHAVE_TOKEN = "servico_token";
export function urlServico() {
    if (emModoDemo())
        return "demo://safemask";
    const valor = localStorage.getItem(CHAVE_URL);
    return valor ? valor.replace(/\/+$/, "") : null;
}
export function salvarUrlServico(valor) {
    localStorage.setItem(CHAVE_URL, valor.trim().replace(/\/+$/, ""));
}
export function token() {
    return localStorage.getItem(CHAVE_TOKEN);
}
export function salvarToken(novo) {
    localStorage.setItem(CHAVE_TOKEN, novo);
}
export function sair() {
    localStorage.removeItem(CHAVE_TOKEN);
}
export class ErroApi extends Error {
    constructor(status, mensagem) {
        super(mensagem);
        this.status = status;
    }
}
function semServico() {
    throw new ErroApi(0, "Sem URL do serviço. Configure o endereço do servidor.");
}
export async function pedir(path, opcoes = {}) {
    const metodo = opcoes.metodo ?? (opcoes.corpo !== undefined ? "POST" : "GET");
    if (emModoDemo())
        return demoFetch(path, metodo, opcoes.corpo);
    const base = urlServico() ?? semServico();
    const cabecalhos = { Accept: "application/json" };
    const t = token();
    if (t)
        cabecalhos.Authorization = `Bearer ${t}`;
    if (opcoes.corpo !== undefined)
        cabecalhos["Content-Type"] = "application/json";
    let resp;
    try {
        resp = await fetch(`${base}${path}`, {
            method: metodo,
            headers: cabecalhos,
            body: opcoes.corpo !== undefined ? JSON.stringify(opcoes.corpo) : undefined,
        });
    }
    catch {
        throw new ErroApi(0, "Serviço indisponível (rede/offline?).");
    }
    return resp;
}
async function corpo_do_erro(resp) {
    try {
        const dados = await resp.json();
        return typeof dados.detail === "string"
            ? dados.detail
            : "Requisição recusada pelo serviço.";
    }
    catch {
        return `Erro ${resp.status} no serviço.`;
    }
}
export async function pedirJson(path, opcoes = {}) {
    const resp = await pedir(path, opcoes);
    if (!resp.ok)
        throw new ErroApi(resp.status, await corpo_do_erro(resp));
    return (await resp.json());
}
export async function pedirArquivo(path) {
    if (emModoDemo()) {
        const resposta = demoFetch(path, "GET");
        if (!resposta.ok)
            throw new ErroApi(resposta.status, await corpo_do_erro(resposta));
        return await resposta.blob();
    }
    const base = urlServico() ?? semServico();
    const cabecalhos = {};
    const t = token();
    if (t)
        cabecalhos.Authorization = `Bearer ${t}`;
    const resp = await fetch(`${base}${path}`, { headers: cabecalhos });
    if (!resp.ok)
        throw new ErroApi(resp.status, await corpo_do_erro(resp));
    return await resp.blob();
}
export async function enviarLote(teamId, nivelSeguranca, arquivos) {
    if (emModoDemo())
        return demoEnviarLote(teamId, nivelSeguranca, arquivos);
    const base = urlServico() ?? semServico();
    const formulario = new FormData();
    formulario.append("team_id", String(teamId));
    formulario.append("nivel_seguranca", String(nivelSeguranca));
    for (const arquivo of arquivos)
        formulario.append("files", arquivo);
    const cabecalhos = { Accept: "application/json" };
    const t = token();
    if (t)
        cabecalhos.Authorization = `Bearer ${t}`;
    let resp;
    try {
        // Sem Content-Type manual: o navegador/webview define o boundary.
        resp = await fetch(`${base}/documentos/upload/lote`, {
            method: "POST",
            headers: cabecalhos,
            body: formulario,
        });
    }
    catch {
        throw new ErroApi(0, "Serviço indisponível (rede/offline?).");
    }
    if (!resp.ok)
        throw new ErroApi(resp.status, await corpo_do_erro(resp));
    return (await resp.json());
}
export async function login(email, senha) {
    const resp = await pedir("/auth/login", { corpo: { email, senha_hash: senha } });
    if (!resp.ok)
        throw new ErroApi(resp.status, await corpo_do_erro(resp));
    return (await resp.json());
}
export async function trocarSenha(senhaAtual, novaSenha) {
    const resp = await pedir("/auth/trocar-senha", {
        corpo: { senha_atual: senhaAtual, nova_senha: novaSenha },
    });
    if (!resp.ok)
        throw new ErroApi(resp.status, await corpo_do_erro(resp));
    return (await resp.json());
}
export async function considerarServico() {
    if (emModoDemo())
        return true;
    const base = urlServico() ?? semServico();
    try {
        const resp = await fetch(`${base}/auth/me`);
        // 401 com JSON do FastAPI = servico vivo e no lugar certo (404 = URL errada).
        return resp.status === 401 || resp.status === 200;
    }
    catch {
        return false;
    }
}
