// erpnext_mcp_server/public/js/terminal-utils.js

/**
 * Terminal styling utilities for ERPNext MCP Terminal
 * Browser-compatible versions of ora, chalk, and figlet functionality
 */

// Chalk-like color utilities for browser terminal
export class TerminalColors {
  static colors = {
    // Basic colors
    black: '\x1b[30m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    white: '\x1b[37m',
    gray: '\x1b[90m',
    grey: '\x1b[90m',

    // Bright colors
    brightRed: '\x1b[91m',
    brightGreen: '\x1b[92m',
    brightYellow: '\x1b[93m',
    brightBlue: '\x1b[94m',
    brightMagenta: '\x1b[95m',
    brightCyan: '\x1b[96m',
    brightWhite: '\x1b[97m',

    // Background colors
    bgBlack: '\x1b[40m',
    bgRed: '\x1b[41m',
    bgGreen: '\x1b[42m',
    bgYellow: '\x1b[43m',
    bgBlue: '\x1b[44m',
    bgMagenta: '\x1b[45m',
    bgCyan: '\x1b[46m',
    bgWhite: '\x1b[47m',

    // Styles
    reset: '\x1b[0m',
    bold: '\x1b[1m',
    dim: '\x1b[2m',
    italic: '\x1b[3m',
    underline: '\x1b[4m',
    inverse: '\x1b[7m',
    hidden: '\x1b[8m',
    strikethrough: '\x1b[9m',
  };

  // Chalk-like API
  static red(text) {
    return `${this.colors.red}${text}${this.colors.reset}`;
  }
  static green(text) {
    return `${this.colors.green}${text}${this.colors.reset}`;
  }
  static yellow(text) {
    return `${this.colors.yellow}${text}${this.colors.reset}`;
  }
  static blue(text) {
    return `${this.colors.blue}${text}${this.colors.reset}`;
  }
  static magenta(text) {
    return `${this.colors.magenta}${text}${this.colors.reset}`;
  }
  static cyan(text) {
    return `${this.colors.cyan}${text}${this.colors.reset}`;
  }
  static white(text) {
    return `${this.colors.white}${text}${this.colors.reset}`;
  }
  static gray(text) {
    return `${this.colors.gray}${text}${this.colors.reset}`;
  }
  static grey(text) {
    return `${this.colors.grey}${text}${this.colors.reset}`;
  }

  // Bright colors
  static brightRed(text) {
    return `${this.colors.brightRed}${text}${this.colors.reset}`;
  }
  static brightGreen(text) {
    return `${this.colors.brightGreen}${text}${this.colors.reset}`;
  }
  static brightYellow(text) {
    return `${this.colors.brightYellow}${text}${this.colors.reset}`;
  }
  static brightBlue(text) {
    return `${this.colors.brightBlue}${text}${this.colors.reset}`;
  }
  static brightMagenta(text) {
    return `${this.colors.brightMagenta}${text}${this.colors.reset}`;
  }
  static brightCyan(text) {
    return `${this.colors.brightCyan}${text}${this.colors.reset}`;
  }
  static brightWhite(text) {
    return `${this.colors.brightWhite}${text}${this.colors.reset}`;
  }

  // Styles
  static bold(text) {
    return `${this.colors.bold}${text}${this.colors.reset}`;
  }
  static dim(text) {
    return `${this.colors.dim}${text}${this.colors.reset}`;
  }
  static italic(text) {
    return `${this.colors.italic}${text}${this.colors.reset}`;
  }
  static underline(text) {
    return `${this.colors.underline}${text}${this.colors.reset}`;
  }
  static inverse(text) {
    return `${this.colors.inverse}${text}${this.colors.reset}`;
  }
  static strikethrough(text) {
    return `${this.colors.strikethrough}${text}${this.colors.reset}`;
  }

  // Background colors
  static bgRed(text) {
    return `${this.colors.bgRed}${text}${this.colors.reset}`;
  }
  static bgGreen(text) {
    return `${this.colors.bgGreen}${text}${this.colors.reset}`;
  }
  static bgYellow(text) {
    return `${this.colors.bgYellow}${text}${this.colors.reset}`;
  }
  static bgBlue(text) {
    return `${this.colors.bgBlue}${text}${this.colors.reset}`;
  }
  static bgMagenta(text) {
    return `${this.colors.bgMagenta}${text}${this.colors.reset}`;
  }
  static bgCyan(text) {
    return `${this.colors.bgCyan}${text}${this.colors.reset}`;
  }
  static bgWhite(text) {
    return `${this.colors.bgWhite}${text}${this.colors.reset}`;
  }

  // Chainable API (chalk-like)
  static chain() {
    let styles = [];
    const api = {
      red: () => {
        styles.push('red');
        return api;
      },
      green: () => {
        styles.push('green');
        return api;
      },
      yellow: () => {
        styles.push('yellow');
        return api;
      },
      blue: () => {
        styles.push('blue');
        return api;
      },
      magenta: () => {
        styles.push('magenta');
        return api;
      },
      cyan: () => {
        styles.push('cyan');
        return api;
      },
      white: () => {
        styles.push('white');
        return api;
      },
      gray: () => {
        styles.push('gray');
        return api;
      },
      bold: () => {
        styles.push('bold');
        return api;
      },
      dim: () => {
        styles.push('dim');
        return api;
      },
      italic: () => {
        styles.push('italic');
        return api;
      },
      underline: () => {
        styles.push('underline');
        return api;
      },
      inverse: () => {
        styles.push('inverse');
        return api;
      },
      bgRed: () => {
        styles.push('bgRed');
        return api;
      },
      bgGreen: () => {
        styles.push('bgGreen');
        return api;
      },
      bgYellow: () => {
        styles.push('bgYellow');
        return api;
      },
      bgBlue: () => {
        styles.push('bgBlue');
        return api;
      },
      apply: (text) => {
        let result = text;
        const opening = styles.map((style) => this.colors[style]).join('');
        return `${opening}${result}${this.colors.reset}`;
      },
    };
    return api;
  }

  // Gradient text (advanced feature)
  static gradient(text, colors = ['red', 'yellow', 'green']) {
    const chars = text.split('');
    const colorCount = colors.length;
    const step = Math.max(1, Math.floor(chars.length / colorCount));

    return chars
      .map((char, index) => {
        const colorIndex = Math.min(Math.floor(index / step), colorCount - 1);
        const color = colors[colorIndex];
        return this[color] ? this[color](char) : char;
      })
      .join('');
  }
}

// Ora-like spinner for browser terminal
export class TerminalSpinner {
  constructor(options = {}) {
    this.text = options.text || 'Loading...';
    this.spinner = options.spinner || 'dots';
    this.color = options.color || 'cyan';
    this.terminal = options.terminal;
    this.isSpinning = false;
    this.interval = null;
    this.currentFrame = 0;

    this.spinners = {
      dots: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
      dots2: ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'],
      dots3: [
        '⠄',
        '⠆',
        '⠇',
        '⠋',
        '⠙',
        '⠸',
        '⠰',
        '⠠',
        '⠰',
        '⠸',
        '⠙',
        '⠋',
        '⠇',
        '⠆',
      ],
      line: ['-', '\\', '|', '/'],
      pipe: ['┤', '┘', '┴', '└', '├', '┌', '┬', '┐'],
      arrow: ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'],
      clock: [
        '🕐',
        '🕑',
        '🕒',
        '🕓',
        '🕔',
        '🕕',
        '🕖',
        '🕗',
        '🕘',
        '🕙',
        '🕚',
        '🕛',
      ],
      moon: ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘'],
      star: ['✦', '✧', '✨', '✧'],
      bounce: ['⠁', '⠂', '⠄', '⠂'],
      toggle: ['⊶', '⊷'],
      balloon: [' ', '.', 'o', 'O', '@', '*'],
      noise: ['▓', '▒', '░'],
      hearts: ['💛', '💙', '💜', '💚', '❤️'],
      earth: ['🌍', '🌎', '🌏'],
      boxBounce: ['▖', '▘', '▝', '▗'],
    };
  }

