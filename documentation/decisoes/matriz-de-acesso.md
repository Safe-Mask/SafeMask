# Matriz de acesso por cargo

**Data:** 28/10/2026 · **Origem:** PI-III (CAMPUSCEUB/SafeMask#87) · **Testes:** `backend/tests/test_matriz_acesso.py`, um teste por célula

Quem pode ver cada versão de um documento, pelo cargo na **equipe dona** do documento. A escala de cargos é membro = 1, supervisor = 2 e líder = 3.

| Versão do documento | Membro (1) | Supervisor (2) | Líder (3) | Fora da equipe (mesma organização ou outra) |
| --- | --- | --- | --- | --- |
| Detalhes e listagem da equipe (`GET /documentos/censurados/{id}`, `GET /documentos/listar/{equipe}`) | ✓ | ✓ | ✓ | **404** |
| Censurado, com tarja (`GET /documentos/censurados/{id}/arquivo`) | ✓ | ✓ | ✓ | **404** |
| Parcial (`GET /documentos/{id}/parcial`) | ✓ cobre os dados de nível 2 e 3 | ✓ cobre os dados de nível 3 | recebe o **original** | **404** |
| Original (`GET /documentos/{id}/original`) | **403** | **403** | ✓ | **404** |
| Excluir (`DELETE /documentos/{id}`) | **403** | **403** | ✓ | **404** |

## Regras

- **Fora da equipe é sempre 404, nunca 403.** Responder "proibido" confirmaria que o documento existe. A tentativa de quem é da mesma organização fica na trilha de auditoria como `negado`; a de outra organização não deixa rastro no histórico da organização dona.
- **Todo membro vê os documentos da equipe**, e não só os que ele mesmo enviou.
- **Parcial:** cobre só os dados cujo nível exigido é maior que o nível do cargo. Cada nível tem a sua versão em cache (`<hash>_parcial_nivel<N>_...`). Sem nada a cobrir, a rota entrega a versão com tarja, nunca o original.
- **Nível mínimo para o original:** vem de `SAFEMASK_NIVEL_MIN_DESCENSURA`, com padrão 3 (líder). Aceita de 1 a 3; um valor ausente ou inválido volta ao padrão, com aviso no log. O mesmo nível decide quem recebe o original pela rota parcial e o campo `pode_descensurar` dos detalhes.
- **A tela não decide permissão:** a Descensura usa `pode_descensurar`, devolvido pela API, para escolher entre "Baixar versão original" e "Baixar descensura parcial".

## Divergências corrigidas ao montar a matriz

1. `GET /documentos/listar/{equipe}` listava só os documentos do próprio usuário e respondia 403 a quem estava fora. Agora lista todos os da equipe e responde 404.
2. A tela de Descensura escolhia o rótulo do botão com o nível 3 fixo no código, e ignorava a configuração.

## Nível de segurança do documento

**Data:** 11/11/2026 · **Origem:** PI-III (CAMPUSCEUB/SafeMask#176) · **Testes:** `backend/tests/test_matriz_acesso.py`, seção "nível do documento"

O nível escolhido no envio (Básico a Proteção máxima) deixa de ser só um rótulo e passa a valer no acesso, junto com o cargo. A tabela acima vale para o nível 1 (Básico); nos demais, o mínimo sobe:

| Nível do documento | Parcial a partir de | Original a partir de | Na prática, com N = 3 |
| --- | --- | --- | --- |
| 1 Básico | membro (1) | N | todos pedem a parcial; o original é do líder |
| 2 Proteção média | supervisor (2) | maior entre N e 2 | o membro vê só a versão com tarja |
| 3 Proteção alta | supervisor (2) | líder (3), mesmo com N menor | o original é sempre só do líder |
| 4 Proteção máxima | líder (3) | líder (3) | só o líder remove a tarja |

- N é o `SAFEMASK_NIVEL_MIN_DESCENSURA` (padrão 3). O original nunca exige menos que a parcial do mesmo documento.
- Abaixo do mínimo, a parcial e o original respondem **403** e a tentativa fica na trilha como `negado`. Quem está fora da equipe continua recebendo **404**.
- Quem alcança o mínimo do original recebe o original também pela rota da parcial, como antes.
- `GET /documentos/censurados/{id}` devolve `pode_descensura_parcial`, `pode_descensurar` e `acesso_minimo` (`parcial` e `original`) já com o nível do documento. A tela de envio explica o efeito de cada nível.
- Regra em `backend/app/core/autorizacao.py` (`nivel_min_parcial`, `nivel_min_original`).

**Efeito em documentos já enviados:** o nível já gravado passa a valer. Como o padrão da tela é Proteção alta, membros deixam de receber a parcial da maioria dos documentos antigos.
