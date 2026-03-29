'use strict';

const AdminApp = {
    async init() {
        const token = API.getToken();

        // If on index.html (login page)
        if (window.location.pathname.endsWith('index.html') || window.location.pathname === '/admin/' || window.location.pathname === '/admin') {
            if (token) {
                window.location.href = '/admin/pages/dashboard.html';
                return;
            }
            this.initAuthPage();
        }
    },

    initAuthPage() {
        document.getElementById('show-register').addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('login-form').style.display = 'none';
            document.getElementById('register-form').style.display = 'block';
        });
        document.getElementById('show-login').addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('register-form').style.display = 'none';
            document.getElementById('login-form').style.display = 'block';
        });

        document.getElementById('btn-login').addEventListener('click', async () => {
            const email = document.getElementById('login-email').value.trim();
            const password = document.getElementById('login-password').value;
            const errEl = document.getElementById('login-error');
            try {
                const res = await API.loginUser(email, password);
                API.setToken(res.access_token);
                window.location.href = '/admin/pages/dashboard.html';
            } catch (e) {
                errEl.textContent = e.message;
                errEl.style.display = 'block';
            }
        });

        document.getElementById('btn-register').addEventListener('click', async () => {
            const name = document.getElementById('reg-name').value.trim();
            const email = document.getElementById('reg-email').value.trim();
            const password = document.getElementById('reg-password').value;
            const errEl = document.getElementById('register-error');
            try {
                const res = await API.register(email, password, name);
                API.setToken(res.access_token);
                window.location.href = '/admin/pages/dashboard.html';
            } catch (e) {
                errEl.textContent = e.message;
                errEl.style.display = 'block';
            }
        });
    },
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