  start(text) {
    if (text) this.text = text;
    if (this.isSpinning) return this;

    this.isSpinning = true;
    this.currentFrame = 0;

    if (this.terminal) {
      this.interval = setInterval(() => {
        const frames = this.spinners[this.spinner];
        const frame = frames[this.currentFrame % frames.length];
        const coloredFrame = TerminalColors[this.color]
          ? TerminalColors[this.color](frame)
          : frame;

        // Clear current line and write spinner
        this.terminal.write('\r\x1b[K');
        this.terminal.write(`${coloredFrame} ${this.text}`);

        this.currentFrame++;
      }, 100);
    }

    return this;
  }

  stop() {
    if (!this.isSpinning) return this;

    this.isSpinning = false;
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }

    if (this.terminal) {
      this.terminal.write('\r\x1b[K');
    }

    return this;
  }

  succeed(text) {
    this.stop();
    if (this.terminal) {
      const successText = text || this.text;
      this.terminal.write(`${TerminalColors.green('✓')} ${successText}\r\n`);
    }
    return this;
  }

  fail(text) {
    this.stop();
    if (this.terminal) {
      const failText = text || this.text;
      this.terminal.write(`${TerminalColors.red('✗')} ${failText}\r\n`);
    }
    return this;
  }

  warn(text) {
    this.stop();
    if (this.terminal) {
      const warnText = text || this.text;
      this.terminal.write(`${TerminalColors.yellow('⚠')} ${warnText}\r\n`);
    }
    return this;
  }

