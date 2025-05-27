<template>
  <div class="mcp-terminal-app" :class="{ fullscreen: isFullscreen }">
    <div class="terminal-container">
      <!-- Enhanced Terminal Header -->
      <div class="terminal-header">
        <div class="header-left">
          <div class="terminal-title">
            <span class="title-icon">🚀</span>
            <h3>ERPNext MCP Terminal</h3>
            <div class="version-badge">v1.0</div>
          </div>
          <div class="terminal-status">
            <div class="status-indicator">
              <div class="status-dot" :class="connectionStatusClass"></div>
              <span class="status-text">{{ connectionStatusText }}</span>
            </div>
            <div class="session-info" v-if="sessionId">
              <span class="session-label">Session:</span>
              <span class="session-id">{{ sessionId.substring(0, 8) }}...</span>
            </div>
          </div>
        </div>

        <div class="header-right">
          <div class="user-info">
            <span class="user-label">👤</span>
            <span class="user-details">{{ userInfo }}</span>
          </div>
          <div class="terminal-controls">
            <button
              class="control-btn"
              @click="clearTerminal"
              title="Clear Terminal (Ctrl+L)"
            >
              🧹
            </button>
            <button
              class="control-btn"
              @click="showQuickHelp"
              title="Quick Help (Tab)"
            >
              ❓
            </button>
            <button
              class="control-btn minimize-btn"
              @click="toggleFullscreen"
              :title="isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'"
            >
              {{ isFullscreen ? '🗗' : '🗖' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Terminal Body -->
      <div class="terminal-body" ref="terminalContainer">
        <!-- Terminal Element -->
        <div
          id="terminal"
          ref="terminalRef"
          v-show="!isLoading && !error"
          class="terminal-content"
        ></div>

        <!-- Loading State -->
        <div v-if="isLoading" class="loading-container">
          <div class="loading-animation">
            <div class="loading-spinner"></div>
            <div class="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
          <div class="loading-message">
            <div class="loading-title">{{ loadingTitle }}</div>
            <div class="loading-subtitle">{{ loadingMessage }}</div>
          </div>
        </div>

        <!-- Error State -->
        <div v-if="error" class="error-container">
          <div class="error-content">
            <div class="error-icon">⚠️</div>
            <div class="error-title">Terminal Error</div>
            <div class="error-message">{{ error }}</div>
            <div class="error-actions">
              <button class="btn-retry" @click="retryConnection">
                🔄 Retry Connection
              </button>
              <button class="btn-reset" @click="resetTerminal">
                🔧 Reset Terminal
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Terminal Footer -->
      <div class="terminal-footer" v-if="!isLoading && !error">
        <div class="footer-info">
          <span class="footer-item">
            <span class="footer-icon">⌨️</span>
            <span>Tab: Quick Commands</span>
          </span>
          <span class="footer-item">
            <span class="footer-icon">📚</span>
            <span>Type 'help' for detailed guide</span>
          </span>
          <span class="footer-item">
            <span class="footer-icon">⏱️</span>
            <span>{{ currentTime }}</span>
          </span>
        </div>
        <div class="footer-stats" v-if="stats.commandsExecuted > 0">
          <span class="stat-item">Commands: {{ stats.commandsExecuted }}</span>
          <span class="stat-item">Uptime: {{ uptime }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';

export default {
  name: 'MCPTerminalApp',
  setup() {
    // Core refs
    const terminalRef = ref(null);
    const terminalContainer = ref(null);
    const terminal = ref(null);

    // State management
    const isLoading = ref(true);
    const loadingTitle = ref('Initializing Terminal');
    const loadingMessage = ref('Setting up MCP connection...');
    const error = ref(null);
    const sessionId = ref(null);
    const isFullscreen = ref(false);

    // Statistics
    const stats = ref({
      commandsExecuted: 0,
      sessionStartTime: Date.now(),
    });

    // Time tracking
    const currentTime = ref(new Date().toLocaleTimeString());
    const timeInterval = ref(null);

    // Computed properties
    const connectionStatusClass = computed(() => ({
      connected: sessionId.value && !isLoading.value,
      connecting: isLoading.value,
      disconnected: !sessionId.value && !isLoading.value,
    }));

    const connectionStatusText = computed(() => {
      if (isLoading.value) return 'Connecting...';
      if (sessionId.value) return 'Connected';
      return 'Disconnected';
    });

    const userInfo = computed(() => {
      const user = window.frappe?.session?.user || 'Guest';
      const site = window.frappe?.boot?.sitename || 'ERPNext';
      return `${user}@${site}`;
    });

    const uptime = computed(() => {
      const now = Date.now();
      const diff = now - stats.value.sessionStartTime;
      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      return `${minutes}m ${seconds}s`;
    });

    // Terminal initialization - delegate to bundle.js
    const initializeTerminal = async () => {
      try {
        loadingTitle.value = 'Loading Terminal';
        loadingMessage.value = 'Initializing xterm.js...';

        await nextTick();

        // Check if bundle.js is available
        if (typeof window.initMCPTerminal !== 'function') {
          throw new Error(
            'MCP Terminal bundle not loaded. Please ensure mcp_chatbot.bundle.js is included.'
          );
        }

        loadingMessage.value = 'Starting MCP session...';

        // Use the bundle.js initialization
        terminal.value = await window.initMCPTerminal('mcp-terminal-app');

        // Setup additional listeners for Vue component
        setupVueListeners();

        loadingMessage.value = 'Terminal ready!';

        // Small delay to show ready message
        setTimeout(() => {
          isLoading.value = false;
          startTimeTracking();
        }, 500);
      } catch (err) {
        console.error('Terminal initialization failed:', err);
        error.value = err.message;
        isLoading.value = false;
      }
    };

    const setupVueListeners = () => {
      // Listen for command executions to update stats
      window.frappe.realtime.on('terminal_output', (message) => {
        if (message.type === 'command') {
          stats.value.commandsExecuted++;
        }
      });

      // Listen for session events
      window.frappe.realtime.on('mcp_session_started', (data) => {
        sessionId.value = data.session_id;
        stats.value.sessionStartTime = Date.now();
      });

      window.frappe.realtime.on('mcp_session_ended', () => {
        sessionId.value = null;
      });
    };

    const startTimeTracking = () => {
      timeInterval.value = setInterval(() => {
        currentTime.value = new Date().toLocaleTimeString();
      }, 1000);
    };

    // UI Actions
    const toggleFullscreen = () => {
      isFullscreen.value = !isFullscreen.value;

      // Refit terminal after fullscreen toggle
      setTimeout(() => {
        if (window.terminal && window.terminal.fitAddon) {
          window.terminal.fitAddon.fit();
        }
      }, 100);
    };

    const clearTerminal = () => {
      if (terminal.value) {
        // Simulate Ctrl+L
        terminal.value.write('\x0c');
      }
    };

    const showQuickHelp = () => {
      if (terminal.value) {
        // Simulate Tab key
        terminal.value.write('\t');
      }
    };

    const retryConnection = () => {
      error.value = null;
      isLoading.value = true;
      loadingTitle.value = 'Retrying Connection';
      loadingMessage.value = 'Attempting to reconnect...';
      initializeTerminal();
    };

    const resetTerminal = () => {
      // Clean up existing terminal
      if (terminal.value && terminal.value.dispose) {
        terminal.value.dispose();
      }

      // Reset state
      error.value = null;
      sessionId.value = null;
      stats.value = {
        commandsExecuted: 0,
        sessionStartTime: Date.now(),
      };

      // Reinitialize
      isLoading.value = true;
      loadingTitle.value = 'Resetting Terminal';
      loadingMessage.value = 'Cleaning up and restarting...';

      setTimeout(() => {
        initializeTerminal();
      }, 1000);
    };

    // Lifecycle hooks
    onMounted(() => {
      initializeTerminal();
    });

    onUnmounted(() => {
      // Clean up
      if (timeInterval.value) {
        clearInterval(timeInterval.value);
      }

      if (terminal.value && terminal.value.dispose) {
        terminal.value.dispose();
      }

      console.log('window.frappe', window.frappe);

      // Clean up realtime listeners
      if (window.frappe && window.frappe.realtime) {
        window.frappe.realtime.off('terminal_output');
        window.frappe.realtime.off('mcp_session_started');
        window.frappe.realtime.off('mcp_session_ended');
      }
    });

    return {
      // Refs
      terminalRef,
      terminalContainer,

      // State
      isLoading,
      loadingTitle,
      loadingMessage,
      error,
      sessionId,
      isFullscreen,
      stats,
      currentTime,

      // Computed
      connectionStatusClass,
      connectionStatusText,
      userInfo,
      uptime,

      // Methods
      toggleFullscreen,
      clearTerminal,
      showQuickHelp,
      retryConnection,
      resetTerminal,
    };
  },
};
</script>

<style scoped>
/* Enhanced Styling */
.mcp-terminal-app {
  height: 100vh;
  width: 100%;
  font-family:
    'Segoe UI',
    -apple-system,
    BlinkMacSystemFont,
    sans-serif;
  background: linear-gradient(135deg, #1a1a1a 0%, #2d2d30 100%);
  overflow: hidden;
}

.terminal-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  border-radius: 12px;
  overflow: hidden;
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.4),
    0 10px 10px -5px rgba(0, 0, 0, 0.2);
  border: 1px solid #404040;
}

/* Enhanced Header */
.terminal-header {
  background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
  color: white;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #404040;
  flex-shrink: 0;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  min-height: 80px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.terminal-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 24px;
  animation: pulse 2s infinite;
}

.terminal-title h3 {
  margin: 0;
  color: #4caf50;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.version-badge {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.terminal-status {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.05);
  padding: 6px 12px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  transition: all 0.3s ease;
  position: relative;
}

.status-dot.connected {
  background: #4caf50;
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.6);
}

.status-dot.connecting {
  background: #ff9800;
  animation: pulse 1.5s infinite;
}

.status-dot.disconnected {
  background: #f44336;
  box-shadow: 0 0 6px rgba(244, 67, 54, 0.4);
}

.status-text {
  font-size: 12px;
  font-weight: 600;
  color: #e0e0e0;
}

.session-info {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(33, 150, 243, 0.1);
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid rgba(33, 150, 243, 0.2);
}

.session-label {
  font-size: 11px;
  color: #90caf9;
  font-weight: 500;
}

.session-id {
  font-size: 11px;
  color: #2196f3;
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

.header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.05);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.user-label {
  font-size: 14px;
}

.user-details {
  font-size: 13px;
  color: #e0e0e0;
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

.terminal-controls {
  display: flex;
  gap: 8px;
}

.control-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #e0e0e0;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.minimize-btn:hover {
  background: rgba(76, 175, 80, 0.2);
  border-color: rgba(76, 175, 80, 0.4);
}

/* Terminal Body */
.terminal-body {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: #0c0c0c;
}

.terminal-content {
  height: 100%;
  width: 100%;
}

/* Enhanced Loading State */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  flex-direction: column;
  background: linear-gradient(135deg, #1a1a1a 0%, #0c0c0c 100%);
  position: relative;
}

.loading-animation {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #333;
  border-top: 4px solid #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-dots {
  display: flex;
  gap: 8px;
}

.loading-dots span {
  width: 8px;
  height: 8px;
  background: #4caf50;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}
.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}
.loading-dots span:nth-child(3) {
  animation-delay: 0s;
}

.loading-message {
  text-align: center;
  color: #e0e0e0;
}

.loading-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #4caf50;
}

