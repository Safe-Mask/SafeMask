// Sessao do usuario: ponto unico de leitura/escrita do token e do papel.
// Antes cada pagina repetia `localStorage.getItem('token')` e nao havia papel
// salvo, o que impedia esconder itens de menu por cargo.
window.AppShell = window.AppShell || {};

(function () {
    // Nivel de cada cargo no backend: membro=1, supervisor=2, lider=3.
    const NIVEL_POR_CARGO = { membro: 1, supervisor: 2, lider: 3 };

    function getToken() {
        return localStorage.getItem('token');
    }

    function getNome() {
        return localStorage.getItem('userName') || 'Usuario';
    }

    // Papel e guardado como nome de cargo ('lider'), nao como numero.
    function getCargo() {
        const bruto = (localStorage.getItem('cargo') || '').toLowerCase();
        return bruto in NIVEL_POR_CARGO ? bruto : '';
    }

    function getNivel() {
        return NIVEL_POR_CARGO[getCargo()] || 0;
    }

    function temCargoMinimo(cargoMinimo) {
        const alvo = String(cargoMinimo || '').toLowerCase();
        if (!(alvo in NIVEL_POR_CARGO)) return false;
        return getNivel() >= NIVEL_POR_CARGO[alvo];
    }

    function salvar({ token, nome, cargo, userId }) {
        if (token) localStorage.setItem('token', token);
        if (nome) localStorage.setItem('userName', nome);
        if (userId) localStorage.setItem('userId', String(userId));
        // Chave legada 'role' mantida por compatibilidade com paginas antigas.
        if (cargo) {
            localStorage.setItem('cargo', cargo);
            localStorage.setItem('role', cargo);
        }
    }

    function limpar() {
        ['token', 'userName', 'userId', 'cargo', 'role', 'userTeams'].forEach((chave) => {
            localStorage.removeItem(chave);
        });
    }

    function exigirLogin(caminhoLogin = '../auth/login.html') {
        if (getToken()) return true;
        window.location.href = caminhoLogin;
        return false;
    }

    function logout(caminhoSaida = '/index.html') {
        limpar();
        window.location.href = caminhoSaida;
    }

    window.AppShell.Sessao = {
        getToken,
        getNome,
        getCargo,
        getNivel,
        temCargoMinimo,
        salvar,
        limpar,
        exigirLogin,
        logout,
        NIVEL_POR_CARGO,
    };
})();