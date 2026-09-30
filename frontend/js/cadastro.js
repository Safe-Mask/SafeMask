const API_URL = `${API_ROOT}/auth`;

// Validação de formato de email
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Validar campo nome obrigatório
document.getElementById('cadastro-nome').addEventListener('blur', (e) => {
    const nome = e.target.value;
    const nomeInput = e.target;
    const validationMsg = document.getElementById('nome-validation');
    
    if (nome.trim() === '') {
        validationMsg.textContent = 'Nome é obrigatório';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        nomeInput.classList.remove('valid');
        nomeInput.classList.add('invalid');
    } else {
        validationMsg.textContent = '';
        nomeInput.classList.remove('invalid');
    }
});

// Validar formato do email ao sair do campo.
//
// Só formato, de propósito. A versão anterior consultava
// `/auth/verificar-email/{email}` e mostrava "Email já cadastrado" ou
// "Email disponível": um endpoint público que respondia {"existe": bool}
// permitia montar a lista de quem usa o sistema, sem login. O e-mail em uso
// agora só é revelado no envio do cadastro, que precisa responder de qualquer
// forma para a pessoa saber o que aconteceu.
document.getElementById('cadastro-email').addEventListener('blur', (e) => {
    const email = e.target.value.trim();
    const validationMsg = document.getElementById('email-validation');
    const emailInput = e.target;

    if (email === '') {
        validationMsg.textContent = 'Email é obrigatório';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        emailInput.classList.remove('valid');
        emailInput.classList.add('invalid');
        return;
    }

    if (!emailRegex.test(email)) {
        validationMsg.textContent = 'Email inválido';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        emailInput.classList.remove('valid');
        emailInput.classList.add('invalid');
        return;
    }

    validationMsg.textContent = '';
    validationMsg.classList.remove('valid', 'invalid');
    emailInput.classList.remove('invalid');
    emailInput.classList.add('valid');
});

// Validar força da senha em tempo real
document.getElementById('cadastro-senha').addEventListener('blur', (e) => {
    const senha = e.target.value;
    const senhaInput = e.target;
    const validationMsg = document.getElementById('senha-validation');

    if (senha.trim() === '') {
        validationMsg.textContent = 'Senha é obrigatória';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        senhaInput.classList.remove('valid');
        senhaInput.classList.add('invalid');
    }
});

document.getElementById('cadastro-senha').addEventListener('input', (e) => {
    const senha = e.target.value;
    const senhaInput = e.target;
    const strengthFill = document.getElementById('strength-fill');
    const strengthText = document.getElementById('strength-text');
    const validationMsg = document.getElementById('senha-validation');

    let strength = 0;
    let requirements = [];

    // Verificar requisitos
    if (/[0-9]/.test(senha)) {
        strength++;
        requirements.push('✓ Números');
    } else {
        requirements.push('✗ Números');
    }

    if (/[a-z]/.test(senha)) {
        strength++;
        requirements.push('✓ Minúsculas');
    } else {
        requirements.push('✗ Minúsculas');
    }

    if (/[A-Z]/.test(senha)) {
        strength++;
        requirements.push('✓ Maiúsculas');
    } else {
        requirements.push('✗ Maiúsculas');
    }

    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(senha)) {
        strength++;
        requirements.push('✓ Caracteres especiais');
    }

    if (senha.length >= 8) {
        strength++;
    } else {
        requirements.push(`✗ Mínimo 8 caracteres (${senha.length}/8)`);
    }

    // Atualizar barra de força
    strengthFill.className = 'strength-fill';
    if (senha.length === 0) {
        strengthFill.style.width = '0%';
        strengthText.textContent = '';
        validationMsg.textContent = '';
        senhaInput.classList.remove('valid', 'invalid');
    } else if (strength <= 2) {
        strengthFill.classList.add('weak');
        strengthText.textContent = 'Fraca';
        validationMsg.textContent = 'Senha muito fraca. Requisitos: números, minúsculas, maiúsculas e mínimo 8 caracteres';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        senhaInput.classList.remove('valid');
        senhaInput.classList.add('invalid');
    } else if (strength === 3) {
        strengthFill.classList.add('medium');
        strengthText.textContent = 'Média';
        validationMsg.textContent = 'Adicione números ou caracteres especiais para melhorar';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        senhaInput.classList.remove('valid');
        senhaInput.classList.add('invalid');
    } else {
        strengthFill.classList.add('strong');
        strengthText.textContent = 'Forte';
        validationMsg.textContent = 'Senha forte';
        validationMsg.classList.remove('invalid');
        validationMsg.classList.add('valid');
        senhaInput.classList.remove('invalid');
        senhaInput.classList.add('valid');
    }
});

document.getElementById('registerForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const nome = document.getElementById('cadastro-nome').value;
    const email = document.getElementById('cadastro-email').value;
    const senha = document.getElementById('cadastro-senha').value;
    const emailInput = document.getElementById('cadastro-email');
    const senhaInput = document.getElementById('cadastro-senha');

    // Validações finais
    if (!emailInput.classList.contains('valid')) {
        alert('Por favor, use um email válido e disponível.');
        return;
    }

    if (!senhaInput.classList.contains('valid')) {
        alert('Por favor, use uma senha forte.');
        return;
    }

    console.log('Dados enviados: ', { nome, email, senha });
    console.log('JSON enviado: ', JSON.stringify({ nome, email, senha }));

    // Iniciar animação de loading (puzzle)
    loadingManager.show('Montando sua conta segura...');

    // Fazer requisição ao backend em paralelo
    const requestPromise = fetch(`${API_URL}/cadastro`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            nome: nome,
            email: email,
            senha_hash: senha
        })
    }).then(response => response.json());

    try {
        const data = await requestPromise;

        // Verificar resultado do backend enquanto o puzzle ainda se move
        if (data.access_token) {
            await loadingManager.assemblePuzzle();
            await new Promise(resolve => setTimeout(resolve, 800));
            loadingManager.hide();
            localStorage.setItem('token', data.access_token);
            const user = data.user || {};
            AppShell.Sessao.salvar({
                token: data.access_token,
                nome: user.nome || '',
                cargo: user.cargo || '',
                userId: user.user_id,
            });
            window.location.href = '../dashboard.html';
        } else {
            await loadingManager.failPuzzle();
            loadingManager.hide();
            alert(data.detail || 'Erro ao realizar o cadastro.');
            window.location.href = 'login.html';
        }
    } catch (error) {
        await loadingManager.failPuzzle();
        loadingManager.hide();
        alert('Erro ao se comunicar com o servidor.');
        window.location.href = 'login.html';
        console.error(error);
    }
})