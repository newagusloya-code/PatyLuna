import './style.css';
import { router } from './router.js';
import { LoginView } from './views/auth.js';
import { DashboardView } from './views/dashboard.js';
import { SoundsView } from './views/sounds.js';
import { SleepView } from './views/sleep.js';
import { TherapyView } from './views/therapy.js';
import { soundEngine } from './audio.js';

// Define Routes
router.addRoute('/', DashboardView, { requiresAuth: true });
router.addRoute('/dashboard', DashboardView, { requiresAuth: true });
router.addRoute('/login', LoginView, { guestOnly: true });
router.addRoute('/sounds', SoundsView, { requiresAuth: true });
router.addRoute('/sleep', SleepView, { requiresAuth: true });
router.addRoute('/therapy', TherapyView, { requiresAuth: true });

// Initial render shell with Android-friendly layout & bottom navigation
document.querySelector('#app').innerHTML = `
  <div class="app-shell">
    <header class="navbar">
      <div class="brand" onclick="window.location.hash='#/dashboard'" style="cursor: pointer;">
        <span style="font-size: 1.3rem; margin-right: 6px;">🌙</span>
        Paty Luna
      </div>
      <nav id="top-nav">
        <!-- Injected by views -->
      </nav>
    </header>

    <main id="main-content" class="content-area container">
      <!-- Views will be mounted here -->
    </main>

    <!-- Mini Floating Audio Controller -->
    <div id="floating-audio-bar" style="display: none; position: fixed; bottom: 70px; left: 50%; transform: translateX(-50%); width: 90%; max-width: 400px; background: rgba(19, 26, 40, 0.95); backdrop-filter: blur(12px); border: 1px solid var(--accent-calm); border-radius: 30px; padding: 8px 18px; z-index: 100; box-shadow: 0 8px 32px rgba(0,0,0,0.6); align-items: center; justify-content: space-between;">
      <div style="display: flex; align-items: center; gap: 10px; cursor: pointer;" onclick="window.location.hash='#/sounds'">
        <span style="font-size: 1.2rem; animation: pulse 2s infinite;">🎧</span>
        <div>
          <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-primary);">Sonido de Relajación</div>
          <div style="font-size: 0.7rem; color: var(--accent-calm);">Reproduciendo atmósfera...</div>
        </div>
      </div>
      <button id="floating-audio-toggle" style="background: var(--accent-calm); color: #000; border: none; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 0.8rem;">
        ⏸
      </button>
    </div>

    <!-- Android Native Bottom Navigation Bar (4 items: Inicio, Sonidos, Therapy, Noche) -->
    <nav class="bottom-nav" id="bottom-bar">
      <a href="#/dashboard" class="nav-item active" data-path="/dashboard">
        <span class="nav-icon">🏠</span>
        <span class="nav-label">Inicio</span>
      </a>
      <a href="#/sounds" class="nav-item" data-path="/sounds">
        <span class="nav-icon">🎧</span>
        <span class="nav-label">Sonidos</span>
      </a>
      <a href="#/therapy" class="nav-item" data-path="/therapy">
        <span class="nav-icon">🛋️</span>
        <span class="nav-label">Terapia</span>
      </a>
      <a href="#/sleep" class="nav-item" data-path="/sleep">
        <span class="nav-icon">🌙</span>
        <span class="nav-label">Noche</span>
      </a>
    </nav>
  </div>
`;

// Sync audio floating bar
window.addEventListener('paty-audio-state-changed', (e) => {
  const bar = document.getElementById('floating-audio-bar');
  const btn = document.getElementById('floating-audio-toggle');
  if (bar && btn) {
    if (e.detail.isPlaying) {
      bar.style.display = 'flex';
      btn.textContent = '⏸';
    } else {
      bar.style.display = 'none';
      btn.textContent = '▶';
    }
  }
});

const floatBtn = document.getElementById('floating-audio-toggle');
if (floatBtn) {
  floatBtn.addEventListener('click', () => {
    if (soundEngine.isPlaying) soundEngine.stopAll();
    else soundEngine.loadPreset('tinnitus');
  });
}

// Sync active bottom nav item on route change
window.addEventListener('hashchange', () => {
  const currentPath = window.location.hash.replace('#', '') || '/';
  const bottomBar = document.getElementById('bottom-bar');
  if (bottomBar) {
    if (currentPath === '/login') {
      bottomBar.style.display = 'none';
    } else {
      bottomBar.style.display = 'flex';
    }

    document.querySelectorAll('.bottom-nav .nav-item').forEach((item) => {
      if (item.getAttribute('href') === window.location.hash || (currentPath === '/' && item.dataset.path === '/dashboard')) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }
});

router.appElement = document.getElementById('main-content');
router.start();
