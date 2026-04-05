'use strict';

const API = {
    baseUrl: '/api',

    getToken() {
        return localStorage.getItem('aigito_token');
    },

    setToken(token) {
        localStorage.setItem('aigito_token', token);
    },

    clearToken() {
        localStorage.removeItem('aigito_token');
    },

    async request(method, path, body = null, isForm = false) {
        const headers = {};
        const token = this.getToken();
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const opts = { method, headers };

        if (body) {
            if (isForm) {
                opts.body = body; // FormData
            } else {
                headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(body);
            }
        }

        const res = await fetch(`${this.baseUrl}${path}`, opts);

        if (res.status === 401) {
            this.clearToken();
            window.location.href = '/admin/index.html';
            return null;
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || 'Request failed');
        }

        if (res.status === 204) return null;
        return res.json();
    },

    // Auth
    login: (email, password) => API.request('POST', '/auth/login', null, true) || (() => {
        const form = new URLSearchParams();
        form.append('username', email);
        form.append('password', password);
        return fetch(`${API.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form,
        }).then(r => r.json());
    })(),

    async loginUser(email, password) {
        const form = new URLSearchParams();
        form.append('username', email);
        form.append('password', password);
        const res = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form,
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
        return res.json();
    },

    register: (email, password, fullName) =>
        API.request('POST', '/auth/register', { email, password, full_name: fullName }),

    // Companies
    getCompany: () => API.request('GET', '/companies/me'),
    updateCompany: (data) => API.request('PUT', '/companies/me', data),
    updateAvatar: (data) => API.request('PUT', '/companies/me/avatar', data),
    uploadAvatarImage: (file) => {
        const fd = new FormData();
        fd.append('file', file);
        return API.request('POST', '/companies/me/avatar/upload', fd, true);
    },
    createCompany: (data) => API.request('POST', '/companies/', data),

    // API Keys
    getApiKeys: () => API.request('GET', '/companies/me/api-keys'),
    updateApiKeys: (data) => API.request('PUT', '/companies/me/api-keys', data),

    // Knowledge
    getDocuments: () => API.request('GET', '/knowledge/documents'),
    uploadDocument: (formData) => API.request('POST', '/knowledge/documents/upload', formData, true),
    deleteDocument: (id) => API.request('DELETE', `/knowledge/documents/${id}`),
    rebuildIndex: () => API.request('POST', '/knowledge/rebuild'),

    // Analytics
    getSummary: () => API.request('GET', '/analytics/summary'),
    getDialogs: (limit = 50, offset = 0) => API.request('GET', `/analytics/dialogs?limit=${limit}&offset=${offset}`),
    getTopics: () => API.request('GET', '/analytics/topics'),
    getUsage: () => API.request('GET', '/analytics/usage'),
};
