const API_URL = 'http://127.0.0.1:8000/auth';

document.getElementById('loginForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const email = document.getElementById('login-email').value;
    const senha = document.getElementById('login-senha').value;

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                senha_hash: senha
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Login realizado com sucesso.');
            localStorage.setItem('token', data.access_token);

            window.location.href = '../../index.html';
        } else {
            alert(data.detail || 'Erro ao fazer login.');
        }
    } catch (error) {
        alert('Erro ao se comunicar com o servidor.');
        console.error(error);
    }
})