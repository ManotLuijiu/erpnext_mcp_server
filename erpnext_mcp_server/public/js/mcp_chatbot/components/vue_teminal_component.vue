<template>
  <div class="mcp-terminal-container">
    <!-- Terminal Header -->
    <div class="terminal-header">
      <div class="header-left">
        <div class="terminal-controls">
          <span class="control-dot red"></span>
          <span class="control-dot yellow"></span>
          <span class="control-dot green"></span>
        </div>
        <h2 class="terminal-title">
          <i class="fa fa-terminal"></i>
          ERPNext MCP Terminal
        </h2>
      </div>
      <div class="header-right">
        <div class="status-indicator" :class="connectionStatus">
          <span class="status-dot"></span>
          {{ connectionStatusText }}
        </div>
        <button @click="toggleTerminal" class="minimize-btn">
          <i :class="isMinimized ? 'fa fa-expand' : 'fa fa-minus'"></i>
        </button>
      </div>
    </div>

    <!-- Terminal Content -->
    <div
      v-show="!isMinimized"
      class="terminal-content"
      :style="{ height: terminalHeight + 'px' }"
    >
      <!-- Terminal Element -->
      <div id="terminal" class="terminal-element"></div>

      <!-- Loading Overlay -->
      <div v-if="isLoading" class="loading-overlay">
        <div class="loading-spinner">
          <i class="fa fa-circle-o-notch fa-spin"></i>
          <p>{{ loadingMessage }}</p>
        </div>
      </div>
    </div>

    <!-- Terminal Footer -->
    <div v-show="!isMinimized" class="terminal-footer">
      <div class="footer-info">
        <span class="user-info">
          <i class="fa fa-user"></i>
          {{ currentUser }}@{{ currentSite }}
        </span>
        <span class="session-info">
          <i class="fa fa-clock-o"></i>
          {{ sessionDuration }}
        </span>
      </div>
      <div class="footer-controls">
        <button
          @click="clearTerminal"
          class="footer-btn"
          title="Clear Terminal"
        >
          <i class="fa fa-eraser"></i>
        </button>
        <button
          @click="restartMCP"
          class="footer-btn"
          title="Restart MCP Server"
        >
          <i class="fa fa-refresh"></i>
        </button>
        <button @click="showHelp" class="footer-btn" title="Show Help">
          <i class="fa fa-question"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { initEnhancedMCPTerminal } from '../assets/js/mcp_chatbot.bundle.js';