  info(text) {
    this.stop();
    if (this.terminal) {
      const infoText = text || this.text;
      this.terminal.write(`${TerminalColors.blue('ℹ')} ${infoText}\r\n`);
    }
    return this;
  }
}

// Figlet-like ASCII art generator
export class TerminalFiglet {
  static fonts = {
    small: {
      height: 3,
      chars: {
        E: ['███', '█  ', '███'],
        R: ['██ ', '██ ', '█ █'],
        P: ['██ ', '██ ', '█  '],
        N: ['█ █', '███', '█ █'],
        e: [' ██', '█  ', ' ██'],
        X: ['█ █', ' █ ', '█ █'],
        x: ['█ █', ' █ ', '█ █'],
        T: ['███', ' █ ', ' █ '],
        t: ['███', ' █ ', ' █ '],
        ' ': ['   ', '   ', '   '],
        M: ['█ █', '███', '█ █'],
        C: ['███', '█  ', '███'],
        S: ['███', ' ██', '███'],
        r: ['██ ', '█ █', '█ █'],
        v: ['█ █', '█ █', ' █ '],
      },
    },
    block: {
      height: 5,
      chars: {
        E: ['████', '█   ', '███ ', '█   ', '████'],
        R: ['████', '█  █', '███ ', '█ █ ', '█  █'],
        P: ['████', '█  █', '███ ', '█   ', '█   '],
        N: ['█  █', '██ █', '█ ██', '█  █', '█  █'],
        e: ['    ', ' ███', '█   ', '█  █', ' ██ '],
        X: ['    ', '█  █', ' ██ ', ' ██ ', '█  █'],
        x: ['    ', '█  █', ' ██ ', ' ██ ', '█  █'],
        T: [' █  ', '███ ', ' █  ', ' █  ', ' ██ '],
        t: [' █  ', '███ ', ' █  ', ' █  ', ' ██ '],
        ' ': ['    ', '    ', '    ', '    ', '    '],
        M: ['█  █', '████', '█  █', '█  █', '█  █'],
        C: [' ███', '█   ', '█   ', '█   ', ' ███'],
        S: [' ███', '█   ', ' ██ ', '   █', '███ '],
        r: ['    ', '██  ', '█ █ ', '█   ', '█   '],
        v: ['    ', '█  █', '█  █', ' ██ ', '  █ '],
      },
    },
  };

  static generate(text, font = 'small', color = null) {
    const fontData = this.fonts[font];
    if (!fontData) return text;

    const lines = Array(fontData.height).fill('');
    const chars = text.toUpperCase().split('');

    chars.forEach((char) => {
      const charData = fontData.chars[char] || fontData.chars[' '];
      charData.forEach((line, index) => {
        lines[index] += line + ' ';
      });
    });

    const result = lines.join('\n');
    return color && TerminalColors[color]
      ? TerminalColors[color](result)
      : result;
  }

