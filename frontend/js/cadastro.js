const API_URL = 'http://127.0.0.1:8000/auth';

document.getElementById('registerForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const nome = document.getElementById('cadastro-nome').value;
    const email = document.getElementById('cadastro-email').value;
    const senha = document.getElementById('cadastro-senha').value;

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

            window.location.href = '../../index.html';
        } else {
            alert(data.detail || 'Erro ao realizar o cadastro.');
        }
    } catch (error) {
        alert('Erro ao se comunicar com o servidor.');
        console.error(error);
    }
})