export default {
  name: 'MCPTerminal',
  setup() {
    // Reactive state
    const isLoading = ref(true);
    const loadingMessage = ref('Initializing terminal...');
    const isMinimized = ref(false);
    const connectionStatus = ref('disconnected');
    const terminalHeight = ref(400);
    const sessionStartTime = ref(new Date());
    const currentUser = ref('visitor');
    const currentSite = ref('erpnext');

    // Terminal instance
    let terminal = null;
    let sessionTimer = null;

    // Computed properties
    const connectionStatusText = computed(() => {
      switch (connectionStatus.value) {
        case 'connected':
          return 'Connected';
        case 'connecting':
          return 'Connecting';
        case 'disconnected':
          return 'Disconnected';
        case 'error':
          return 'Error';
        default:
          return 'Unknown';
      }
    });

    const sessionDuration = computed(() => {
      if (!sessionStartTime.value) return '00:00:00';

      const now = new Date();
      const diff = now - sessionStartTime.value;
      const hours = Math.floor(diff / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);

      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    });

    // Methods
    const initializeTerminal = async () => {
      try {
        isLoading.value = true;
        loadingMessage.value = 'Initializing MCP Terminal...';

        // Get user info
        updateUserInfo();

        // Wait for DOM element
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Initialize terminal
        terminal = await initEnhancedMCPTerminal('terminal');

        if (terminal) {
          loadingMessage.value = 'Terminal ready!';
          setTimeout(() => {
            isLoading.value = false;
          }, 500);

          // Set up realtime listeners
          setupRealtimeListeners();

          // Start session timer
          startSessionTimer();

          console.log('Terminal initialized successfully');
        } else {
          throw new Error('Failed to initialize terminal');
        }
      } catch (error) {
        console.error('Terminal initialization failed:', error);
        loadingMessage.value = 'Failed to initialize terminal';
        setTimeout(() => {
          isLoading.value = false;
        }, 2000);
      }
    };

    const updateUserInfo = () => {
      currentUser.value = frappe?.session?.user || 'visitor';
      currentSite.value = frappe?.boot?.sitename || 'erpnext';
    };

    const setupRealtimeListeners = () => {
      // Listen for MCP status updates
      frappe.realtime.on('mcp_status', (data) => {
        connectionStatus.value = data.status;
        console.log('MCP Status Update:', data);
      });

      // Listen for terminal output
      frappe.realtime.on('terminal_output', (data) => {
        console.log('Terminal Output:', data);
        // Terminal output is handled by the terminal component itself
      });
    };

    const startSessionTimer = () => {
      sessionTimer = setInterval(() => {
        // Force reactivity update for session duration
        sessionStartTime.value = new Date(sessionStartTime.value);
      }, 1000);
    };

    const toggleTerminal = () => {
      isMinimized.value = !isMinimized.value;
    };

    const clearTerminal = () => {
      if (terminal) {
        terminal.clear();
        // Show welcome message again
        if (window.initEnhancedMCPTerminal) {
          // Trigger welcome display
          terminal.write('\x0c'); // Form feed to clear and reset
        }
      }
    };

    const restartMCP = async () => {
      try {
        connectionStatus.value = 'connecting';

        // Stop existing MCP server
        await frappe.call({
          method: 'erpnext_mcp_server.api.vue_mcp_server.stop_mcp_server',
        });

        // Wait a bit
        await new Promise((resolve) => setTimeout(resolve, 1000));

        // Start MCP server
        const response = await frappe.call({
          method: 'erpnext_mcp_server.api.vue_mcp_server.start_mcp_server',
        });

        if (response.message && response.message.success) {
          connectionStatus.value = 'connected';
          if (terminal) {
            terminal.write('\r\n🔄 MCP Server restarted successfully\r\n');
          }
        } else {
          connectionStatus.value = 'error';
        }
      } catch (error) {
        console.error('Failed to restart MCP server:', error);
        connectionStatus.value = 'error';
        if (terminal) {
          terminal.write(
            `\r\n❌ Failed to restart MCP server: ${error.message}\r\n`
          );
        }
      }
    };

    const showHelp = () => {
      if (terminal) {
        // Send help command to terminal
        const helpEvent = new CustomEvent('terminal-input', {
          detail: { data: 'help\r' },
        });
        console.log('helpEvent', helpEvent);
        terminal.write('help\r');
        // Simulate enter key press
        setTimeout(() => {
          if (window.terminalState) {
            window.terminalState.currentCommand = 'help';
          }
        }, 100);
      }
    };

    const handleResize = () => {
      if (terminal && terminal.fitAddon) {
        terminal.fitAddon.fit();
      }
    };

    // Lifecycle
    onMounted(async () => {
      await initializeTerminal();
      window.addEventListener('resize', handleResize);
    });

    onUnmounted(() => {
      if (sessionTimer) {
        clearInterval(sessionTimer);
      }
      window.removeEventListener('resize', handleResize);

      // Clean up realtime listeners
      frappe.realtime.off('mcp_status');
      frappe.realtime.off('terminal_output');
    });

    return {
      isLoading,
      loadingMessage,
      isMinimized,
      connectionStatus,
      connectionStatusText,
      terminalHeight,
      sessionDuration,
      currentUser,
      currentSite,
      toggleTerminal,
      clearTerminal,
      restartMCP,
      showHelp,
    };
  },
};
</script>

