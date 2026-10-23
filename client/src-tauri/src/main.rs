// Client SafeMask: webview que fala com o servico central da empresa
// (HTTP em http://<servidor>:porta). Toda regra fica no servico; o client
// guarda so a URL do servico e o token de sessao.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("falha ao iniciar o client SafeMask");
}
