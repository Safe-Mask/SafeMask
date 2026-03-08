const API_URL = 'http://127.0.0.1:8000/auth';

// Validar email ao sair do campo
document.getElementById('cadastro-email').addEventListener('blur', async (e) => {
    const email = e.target.value;
    const validationMsg = document.getElementById('email-validation');
    const emailInput = e.target;

    if (email.trim() === '') {
        validationMsg.textContent = '';
        emailInput.classList.remove('valid', 'invalid');
        return;
    }

    // Validação de formato de email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        validationMsg.textContent = 'Email inválido';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        emailInput.classList.remove('valid');
        emailInput.classList.add('invalid');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/verificar-email/${email}`);
        const data = await response.json();

        if (data.existe) {
            validationMsg.textContent = 'Email já cadastrado';
            validationMsg.classList.remove('valid');
            validationMsg.classList.add('invalid');
            emailInput.classList.remove('valid');
            emailInput.classList.add('invalid');
        } else {
            validationMsg.textContent = 'Email disponível';
            validationMsg.classList.remove('invalid');
            validationMsg.classList.add('valid');
            emailInput.classList.remove('invalid');
            emailInput.classList.add('valid');
        }
    } catch (error) {
        console.error('Erro ao verificar email:', error);
    }
});

// Validar força da senha em tempo real
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

    try {
        const response = await fetch(`${API_URL}/cadastro`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                nome: nome,
                email: email,
                senha_hash: senha
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Cadastro realizado com sucesso. Você foi logado automaticamente.');
            localStorage.setItem('token', data.access_token);

            window.location.href = '../../../index.html';
        } else {
            alert(data.detail || 'Erro ao realizar o cadastro.');
        }
    } catch (error) {
        alert('Erro ao se comunicar com o servidor.');
        console.error(error);
    }
})