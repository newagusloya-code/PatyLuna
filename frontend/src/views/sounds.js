import { soundEngine } from '../audio.js';

export class SoundsView {
  constructor() {
    this.container = document.createElement('div');
    this.container.className = 'sounds-container';
    this.selectedPreset = 'tinnitus';
  }

  formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  updateTimerUI() {
    const timerStatus = this.container.querySelector('#timer-status');
    const visualTimer = this.container.querySelector('#visual-timer-text');
    const orb = this.container.querySelector('#main-sound-orb');

    if (soundEngine.timerSecondsRemaining > 0) {
      const modeText = soundEngine.isAlarmMode ? 'Alarma en:' : 'Apagado automático en:';
      const timeStr = this.formatTime(soundEngine.timerSecondsRemaining);
      
      if (timerStatus) {
        timerStatus.style.display = 'block';
        timerStatus.innerHTML = `⏱️ <strong>${modeText}</strong> ${timeStr}`;
      }
      if (visualTimer) {
        visualTimer.style.display = 'block';
        visualTimer.textContent = timeStr;
      }
      if (soundEngine.isAlarmMode) {
        this.container.querySelectorAll('.sleep-btn').forEach((b) => b.classList.remove('primary'));
      } else {
        this.container.querySelectorAll('.alarm-btn').forEach((b) => b.classList.remove('primary'));
      }
    } else {
      if (timerStatus) timerStatus.style.display = 'none';
      if (visualTimer) visualTimer.style.display = 'none';
      if (soundEngine.isAlarmMode && orb) {
        orb.style.boxShadow = 'none';
      }
      this.container.querySelectorAll('.timer-btn').forEach((b) => {
        if (b.dataset.min !== '0') b.classList.remove('primary');
      });
    }
  }

