# PLANO PARA PRÓXIMAS FASES - SafeMask

## O que foi feito até aqui (estado atual)
- Backend local estável em http://127.0.0.1:9015 (IA + OCR validados)
- Frontend local estável em http://127.0.0.1:8082 (config apontando p/ 9015)
- Dashboard remodelado: removidos 4 cards, adicionado "Mapa Mental dos Documentos"
- E2E local completo passou (16/16 etapas)
- Nuvem: PDF com texto OK; OCR pendente (Tesseract via buildCommand no deploy 6364c53)
- Commits organizados, testes 153 passed, ruff OK

## Ideia proposta pelo usuário
Sistema multi-tenant por empresa (SaaS B2B). Cada empresa tem sua base de documentos (isolamento por organização). 
O SafeMask é a interface da empresa com essa base. Qualquer usuário pode consultar, mas com acesso baseado no nível/cargo (RBAC). 
Mudança de modelo: foco em "organização/tenant" vs modelo atual de equipes soltas.

## Próximas fases - O que falar/validar
1. **Arquitetura multi-tenant**
   - Confirmar: isolamento por `organizacao_id` (já existe em modelos)? Ampliar escopo (todas rotas filtram por org)
   - Conceito: 1 empresa = 1 organização. Usuários pertencem à org. Documentos pertencem à org (herda via equipe/user_team)
   
2. **Modelo de equipes vs estrutura organizacional**
   - Revisar fluxos de criação de equipes (hoje por usuário). Quer centralizar (admin da empresa cria estrutura)?
   - Definir papéis: superadmin/org admin, líder, supervisor, membro
   - Navegação por "base da empresa" (catálogo unificado) vs por equipes

3. **Frontend - visão por organização/base**
   - Dashboard: mapa mental por pastas/equipes/org? Expandir para visão de "repositório da empresa"
   - Navegação tipo explorer (árvore/documentos) com permissões por nível
   - UI para gerenciar usuários da empresa (convites, cargos)

4. **Banco/isolamento**
   - Garantir tenant isolation em todas queries (org_id obrigatório)
   - Auditoria por organização
   - Compartilhamento interno à org vs entre orgs (bloquear)

5. **Roadmap sugerido (fases pequenas)**
   - Fase 1: Validar modelo de dados/tenant (confirmar escopo)
   - Fase 2: Ajustar rotas p/ filtrar por organização (garantir)
   - Fase 3: Redesign frontend (navegação por base da empresa + permissões)
   - Fase 4: Gestão de usuários da empresa (admin)
   - Fase 5: Testes + migrações

## Perguntas para esclarecer com o usuário
- A empresa quer que usuários externos consultem? Ou só colaboradores internos?
- Quem cria equipes: admin da empresa ou qualquer líder?
- Quer visão unificada "todos documentos da empresa" (com filtros por nível) ou estritamente por equipes?
- Precisa de convites por e-mail (domínio da empresa)?
- Multi-org no mesmo tenant? (hoje já tem org_acme/org_globex nos testes)

## Resumo para apresentar/avançar
Explicar: migrar de "equipes isoladas" p/ "base organizacional única com RBAC por nível". SafeMask vira interface da base documental da empresa. Isolamento por organização garantido, navegação simplificada (mapa mental/explorer), gestão centralizada.

