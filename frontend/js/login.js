const API_URL = 'https://safemask-3.onrender.com/auth';

// Validar campos obrigatórios no login
document.getElementById('login-email').addEventListener('blur', (e) => {
    const email = e.target.value;
    const emailInput = e.target;
    const validationMsg = document.getElementById('email-login-validation');
    
    if (email.trim() === '') {
        validationMsg.textContent = 'Email é obrigatório';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        emailInput.classList.remove('valid');
        emailInput.classList.add('invalid');
    } else {
        validationMsg.textContent = '';
        emailInput.classList.remove('invalid');
    }
});

document.getElementById('login-senha').addEventListener('blur', (e) => {
    const senha = e.target.value;
    const senhaInput = e.target;
    const validationMsg = document.getElementById('senha-login-validation');
    
    if (senha.trim() === '') {
        validationMsg.textContent = 'Senha é obrigatória';
        validationMsg.classList.remove('valid');
        validationMsg.classList.add('invalid');
        senhaInput.classList.remove('valid');
        senhaInput.classList.add('invalid');
    } else {
        validationMsg.textContent = '';
        senhaInput.classList.remove('invalid');
    }
});

document.getElementById('loginForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const email = document.getElementById('login-email').value;
    const senha = document.getElementById('login-senha').value;

    // Iniciar animação de loading (puzzle)
    loadingManager.show('Montando seu acesso...');

    // Fazer requisição ao backend em paralelo
    const requestPromise = fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
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
            const userName = email.includes('@') ? email.split('@')[0] : email;
            localStorage.setItem('userName', userName);
            window.location.href = '../dashboard.html';
        } else {
            await loadingManager.failPuzzle();
            loadingManager.hide();
            alert(data.detail || 'Erro ao fazer login.');
        }
    } catch (error) {
        await loadingManager.failPuzzle();
        loadingManager.hide();
        alert('Erro ao se comunicar com o servidor.');
        console.error(error);
    }
})