  render() {
    this.container.innerHTML = `
      <div class="sounds-page-wrapper" style="max-width: 800px; margin: 0 auto; padding-bottom: 80px;">
        
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 32px;">
          <div style="font-size: 2.5rem; margin-bottom: 8px;">🎧</div>
          <h1 style="font-size: 2.2rem; font-weight: 300; margin-bottom: 8px; color: var(--text-primary);">
            Frecuencias & Serenidad
          </h1>
          <p style="font-size: 1rem; color: var(--text-secondary); max-width: 500px; margin: 0 auto;">
            Tonos sanadores y ruido acústico diseñados para calmar la mente y aliviar el acúfeno (tinnitus).
          </p>
        </div>

        <!-- Visualizer Ring / Main Play Button -->
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 36px;">
          <div class="sound-glow-orb ${soundEngine.isPlaying ? 'active' : ''}" id="main-sound-orb" style="position: relative; width: 160px; height: 160px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-direction: column; cursor: pointer; transition: all 0.5s ease; background: radial-gradient(circle, rgba(196, 181, 253, 0.15) 0%, rgba(12, 15, 29, 0.8) 70%); border: 2px solid var(--accent-calm); box-shadow: ${soundEngine.isPlaying ? '0 0 40px rgba(196, 181, 253, 0.35)' : 'none'};">
            <span id="play-icon" style="font-size: 2.8rem; margin-bottom: 4px;">${soundEngine.isPlaying ? '⏸️' : '▶️'}</span>
            <div id="visual-timer-text" style="font-size: 1.4rem; font-weight: 600; display: none;"></div>
          </div>
          <div id="playback-status-text" style="margin-top: 14px; font-size: 0.95rem; font-weight: 500; color: var(--accent-calm);">
            ${soundEngine.isPlaying ? 'Sonido relajante activo' : 'Toca el círculo para escuchar'}
          </div>
          <div id="timer-status" style="margin-top: 6px; font-size: 0.85rem; color: var(--text-secondary); display: none;"></div>
        </div>

        <!-- Presets Populares -->
        <div class="card" style="margin-bottom: 28px; padding: 20px;">
          <h3 style="font-size: 1.1rem; margin-bottom: 14px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
            <span>✨</span> Mezclas Especiales para Paty
          </h3>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;">
            
            <button class="preset-btn ${this.selectedPreset === 'tinnitus' ? 'active' : ''}" data-preset="tinnitus" style="padding: 14px; text-align: left; border-radius: 12px; background: var(--bg-elevated); border: 1px solid ${this.selectedPreset === 'tinnitus' ? 'var(--accent-calm)' : 'var(--border-color)'}; cursor: pointer;">
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 4px;">Alivio Tinnitus</div>
              <div style="font-size: 0.75rem; color: var(--text-secondary);">Ruido Marrón + 528Hz + Lluvia</div>
            </button>

            <button class="preset-btn ${this.selectedPreset === 'sueno432' ? 'active' : ''}" data-preset="sueno432" style="padding: 14px; text-align: left; border-radius: 12px; background: var(--bg-elevated); border: 1px solid ${this.selectedPreset === 'sueno432' ? 'var(--accent-calm)' : 'var(--border-color)'}; cursor: pointer;">
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 4px;">Sueño 432 Hz</div>
              <div style="font-size: 0.75rem; color: var(--text-secondary);">Frecuencia Cósmica + Ruido Marrón</div>
            </button>

            <button class="preset-btn ${this.selectedPreset === 'lluvia_paz' ? 'active' : ''}" data-preset="lluvia_paz" style="padding: 14px; text-align: left; border-radius: 12px; background: var(--bg-elevated); border: 1px solid ${this.selectedPreset === 'lluvia_paz' ? 'var(--accent-calm)' : 'var(--border-color)'}; cursor: pointer;">
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 4px;">Lluvia de Noche</div>
              <div style="font-size: 0.75rem; color: var(--text-secondary);">Lluvia continua + Ruido Rosa + 432Hz</div>
            </button>

            <button class="preset-btn ${this.selectedPreset === 'paz528' ? 'active' : ''}" data-preset="paz528" style="padding: 14px; text-align: left; border-radius: 12px; background: var(--bg-elevated); border: 1px solid ${this.selectedPreset === 'paz528' ? 'var(--accent-calm)' : 'var(--border-color)'}; cursor: pointer;">
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary); margin-bottom: 4px;">Paz 528 Hz</div>
              <div style="font-size: 0.75rem; color: var(--text-secondary);">Tono de Sanación y Serenidad</div>
            </button>

          </div>
        </div>

        <!-- Mezclador de Capas (3 Capas Fundamentales) -->
        <div class="card" style="margin-bottom: 28px; padding: 20px;">
          <h3 style="font-size: 1.1rem; margin-bottom: 16px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
            <span>🎚️</span> Mezclador Personalizado
          </h3>

          <div style="display: flex; flex-direction: column; gap: 20px;">
            
            <!-- 1. Ruido Terapéutico (Tinnitus Masker) -->
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <label style="font-size: 0.9rem; font-weight: 500;">
                  🛡️ Ruido Acústico (Alivio Acúfenos)
                </label>
                <div style="display: flex; gap: 6px;">
                  <button class="noise-type-btn ${soundEngine.currentNoiseType === 'brown' ? 'active-noise' : ''}" data-type="brown" style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: var(--bg-primary); border: 1px solid ${soundEngine.currentNoiseType === 'brown' ? 'var(--accent-calm)' : 'var(--border-color)'}; color: ${soundEngine.currentNoiseType === 'brown' ? 'var(--accent-calm)' : 'var(--text-primary)'}; cursor: pointer;">Marrón</button>
                  <button class="noise-type-btn ${soundEngine.currentNoiseType === 'pink' ? 'active-noise' : ''}" data-type="pink" style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: var(--bg-primary); border: 1px solid ${soundEngine.currentNoiseType === 'pink' ? 'var(--accent-calm)' : 'var(--border-color)'}; color: ${soundEngine.currentNoiseType === 'pink' ? 'var(--accent-calm)' : 'var(--text-primary)'}; cursor: pointer;">Rosa</button>
                  <button class="noise-type-btn ${soundEngine.currentNoiseType === 'white' ? 'active-noise' : ''}" data-type="white" style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: var(--bg-primary); border: 1px solid ${soundEngine.currentNoiseType === 'white' ? 'var(--accent-calm)' : 'var(--border-color)'}; color: ${soundEngine.currentNoiseType === 'white' ? 'var(--accent-calm)' : 'var(--text-primary)'}; cursor: pointer;">Blanco</button>
                </div>
              </div>
              <input type="range" class="volume-slider" data-layer="noise" min="0" max="1" step="0.01" value="${soundEngine.volumes.noise}" style="width: 100%; accent-color: var(--accent-calm);">
            </div>

            <!-- 2. Frecuencia Hz / Solfeggio -->
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <label style="font-size: 0.9rem; font-weight: 500;">
                  ✨ Frecuencia Armónica (${soundEngine.currentHz} Hz)
                </label>
                <div style="display: flex; gap: 6px;">
                  <button class="hz-btn ${soundEngine.currentHz === 432 ? 'active-hz' : ''}" data-hz="432" style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: var(--bg-primary); border: 1px solid ${soundEngine.currentHz === 432 ? 'var(--accent-calm)' : 'var(--border-color)'}; color: ${soundEngine.currentHz === 432 ? 'var(--accent-calm)' : 'var(--text-primary)'}; cursor: pointer;">432 Hz</button>
                  <button class="hz-btn ${soundEngine.currentHz === 528 ? 'active-hz' : ''}" data-hz="528" style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: var(--bg-primary); border: 1px solid ${soundEngine.currentHz === 528 ? 'var(--accent-calm)' : 'var(--border-color)'}; color: ${soundEngine.currentHz === 528 ? 'var(--accent-calm)' : 'var(--text-primary)'}; cursor: pointer;">528 Hz</button>
                  <button class="hz-btn ${soundEngine.currentHz === 639 ? 'active-hz' : ''}" data-hz="639" style="font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: var(--bg-primary); border: 1px solid ${soundEngine.currentHz === 639 ? 'var(--accent-calm)' : 'var(--border-color)'}; color: ${soundEngine.currentHz === 639 ? 'var(--accent-calm)' : 'var(--text-primary)'}; cursor: pointer;">639 Hz</button>
                </div>
              </div>
              <input type="range" class="volume-slider" data-layer="hz" min="0" max="1" step="0.01" value="${soundEngine.volumes.hz}" style="width: 100%; accent-color: var(--accent-calm);">
            </div>

            <!-- 3. Lluvia Nocturna -->
            <div>
              <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <label style="font-size: 0.9rem; font-weight: 500;">🌧️ Lluvia Nocturna Suave</label>
              </div>
              <input type="range" class="volume-slider" data-layer="rain" min="0" max="1" step="0.01" value="${soundEngine.volumes.rain}" style="width: 100%; accent-color: var(--accent-calm);">
            </div>

          </div>
        </div>

        <!-- Temporizadores -->
        <div class="card" style="padding: 20px;">
          
          <div style="margin-bottom: 24px;">
            <h3 style="font-size: 1.1rem; margin-bottom: 8px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
              <span>⏰</span> Alarma Despertador (Silencio -> Sonido)
            </h3>
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 14px;">
              Espera en silencio y luego reproduce el sonido activo al llegar a cero.
            </p>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
              <button class="timer-btn alarm-btn btn secondary" data-min="5" style="padding: 8px 16px; font-size: 0.85rem;">5 min</button>
              <button class="timer-btn alarm-btn btn secondary" data-min="15" style="padding: 8px 16px; font-size: 0.85rem;">15 min</button>
              <button class="timer-btn alarm-btn btn secondary" data-min="25" style="padding: 8px 16px; font-size: 0.85rem;">25 min</button>
              <button class="timer-btn alarm-btn btn secondary" data-min="0" style="padding: 8px 16px; font-size: 0.85rem; color: var(--accent-danger);">Cancelar</button>
            </div>
          </div>

          <div style="border-top: 1px solid var(--border-color); padding-top: 20px;">
            <h3 style="font-size: 1.1rem; margin-bottom: 8px; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
              <span>⏱️</span> Temporizador de Apagado (Sonido -> Silencio)
            </h3>
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 14px;">
              El sonido se reproducirá y se atenuará suavemente para que duermas.
            </p>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
              <button class="timer-btn sleep-btn btn secondary" data-min="15" style="padding: 8px 16px; font-size: 0.85rem;">15 min</button>
              <button class="timer-btn sleep-btn btn secondary" data-min="30" style="padding: 8px 16px; font-size: 0.85rem;">30 min</button>
              <button class="timer-btn sleep-btn btn secondary" data-min="60" style="padding: 8px 16px; font-size: 0.85rem;">60 min</button>
              <button class="timer-btn sleep-btn btn secondary" data-min="0" style="padding: 8px 16px; font-size: 0.85rem; color: var(--accent-danger);">Cancelar</button>
            </div>
          </div>
          
        </div>

      </div>
    `;

    this.attachEvents();
    return this.container;
  }

