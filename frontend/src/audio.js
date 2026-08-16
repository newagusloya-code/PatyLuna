/**
 * Paty Luna - Motor de Audio y Frecuencias Terapéuticas
 * Sintetizador Web Audio de alta fidelidad para sueño, relajación y alivio de tinnitus (acúfenos).
 */

class SoundEngine {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.isPlaying = false;
    
    // Nodos de capas activas
    this.activeNodes = {
      hz: null,        // Frecuencia Solfeggio / Hz
      binaural: null,  // Ondas binaurales
      noise: null,     // Ruido Marrón / Rosa / Blanco
      rain: null,      // Lluvia relajante
      ocean: null,     // Olas del mar
      forest: null,    // Bosque nocturno
    };

    this.gains = {
      hz: null,
      binaural: null,
      noise: null,
      rain: null,
      ocean: null,
      forest: null,
    };

    // Volúmenes por capa (0.0 a 1.0)
    this.volumes = {
      hz: 0.5,
      binaural: 0.3,
      noise: 0.4,
      rain: 0.0,
      ocean: 0.0,
      forest: 0.0,
    };

    this.currentHz = 432;
    this.currentNoiseType = 'brown'; // brown (tinnitus), pink, white
    this.timerTimeout = null;
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

  // --- Generadores de Sonido ---

  // 1. Tono Senoidal Puro con Armónicos Cálidos (Hz)
  startHz(freq = 432) {
    this.init();
    this.resume();
    this.stopHz();

    this.currentHz = freq;
    const osc = this.ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);

