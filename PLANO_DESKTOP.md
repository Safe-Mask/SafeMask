# Plano de Desenvolvimento: Frontend Desktop (MVP)

## 1. Stack Tecnológica
*   **Frontend UI:** React.js com Vite (rápido, leve e fácil de debugar).
*   **Empacotamento Desktop:** Tauri ou Electron (recomendado Tauri para rodar mais leve no Ubuntu, aproveitando que não precisamos do backend em Python embutido na interface agora).
*   **Estilização:** TailwindCSS (para prototipagem rápida da interface de redação de documentos).

## 2. Especificação de Componentes (UI)
*   **Layout Principal:** Sidebar lateral para navegação e área principal de visualização.
*   **Componente de Upload (`UploadArea.jsx`):** 
    *   Área de drag-and-drop para inserir documentos (PDF/Imagens).
    *   Botão de "Processar/Anonimizar".
*   **Componente de Visualização (`DocumentViewer.jsx`):**
    *   Renderização do documento lado a lado (Original vs. Mascarado).
    *   Highlight visual sobre as áreas sensíveis que foram detectadas.
*   **Painel de Configurações (`SettingsPanel.jsx`):**
    *   Seleção de quais dados ocultar (CPFs, Nomes, Valores, etc.).

## 3. Estrutura de Dados Estáticos (Mock)
Como o backend real não será conectado no MVP[cite: 1], criaremos um arquivo `mockData.json` contendo a resposta simulada da detecção da IA:
- Posições (X, Y) das tarjas pretas (bounding boxes).
- Textos extraídos e classificados como sensíveis.

## 4. Próximos Passos de Execução
1. Inicializar o projeto com `npm create vite@latest safemask-ui -- --template react`.
2. Criar a estrutura de pastas `/components`, `/pages` e `/mocks`.
3. Desenvolver os componentes usando os dados falsos.
