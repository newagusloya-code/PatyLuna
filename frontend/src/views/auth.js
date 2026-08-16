import { api, setTokens } from '../api.js';

export class LoginView {
  constructor() {
    this.container = document.createElement('div');
    this.container.className = 'auth-container';
    this.isRegistering = false;
  }

  async handleSubmit(e) {
    e.preventDefault();
    const email = this.container.querySelector('#email').value;
    const password = this.container.querySelector('#password').value;
    const errorBox = this.container.querySelector('#auth-error');
    const submitBtn = this.container.querySelector('#submit-btn');

    errorBox.textContent = '';
    errorBox.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Ingresando...';

    try {
      const emailInput = this.container.querySelector('#email');
      const passwordInput = this.container.querySelector('#password');
      const email = emailInput ? emailInput.value.trim() : '';
      const password = passwordInput ? passwordInput.value : '';

      if (!email || !password) {
        throw new Error('Por favor ingresa tu correo y contraseña');
      }

      if (this.isRegistering) {
        const usernameInput = this.container.querySelector('#username');
        const username = usernameInput ? usernameInput.value.trim() : '';
        if (!username) {
          throw new Error('Por favor ingresa tu nombre');
        }

        const res = await api('/auth/register', {
          method: 'POST',
          body: { email, username, password },
        });

        if (!res.ok) {
          let errData = {};
          try {
            errData = await res.json();
          } catch (jsonErr) {
            const rawText = await res.text().catch(() => '');
            errData = { detail: rawText || `Error del servidor (${res.status})` };
          }
          let errorMsg = 'Error al crear la cuenta';
          if (typeof errData.detail === 'string') {
            errorMsg = errData.detail;
          } else if (Array.isArray(errData.detail)) {
            errorMsg = errData.detail.map(e => {
              const field = e.loc ? e.loc[e.loc.length - 1] : '';
              let msg = e.msg ? e.msg.replace('Value error, ', '') : 'Campo inválido';
              if (msg.toLowerCase().includes('field required')) msg = 'Este campo es obligatorio';
              const fieldNames = { username: 'Nombre', email: 'Correo', password: 'Contraseña' };
              const translatedField = fieldNames[field];
              return translatedField ? `${translatedField}: ${msg}` : msg;
            }).join(' | ');
          }
          throw new Error(errorMsg);
        }

        this.isRegistering = false;
        await this.login(email, password);
      } else {
        await this.login(email, password);
      }
    } catch (err) {
      errorBox.textContent = err.message;
      errorBox.style.display = 'block';
      this.container.querySelector('.card').animate([
        { transform: 'translateX(0)' },
        { transform: 'translateX(-10px)' },
        { transform: 'translateX(10px)' },
        { transform: 'translateX(0)' },
      ], { duration: 300 });
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = this.isRegistering ? 'Crear mi espacio' : 'Entrar al Santuario';
    }
  }

  async login(email, password) {
    const res = await api('/auth/login', {
      method: 'POST',
      body: { email, password },
    });

    if (!res.ok) {
      let errData = {};
      try {
        errData = await res.json();
      } catch (jsonErr) {
        const rawText = await res.text().catch(() => '');
        errData = { detail: rawText || `Error del servidor (${res.status})` };
      }
      let errorMsg = 'Credenciales no válidas';
      if (typeof errData.detail === 'string') {
        errorMsg = errData.detail;
      } else if (Array.isArray(errData.detail)) {
        errorMsg = errData.detail.map(e => {
          const field = e.loc ? e.loc[e.loc.length - 1] : '';
          let msg = e.msg ? e.msg.replace('Value error, ', '') : 'Campo inválido';
          if (msg.toLowerCase() === 'field required') msg = 'Este campo es obligatorio';
          const fieldNames = { username: 'Nombre', email: 'Correo', password: 'Contraseña' };
          const translatedField = fieldNames[field] || field;
          return translatedField ? `${translatedField}: ${msg}` : msg;
        }).join(' | ');
      }
      throw new Error(errorMsg);
    }

    let data = {};
    try {
      data = await res.json();
    } catch (e) {
      throw new Error('Error al procesar la respuesta del servidor');
    }
    setTokens(data.access_token, data.refresh_token);
    window.location.hash = '#/dashboard';
  }

  toggleMode() {
    this.isRegistering = !this.isRegistering;
    this.renderForm();
  }

  renderForm() {
    this.container.innerHTML = `
      <div class="auth-wrapper" style="max-width: 420px; margin: 40px auto; padding: 0 16px;">
        <div class="card" style="padding: 32px 28px; border: 1px solid var(--border-color); box-shadow: 0 10px 40px rgba(0,0,0,0.5);">
          
          <!-- Logo & Header Paty Luna -->
          <div style="text-align: center; margin-bottom: 24px;">
            <div style="font-size: 3rem; margin-bottom: 8px; filter: drop-shadow(0 0 12px rgba(251, 191, 36, 0.4));">🌙</div>
            <h2 style="font-weight: 400; font-size: 1.8rem; margin-bottom: 4px; color: var(--text-primary);">
              Paty Luna
            </h2>
            <p style="font-size: 0.9rem; color: var(--text-secondary); margin: 0;">
              ${this.isRegistering ? 'Crea tu espacio personal de paz' : 'Bienvenida a tu santuario nocturno'}
            </p>
          </div>

          <div id="auth-error" style="display: none; color: var(--accent-danger); margin-bottom: 16px; font-size: 0.85rem; text-align: center; background: rgba(248, 113, 113, 0.1); padding: 8px; border-radius: 6px;"></div>

          <form id="auth-form" style="display: flex; flex-direction: column; gap: 16px;">
            ${this.isRegistering ? `
            <div>
              <label style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 4px;">Tu Nombre</label>
              <input type="text" id="username" required placeholder="Patricia" style="width: 100%; padding: 12px; border-radius: 8px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary);">
            </div>
            ` : ''}
            <div>
              <label style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 4px;">Correo electrónico</label>
              <input type="email" id="email" required placeholder="tu@correo.com" style="width: 100%; padding: 12px; border-radius: 8px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary);">
            </div>
            <div>
              <label style="font-size: 0.85rem; color: var(--text-secondary); display: block; margin-bottom: 4px;">Contraseña</label>
              <input type="password" id="password" required placeholder="••••••••" style="width: 100%; padding: 12px; border-radius: 8px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary);">
            </div>

            <button type="submit" class="btn primary" id="submit-btn" style="margin-top: 8px; padding: 14px; font-size: 1rem; border-radius: 8px; font-weight: 600;">
              ${this.isRegistering ? 'Crear mi espacio' : 'Entrar al Santuario'}
            </button>
          </form>

          <div style="margin-top: 24px; text-align: center; font-size: 0.85rem;">
            <a href="#" id="toggle-mode-btn" style="color: var(--text-secondary);">
              ${this.isRegistering ? '¿Ya tienes cuenta? Inicia sesión aquí' : '¿Primera vez en Paty Luna? Regístrate'}
            </a>
          </div>
        </div>
      </div>
    `;

    this.container.querySelector('#auth-form').addEventListener('submit', (e) => this.handleSubmit(e));
    this.container.querySelector('#toggle-mode-btn').addEventListener('click', (e) => {
      e.preventDefault();
      this.toggleMode();
    });
  }

  async render() {
    this.renderForm();
    const nav = document.getElementById('top-nav');
    if (nav) nav.innerHTML = '';
    return this.container;
  }
}