  // Create custom ASCII banner
  static banner(text, options = {}) {
    const {
      font = 'block',
      color = 'cyan',
      border = true,
      padding = 1,
    } = options;

    const ascii = this.generate(text, font, color);
    const lines = ascii.split('\n');
    const maxWidth = Math.max(...lines.map((line) => line.length));

    if (border) {
      const borderChar = '═';
      const cornerTL = '╔';
      const cornerTR = '╗';
      const cornerBL = '╚';
      const cornerBR = '╝';
      const vertical = '║';

      const topBorder =
        cornerTL + borderChar.repeat(maxWidth + padding * 2) + cornerTR;
      const bottomBorder =
        cornerBL + borderChar.repeat(maxWidth + padding * 2) + cornerBR;
      const emptyLine =
        vertical + ' '.repeat(maxWidth + padding * 2) + vertical;

      let result = topBorder + '\n';

      for (let i = 0; i < padding; i++) {
        result += emptyLine + '\n';
      }

      lines.forEach((line) => {
        const paddedLine = line.padEnd(maxWidth);
        result +=
          vertical +
          ' '.repeat(padding) +
          paddedLine +
          ' '.repeat(padding) +
          vertical +
          '\n';
      });

      for (let i = 0; i < padding; i++) {
        result += emptyLine + '\n';
      }

      result += bottomBorder;

      return color && TerminalColors[color]
        ? TerminalColors[color](result)
        : result;
    }

    return ascii;
  }
}

// Progress bar utility
export class TerminalProgress {
  constructor(total, options = {}) {
    this.total = total;
    this.current = 0;
    this.terminal = options.terminal;
    this.width = options.width || 40;
    this.format = options.format || '{bar} {percentage}% | {current}/{total}';
    this.complete = options.complete || '█';
    this.incomplete = options.incomplete || '░';
    this.clear = options.clear !== false;
  }

  update(current, payload = {}) {
    this.current = current;

    if (this.terminal) {
      const percentage = Math.round((current / this.total) * 100);
      const completed = Math.round((current / this.total) * this.width);
      const remaining = this.width - completed;

      const bar =
        TerminalColors.green(this.complete.repeat(completed)) +
        TerminalColors.gray(this.incomplete.repeat(remaining));

      let display = this.format
        .replace('{bar}', bar)
        .replace('{percentage}', percentage.toString())
        .replace('{current}', current.toString())
        .replace('{total}', this.total.toString());

      // Add custom payload
      Object.keys(payload).forEach((key) => {
        display = display.replace(`{${key}}`, payload[key]);
      });

      this.terminal.write('\r\x1b[K' + display);

      if (current >= this.total && this.clear) {
        this.terminal.write('\r\n');
      }
    }
  }

  increment(step = 1, payload = {}) {
    this.update(this.current + step, payload);
  }

  tick(payload = {}) {
    this.increment(1, payload);
  }
}

// Box drawing utilities
export class TerminalBox {
  static single = {
    topLeft: '┌',
    topRight: '┐',
    bottomLeft: '└',
    bottomRight: '┘',
    horizontal: '─',
    vertical: '│',
    cross: '┼',
    topTee: '┬',
    bottomTee: '┴',
    leftTee: '├',
    rightTee: '┤',
  };

  static double = {
    topLeft: '╔',
    topRight: '╗',
    bottomLeft: '╚',
    bottomRight: '╝',
    horizontal: '═',
    vertical: '║',
    cross: '╬',
    topTee: '╦',
    bottomTee: '╩',
    leftTee: '╠',
    rightTee: '╣',
  };

  static rounded = {
    topLeft: '╭',
    topRight: '╮',
    bottomLeft: '╰',
    bottomRight: '╯',
    horizontal: '─',
    vertical: '│',
    cross: '┼',
    topTee: '┬',
    bottomTee: '┴',
    leftTee: '├',
    rightTee: '┤',
  };