  attachEvents() {
    const orb = this.container.querySelector('#main-sound-orb');
    const playIcon = this.container.querySelector('#play-icon');
    const statusText = this.container.querySelector('#playback-status-text');

    orb.addEventListener('click', () => {
      if (soundEngine.isPlaying) {
        soundEngine.stopAll();
        playIcon.textContent = '▶️';
        statusText.textContent = 'Sonido en pausa';
        orb.classList.remove('active');
        orb.style.boxShadow = 'none';
      } else {
        soundEngine.loadPreset(this.selectedPreset);
        playIcon.textContent = '⏸️';
        statusText.textContent = 'Sonido relajante activo';
        orb.classList.add('active');
        orb.style.boxShadow = '0 0 40px rgba(196, 181, 253, 0.35)';
      }
    });

    // Preset buttons
    this.container.querySelectorAll('.preset-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const preset = btn.dataset.preset;
        this.selectedPreset = preset;
        this.container.querySelectorAll('.preset-btn').forEach((b) => {
          b.style.borderColor = 'var(--border-color)';
        });
        btn.style.borderColor = 'var(--accent-calm)';

        soundEngine.loadPreset(preset);
        playIcon.textContent = '⏸️';
        statusText.textContent = `Mezcla cargada: ${btn.querySelector('div').textContent}`;
        orb.classList.add('active');
        orb.style.boxShadow = '0 0 40px rgba(196, 181, 253, 0.35)';

        // Actualizar sliders en pantalla
        this.container.querySelectorAll('.volume-slider').forEach((slider) => {
          const layer = slider.dataset.layer;
          if (soundEngine.volumes[layer] !== undefined) {
            slider.value = soundEngine.volumes[layer];
          }
        });
      });
    });

    // Layer volume sliders
    this.container.querySelectorAll('.volume-slider').forEach((slider) => {
      slider.addEventListener('input', (e) => {
        const layer = e.target.dataset.layer;
        const val = parseFloat(e.target.value);
        soundEngine.setLayerVolume(layer, val);
        if (!soundEngine.isPlaying && val > 0) {
          soundEngine.resume();
        }
      });
    });

    // Noise type buttons
    this.container.querySelectorAll('.noise-type-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const type = btn.dataset.type;
        soundEngine.startNoise(type);
        this.container.querySelectorAll('.noise-type-btn').forEach((b) => {
          b.style.borderColor = 'var(--border-color)';
          b.style.color = 'var(--text-primary)';
        });
        btn.style.borderColor = 'var(--accent-calm)';
        btn.style.color = 'var(--accent-calm)';
      });
    });

    // Hz frequency buttons
    this.container.querySelectorAll('.hz-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const hz = parseInt(btn.dataset.hz, 10);
        soundEngine.startHz(hz);
        this.container.querySelectorAll('.hz-btn').forEach((b) => {
          b.style.borderColor = 'var(--border-color)';
          b.style.color = 'var(--text-primary)';
        });
        btn.style.borderColor = 'var(--accent-calm)';
        btn.style.color = 'var(--accent-calm)';
      });
    });

    // Timer buttons
    this.container.querySelectorAll('.timer-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const min = parseInt(btn.dataset.min, 10);
        this.container.querySelectorAll('.timer-btn').forEach((b) => b.classList.remove('primary'));
        
        if (min === 0) {
          soundEngine.clearTimer();
          this.updateTimerUI();
          return;
        }

        btn.classList.add('primary');

        if (btn.classList.contains('alarm-btn')) {
          soundEngine.setAlarm(min, this.selectedPreset);
          playIcon.textContent = '▶️';
          statusText.textContent = 'Alarma programada en silencio';
          orb.classList.remove('active');
          orb.style.boxShadow = '0 0 20px rgba(251, 191, 36, 0.4)';
        } else {
          soundEngine.setTimer(min);
          if (!soundEngine.isPlaying) {
            soundEngine.loadPreset(this.selectedPreset);
            playIcon.textContent = '⏸️';
            orb.classList.add('active');
            orb.style.boxShadow = '0 0 40px rgba(196, 181, 253, 0.35)';
          }
        }
        this.updateTimerUI();
      });
    });

    // Hook timer tick
    soundEngine.onTimerTick = () => this.updateTimerUI();
    soundEngine.onTimerEnd = (isAlarm) => {
      this.updateTimerUI();
      if (isAlarm) {
        if (playIcon) playIcon.textContent = '⏸️';
        if (statusText) statusText.textContent = '¡Tiempo cumplido! Sonido activo';
        if (orb) {
          orb.classList.add('active');
          orb.style.boxShadow = '0 0 40px rgba(196, 181, 253, 0.35)';
        }
      } else {
        if (playIcon) playIcon.textContent = '▶️';
        if (statusText) statusText.textContent = 'Temporizador finalizado. ¡Buenas noches!';
        if (orb) {
          orb.classList.remove('active');
          orb.style.boxShadow = 'none';
        }
      }
    };
  }
}
