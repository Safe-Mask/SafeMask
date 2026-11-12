/* Painel de conformidade no dashboard (PI-III #228).
   Le GET /dashboard/conformidade e desenha barras simples, sem biblioteca,
   com o mesmo estilo de "Uploads por Equipe". Carregar depois do config.js. */
(function () {
    'use strict';

    const ROTULOS_ACAO = {
        acesso_original: 'Original',
        acesso_parcial: 'Versão parcial',
        acesso_censurado: 'Versão com tarja',
        upload: 'Envio',
        salvar_censurado: 'Salvar censurado',
        excluir_documento: 'Exclusão',
        adicionar_membro: 'Adicionar membro',
        remover_membro: 'Remover membro',
        alterar_cargo: 'Alterar cargo',
        alterar_politica_niveis: 'Política de níveis',
        gerar_comprovante: 'Comprovante',
        ver_original: 'Original',
        ver_parcial: 'Versão parcial',
        ver_censurado: 'Versão com tarja',
        upload_documento: 'Envio',
    };
    const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

    const porTipo = document.getElementById('chartTarjasTipo');
    const porMes = document.getElementById('chartTarjasMes');
    const negados = document.getElementById('chartNegados');
    const negadosTotal = document.getElementById('negadosTotal');
    if (!porTipo || !porMes || !negados) {
        return;
    }

    function esc(valor) {
        return String(valor ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    function barras(alvo, itens, vazio) {
        if (!itens.length || itens.every((i) => !i.valor)) {
            alvo.innerHTML = `<p class="empty-message">${esc(vazio)}</p>`;
            return;
        }
        const maximo = Math.max(...itens.map((i) => i.valor), 1);
        alvo.innerHTML = itens
            .map((i) => {
                const largura = i.valor ? Math.max(6, Math.round((i.valor / maximo) * 100)) : 0;
                return `
                    <div class="bar-item" role="listitem" aria-label="${esc(i.rotulo)}: ${esc(i.texto || i.valor)}">
                        <span class="label">${esc(i.rotulo)}</span>
                        <div class="bar-track"><div class="bar" style="width: ${largura}%;"></div></div>
                        <span class="value">${esc(i.texto || i.valor)}</span>
                    </div>`;
            })
            .join('');
    }

    function nomeDoMes(chave) {
        const [ano, mes] = chave.split('-');
        return `${MESES[Number(mes) - 1]}/${ano.slice(2)}`;
    }

    async function carregar() {
        const token = localStorage.getItem('token');
        if (!token) {
            return;
        }
        try {
            const response = await fetch(`${API_ROOT}/dashboard/conformidade`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const dados = await response.json();

            barras(porTipo, dados.tarjas_por_tipo.map((t) => ({ rotulo: t.rotulo, valor: t.quantidade })),
                'Nenhum dado tarjado ainda.');
            barras(porMes, dados.por_mes.map((m) => ({
                rotulo: nomeDoMes(m.mes), valor: m.tarjas, texto: `${m.tarjas} tarja(s) · ${m.documentos} doc.`,
            })), 'Nenhum documento nos últimos meses.');

            if (!dados.negados.visivel) {
                negadosTotal.textContent = '-';
                negados.innerHTML = '<p class="empty-message">Visível para supervisor e líder, como a auditoria.</p>';
            } else {
                negadosTotal.textContent = dados.negados.total;
                barras(negados, dados.negados.por_acao.map((n) => ({
                    rotulo: ROTULOS_ACAO[n.acao] || n.acao, valor: n.quantidade,
                })), `Nenhum acesso negado nos últimos ${dados.negados.dias} dias.`);
            }
        } catch (erro) {
            console.error('Painel de conformidade:', erro);
            [porTipo, porMes, negados].forEach((alvo) => {
                alvo.innerHTML = '<p class="empty-message">Não foi possível carregar os indicadores.</p>';
            });
        }
    }

    carregar();
})();
