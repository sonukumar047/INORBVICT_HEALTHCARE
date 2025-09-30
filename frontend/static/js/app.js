class ChatBot {
  constructor() {
    this.currentMode = 'flow';
    this.currentSessionId = null;
    this.isWaitingForResponse = false;
    this.baseUrl = 'http://localhost:8000';
    this.maxRetries = 3;
    this.retryCount = 0;
    this.isConnected = false;

    this.initEls();
    this.bindEvents();
    this.checkConnection().then(() => this.initializeMode());
  }

  initEls() {
    this.flowModeBtn = document.getElementById('flowModeBtn');
    this.ragModeBtn = document.getElementById('ragModeBtn');
    this.uploadArea = document.getElementById('uploadArea');
    this.fileInput = document.getElementById('fileInput');
    this.uploadBtn = document.getElementById('uploadBtn');
    this.chatMessages = document.getElementById('chatMessages');
    this.messageInput = document.getElementById('messageInput');
    this.sendBtn = document.getElementById('sendBtn');
    this.statusText = document.getElementById('statusText');
    this.summaryModal = document.getElementById('summaryModal');
    this.summaryContent = document.getElementById('summaryContent');
    this.startNewFlowBtn = document.getElementById('startNewFlow');

    // Error container
    this.errorContainer = document.getElementById('errorContainer');
    if (!this.errorContainer) {
      this.errorContainer = document.createElement('div');
      this.errorContainer.id = 'errorContainer';
      this.errorContainer.className = 'error-container';
      document.body.appendChild(this.errorContainer);
    }
  }

  bindEvents() {
    // Mode switching
    this.flowModeBtn?.addEventListener('click', () => this.setMode('flow'));
    this.ragModeBtn?.addEventListener('click', () => this.setMode('rag'));

    // File upload trigger via button and label
    this.uploadBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      this.fileInput?.click();
    });
    this.fileInput?.addEventListener('change', (e) => this.handleFileUpload(e));

    // Chat sending
    const chatForm = document.getElementById('chatForm');
    chatForm?.addEventListener('submit', (e) => { e.preventDefault(); this.sendMessage(); });
    this.sendBtn?.addEventListener('click', (e) => { e.preventDefault(); this.sendMessage(); });
    this.messageInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.sendMessage(); }
    });
    this.messageInput?.addEventListener('input', () => this.validateInput());

    // Modal
    this.summaryModal?.querySelector('.close')?.addEventListener('click', () => this.closeModal());
    this.startNewFlowBtn?.addEventListener('click', () => { this.closeModal(); this.startNewSession(); });
  }

  async checkConnection() {
    try {
      const res = await fetch(`${this.baseUrl}/health`, { headers: { Accept: 'application/json; charset=utf-8' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.isConnected = true;
      this.updateStatus('Connected');
      return true;
    } catch (e) {
      this.isConnected = false;
      this.updateStatus('Disconnected');
      this.showError('Backend not reachable. Start the API and refresh.', 'error');
      return false;
    }
  }

  setMode(mode) {
    if (!this.isConnected) { this.showError('Connect to server first.', 'warning'); return; }
    this.currentMode = mode;
    this.flowModeBtn.classList.toggle('active', mode === 'flow');
    this.ragModeBtn.classList.toggle('active', mode === 'rag');

    // Toggle upload area
    if (mode === 'rag') {
      this.uploadArea.classList.add('show');
      this.uploadArea.setAttribute('aria-hidden', 'false');
    } else {
      this.uploadArea.classList.remove('show');
      this.uploadArea.setAttribute('aria-hidden', 'true');
    }

    this.clearChat();
    this.initializeMode();
  }

  async initializeMode() {
    try {
      this.updateStatus('Initializing...');
      this.disableInput();
      const endpoint = this.currentMode === 'flow' ? '/flow/start' : '/rag/start';
      const res = await this.request(endpoint, 'POST');
      this.currentSessionId = res.session_id;
      this.addBot(res.message);
      this.enableInput();
      this.updateStatus('Ready');

      if (this.currentMode === 'rag') {
        setTimeout(() => this.addBot('💡 Tip: Upload documents above, then ask questions about them.'), 600);
      }
    } catch (e) {
      this.addBot('Failed to initialize. Try again.');
      this.showError(e.message, 'error');
      this.updateStatus('Error');
    }
  }

  async handleFileUpload(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    // Validate
    const valid = files.filter(f => (['application/pdf', 'text/plain'].includes(f.type)) && f.size <= 10*1024*1024);
    if (!valid.length) { this.showError('Only PDF/TXT <= 10MB allowed.', 'warning'); event.target.value=''; return; }

    this.updateStatus('Uploading...');
    this.disableInput();
    const progress = this.createProgress(valid.length);

    const formData = new FormData();
    valid.forEach(f => formData.append('files', f));

    try {
      const data = await this.uploadFormData(`${this.baseUrl}/rag/upload`, formData, (p)=>this.updateProgress(progress, p));
      if (!data.processed_files) throw new Error('Server did not return processed_files');

      const total = data.total_chunks || 0;
      const count = Object.keys(data.processed_files).length;
      this.addBot(`✅ Uploaded ${count} file(s). Indexed ${total} chunks. Ask your question now!`);

      const summary = Object.entries(data.processed_files).map(([fn, n]) => `• ${fn.split('/').pop()}: ${n} chunks`).join('\n');
      if (summary) this.addBot(`📊 Summary:\n${summary}`);

      if (data.errors) this.showError(data.errors.join('; '), 'warning');
      this.updateStatus('Ready');
    } catch (e) {
      this.addBot(`❌ Upload failed: ${e.message}`);
      this.showError(`Upload error: ${e.message}`, 'error');
      this.updateStatus('Error');
    } finally {
      this.removeProgress(progress);
      this.enableInput();
      event.target.value='';
    }
  }

  createProgress(count) {
    const el = document.createElement('div');
    el.className = 'upload-progress';
    el.innerHTML = `
      <div class="upload-progress-content">
        <p>Uploading ${count} file(s)...</p>
        <div class="progress-bar-container"><div class="progress-bar"></div></div>
        <span class="progress-text">0%</span>
      </div>`;
    document.body.appendChild(el);
    return el;
  }
  updateProgress(container, p) {
    const bar = container.querySelector('.progress-bar');
    const txt = container.querySelector('.progress-text');
    if (bar) bar.style.width = `${p}%`;
    if (txt) txt.textContent = `${Math.round(p)}%`;
  }
  removeProgress(container) { container?.remove(); }

  async uploadFormData(url, formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener('progress', (e) => { if (e.lengthComputable) onProgress((e.loaded/e.total)*100); });
      xhr.onreadystatechange = () => {
        if (xhr.readyState === 4) {
          try {
            const data = JSON.parse(xhr.responseText || '{}');
            if (xhr.status >= 200 && xhr.status < 300) resolve(data);
            else reject(new Error(data.detail || `HTTP ${xhr.status}`));
          } catch { reject(new Error('Invalid server response')); }
        }
      };
      xhr.open('POST', url);
      xhr.send(formData);
    });
  }

  validateInput() {
    const msg = (this.messageInput?.value || '').trim();
    const ok = msg.length > 0 && msg.length <= 1000;
    this.sendBtn.disabled = !ok || this.isWaitingForResponse;
  }

  async sendMessage() {
    const text = (this.messageInput?.value || '').trim();
    if (!text || this.isWaitingForResponse || !this.isConnected) return;

    this.addUser(text);
    this.messageInput.value = '';
    this.disableInput();
    this.showTyping();

    try {
      const endpoint = this.currentMode === 'flow' ? `/flow/chat/${this.currentSessionId}` : `/rag/chat/${this.currentSessionId}`;
      const res = await this.request(endpoint, 'POST', { message: text });
      this.hideTyping();
      this.retryCount = 0;

      this.handleResponse(res);
    } catch (e) {
      this.hideTyping();
      this.addBot(`Error: ${e.message}`);
      this.showError(e.message, 'error');
    } finally {
      this.enableInput();
    }
  }

  handleResponse(data) {
    if (this.currentMode === 'flow' && data.metadata) {
      const md = data.metadata;
      if (md.validation_error) { this.addBot(md.validation_error, true); return; }
      this.addBot(data.message);
      if (md.summary && md.is_complete) { this.showSummary(md.summary); this.updateStatus('Complete'); }
    } else {
      this.addBot(data.message);
    }
  }

  addUser(text) {
    const el = document.createElement('div');
    el.className = 'message-container user';
    const ts = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
    el.innerHTML = `
      <div class="user-avatar" aria-hidden="true">👤</div>
      <div class="message-content">
        <div class="message user-message">${this.escape(text)}</div>
        <div class="message-timestamp">${ts}</div>
      </div>`;
    this.chatMessages.appendChild(el);
    this.scroll();
  }

  addBot(text, isError=false) {
    const el = document.createElement('div');
    el.className = 'message-container bot';
    const ts = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
    el.innerHTML = `
      <div class="bot-avatar" aria-hidden="true">🤖</div>
      <div class="message-content">
        <div class="message ${isError?'error-message bot-message':'bot-message'}">${this.format(text)}</div>
        <div class="message-timestamp">${ts}</div>
      </div>`;
    this.chatMessages.appendChild(el);
    this.scroll();
  }

  format(text) {
    return this.escape(text).replace(/\n/g,'<br>').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\*(.*?)\*/g,'<em>$1</em>');
  }
  escape(text) { const d=document.createElement('div'); d.textContent=text; return d.innerHTML; }

  showTyping() {
    const el = document.createElement('div');
    el.className = 'message-container bot typing';
    el.innerHTML = `
      <div class="bot-avatar" aria-hidden="true">🤖</div>
      <div class="typing-indicator">
        <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
      </div>`;
    this.chatMessages.appendChild(el);
    this.scroll();
  }
  hideTyping() { this.chatMessages.querySelector('.typing')?.remove(); }

  showSummary(summary) {
    let html = '<div class="summary-display"><h4>📋 Your Information Summary:</h4>';
    for (const [k,v] of Object.entries(summary)) {
      if (['session_id','completed_at'].includes(k)) continue;
      const label = k.charAt(0).toUpperCase()+k.slice(1);
      html += `<div class="summary-item"><span class="summary-label">${label}:</span><span class="summary-value">${this.escape(String(v))}</span></div>`;
    }
    html += '</div>';
    this.summaryContent.innerHTML = html;
    this.summaryModal.classList.add('show');
    this.summaryModal.setAttribute('aria-hidden','false');
    this.summaryModal.querySelector('.close')?.focus();
  }
  closeModal() {
    this.summaryModal.classList.remove('show');
    this.summaryModal.setAttribute('aria-hidden','true');
    this.messageInput?.focus();
  }

  async request(endpoint, method='GET', body=null) {
    const opts = { method, headers: { 'Accept':'application/json; charset=utf-8' } };
    if (body) { opts.headers['Content-Type']='application/json; charset=utf-8'; opts.body=JSON.stringify(body); }
    const res = await fetch(`${this.baseUrl}${endpoint}`, opts);
    if (!res.ok) {
      let detail=''; try { const j=await res.json(); detail=j.detail || ''; } catch {}
      throw new Error(detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  disableInput() { this.isWaitingForResponse = true; this.messageInput.disabled = true; this.sendBtn.disabled = true; }
  enableInput() { this.isWaitingForResponse = false; this.messageInput.disabled = false; this.sendBtn.disabled = false; this.validateInput(); }
  updateStatus(text) { if (this.statusText) this.statusText.textContent = text; }
  clearChat() { this.chatMessages.querySelectorAll('.message-container:not(.welcome-message)').forEach(n=>n.remove()); }
  startNewSession(){ this.currentSessionId=null; this.retryCount=0; this.clearChat(); this.initializeMode(); }
  scroll(){ setTimeout(()=>{ this.chatMessages.scrollTop = this.chatMessages.scrollHeight; }, 50); }

  showError(msg, type='error') {
    const toast = document.createElement('div');
    toast.className = `error-toast error-${type}`;
    toast.innerHTML = `<div class="error-content"><span class="error-icon">${type==='warning'?'⚠️':'❌'}</span><span class="error-text">${this.escape(msg)}</span><button class="error-close" type="button" aria-label="Close">×</button></div>`;
    if (!this.errorContainer) { this.errorContainer = document.createElement('div'); this.errorContainer.className='error-container'; this.errorContainer.id='errorContainer'; document.body.appendChild(this.errorContainer); }
    this.errorContainer.appendChild(toast);
    this.errorContainer.classList.add('show');
    toast.querySelector('.error-close').addEventListener('click', ()=>toast.remove());
    setTimeout(()=>{ toast.remove(); if (!this.errorContainer.children.length) this.errorContainer.classList.remove('show'); }, type==='error'?8000:5000);
  }
}

document.addEventListener('DOMContentLoaded', () => { window.chatBot = new ChatBot(); });
