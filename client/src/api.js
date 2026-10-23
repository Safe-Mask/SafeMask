// API do servico central. A URL do servico e o token de sessao moram no
// localStorage do webview: 1 client = 1 usuario da mesma empresa e a URL
// nunca muda entre acessos.
const CHAVE_URL = "servico_url";
const CHAVE_TOKEN = "servico_token";
export function urlServico() {
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
    const base = urlServico() ?? semServico();
    const metodo = opcoes.metodo ?? (opcoes.corpo !== undefined ? "POST" : "GET");
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
