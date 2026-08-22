import { api } from '../api.js';

export class TherapyView {
  constructor() {
    this.container = document.createElement('div');
    this.container.className = 'therapy-container';
    this.agents = [];
    this.currentEntryId = null;
    this.messages = [];
  }

  async loadAgents() {
    try {
      const res = await api('/ai/agents');
      if (res.ok) {
        const data = await res.json();
        this.agents = data.agents;
      }
    } catch (e) {
      console.error('Failed to load agents', e);
    }
  }

  async loadThread(entryId) {
    try {
      const res = await api(`/diary/${entryId}`);
      if (res.ok) {
        const data = await res.json();
        this.currentEntryId = entryId;
        this.messages = data.messages || [];
        this.renderChat();
      }
    } catch (e) {
      console.error('Failed to load thread', e);
    }
  }

  async startNewSession(content, selectedAgents) {
    try {
      // Create empty diary entry as the "Thread"
      const entryRes = await api('/diary/', {
        method: 'POST',
        body: JSON.stringify({ content: "Chat Session", title: new Date().toLocaleDateString() })
      });
      
      if (!entryRes.ok) throw new Error('Failed to create thread');
      const entry = await entryRes.json();
      this.currentEntryId = entry.id;

      // Send the first message
      await this.sendMessage(content, selectedAgents);
    } catch (e) {
      alert('Error: ' + e.message);
    }
  }

  async sendMessage(content, selectedAgents) {
    if (!this.currentEntryId) return;
    
    // Optimistic UI update for user message
    this.messages.push({
      role: 'user',
      content: content,
      created_at: new Date().toISOString()
    });
    this.renderChat();

    try {
      const res = await api(`/ai/diary/${this.currentEntryId}/chat`, {
        method: 'POST',
        body: JSON.stringify({
          content: content,
          selected_agents: selectedAgents
        })
      });

      if (res.ok) {
        const newMessages = await res.json();
        // Update all messages from server
        this.messages = this.messages.filter(m => m.id); // remove optimistic
        this.messages = [...this.messages, ...newMessages.filter(nm => !this.messages.find(em => em.id === nm.id))];
        this.renderChat();
      }
    } catch (e) {
      console.error('Failed to send message', e);
    }
  }

  getAgentIcon(type) {
    const agent = this.agents.find(a => a.type === type);
    return agent ? agent.icon : '🤖';
  }
  
  getAgentName(type) {
    const map = {
      'tough_coach': 'Coach Estricto',
      'sleep_analyst': 'Especialista de Sueño',
      'productivity_mentor': 'Mentor Productividad'
    };
    return map[type] || type;
  }

  renderBuilder() {
    this.container.innerHTML = `
      <div style="max-width: 600px; margin: 0 auto; padding: 24px 16px; padding-bottom: 90px;">
        <div style="text-align: center; margin-bottom: 30px;">
          <div style="font-size: 3rem; margin-bottom: 10px;">🛋️</div>
          <h1 style="font-size: 2rem; color: var(--text-primary); margin-bottom: 8px;">Therapy Room</h1>
          <p style="color: var(--text-secondary); font-size: 0.95rem;">Selecciona a tus terapeutas de IA y cuéntales cómo te sientes hoy.</p>
        </div>

        <div class="card" style="padding: 24px;">
          <textarea id="therapy-input" class="input-field" rows="4" placeholder="¿Qué hay en tu mente? Me siento..." style="width: 100%; resize: none; margin-bottom: 20px;"></textarea>
          
          <h3 style="font-size: 1rem; color: var(--text-primary); margin-bottom: 12px;">¿Quién quieres que te responda?</h3>
          <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px;" id="agent-checkboxes">
            ${this.agents.map(a => `
              <label style="display: flex; align-items: center; gap: 12px; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 12px; cursor: pointer; border: 1px solid var(--border-color);">
                <input type="checkbox" value="${a.type}" class="agent-cb" style="width: 20px; height: 20px; accent-color: var(--accent-calm);">
                <div>
                  <div style="font-weight: 600; font-size: 0.95rem;">${a.icon} ${this.getAgentName(a.type)}</div>
                  <div style="font-size: 0.8rem; color: var(--text-secondary);">${a.description}</div>
                </div>
              </label>
            `).join('')}
          </div>

          <button id="start-chat-btn" class="btn primary" style="width: 100%; padding: 14px; font-size: 1.05rem;">
            Comenzar Sesión
          </button>
        </div>
      </div>
    `;

    // Ensure at least one agent is selected
    const btn = this.container.querySelector('#start-chat-btn');
    btn.addEventListener('click', async () => {
      const content = this.container.querySelector('#therapy-input').value.trim();
      const selectedAgents = Array.from(this.container.querySelectorAll('.agent-cb:checked')).map(cb => cb.value);

      if (!content) return alert('Por favor escribe cómo te sientes.');
      if (selectedAgents.length === 0) return alert('Selecciona al menos un terapeuta.');

      btn.disabled = true;
      btn.textContent = 'Generando respuestas...';
      await this.startNewSession(content, selectedAgents);
    });
  }