<style scoped>
.mcp-terminal-container {
  background: linear-gradient(135deg, #0c0c0c 0%, #1a1a1a 100%);
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
  overflow: hidden;
  margin: 20px;
  border: 1px solid #333;
}

.terminal-header {
  background: linear-gradient(135deg, #2d2d2d 0%, #1e1e1e 100%);
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #444;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.terminal-controls {
  display: flex;
  gap: 8px;
}

.control-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.control-dot.red {
  background: #ff5f56;
}

.control-dot.yellow {
  background: #ffbd2e;
}

.control-dot.green {
  background: #27ca3f;
}

.terminal-title {
  color: #00ff41;
  font-size: 16px;
  font-weight: bold;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.3);
}

.status-indicator.connected {
  color: #27ca3f;
}

.status-indicator.connecting {
  color: #ffbd2e;
}

.status-indicator.disconnected {
  color: #ff5f56;
}

.status-indicator.error {
  color: #ff4444;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
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

.minimize-btn {
  background: transparent;
  border: none;
  color: #888;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.minimize-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.terminal-content {
  position: relative;
  background: #0c0c0c;
  overflow: hidden;
}

.terminal-element {
  width: 100%;
  height: 100%;
  padding: 10px;
  box-sizing: border-box;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(12, 12, 12, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.loading-spinner {
  text-align: center;
  color: #00ff41;
}

.loading-spinner i {
  font-size: 24px;
  margin-bottom: 10px;
  display: block;
}

.loading-spinner p {
  margin: 0;
  font-size: 14px;
}

.terminal-footer {
  background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
  padding: 8px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #444;
  font-size: 12px;
}

.footer-info {
  display: flex;
  gap: 20px;
  color: #888;
}

.user-info,
.session-info {
  display: flex;
  align-items: center;
  gap: 5px;
}

.footer-controls {
  display: flex;
  gap: 10px;
}

.footer-btn {
  background: transparent;
  border: none;
  color: #888;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.footer-btn:hover {
  color: #00ff41;
  background: rgba(0, 255, 65, 0.1);
}

/* Dark scrollbar for terminal */
.terminal-element ::-webkit-scrollbar {
  width: 8px;
}

.terminal-element ::-webkit-scrollbar-track {
  background: #1a1a1a;
}

.terminal-element ::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}

.terminal-element ::-webkit-scrollbar-thumb:hover {
  background: #666;
}

/* Responsive design */
@media (max-width: 768px) {
  .mcp-terminal-container {
    margin: 10px;
  }

  .terminal-header {
    padding: 10px 15px;
  }

  .header-left,
  .header-right {
    gap: 10px;
  }

  .terminal-title {
    font-size: 14px;
  }

  .footer-info {
    gap: 15px;
  }

  .terminal-content {
    min-height: 300px;
  }
}

/* Animation for status changes */
.status-indicator {
  transition: all 0.3s ease;
}

.terminal-content {
  transition: height 0.3s ease;
}

/* Custom focus styles */
.minimize-btn:focus,
.footer-btn:focus {
  outline: 2px solid #00ff41;
  outline-offset: 2px;
}

/* Loading animation enhancement */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.fa-spin {
  animation: spin 1s linear infinite;
}

/* Terminal glow effect */
.terminal-element {
  box-shadow: inset 0 0 20px rgba(0, 255, 65, 0.1);
}

/* Header gradient animation */
.terminal-header {
  position: relative;
  overflow: hidden;
}

.terminal-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(0, 255, 65, 0.1),
    transparent
  );
  animation: sweep 3s ease-in-out infinite;
}

@keyframes sweep {
  0% {
    left: -100%;
  }
  50% {
    left: 100%;
  }
  100% {
    left: 100%;
  }
}

/* Enhanced button hover effects */
.footer-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 255, 65, 0.2);
}

.minimize-btn:hover {
  transform: scale(1.05);
}

/* Status indicator glow */
.status-indicator.connected .status-dot {
  box-shadow: 0 0 6px #27ca3f;
}

.status-indicator.connecting .status-dot {
  box-shadow: 0 0 6px #ffbd2e;
}

.status-indicator.error .status-dot {
  box-shadow: 0 0 6px #ff4444;
}
</style>
