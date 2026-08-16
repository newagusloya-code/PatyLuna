import { api } from '../api.js';
import { soundEngine } from '../audio.js';

export class SleepView {
  constructor() {
    this.container = document.createElement('div');
    this.container.className = 'sleep-container';
    this.currentSession = null;
    this.sleepHistory = [];
    this.breathingInterval = null;
    this.breathingState = 'ready'; // ready, inhale (4s), hold (7s), exhale (8s)
    this.breathingSeconds = 4;
  }

  async loadActiveAndPastSessions() {
    try {
      const res = await api('/sleep');
      if (res.ok) {
        this.sleepHistory = await res.json();
        // Verificar si hay una sesión activa sin terminar
        const active = this.sleepHistory.find((s) => !s.ended_at);
        if (active) {
          this.currentSession = active;
        }
      }
    } catch (err) {
      console.error('Error al cargar sesiones de sueño, usando respaldo:', err);
      this.sleepHistory = [];
      this.currentSession = null;
    }
  }

  startBreathingExercise() {
    const bubble = this.container.querySelector('#breathing-bubble');
    const instruction = this.container.querySelector('#breathing-instruction');
    const timerEl = this.container.querySelector('#breathing-timer');
    const actionBtn = this.container.querySelector('#breathing-toggle-btn');

    if (this.breathingInterval) {
      // Detener
      clearInterval(this.breathingInterval);
      this.breathingInterval = null;
      if (bubble) {
        bubble.style.transform = 'scale(1)';
        bubble.style.transition = 'all 0.5s ease';
      }
      if (instruction) instruction.textContent = 'Toca para iniciar';
      if (timerEl) timerEl.textContent = '4-7-8';
      if (actionBtn) actionBtn.textContent = 'Iniciar Respiración';
      return;
    }

    let phase = 'inhale'; // inhale (4s), hold (7s), exhale (8s)
    let count = 4;
    if (actionBtn) actionBtn.textContent = 'Pausar Guía';

    const runStep = () => {
      if (phase === 'inhale') {
        if (instruction) instruction.textContent = 'Inhala profundamente por la nariz...';
        if (bubble) {
          bubble.style.transition = 'transform 4s ease-in-out';
          bubble.style.transform = 'scale(1.4)';
          bubble.style.borderColor = 'var(--accent-calm)';
        }
      } else if (phase === 'hold') {
        if (instruction) instruction.textContent = 'Sostén el aire con calma...';
        if (bubble) {
          bubble.style.transition = 'none';
          bubble.style.transform = 'scale(1.4)';
          bubble.style.borderColor = 'var(--accent-nature)';
        }
      } else if (phase === 'exhale') {
        if (instruction) instruction.textContent = 'Exhala suavemente por la boca...';
        if (bubble) {
          bubble.style.transition = 'transform 8s ease-in-out';
          bubble.style.transform = 'scale(1)';
          bubble.style.borderColor = 'var(--accent-focus)';
        }
      }
      if (timerEl) timerEl.textContent = count;
    };

    runStep();

    this.breathingInterval = setInterval(() => {
      count--;
      if (count <= 0) {
        if (phase === 'inhale') {
          phase = 'hold';
          count = 7;
        } else if (phase === 'hold') {
          phase = 'exhale';
          count = 8;
        } else if (phase === 'exhale') {
          phase = 'inhale';
          count = 4;
        }
      }
      runStep();
    }, 1000);
  }

  async startSleepSession() {
    const soundPreset = this.container.querySelector('#sleep-sound-select').value;
    const statusMsg = this.container.querySelector('#sleep-action-status');

    if (soundPreset !== 'none') {
      soundEngine.loadPreset(soundPreset);
      soundEngine.setTimer(45); // 45 min fade-out
    }

    try {
      const res = await api('/sleep', {
        method: 'POST',
        body: {
          sound_preset: soundPreset,
          meditation_type: 'breathing_478',
        },
      });

      if (res.ok) {
        this.currentSession = await res.json();
      } else {
        throw new Error('API request failed');
      }
    } catch (err) {
      if (statusMsg) statusMsg.textContent = 'Modo sin conexión. Sesión simulada.';
      this.currentSession = { id: 'mock', started_at: new Date().toISOString() };
    }
    this.render();
  }