  renderChat() {
    this.container.innerHTML = `
      <div style="max-width: 600px; margin: 0 auto; display: flex; flex-direction: column; height: calc(100vh - 60px);">
        <!-- Header -->
        <div style="padding: 16px; background: var(--bg-elevated); border-bottom: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 10;">
          <h2 style="font-size: 1.2rem; margin: 0;">🛋️ Sesión de Terapia</h2>
          <button class="btn secondary" style="padding: 6px 12px; font-size: 0.8rem;" onclick="window.location.hash='#/dashboard'">Salir</button>
        </div>

        <!-- Messages Area -->
        <div id="chat-messages" style="flex: 1; overflow-y: auto; padding: 20px 16px; display: flex; flex-direction: column; gap: 16px; padding-bottom: 120px;">
          ${this.messages.map(m => `
            <div style="display: flex; flex-direction: column; align-items: ${m.role === 'user' ? 'flex-end' : 'flex-start'};">
              ${m.role === 'agent' ? `<span style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 4px; margin-left: 4px;">${this.getAgentIcon(m.agent_type)} ${this.getAgentName(m.agent_type)}</span>` : ''}
              <div style="
                max-width: 85%;
                padding: 12px 16px;
                border-radius: 18px;
                font-size: 0.95rem;
                line-height: 1.4;
                background: ${m.role === 'user' ? 'var(--accent-calm)' : 'var(--bg-elevated)'};
                color: ${m.role === 'user' ? '#000' : 'var(--text-primary)'};
                border: ${m.role === 'agent' ? '1px solid var(--border-color)' : 'none'};
                border-bottom-right-radius: ${m.role === 'user' ? '4px' : '18px'};
                border-bottom-left-radius: ${m.role === 'agent' ? '4px' : '18px'};
                white-space: pre-wrap;
              ">${m.content}</div>
            </div>
          `).join('')}
        </div>

        <!-- Chat Input Area -->
        <div style="position: fixed; bottom: 65px; left: 0; right: 0; background: var(--bg-primary); padding: 12px 16px; border-top: 1px solid var(--border-color); z-index: 20;">
          <div style="max-width: 600px; margin: 0 auto;">
            <!-- Mini Agent Selector for Replies -->
            <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 8px;" id="reply-agents">
              ${this.agents.map(a => `
                <label style="display: flex; align-items: center; gap: 6px; background: var(--bg-elevated); padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; border: 1px solid var(--border-color); cursor: pointer; white-space: nowrap;">
                  <input type="checkbox" value="${a.type}" class="reply-agent-cb" checked style="accent-color: var(--accent-calm);">
                  ${a.icon} ${this.getAgentName(a.type).split(' ')[0]}
                </label>
              `).join('')}
            </div>
            
            <div style="display: flex; gap: 8px;">
              <input type="text" id="chat-reply-input" class="input-field" placeholder="Escribe una respuesta..." style="flex: 1; border-radius: 20px; padding: 10px 16px;">
              <button id="chat-send-btn" class="btn primary" style="border-radius: 50%; width: 44px; height: 44px; padding: 0; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
                ↑
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Auto-scroll to bottom
    const msgsDiv = this.container.querySelector('#chat-messages');
    msgsDiv.scrollTop = msgsDiv.scrollHeight;

    const btn = this.container.querySelector('#chat-send-btn');
    const input = this.container.querySelector('#chat-reply-input');

    const handleSend = async () => {
      const content = input.value.trim();
      const selectedAgents = Array.from(this.container.querySelectorAll('.reply-agent-cb:checked')).map(cb => cb.value);
      
      if (!content) return;
      if (selectedAgents.length === 0) return alert('Selecciona al menos un terapeuta para que te responda.');

      input.value = '';
      btn.disabled = true;
      await this.sendMessage(content, selectedAgents);
    };

    btn.addEventListener('click', handleSend);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleSend();
    });
  }

  async render() {
    await this.loadAgents();
    
    if (this.currentEntryId) {
      this.renderChat();
    } else {
      this.renderBuilder();
    }
    
    return this.container;
  }
}
