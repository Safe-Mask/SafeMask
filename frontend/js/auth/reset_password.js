const API_URL = 'https://safemask-3.onrender.com/auth';

function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name) || '';
}

const form = document.getElementById('resetPasswordForm');
const emailInput = document.getElementById('email');
const senhaInput = document.getElementById('senha');
const confirmarInput = document.getElementById('confirmar_senha');
const feedback = document.getElementById('reset-feedback');

// Preenche o email a partir da query string e torna read-only
const emailFromQuery = getQueryParam('email');
emailInput.value = emailFromQuery;

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const senha = senhaInput.value.trim();
    const confirmar = confirmarInput.value.trim();

    feedback.textContent = '';

    if (!senha || !confirmar) {
        feedback.textContent = 'Preencha os campos de senha.';
        return;
    }
    if (senha !== confirmar) {
        feedback.textContent = 'As senhas não coincidem.';
        return;
    }

    const token = getQueryParam('token');
    if (!token) {
        feedback.textContent = 'Token de redefinição ausente.';
        return;
    }

    try {
        const resp = await fetch(`${API_URL}/reset-senha`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, senha }),
        });

        const data = await resp.json();
        if (!resp.ok) {
            feedback.textContent = data.detail || data.mensagem || 'Erro ao redefinir senha.';
            return;
        }

        feedback.textContent = data.mensagem || 'Senha alterada com sucesso.';
        // opcional: redirecionar para login
        setTimeout(() => { window.location.href = '/html/auth/login.html'; }, 1500);
    } catch (err) {
        console.error(err);
        feedback.textContent = 'Erro ao comunicar com o servidor.';
    }
});