  async endSleepSession(rating, notes) {
    if (!this.currentSession) return;
    try {
      const res = await api(`/sleep/${this.currentSession.id}/end`, {
        method: 'PATCH',
        body: {
          quality_rating: rating,
          notes: notes,
        },
      });

      if (res.ok) {
        this.currentSession = null;
        soundEngine.stopAll();
        await this.loadActiveAndPastSessions();
        this.render();
      } else {
        throw new Error('API request failed');
      }
    } catch (err) {
      console.error('Error al finalizar sesión, usando respaldo:', err);
      // Fallback
      this.sleepHistory.unshift({
        started_at: this.currentSession.started_at,
        ended_at: new Date().toISOString(),
        quality_rating: rating,
        notes: notes
      });
      this.currentSession = null;
      soundEngine.stopAll();
      this.render();
    }
  }

  unmount() {
    if (this.breathingInterval) {
      clearInterval(this.breathingInterval);
      this.breathingInterval = null;
    }
  }

  async render() {
    await this.loadActiveAndPastSessions();

    const isSleeping = !!this.currentSession;

    this.container.innerHTML = `
      <div style="max-width: 800px; margin: 0 auto; padding-bottom: 80px;">
        
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 32px;">
          <div style="font-size: 2.5rem; margin-bottom: 8px;">🌙</div>
          <h1 style="font-size: 2.2rem; font-weight: 300; margin-bottom: 8px; color: var(--text-primary);">
            Santuario del Sueño
          </h1>
          <p style="font-size: 1rem; color: var(--text-secondary); max-width: 500px; margin: 0 auto;">
            Prepara tu cuerpo y mente para un descanso profundo y reparador.
          </p>
        </div>

        ${isSleeping ? `
        <!-- Modo Noche Activa -->
        <div class="card" style="margin-bottom: 32px; text-align: center; padding: 32px; border: 1px solid var(--accent-calm); box-shadow: 0 0 30px rgba(129, 140, 248, 0.15);">
          <div style="font-size: 3rem; margin-bottom: 12px; animation: pulse 3s infinite;">✨</div>
          <h2 style="font-size: 1.6rem; font-weight: 400; margin-bottom: 8px;">Que descanses, Paty</h2>
          <p style="color: var(--text-secondary); margin-bottom: 24px;">
            Sesión de descanso en curso desde las ${new Date(this.currentSession.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.
          </p>

          <div style="max-width: 400px; margin: 0 auto; background: var(--bg-primary); padding: 20px; border-radius: 12px; border: 1px solid var(--border-color);">
            <h4 style="margin-bottom: 12px; font-size: 1rem;">¿Ya es de mañana?</h4>
            <label style="display: block; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px;">
              ¿Cómo sentiste tu descanso?
            </label>
            <div id="star-rating" style="font-size: 1.8rem; margin-bottom: 16px; cursor: pointer; display: flex; justify-content: center; gap: 8px;">
              <span class="star" data-val="1">★</span>
              <span class="star" data-val="2">★</span>
              <span class="star" data-val="3">★</span>
              <span class="star" data-val="4">★</span>
              <span class="star" data-val="5">★</span>
            </div>
            <textarea id="morning-notes" placeholder="Nota matutina (Ej: Desperté muy descansada sin dolor de cabeza)..." 
              style="width: 100%; height: 70px; margin-bottom: 16px; font-size: 0.85rem;"></textarea>
            
            <button id="wake-up-btn" class="btn primary" style="width: 100%; padding: 12px;">
              ☀️ He despertado
            </button>
          </div>
        </div>
        ` : `
        <!-- Modo Preparación al Sueño -->
        
        <!-- Respiración Guiada 4-7-8 -->
        <div class="card" style="margin-bottom: 28px; padding: 24px; text-align: center;">
          <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-primary); display: flex; align-items: center; justify-content: center; gap: 8px;">
            <span>🌸</span> Ejercicio de Respiración 4-7-8
          </h3>
          <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 24px;">
            Técnica natural para calmar el ritmo cardíaco y conciliar el sueño en minutos.
          </p>

          <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 20px;">
            <div id="breathing-bubble" style="width: 130px; height: 130px; border-radius: 50%; border: 2px solid var(--accent-calm); background: radial-gradient(circle, rgba(129, 140, 248, 0.15) 0%, rgba(10, 14, 23, 0.8) 70%); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
              <span id="breathing-timer" style="font-size: 2rem; font-weight: 300;">4-7-8</span>
            </div>
            <div id="breathing-instruction" style="font-size: 1rem; font-weight: 500; color: var(--accent-calm); min-height: 24px;">
              Toca para iniciar la relajación
            </div>
          </div>

          <button id="breathing-toggle-btn" class="btn secondary" style="padding: 10px 24px; border-radius: 20px;">
            Iniciar Respiración
          </button>
        </div>

        <!-- Iniciar Descanso Nocturno -->
        <div class="card" style="margin-bottom: 28px; padding: 24px;">
          <h3 style="font-size: 1.2rem; margin-bottom: 12px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
            <span>🛌</span> Iniciar Noche de Descanso
          </h3>
          <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 16px;">
            Elige tu atmósfera de sonido favorita. Se apagará con suavidad tras quedarte dormida.
          </p>

          <div style="margin-bottom: 20px;">
            <label style="display: block; font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 6px;">Atmósfera de Sonido:</label>
            <select id="sleep-sound-select" style="width: 100%; padding: 10px; border-radius: 8px; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary); font-size: 0.95rem;">
              <option value="tinnitus">Alivio Tinnitus (Ruido Marrón + 528 Hz + Lluvia)</option>
              <option value="sueno432">Sueño Cósmico 432 Hz + Olas del Mar</option>
              <option value="lluvia_paz">Lluvia Nocturna Suave & Ruido Rosa</option>
              <option value="paz528">Frecuencia de Sanación 528 Hz</option>
              <option value="none">En Silencio (Sin sonido)</option>
            </select>
          </div>

          <button id="start-sleep-btn" class="btn primary" style="width: 100%; padding: 14px; font-size: 1.05rem;">
            🌙 Comenzar a Dormir
          </button>
          <div id="sleep-action-status" style="color: var(--accent-danger); font-size: 0.85rem; margin-top: 8px; text-align: center;"></div>
        </div>
        `}

        <!-- Historial de Sueño -->
        <div class="card" style="padding: 24px;">
          <h3 style="font-size: 1.1rem; margin-bottom: 16px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
            <span>📊</span> Historial de Descansos
          </h3>
          
          ${this.sleepHistory.length === 0 ? `
            <p style="font-size: 0.9rem; color: var(--text-secondary);">Aún no tienes registros de sueño guardados.</p>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 12px;">
              ${this.sleepHistory.slice(0, 5).map((s) => {
                const dateStr = new Date(s.started_at).toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
                const stars = s.quality_rating ? '★'.repeat(s.quality_rating) + '☆'.repeat(5 - s.quality_rating) : 'Sin calificar';
                return `
                  <div style="padding: 12px 16px; background: var(--bg-primary); border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                      <div style="font-weight: 500; font-size: 0.9rem; color: var(--text-primary);">${dateStr}</div>
                      <div style="font-size: 0.8rem; color: var(--text-secondary);">${s.notes || 'Noche de descanso en Paty Luna'}</div>
                    </div>
                    <div style="color: var(--accent-focus); font-size: 0.95rem; letter-spacing: 2px;">
                      ${stars}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          `}
        </div>

      </div>
    `;

    this.attachEvents();
    return this.container;
  }

  attachEvents() {
    const breathingBtn = this.container.querySelector('#breathing-toggle-btn');
    if (breathingBtn) {
      breathingBtn.addEventListener('click', () => this.startBreathingExercise());
    }

    const startSleepBtn = this.container.querySelector('#start-sleep-btn');
    if (startSleepBtn) {
      startSleepBtn.addEventListener('click', () => this.startSleepSession());
    }

    let selectedRating = 5;
    const starEls = this.container.querySelectorAll('.star');
    starEls.forEach((star) => {
      star.addEventListener('click', () => {
        selectedRating = parseInt(star.dataset.val, 10);
        starEls.forEach((s) => {
          const val = parseInt(s.dataset.val, 10);
          s.style.color = val <= selectedRating ? 'var(--accent-focus)' : 'var(--text-muted)';
        });
      });
    });

    const wakeUpBtn = this.container.querySelector('#wake-up-btn');
    if (wakeUpBtn) {
      wakeUpBtn.addEventListener('click', () => {
        const notes = this.container.querySelector('#morning-notes').value;
        this.endSleepSession(selectedRating, notes);
      });
    }
  }
}
