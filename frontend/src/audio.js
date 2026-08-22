/**
 * Paty Luna - Motor de Audio y Frecuencias Terapéuticas
 * Sintetizador Web Audio de alta fidelidad para sueño, relajación y alivio de tinnitus (acúfenos).
 * Contiene los 3 generadores fundamentales:
 * 1. Frecuencias Armónicas Solfeggio (432 Hz, 528 Hz, 639 Hz)
 * 2. Ruido Acústico Terapéutico (Marrón, Rosa, Blanco)
 * 3. Lluvia Nocturna Suave
 */

class SoundEngine {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.isPlaying = false;
    
    // Nodos de capas activas (Las 3 capas fundamentales)
    this.activeNodes = {
      hz: null,        // Frecuencia Armónica Solfeggio
      noise: null,     // Ruido Acústico (Marrón / Rosa / Blanco)
      rain: null,      // Lluvia Nocturna Suave
    };

    this.gains = {
      hz: null,
      noise: null,
      rain: null,
    };

    // Volúmenes por capa (0.0 a 1.0)
    this.volumes = {
      noise: 0.5,
      hz: 0.4,
      rain: 0.0,
    };

    this.currentHz = 432;
    this.currentNoiseType = 'brown'; // brown (tinnitus), pink, white
    this.timerSecondsRemaining = 0;
    this.timerInterval = null;
    this.onTimerTick = null;
    this.onTimerEnd = null;
    this.isAlarmMode = false;
    this.alarmPreset = null;
  }

  init() {
    if (this.ctx) return;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AudioContext();
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.setValueAtTime(0.8, this.ctx.currentTime);
    this.masterGain.connect(this.ctx.destination);

    // Crear gains para cada capa
    for (const key of Object.keys(this.volumes)) {
      const g = this.ctx.createGain();
      g.gain.setValueAtTime(this.volumes[key], this.ctx.currentTime);
      g.connect(this.masterGain);
      this.gains[key] = g;
    }
  }

  resume() {
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  // ── 1. Tono Senoidal Puro con Armónicos Cálidos (Hz) ───────────────────────
  startHz(freq = 432) {
    this.init();
    this.resume();
    this.stopHz();

    this.currentHz = freq;
    const osc = this.ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);

    // Filtro pasa-bajos suave para calidez sonora
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(freq * 2.5, this.ctx.currentTime);

    osc.connect(filter);
    filter.connect(this.gains.hz);
    osc.start();

    this.activeNodes.hz = { osc, filter };
  }

  stopHz() {
    if (this.activeNodes.hz) {
      try {
        this.activeNodes.hz.osc.stop();
        this.activeNodes.hz.osc.disconnect();
        this.activeNodes.hz.filter.disconnect();
      } catch (e) {}
      this.activeNodes.hz = null;
    }
  }

  // ── 2. Generador de Ruido Terapéutico (Marrón, Rosa, Blanco) ───────────────
  startNoise(type = 'brown') {
    this.init();
    this.resume();
    this.stopNoise();
    this.currentNoiseType = type;

    const bufferSize = 2 * this.ctx.sampleRate;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = buffer.getChannelData(0);

    if (type === 'white') {
      for (let i = 0; i < bufferSize; i++) {
        output[i] = Math.random() * 2 - 1;
      }
    } else if (type === 'pink') {
      let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        b0 = 0.99886 * b0 + white * 0.0555179;
        b1 = 0.99332 * b1 + white * 0.0750759;
        b2 = 0.96900 * b2 + white * 0.1538520;
        b3 = 0.86650 * b3 + white * 0.3104856;
        b4 = 0.55000 * b4 + white * 0.5329522;
        b5 = -0.7616 * b5 - white * 0.0168980;
        output[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
        output[i] *= 0.11;
        b6 = white * 0.115926;
      }
    } else {
      // Ruido Marrón (Brownian / Red noise) - El mejor para Tinnitus y relajación
      let lastOut = 0.0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        output[i] = (lastOut + (0.02 * white)) / 1.02;
        lastOut = output[i];
        output[i] *= 3.5;
      }
    }

    const whiteNoise = this.ctx.createBufferSource();
    whiteNoise.buffer = buffer;
    whiteNoise.loop = true;

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(type === 'brown' ? 450 : 1200, this.ctx.currentTime);

    whiteNoise.connect(filter);
    filter.connect(this.gains.noise);
    whiteNoise.start();

    this.activeNodes.noise = { whiteNoise, filter };
  }

  stopNoise() {
    if (this.activeNodes.noise) {
      try {
        this.activeNodes.noise.whiteNoise.stop();
        this.activeNodes.noise.whiteNoise.disconnect();
        this.activeNodes.noise.filter.disconnect();
      } catch (e) {}
      this.activeNodes.noise = null;
    }
  }

  // ── 3. Lluvia Suave Nocturna ────────────────────────────────────────────────
  startRain() {
    this.init();
    this.resume();
    this.stopRain();

    const bufferSize = 2 * this.ctx.sampleRate;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = buffer.getChannelData(0);

    let lastOut = 0.0;
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      output[i] = (lastOut + (0.05 * white)) / 1.05;
      lastOut = output[i];
      output[i] *= 1.5;
    }

    const rainSource = this.ctx.createBufferSource();
    rainSource.buffer = buffer;
    rainSource.loop = true;

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(900, this.ctx.currentTime);
    filter.Q.setValueAtTime(0.8, this.ctx.currentTime);

    rainSource.connect(filter);
    filter.connect(this.gains.rain);
    rainSource.start();

    this.activeNodes.rain = { rainSource, filter };
  }

  stopRain() {
    if (this.activeNodes.rain) {
      try {
        this.activeNodes.rain.rainSource.stop();
        this.activeNodes.rain.rainSource.disconnect();
        this.activeNodes.rain.filter.disconnect();
      } catch (e) {}
      this.activeNodes.rain = null;
    }
  }

  // ── Control de Volúmenes con Activación Dinámica ────────────────────────────
  setLayerVolume(layer, val) {
    if (this.volumes[layer] === undefined) return;
    this.volumes[layer] = Math.max(0, Math.min(1, val));
    if (this.gains[layer] && this.ctx) {
      this.gains[layer].gain.setTargetAtTime(this.volumes[layer], this.ctx.currentTime, 0.05);
    }
    
    // Si el reproductor está activo, encender/apagar el generador en caliente
    if (this.isPlaying) {
      if (val > 0 && !this.activeNodes[layer]) {
        if (layer === 'hz') this.startHz(this.currentHz);
        else if (layer === 'noise') this.startNoise(this.currentNoiseType);
        else if (layer === 'rain') this.startRain();
      } else if (val === 0 && this.activeNodes[layer]) {
        if (layer === 'hz') this.stopHz();
        else if (layer === 'noise') this.stopNoise();
        else if (layer === 'rain') this.stopRain();
      }
    }
  }

  setMasterVolume(val) {
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setTargetAtTime(Math.max(0, Math.min(1, val)), this.ctx.currentTime, 0.05);
    }
  }

  // ── Preajustes de Sonido ───────────────────────────────────────────────────
  loadPreset(presetName) {
    this.init();
    this.resume();
    this.stopAll();

    switch (presetName) {
      case 'tinnitus':
        // Alivio Tinnitus: Ruido Marrón profundo + 528Hz suave + Lluvia
        this.setLayerVolume('noise', 0.6);
        this.setLayerVolume('hz', 0.25);
        this.setLayerVolume('rain', 0.15);
        this.startNoise('brown');
        this.startHz(528);
        this.startRain();
        break;

      case 'sueno432':
        // Sueño Cósmico 432 Hz: Tono Armónico 432 Hz + Ruido Marrón
        this.setLayerVolume('hz', 0.55);
        this.setLayerVolume('noise', 0.35);
        this.setLayerVolume('rain', 0.0);
        this.startHz(432);
        this.startNoise('brown');
        break;

      case 'lluvia_paz':
        // Lluvia de Medianoche con Ruido Rosa y 432 Hz
        this.setLayerVolume('rain', 0.65);
        this.setLayerVolume('noise', 0.3);
        this.setLayerVolume('hz', 0.2);
        this.startRain();
        this.startNoise('pink');
        this.startHz(432);
        break;

      case 'paz528':
        // Sanación y Serenidad: 528 Hz pura + Ruido Marrón
        this.setLayerVolume('hz', 0.55);
        this.setLayerVolume('noise', 0.35);
        this.setLayerVolume('rain', 0.0);
        this.startHz(528);
        this.startNoise('brown');
        break;

      default:
        this.setLayerVolume('hz', 0.5);
        this.setLayerVolume('noise', 0.4);
        this.setLayerVolume('rain', 0.0);
        this.startHz(432);
        this.startNoise('brown');
        break;
    }

    this.isPlaying = true;
    window.dispatchEvent(new CustomEvent('paty-audio-state-changed', { detail: { isPlaying: true } }));
  }

  stopAll() {
    this.stopHz();
    this.stopNoise();
    this.stopRain();
    this.isPlaying = false;
    window.dispatchEvent(new CustomEvent('paty-audio-state-changed', { detail: { isPlaying: false } }));
  }

  // ── Temporizador con Desvanecimiento Suave (Fade-Out) ──────────────────────
  setTimer(minutes) {
    this.clearTimer();
    if (!minutes || minutes <= 0) return;

    this.timerSecondsRemaining = minutes * 60;
    
    this.timerInterval = setInterval(() => {
      this.timerSecondsRemaining--;
      if (this.onTimerTick) this.onTimerTick(this.timerSecondsRemaining);

      // Iniciar suave fade-out en los últimos 45 segundos
      if (this.timerSecondsRemaining <= 45 && this.timerSecondsRemaining > 0 && this.masterGain && this.ctx) {
        const factor = this.timerSecondsRemaining / 45;
        this.masterGain.gain.setValueAtTime(0.8 * factor, this.ctx.currentTime);
      }

      if (this.timerSecondsRemaining <= 0) {
        this.clearTimer();
        this.stopAll();
        if (this.masterGain && this.ctx) {
          this.masterGain.gain.setValueAtTime(0.8, this.ctx.currentTime);
        }
        if (this.onTimerEnd) this.onTimerEnd(false);
      }
    }, 1000);
  }

  // ── Temporizador de Alarma ─────────────────────────────────────────────────
  setAlarm(minutes, presetName) {
    this.clearTimer();
    this.stopAll();
    if (!minutes || minutes <= 0) return;

    this.timerSecondsRemaining = minutes * 60;
    this.isAlarmMode = true;
    this.alarmPreset = presetName || 'tinnitus';
    
    this.init();
    this.resume();
    
    try {
      const silentOsc = this.ctx.createOscillator();
      const silentGain = this.ctx.createGain();
      silentGain.gain.value = 0.001;
      silentOsc.connect(silentGain);
      silentGain.connect(this.ctx.destination);
      silentOsc.start();
      setTimeout(() => silentOsc.stop(), 500);
    } catch(e) {}

    this.timerInterval = setInterval(() => {
      this.timerSecondsRemaining--;
      if (this.onTimerTick) this.onTimerTick(this.timerSecondsRemaining);

      if (this.timerSecondsRemaining <= 0) {
        this.clearTimer();
        this.loadPreset(this.alarmPreset);
        if (this.onTimerEnd) this.onTimerEnd(true);
      }
    }, 1000);
  }

  clearTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = null;
    this.timerSecondsRemaining = 0;
    this.isAlarmMode = false;
    this.alarmPreset = null;
  }
}

export const soundEngine = new SoundEngine();