.loading-subtitle {
  font-size: 14px;
  color: #aaa;
  font-weight: 400;
}

/* Enhanced Error State */
.error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: linear-gradient(135deg, #1a1a1a 0%, #0c0c0c 100%);
}

.error-content {
  text-align: center;
  max-width: 400px;
  padding: 40px;
  background: rgba(244, 67, 54, 0.1);
  border-radius: 12px;
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.error-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.error-title {
  font-size: 24px;
  font-weight: 700;
  color: #f44336;
  margin-bottom: 12px;
}

.error-message {
  font-size: 16px;
  color: #ffcdd2;
  margin-bottom: 30px;
  line-height: 1.5;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-retry,
.btn-reset {
  padding: 12px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-retry {
  background: #4caf50;
  color: white;
}

.btn-retry:hover {
  background: #45a049;
  transform: translateY(-2px);
}

.btn-reset {
  background: #757575;
  color: white;
}

.btn-reset:hover {
  background: #616161;
  transform: translateY(-2px);
}

/* Terminal Footer */
.terminal-footer {
  background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
  color: #aaa;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #404040;
  flex-shrink: 0;
  font-size: 12px;
}

.footer-info {
  display: flex;
  gap: 20px;
}

.footer-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #ccc;
}

.footer-icon {
  font-size: 14px;
}

.footer-stats {
  display: flex;
  gap: 16px;
}

.stat-item {
  color: #4caf50;
  font-weight: 600;
}

/* Fullscreen Mode */
.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  border-radius: 0;
}

/* Animations */
@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .terminal-header {
    padding: 12px 16px;
    min-height: auto;
  }

  .header-left,
  .header-right {
    gap: 8px;
  }

  .terminal-title h3 {
    font-size: 18px;
  }

  .terminal-controls {
    flex-direction: row;
  }

  .footer-info {
    flex-direction: column;
    gap: 8px;
  }

  .footer-stats {
    flex-direction: column;
    gap: 4px;
  }
}

/* Terminal Integration */
:deep(.xterm-viewport) {
  scrollbar-width: thin;
  scrollbar-color: #555 #1e1e1e;
}

:deep(.xterm-viewport::-webkit-scrollbar) {
  width: 8px;
}

:deep(.xterm-viewport::-webkit-scrollbar-track) {
  background: #1e1e1e;
}

:deep(.xterm-viewport::-webkit-scrollbar-thumb) {
  background: #555;
  border-radius: 4px;
}

:deep(.xterm-viewport::-webkit-scrollbar-thumb:hover) {
  background: #666;
}
</style>
