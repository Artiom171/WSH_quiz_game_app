// Game color theme: presets + applyTheme(), shared by the host screen and the config editor.
// A theme is 6 base colors; everything else (muted text, glows, button text...) is derived.
(function () {
  const DEFAULT_THEME = {
    bg: '#0c1008', accent: '#cce840', answer: '#10b981',
    text: '#ffffff', glow1: '#82af00', glow2: '#d23769',
  };

  const THEME_PRESETS = [
    { name: 'Лайм',    theme: DEFAULT_THEME },
    { name: 'Океан',   theme: { bg: '#071423', accent: '#38bdf8', answer: '#2dd4bf', text: '#ffffff', glow1: '#1d4ed8', glow2: '#0891b2' } },
    { name: 'Закат',   theme: { bg: '#1a0b10', accent: '#fb923c', answer: '#facc15', text: '#fff7ed', glow1: '#e11d48', glow2: '#f97316' } },
    { name: 'Неон',    theme: { bg: '#0b0618', accent: '#e879f9', answer: '#22d3ee', text: '#ffffff', glow1: '#7c3aed', glow2: '#db2777' } },
    { name: 'Золото',  theme: { bg: '#12100a', accent: '#e5c07b', answer: '#fbbf24', text: '#fffbeb', glow1: '#a16207', glow2: '#7c2d12' } },
    { name: 'Светлая', theme: { bg: '#f8fafc', accent: '#4f46e5', answer: '#059669', text: '#0f172a', glow1: '#a5b4fc', glow2: '#f9a8d4' } },
    // Cyberpunk 2077: signature neon yellow, neon-blue "2077", red Cyberware HUD
    { name: 'Киберпанк', theme: { bg: '#0a0b14', accent: '#fcee0a', answer: '#00f0ff', text: '#ffffff', glow1: '#ff003c', glow2: '#00b7ff' } },
    // The Hunger Games: fire palette (red/orange/yellow), gold mockingjay on black
    { name: 'Голодные игры', theme: { bg: '#0d0705', accent: '#d4a537', answer: '#ff5a1f', text: '#f5efe6', glow1: '#b3120f', glow2: '#ff7a00' } },
    // The Matrix: green digital rain on black, bright "lead glyph" for the answer
    { name: 'Матрица', theme: { bg: '#0d0208', accent: '#00ff41', answer: '#c8ffd4', text: '#d7ffde', glow1: '#008f11', glow2: '#003b00' } },
    // Half-Life: HUD orange (255,160,0), lambda/HEV orange #ff6000, Black Mesa steel
    { name: 'Half-Life', theme: { bg: '#111214', accent: '#ffa000', answer: '#ff6000', text: '#f2f2f2', glow1: '#ff6000', glow2: '#2c5d6e' } },
  ];

  // The base colors as the editor shows them, in order
  const THEME_FIELDS = [
    { key: 'bg',     label: 'Фон' },
    { key: 'accent', label: 'Акцент',  hint: 'номер вопроса, таймер, кнопки' },
    { key: 'answer', label: 'Ответ' },
    { key: 'text',   label: 'Текст' },
    { key: 'glow1',  label: 'Подсветка 1', hint: 'размытое пятно слева сверху' },
    { key: 'glow2',  label: 'Подсветка 2', hint: 'размытое пятно справа снизу' },
  ];

  function rgb(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function hex([r, g, b]) {
    return '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  }
  // a*t + b*(1-t)
  function mix(a, b, t) {
    const x = rgb(a), y = rgb(b);
    return hex(x.map((v, i) => v * t + y[i] * (1 - t)));
  }
  function alpha(a, t) {
    const [r, g, b] = rgb(a);
    return `rgba(${r},${g},${b},${t})`;
  }
  // WCAG relative luminance and contrast ratio
  function luminance(a) {
    const [r, g, b] = rgb(a).map(v => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }
  function contrast(a, b) {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  }

  const isHex = v => typeof v === 'string' && /^#[0-9a-fA-F]{6}$/.test(v);

  // Missing or broken values fall back to the default theme
  function normalizeTheme(theme) {
    const t = { ...DEFAULT_THEME };
    if (theme) for (const k in t) if (isHex(theme[k])) t[k] = theme[k].toLowerCase();
    return t;
  }

  // Sets the theme's CSS variables on `el` (the whole page by default)
  function applyTheme(theme, el = document.documentElement) {
    const t = normalizeTheme(theme);
    const vars = {
      '--bg': t.bg,
      '--accent': t.accent,
      '--answer': t.answer,
      '--text': t.text,
      '--text-soft': mix(t.text, t.bg, 0.78),
      '--text-muted': mix(t.text, t.bg, 0.55),
      '--answer-light': mix(t.answer, luminance(t.bg) > 0.5 ? '#000000' : '#ffffff', 0.75),
      '--answer-dark': mix(t.answer, '#000000', 0.8),
      '--answer-glow': alpha(t.answer, 0.45),
      '--glow1': alpha(t.glow1, 0.28),
      '--glow2': alpha(t.glow2, 0.22),
      '--track': alpha(t.text, 0.08),
      '--on-accent': contrast('#ffffff', t.accent) >= contrast('#14180a', t.accent) ? '#ffffff' : '#14180a',
      '--panel': alpha(t.bg, 0.92),
      '--panel-border': alpha(t.text, 0.1),
      // player phones: page, card and field borders are the background tinted by the accent
      '--page': mix(t.accent, t.bg, 0.04),
      '--card': mix(t.accent, t.bg, 0.1),
      '--field-border': mix(t.accent, t.bg, 0.18),
      '--text-faint': mix(t.text, t.bg, 0.4),
      '--accent-a70': alpha(t.accent, 0.7),
      '--accent-a40': alpha(t.accent, 0.4),
      '--accent-a12': alpha(t.accent, 0.12),
      '--text-a20': alpha(t.text, 0.2),
    };
    for (const k in vars) el.style.setProperty(k, vars[k]);
  }

  // Text color that reads best on `bg`
  function readableText(bg) {
    return contrast('#ffffff', bg) >= contrast('#0f172a', bg) ? '#ffffff' : '#0f172a';
  }

  // Player phones remember the game's theme, so the next page paints in it right away
  function rememberTheme(theme) {
    try { localStorage.setItem('game_theme', JSON.stringify(theme || null)); } catch (_) {}
    applyTheme(theme);
  }
  function applyRememberedTheme() {
    let theme = null;
    try { theme = JSON.parse(localStorage.getItem('game_theme')); } catch (_) {}
    applyTheme(theme);
  }

  Object.assign(window, {
    DEFAULT_THEME, THEME_PRESETS, THEME_FIELDS,
    normalizeTheme, applyTheme, themeContrast: contrast, readableText,
    rememberTheme, applyRememberedTheme,
  });
})();
