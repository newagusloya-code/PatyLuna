/**
 * Lightweight Hash-based SPA Router
 */

import { isAuthenticated } from './api.js';

class Router {
  constructor() {
    this.routes = {};
    this.currentView = null;
    this.appElement = document.getElementById('app');
    
    window.addEventListener('hashchange', () => this.handleRoute());
    window.addEventListener('unauthorized', () => {
      window.location.hash = '#/login';
    });
  }

  addRoute(path, viewComponent, options = {}) {
    this.routes[path] = { view: viewComponent, ...options };
  }

  async handleRoute() {
    let path = window.location.hash.slice(1) || '/';
    
    // Default fallback
    if (!this.routes[path]) {
      path = '/';
    }

    const route = this.routes[path];

    // Auth Guards
    if (route.requiresAuth && !isAuthenticated()) {
      window.location.hash = '#/login';
      return;
    }
    
    if (route.guestOnly && isAuthenticated()) {
      window.location.hash = '#/dashboard';
      return;
    }

    // Unmount current view
    if (this.currentView && this.currentView.unmount) {
      this.currentView.unmount();
    }

    // Render new view
    const viewInstance = new route.view();
    this.currentView = viewInstance;
    
    this.appElement.innerHTML = ''; // Clear container
    
    // Add fade-in transition
    const viewElement = await viewInstance.render();
    viewElement.classList.add('animate-fade-in');
    
    this.appElement.appendChild(viewElement);

    // Call mount lifecycle
    if (viewInstance.mount) {
      viewInstance.mount();
    }
  }

  start() {
    this.handleRoute();
  }
}

export const router = new Router();
