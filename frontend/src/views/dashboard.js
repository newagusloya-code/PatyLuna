import { api, clearTokens } from '../api.js';
import { soundEngine } from '../audio.js';

export class DashboardView {
  constructor() {
    this.container = document.createElement('div');
    this.container.className = 'dashboard-container';
    this.userData = null;
  }

  async loadUserData() {
    try {
      const res = await api('/auth/me');
      if (res.ok) {
        this.userData = await res.json();
      }
    } catch (err) {
      console.error('No se pudo cargar el perfil', err);
    }
  }

  handleLogout(e) {
    e.preventDefault();
    soundEngine.stopAll();
    clearTokens();
    window.location.hash = '#/login';
  }

  updateNav() {
    const nav = document.getElementById('top-nav');
    if (nav) {
      nav.innerHTML = `
        <div style="display: flex; gap: 16px; align-items: center;">
          <span style="color: var(--text-secondary); font-size: 0.85rem;">
            ${this.userData ? `Bienvenida, ${this.userData.username}` : ''}
          </span>
          <a href="#" id="logout-btn" style="font-size: 0.85rem; color: var(--text-secondary);">Cerrar sesión</a>
        </div>
      `;
      nav.querySelector('#logout-btn').addEventListener('click', (e) => this.handleLogout(e));
    }
  }