    // Filtro pasa-bajos suave para calidez
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
      } catch (e) {}
      this.activeNodes.hz = null;
    }
  }

  // 2. Ondas Binaurales (Diferencia de 3Hz - 4Hz para sueño profundo Delta)
  startBinaural(baseFreq = 216, beatFreq = 3.5) {
    this.init();
    this.resume();
    this.stopBinaural();

    // Canal Izquierdo
    const oscL = this.ctx.createOscillator();
    oscL.type = 'sine';
    oscL.frequency.setValueAtTime(baseFreq, this.ctx.currentTime);

    const merger = this.ctx.createChannelMerger(2);
    const pannerL = this.ctx.createStereoPanner ? this.ctx.createStereoPanner() : null;
    if (pannerL) pannerL.pan.setValueAtTime(-1, this.ctx.currentTime);

    // Canal Derecho
    const oscR = this.ctx.createOscillator();
    oscR.type = 'sine';
    oscR.frequency.setValueAtTime(baseFreq + beatFreq, this.ctx.currentTime);
    const pannerR = this.ctx.createStereoPanner ? this.ctx.createStereoPanner() : null;
    if (pannerR) pannerR.pan.setValueAtTime(1, this.ctx.currentTime);

    if (pannerL && pannerR) {
      oscL.connect(pannerL);
      pannerL.connect(this.gains.binaural);
      oscR.connect(pannerR);
      pannerR.connect(this.gains.binaural);
    } else {
      oscL.connect(this.gains.binaural);
      oscR.connect(this.gains.binaural);
    }

    oscL.start();
    oscR.start();

    this.activeNodes.binaural = { oscL, oscR };
  }

  stopBinaural() {
    if (this.activeNodes.binaural) {
      try {
        this.activeNodes.binaural.oscL.stop();
        this.activeNodes.binaural.oscR.stop();
        this.activeNodes.binaural.oscL.disconnect();
        this.activeNodes.binaural.oscR.disconnect();
      } catch (e) {}
      this.activeNodes.binaural = null;
    }
  }

  // 3. Generador de Ruido Terapéutico (Marrón, Rosa, Blanco - Especial Tinnitus)
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
        output[i] *= 0.11; // Compensación de volumen
        b6 = white * 0.115926;
      }
    } else {
      // Ruido Marrón (Brownian / Red noise) - El mejor para Tinnitus y relajación profunda
      let lastOut = 0.0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        output[i] = (lastOut + (0.02 * white)) / 1.02;
        lastOut = output[i];
        output[i] *= 3.5; // Compensación de volumen
      }
    }

    const whiteNoise = this.ctx.createBufferSource();
    whiteNoise.buffer = buffer;
    whiteNoise.loop = true;

    // Filtro adicional suave
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
      } catch (e) {}
      this.activeNodes.noise = null;
    }
  }

  // 4. Lluvia Suave Nocturna
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
      } catch (e) {}
      this.activeNodes.rain = null;
    }
  }

  // 5. Olas del Mar Relajantes (Moduladas con LFO)
  startOcean() {
    this.init();
    this.resume();
    this.stopOcean();

    const bufferSize = 2 * this.ctx.sampleRate;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = buffer.getChannelData(0);

    let lastOut = 0.0;
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      output[i] = (lastOut + (0.02 * white)) / 1.02;
      lastOut = output[i];
      output[i] *= 2.5;
    }

    const noiseSource = this.ctx.createBufferSource();
    noiseSource.buffer = buffer;
    noiseSource.loop = true;

    // Filtro modulado para crear el vaivén de las olas
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(350, this.ctx.currentTime);

    // Oscilador LFO para la respiración de las olas (un ciclo cada 10 segundos)
    const lfo = this.ctx.createOscillator();
    lfo.frequency.setValueAtTime(0.1, this.ctx.currentTime); // 0.1 Hz = 10s por ola
    
    const lfoGain = this.ctx.createGain();
    lfoGain.gain.setValueAtTime(250, this.ctx.currentTime);

    lfo.connect(lfoGain);
    lfoGain.connect(filter.frequency);

    noiseSource.connect(filter);
    filter.connect(this.gains.ocean);

    lfo.start();
    noiseSource.start();

    this.activeNodes.ocean = { noiseSource, filter, lfo };
  }

  stopOcean() {
    if (this.activeNodes.ocean) {
      try {
        this.activeNodes.ocean.noiseSource.stop();
        this.activeNodes.ocean.lfo.stop();
        this.activeNodes.ocean.noiseSource.disconnect();
        this.activeNodes.ocean.lfo.disconnect();
      } catch (e) {}
      this.activeNodes.ocean = null;
    }
  }

  // --- Control de Volúmenes ---
  setLayerVolume(layer, val) {
    this.volumes[layer] = Math.max(0, Math.min(1, val));
    if (this.gains[layer] && this.ctx) {
      this.gains[layer].gain.setTargetAtTime(this.volumes[layer], this.ctx.currentTime, 0.05);
    }
  }

  setMasterVolume(val) {
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setTargetAtTime(Math.max(0, Math.min(1, val)), this.ctx.currentTime, 0.05);
    }
  }

  // --- Preajustes Populares de Paty Luna ---
  loadPreset(presetName) {
    this.init();
    this.resume();
    this.stopAll();

    switch (presetName) {
      case 'tinnitus':
        // Alivio Acúfenos: Ruido Marrón profundo + 528Hz suave
        this.setLayerVolume('noise', 0.6);
        this.setLayerVolume('hz', 0.25);
        this.setLayerVolume('binaural', 0.0);
        this.setLayerVolume('rain', 0.15);
        this.setLayerVolume('ocean', 0.0);
        this.startNoise('brown');
        this.startHz(528);
        this.startRain();
        break;

      case 'sueno432':
        // Sueño Cósmico: 432Hz + Ondas Delta Binaurales + Olas
        this.setLayerVolume('hz', 0.45);
        this.setLayerVolume('binaural', 0.35);
        this.setLayerVolume('ocean', 0.4);
        this.setLayerVolume('noise', 0.0);
        this.setLayerVolume('rain', 0.0);
        this.startHz(432);
        this.startBinaural(216, 3.0);
        this.startOcean();
        break;

      case 'lluvia_paz':
        // Lluvia de Medianoche con Ruido Rosa
        this.setLayerVolume('rain', 0.6);
        this.setLayerVolume('noise', 0.3);
        this.setLayerVolume('hz', 0.2);
        this.setLayerVolume('binaural', 0.0);
        this.setLayerVolume('ocean', 0.0);
        this.startRain();
        this.startNoise('pink');
        this.startHz(432);
        break;

      case 'paz528':
        // Sanación y Serenidad: 528 Hz pura + Ruido Marrón
        this.setLayerVolume('hz', 0.5);
        this.setLayerVolume('noise', 0.35);
        this.setLayerVolume('binaural', 0.0);
        this.setLayerVolume('rain', 0.0);
        this.setLayerVolume('ocean', 0.2);
        this.startHz(528);
        this.startNoise('brown');
        this.startOcean();
        break;

      default:
        this.startHz(432);
        this.startNoise('brown');
        break;
    }

    this.isPlaying = true;
    window.dispatchEvent(new CustomEvent('paty-audio-state-changed', { detail: { isPlaying: true } }));
  }

  stopAll() {
    this.stopHz();
    this.stopBinaural();
    this.stopNoise();
    this.stopRain();
    this.stopOcean();
    this.isPlaying = false;
    window.dispatchEvent(new CustomEvent('paty-audio-state-changed', { detail: { isPlaying: false } }));
  }

  // --- Temporizador con Desvanecimiento Suave (Fade-Out) ---
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

  // --- Temporizador de Alarma (Reproduce sonido al final) ---
  setAlarm(minutes, presetName) {
    this.clearTimer();
    this.stopAll(); // Silencio mientras corre el timer
    if (!minutes || minutes <= 0) return;

    this.timerSecondsRemaining = minutes * 60;
    this.isAlarmMode = true;
    this.alarmPreset = presetName;
    
    // Iniciar contexto de audio (necesario en móviles por políticas de autoplay)
    this.init();
    this.resume();
    
    // Crear un oscilador inaudible para mantener el contexto de audio despierto en iOS/Android
    try {
      const silentOsc = this.ctx.createOscillator();
      const silentGain = this.ctx.createGain();
      silentGain.gain.value = 0.001; // Casi inaudible
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
