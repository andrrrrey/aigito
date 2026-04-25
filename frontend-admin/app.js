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

        document.getElementById('login-password').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') document.getElementById('btn-login').click();
        });
    },
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
