const API_URL = 'https://safemask-3.onrender.com/auth';

const forgotPasswordForm = document.getElementById('forgotPasswordForm');
const recoveryEmailInput = document.getElementById('recovery-email');
const recoveryEmailValidation = document.getElementById('recovery-email-validation');
const recoveryFeedback = document.getElementById('recovery-feedback');

function setRecoveryMessage(message, type) {
    recoveryFeedback.textContent = message;
    recoveryFeedback.classList.remove('valid', 'invalid');

    if (type) {
        recoveryFeedback.classList.add(type);
    }
}

recoveryEmailInput.addEventListener('blur', (event) => {
    const email = event.target.value.trim();

    if (!email) {
        recoveryEmailValidation.textContent = 'Email é obrigatório';
        recoveryEmailValidation.classList.remove('valid');
        recoveryEmailValidation.classList.add('invalid');
        recoveryEmailInput.classList.remove('valid');
        recoveryEmailInput.classList.add('invalid');
        return;
    }

    recoveryEmailValidation.textContent = '';
    recoveryEmailValidation.classList.remove('invalid');
    recoveryEmailInput.classList.remove('invalid');
});

forgotPasswordForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const email = recoveryEmailInput.value.trim();
    if (!email) {
        recoveryEmailValidation.textContent = 'Email é obrigatório';
        recoveryEmailValidation.classList.remove('valid');
        recoveryEmailValidation.classList.add('invalid');
        recoveryEmailInput.classList.add('invalid');
        return;
    }

    loadingManager.show('Verificando seu email...');
    setRecoveryMessage('', null);

    try {
        const response = await fetch(`${API_URL}/recuperar-senha`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email }),
        });

        const data = await response.json();

        if (!response.ok) {
            await loadingManager.failPuzzle();
            loadingManager.hide();
            setRecoveryMessage(data.detail || 'Não foi possível localizar esse email.', 'invalid');
            return;
        }

        await loadingManager.assemblePuzzle();
        await new Promise((resolve) => setTimeout(resolve, 600));
        loadingManager.hide();

        setRecoveryMessage(data.mensagem || 'Email de recuperação enviado com sucesso.', 'valid');
        recoveryEmailInput.classList.remove('invalid');
        recoveryEmailInput.classList.add('valid');
    } catch (error) {
        await loadingManager.failPuzzle();
        loadingManager.hide();
        console.error(error);
        setRecoveryMessage('Erro ao se comunicar com o servidor.', 'invalid');
    }
});