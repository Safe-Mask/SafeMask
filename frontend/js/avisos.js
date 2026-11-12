/* Avisos e confirmacoes do site (PBI E6-04, #195).

   Substitui as caixas do navegador (alert/confirm), que travam a pagina,
   nao seguem o visual do SafeMask e nao deixam escolher o texto dos botoes.

   Uso:
     avisar('Documento enviado.', 'sucesso');      // 'erro' (padrao), 'sucesso', 'info'
     const ok = await confirmar({
         titulo: 'Excluir documento',
         mensagem: 'Esta acao nao pode ser desfeita.',
         confirmar: 'Excluir',
         perigo: true,
     });

   Carregar ANTES do script da tela, junto com css/avisos.css.
*/
(function () {
    'use strict';

    const DURACAO_PADRAO = { erro: 7000, sucesso: 4000, info: 5000 };
    const TITULO = { erro: 'Atenção', sucesso: 'Pronto', info: 'Aviso' };

    function areaDeAvisos() {
        let area = document.getElementById('sm-avisos');
        if (!area) {
            area = document.createElement('div');
            area.id = 'sm-avisos';
            area.className = 'sm-avisos';
            document.body.appendChild(area);
        }
        return area;
    }

    function fechar(aviso) {
        if (!aviso.isConnected) {
            return;
        }
        aviso.classList.add('sm-aviso--saindo');
        setTimeout(() => aviso.remove(), 200);
    }

    /** Mostra um aviso no canto da tela, sem travar a pagina. Devolve o elemento. */
    function avisar(mensagem, tipo = 'erro', opcoes = {}) {
        const tipoValido = DURACAO_PADRAO[tipo] ? tipo : 'info';
        const aviso = document.createElement('div');
        aviso.className = `sm-aviso sm-aviso--${tipoValido}`;
        // Erro interrompe o leitor de tela; sucesso e informacao esperam a vez.
        aviso.setAttribute('role', tipoValido === 'erro' ? 'alert' : 'status');

        const texto = document.createElement('div');
        texto.className = 'sm-aviso__texto';
        const titulo = document.createElement('strong');
        titulo.textContent = opcoes.titulo || TITULO[tipoValido];
        const corpo = document.createElement('p');
        corpo.textContent = String(mensagem || '');
        texto.append(titulo, corpo);

        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'sm-aviso__fechar';
        botao.setAttribute('aria-label', 'Fechar aviso');
        botao.textContent = '×';
        botao.addEventListener('click', () => fechar(aviso));

        aviso.append(texto, botao);
        areaDeAvisos().appendChild(aviso);

        const duracao = opcoes.duracao ?? DURACAO_PADRAO[tipoValido];
        if (duracao > 0) {
            setTimeout(() => fechar(aviso), duracao);
        }
        return aviso;
    }

    /** Janela de confirmacao do site. Resolve true (confirmou) ou false (cancelou). */
    function confirmar(opcoes = {}) {
        const {
            titulo = 'Confirmar',
            mensagem = '',
            confirmar: rotuloConfirmar = 'Confirmar',
            cancelar: rotuloCancelar = 'Cancelar',
            perigo = false,
        } = opcoes;

        return new Promise((resolver) => {
            const focoAnterior = document.activeElement;
            const fundo = document.createElement('div');
            fundo.className = 'sm-confirmacao';

            const janela = document.createElement('div');
            janela.className = 'sm-confirmacao__janela';
            janela.setAttribute('role', 'alertdialog');
            janela.setAttribute('aria-modal', 'true');
            janela.setAttribute('aria-labelledby', 'sm-confirmacao-titulo');
            janela.setAttribute('aria-describedby', 'sm-confirmacao-mensagem');

            const h = document.createElement('h2');
            h.id = 'sm-confirmacao-titulo';
            h.textContent = titulo;
            const p = document.createElement('p');
            p.id = 'sm-confirmacao-mensagem';
            p.textContent = mensagem;

            const acoes = document.createElement('div');
            acoes.className = 'sm-confirmacao__acoes';
            const botaoCancelar = document.createElement('button');
            botaoCancelar.type = 'button';
            botaoCancelar.className = 'sm-botao sm-botao--secundario';
            botaoCancelar.textContent = rotuloCancelar;
            const botaoConfirmar = document.createElement('button');
            botaoConfirmar.type = 'button';
            botaoConfirmar.className = `sm-botao ${perigo ? 'sm-botao--perigo' : 'sm-botao--primario'}`;
            botaoConfirmar.textContent = rotuloConfirmar;
            acoes.append(botaoCancelar, botaoConfirmar);

            janela.append(h, p, acoes);
            fundo.appendChild(janela);
            document.body.appendChild(fundo);

            function terminar(resposta) {
                document.removeEventListener('keydown', teclado, true);
                fundo.remove();
                if (focoAnterior && typeof focoAnterior.focus === 'function') {
                    focoAnterior.focus();
                }
                resolver(resposta);
            }

            function teclado(evento) {
                if (evento.key === 'Escape') {
                    evento.preventDefault();
                    terminar(false);
                } else if (evento.key === 'Tab') {
                    // Mantem o foco dentro da janela.
                    const focaveis = [botaoCancelar, botaoConfirmar];
                    const atual = focaveis.indexOf(document.activeElement);
                    evento.preventDefault();
                    const proximo = evento.shiftKey ? atual - 1 : atual + 1;
                    focaveis[(proximo + focaveis.length) % focaveis.length].focus();
                }
            }

            botaoCancelar.addEventListener('click', () => terminar(false));
            botaoConfirmar.addEventListener('click', () => terminar(true));
            fundo.addEventListener('click', (evento) => {
                if (evento.target === fundo) {
                    terminar(false);
                }
            });
            document.addEventListener('keydown', teclado, true);

            // Acao perigosa: o foco comeca em "Cancelar", para Enter nao apagar nada.
            (perigo ? botaoCancelar : botaoConfirmar).focus();
        });
    }

    // Aviso que precisa sobreviver a uma troca de pagina (o alert travava a
    // pagina ate o clique e so depois redirecionava): guardado na sessao e
    // mostrado pela proxima tela que carregar este componente.
    const CHAVE_PENDENTE = 'sm-aviso-pendente';

    function avisarDepois(mensagem, tipo = 'erro') {
        try {
            sessionStorage.setItem(CHAVE_PENDENTE, JSON.stringify({ mensagem, tipo }));
        } catch (erro) {
            // Sem sessionStorage (modo restrito), o aviso se perde; nada trava.
        }
    }

    function mostrarPendente() {
        let pendente = null;
        try {
            pendente = JSON.parse(sessionStorage.getItem(CHAVE_PENDENTE) || 'null');
            sessionStorage.removeItem(CHAVE_PENDENTE);
        } catch (erro) {
            pendente = null;
        }
        if (pendente && pendente.mensagem) {
            avisar(pendente.mensagem, pendente.tipo);
        }
    }

    window.avisar = avisar;
    window.avisarDepois = avisarDepois;
    window.confirmar = confirmar;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', mostrarPendente);
    } else {
        mostrarPendente();
    }
})();