  async render() {
    await this.loadUserData();
    this.updateNav();

    const name = this.userData ? this.userData.username : 'Paty';

    this.container.innerHTML = `
      <div style="max-width: 800px; margin: 0 auto; padding-bottom: 80px;">
        
        <!-- Saludo Principal Paty Luna -->
        <div style="text-align: center; margin-bottom: 36px; padding: 24px 16px;">
          <div style="font-size: 3rem; margin-bottom: 12px; filter: drop-shadow(0 0 15px rgba(251, 191, 36, 0.4));">🌙</div>
          <h1 style="font-weight: 300; font-size: 2.4rem; margin-bottom: 8px; color: var(--text-primary);">
            Buenas noches, ${name}
          </h1>
          <p style="font-size: 1.05rem; color: var(--text-secondary); font-style: italic; max-width: 500px; margin: 0 auto;">
            "Respira profundo, suelta el día y permítete descansar bajo la luz de la luna."
          </p>
        </div>

        <!-- Barra de Reproducción Rápida -->
        <div class="card" style="margin-bottom: 32px; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; background: radial-gradient(circle at 10% 20%, rgba(129, 140, 248, 0.12) 0%, var(--bg-elevated) 90%); border: 1px solid var(--accent-calm);">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 44px; height: 44px; border-radius: 50%; background: var(--bg-primary); display: flex; align-items: center; justify-content: center; font-size: 1.3rem;">
              🎧
            </div>
            <div>
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary);">Atmósfera Anti-Tinnitus & Sueño</div>
              <div style="font-size: 0.8rem; color: var(--text-secondary);">Ruido Marrón suave + 528 Hz + Lluvia</div>
            </div>
          </div>
          <button id="quick-play-btn" class="btn primary" style="padding: 8px 18px; font-size: 0.85rem; border-radius: 20px;">
            ${soundEngine.isPlaying ? 'Pausar' : 'Escuchar ahora'}
          </button>
        </div>

        <!-- 1. Frecuencias & Sonidos (Principal) -->
        <div class="card interactive-card" style="margin-bottom: 24px; cursor: pointer; padding: 24px; border: 2px solid var(--accent-calm); box-shadow: 0 0 20px rgba(129, 140, 248, 0.15);" onclick="window.location.hash='#/sounds'">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 14px;">
              <div style="width: 52px; height: 52px; border-radius: 14px; background-color: rgba(52, 211, 153, 0.15); display: flex; align-items: center; justify-content: center; font-size: 1.6rem;">
                🎧
              </div>
              <div>
                <h3 style="font-size: 1.3rem; color: var(--text-primary); margin-bottom: 2px;">Frecuencias & Sonidos</h3>
                <span style="font-size: 0.8rem; color: var(--accent-nature); font-weight: 500;">Generador Acústico</span>
              </div>
            </div>
            <div style="font-size: 1.5rem; color: var(--accent-calm);">›</div>
          </div>
          <p style="font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 20px;">
            Accede al mezclador completo para alivio de tinnitus, tonos armónicos y relajación nocturna.
          </p>

          <!-- Opciones Rápidas en Dashboard -->
          <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;" onclick="event.stopPropagation();">
            <button class="btn secondary dash-sound-btn" data-preset="tinnitus" style="padding: 10px; font-size: 0.8rem; display: flex; flex-direction: column; align-items: center; gap: 4px;">
              <span style="font-size: 1.2rem;">🍃</span> Alivio Tinnitus
            </button>
            <button class="btn secondary dash-sound-btn" data-preset="sueno432" style="padding: 10px; font-size: 0.8rem; display: flex; flex-direction: column; align-items: center; gap: 4px;">
              <span style="font-size: 1.2rem;">🌌</span> Sueño 432Hz
            </button>
            <button class="btn secondary dash-sound-btn" data-preset="lluvia_paz" style="padding: 10px; font-size: 0.8rem; display: flex; flex-direction: column; align-items: center; gap: 4px;">
              <span style="font-size: 1.2rem;">🌧️</span> Lluvia Noche
            </button>
            <button class="btn secondary dash-sound-btn" data-preset="paz528" style="padding: 10px; font-size: 0.8rem; display: flex; flex-direction: column; align-items: center; gap: 4px;">
              <span style="font-size: 1.2rem;">✨</span> Sanación 528Hz
            </button>
          </div>
        </div>

        <!-- 2. Santuario del Sueño / Noche -->
        <div class="card interactive-card" style="margin-bottom: 24px; cursor: pointer; padding: 24px; border: 1px solid var(--accent-calm); box-shadow: 0 0 15px rgba(129, 140, 248, 0.1);" onclick="window.location.hash='#/sleep'">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 14px;">
              <div style="width: 52px; height: 52px; border-radius: 14px; background-color: rgba(129, 140, 248, 0.15); display: flex; align-items: center; justify-content: center; font-size: 1.6rem;">
                🌙
              </div>
              <div>
                <h3 style="font-size: 1.3rem; color: var(--text-primary); margin-bottom: 2px;">Santuario del Sueño</h3>
                <span style="font-size: 0.8rem; color: var(--accent-calm); font-weight: 500;">Dormir & Despertar</span>
              </div>
            </div>
            <div style="font-size: 1.5rem; color: var(--accent-calm);">›</div>
          </div>
          <p style="font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 16px;">
            Guía de respiración 4-7-8, temporizador nocturno con desvanecimiento de sonido y registro matutino.
          </p>
        </div>

        <!-- 3. Therapy Room -->
        <div class="card interactive-card" style="cursor: pointer; padding: 24px; border: 1px solid var(--border-color);" onclick="window.location.hash='#/therapy'">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 14px;">
              <div style="width: 52px; height: 52px; border-radius: 14px; background-color: rgba(251, 191, 36, 0.15); display: flex; align-items: center; justify-content: center; font-size: 1.6rem;">
                🛋️
              </div>
              <div>
                <h3 style="font-size: 1.3rem; color: var(--text-primary); margin-bottom: 2px;">Therapy Room</h3>
                <span style="font-size: 0.8rem; color: #fbbf24; font-weight: 500;">Diario & IA</span>
              </div>
            </div>
            <div style="font-size: 1.5rem; color: var(--text-secondary);">›</div>
          </div>
          <p style="font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 0;">
            Chatea con tus terapeutas de IA, explora tus emociones y obtén consejos en tiempo real.
          </p>
        </div>

      </div>
    `;

    this.attachEvents();
    return this.container;
  }

  attachEvents() {
    const quickBtn = this.container.querySelector('#quick-play-btn');
    if (quickBtn) {
      quickBtn.addEventListener('click', () => {
        if (soundEngine.isPlaying) {
          soundEngine.stopAll();
          quickBtn.textContent = 'Escuchar ahora';
        } else {
          soundEngine.loadPreset('tinnitus');
          quickBtn.textContent = 'Pausar';
        }
      });
    }

    this.container.querySelectorAll('.dash-sound-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation(); // Avoid triggering card click
        const preset = btn.dataset.preset;
        this.container.querySelectorAll('.dash-sound-btn').forEach(b => b.classList.remove('primary'));
        btn.classList.add('primary');
        soundEngine.loadPreset(preset);
        if (quickBtn) quickBtn.textContent = 'Pausar';
      });
    });
  }
}