  static create(content, options = {}) {
    const {
      style = 'single',
      padding = 1,
      margin = 0,
      title = null,
      color = null,
      width = null,
    } = options;

    const chars = this[style] || this.single;
    const lines = content.split('\n');
    const contentWidth = width || Math.max(...lines.map((line) => line.length));
    const innerWidth = contentWidth + padding * 2;

    let result = '';

    // Add top margin
    for (let i = 0; i < margin; i++) {
      result += '\n';
    }

    // Top border
    let topBorder =
      ' '.repeat(margin) +
      chars.topLeft +
      chars.horizontal.repeat(innerWidth) +
      chars.topRight;

    if (title) {
      const titleText = ` ${title} `;
      const titlePos = Math.max(
        0,
        Math.floor((innerWidth - titleText.length) / 2)
      );
      topBorder =
        ' '.repeat(margin) +
        chars.topLeft +
        chars.horizontal.repeat(titlePos) +
        titleText +
        chars.horizontal.repeat(innerWidth - titlePos - titleText.length) +
        chars.topRight;
    }

    result += topBorder + '\n';

    // Content with padding
    for (let i = 0; i < padding; i++) {
      result +=
        ' '.repeat(margin) +
        chars.vertical +
        ' '.repeat(innerWidth) +
        chars.vertical +
        '\n';
    }

    lines.forEach((line) => {
      const paddedLine = line.padEnd(contentWidth);
      result +=
        ' '.repeat(margin) +
        chars.vertical +
        ' '.repeat(padding) +
        paddedLine +
        ' '.repeat(padding + contentWidth - line.length) +
        chars.vertical +
        '\n';
    });

    for (let i = 0; i < padding; i++) {
      result +=
        ' '.repeat(margin) +
        chars.vertical +
        ' '.repeat(innerWidth) +
        chars.vertical +
        '\n';
    }

    // Bottom border
    const bottomBorder =
      ' '.repeat(margin) +
      chars.bottomLeft +
      chars.horizontal.repeat(innerWidth) +
      chars.bottomRight;
    result += bottomBorder;

    // Add bottom margin
    for (let i = 0; i < margin; i++) {
      result += '\n';
    }

    return color && TerminalColors[color]
      ? TerminalColors[color](result)
      : result;
  }

  static table(data, options = {}) {
    const { style = 'single', headers = null, colors = {} } = options;
    const chars = this[style] || this.single;

    if (!data.length) return '';

    // Calculate column widths
    const rows = headers ? [headers, ...data] : data;
    const colWidths = [];

    rows.forEach((row) => {
      row.forEach((cell, index) => {
        const cellLength = String(cell).length;
        colWidths[index] = Math.max(colWidths[index] || 0, cellLength);
      });
    });

    let result = '';

    // Top border
    result += chars.topLeft;
    colWidths.forEach((width, index) => {
      result += chars.horizontal.repeat(width + 2);
      if (index < colWidths.length - 1) {
        result += chars.topTee;
      }
    });
    result += chars.topRight + '\n';

    // Headers
    if (headers) {
      result += chars.vertical;
      headers.forEach((header, index) => {
        const cell = ` ${String(header).padEnd(colWidths[index])} `;
        result += colors.header ? TerminalColors[colors.header](cell) : cell;
        result += chars.vertical;
      });
      result += '\n';

      // Header separator
      result += chars.leftTee;
      colWidths.forEach((width, index) => {
        result += chars.horizontal.repeat(width + 2);
        if (index < colWidths.length - 1) {
          result += chars.cross;
        }
      });
      result += chars.rightTee + '\n';
    }

    // Data rows
    data.forEach((row) => {
      result += chars.vertical;
      row.forEach((cell, index) => {
        const cellText = ` ${String(cell).padEnd(colWidths[index])} `;
        result += cellText + chars.vertical;
      });
      result += '\n';
    });

    // Bottom border
    result += chars.bottomLeft;
    colWidths.forEach((width, index) => {
      result += chars.horizontal.repeat(width + 2);
      if (index < colWidths.length - 1) {
        result += chars.bottomTee;
      }
    });
    result += chars.bottomRight;

    return result;
  }
}

// Export all utilities
export { TerminalColors as chalk };
export { TerminalSpinner as ora };
export { TerminalFiglet as figlet };

// Global aliases for easier use
if (typeof window !== 'undefined') {
  window.TerminalColors = TerminalColors;
  window.TerminalSpinner = TerminalSpinner;
  window.TerminalFiglet = TerminalFiglet;
  window.TerminalProgress = TerminalProgress;
  window.TerminalBox = TerminalBox;

  // Aliases
  window.chalk = TerminalColors;
  window.ora = TerminalSpinner;
  window.figlet = TerminalFiglet;
}
