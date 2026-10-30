// API do servico central. A URL do servico e o token de sessao moram no
// localStorage do webview: 1 client = 1 usuario da mesma empresa e a URL
// nunca muda entre acessos.

import { demoEnviarLote, demoFetch, emModoDemo } from "./demo";

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
  if (emModoDemo()) return "demo://safemask";
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
  const metodo = opcoes.metodo ?? (opcoes.corpo !== undefined ? "POST" : "GET");
  if (emModoDemo()) return demoFetch(path, metodo, opcoes.corpo);

  const base = urlServico() ?? semServico();
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
  if (emModoDemo()) {
    const resposta = demoFetch(path, "GET");
    if (!resposta.ok) throw new ErroApi(resposta.status, await corpo_do_erro(resposta));
    return await resposta.blob();
  }

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
  status_processamento: string;
  criado_em: string;
  team_id: number;
  equipe_nome: string;
}

export interface ItemLote {
  nome: string;
  doc_id: number | null;
  status: string;
  motivo: string | null;
}

export interface RespostaLote {
  mensagem: string;
  total_recebido: number;
  total_aceito: number;
  itens: ItemLote[];
}

export interface MetricasAdmin {
  escopo: {
    equipes: { team_id: number; nome: string }[];
  };
  documentos: {
    total: number;
    por_nivel: Record<string, number>;
    por_status: Record<string, number>;
  };
  acessos_negados: {
    total: number;
    por_acao: Record<string, number>;
  };
  top_tipos: { tipo: string; quantidade: number }[];
}

export async function enviarLote(
  teamId: number,
  nivelSeguranca: number,
  arquivos: File[],
): Promise<RespostaLote> {
  if (emModoDemo()) return demoEnviarLote(teamId, nivelSeguranca, arquivos);

  const base = urlServico() ?? semServico();
  const formulario = new FormData();
  formulario.append("team_id", String(teamId));
  formulario.append("nivel_seguranca", String(nivelSeguranca));
  for (const arquivo of arquivos) formulario.append("files", arquivo);

  const cabecalhos: Record<string, string> = { Accept: "application/json" };
  const t = token();
  if (t) cabecalhos.Authorization = `Bearer ${t}`;

  let resp: Response;
  try {
    // Sem Content-Type manual: o navegador/webview define o boundary.
    resp = await fetch(`${base}/documentos/upload/lote`, {
      method: "POST",
      headers: cabecalhos,
      body: formulario,
    });
  } catch {
    throw new ErroApi(0, "Serviço indisponível (rede/offline?).");
  }
  if (!resp.ok) throw new ErroApi(resp.status, await corpo_do_erro(resp));
  return (await resp.json()) as RespostaLote;
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
  if (emModoDemo()) return true;
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
