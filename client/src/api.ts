// API do servico central. A URL do servico e o token de sessao moram no
// localStorage do webview: 1 client = 1 usuario da mesma empresa e a URL
// nunca muda entre acessos.

export interface Identidade {
  user_id: number;
  nome: string;
  email: string;
  precisa_trocar_senha?: boolean;
}

interface RespostaLogin {
  access_token: string;
  token_type: string;
  user: Identidade;
}

const CHAVE_URL = "servico_url";
const CHAVE_TOKEN = "servico_token";

export function urlServico(): string | null {
  const valor = localStorage.getItem(CHAVE_URL);
  return valor ? valor.replace(/\/+$/, "") : null;
}

export function salvarUrlServico(valor: string) {
  localStorage.setItem(CHAVE_URL, valor.trim().replace(/\/+$/, ""));
}

export function token(): string | null {
  return localStorage.getItem(CHAVE_TOKEN);
}

export function salvarToken(novo: string) {
  localStorage.setItem(CHAVE_TOKEN, novo);
}

export function sair() {
  localStorage.removeItem(CHAVE_TOKEN);
}

export class ErroApi extends Error {
  status: number;
  constructor(status: number, mensagem: string) {
    super(mensagem);
    this.status = status;
  }
}

function semServico(): never {
  throw new ErroApi(0, "Sem URL do serviço. Configure o endereço do servidor.");
}

interface Opcoes {
  metodo?: "POST" | "DELETE" | "PATCH" | "PUT" | "GET";
  corpo?: unknown;
}

export async function pedir(path: string, opcoes: Opcoes = {}): Promise<Response> {
  const base = urlServico() ?? semServico();
  const metodo = opcoes.metodo ?? (opcoes.corpo !== undefined ? "POST" : "GET");
  const cabecalhos: Record<string, string> = { Accept: "application/json" };
  const t = token();
  if (t) cabecalhos.Authorization = `Bearer ${t}`;
  if (opcoes.corpo !== undefined) cabecalhos["Content-Type"] = "application/json";

  let resp: Response;
  try {
    resp = await fetch(`${base}${path}`, {
      method: metodo,
      headers: cabecalhos,
      body: opcoes.corpo !== undefined ? JSON.stringify(opcoes.corpo) : undefined,
    });
  } catch {
    throw new ErroApi(0, "Serviço indisponível (rede/offline?).");
  }
  return resp;
}

async function corpo_do_erro(resp: Response): Promise<string> {
  try {
    const dados = await resp.json();
    return typeof dados.detail === "string"
      ? dados.detail
      : "Requisição recusada pelo serviço.";
  } catch {
    return `Erro ${resp.status} no serviço.`;
  }
}

export async function pedirJson<T>(path: string, opcoes: Opcoes = {}): Promise<T> {
  const resp = await pedir(path, opcoes);
  if (!resp.ok) throw new ErroApi(resp.status, await corpo_do_erro(resp));
  return (await resp.json()) as T;
}

export async function pedirArquivo(path: string): Promise<Blob> {
  const base = urlServico() ?? semServico();
  const cabecalhos: Record<string, string> = {};
  const t = token();
  if (t) cabecalhos.Authorization = `Bearer ${t}`;
  const resp = await fetch(`${base}${path}`, { headers: cabecalhos });
  if (!resp.ok) throw new ErroApi(resp.status, await corpo_do_erro(resp));
  return await resp.blob();
}

// --- endpoints -----------------------------------------------------------

export interface Documento {
  doc_id: number;
  nome_original: string;
  extensao: string;
  nivel_seguranca: number;
  tamanho_bytes: number;
  criado_em: string;
  team_id: number;
  equipe_nome: string;
}

export async function login(email: string, senha: string): Promise<RespostaLogin> {
  const resp = await pedir("/auth/login", { corpo: { email, senha_hash: senha } });
  if (!resp.ok) throw new ErroApi(resp.status, await corpo_do_erro(resp));
  return (await resp.json()) as RespostaLogin;
}

export async function trocarSenha(senhaAtual: string, novaSenha: string): Promise<RespostaLogin> {
  const resp = await pedir("/auth/trocar-senha", {
    corpo: { senha_atual: senhaAtual, nova_senha: novaSenha },
  });
  if (!resp.ok) throw new ErroApi(resp.status, await corpo_do_erro(resp));
  return (await resp.json()) as RespostaLogin;
}

export async function considerarServico(): Promise<boolean> {
  const base = urlServico() ?? semServico();
  try {
    const resp = await fetch(`${base}/auth/me`);
    // 401 com JSON do FastAPI = servico vivo e no lugar certo (404 = URL errada).
    return resp.status === 401 || resp.status === 200;
  } catch {
    return false;
  }
}

export interface EventoAuditoria {
  log_id: number;
  data_hora: string;
  acao: string;
  resultado: string;
  usuario: { user_id: number; nome: string } | null;
  cargo: string | null;
  documento: { doc_id: number; nome: string } | null;
  equipe: { team_id: number; nome: string } | null;
  ip_origem: string | null;
}

export interface PaginaAuditoria {
  total: number;
  pagina: number;
  paginas: number;
  eventos: EventoAuditoria[];
}
