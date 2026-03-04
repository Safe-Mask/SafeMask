const btnLogin = document.getElementById("btnLogin");
const btnRegister = document.getElementById("btnRegister");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");

btnLogin.onclick = () => {
    btnLogin.classList.add("active");
    btnRegister.classList.remove("active");
    loginForm.classList.add("active");
    registerForm.classList.remove("active");
};

btnRegister.onclick = () => {
    btnRegister.classList.add("active");
    btnLogin.classList.remove("active");
    registerForm.classList.add("active");
    loginForm.classList.remove("active");
};

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
            alert('Cadastro realizado com sucesso.');

            btnLogin.classList.add("active");
            btnRegister.classList.remove("active");
            loginForm.classList.add("active");
            registerForm.classList.remove("active");
        } else {
            alert(data.detail || 'Erro ao realizar o cadastro.');
        }
    } catch (error) {
        alert('Erro ao se comunicar com o servidor.');
        console.error(error);
    }
})