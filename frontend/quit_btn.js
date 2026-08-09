(function () {
  const css = `
    #qb-btn {
      position: fixed;
      bottom: 20px;
      left: 20px;
      z-index: 9000;
      background: rgba(30,30,30,0.82);
      color: #f87171;
      border: 1.5px solid rgba(248,113,113,0.35);
      border-radius: 10px;
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 600;
      font-family: Inter, Arial, sans-serif;
      cursor: pointer;
      backdrop-filter: blur(6px);
      transition: background 0.15s, border-color 0.15s;
      letter-spacing: 0.01em;
    }
    #qb-btn:hover {
      background: rgba(248,113,113,0.18);
      border-color: #f87171;
    }
    #qb-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.6);
      z-index: 9999;
      align-items: center;
      justify-content: center;
      font-family: Inter, Arial, sans-serif;
    }
    #qb-overlay.open { display: flex; }
    #qb-box {
      background: #fff;
      border-radius: 16px;
      padding: 32px 28px 28px;
      max-width: 360px;
      width: 90%;
      box-shadow: 0 8px 40px rgba(0,0,0,0.22);
    }
    #qb-box h2 {
      margin: 0 0 8px;
      font-size: 18px;
      font-weight: 700;
      color: #0f172a;
    }
    #qb-box p {
      margin: 0 0 24px;
      font-size: 14px;
      color: #64748b;
      line-height: 1.5;
    }
    #qb-box .qb-actions {
      display: flex;
      gap: 10px;
    }
    #qb-box button {
      flex: 1;
      padding: 10px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 700;
      border: none;
      cursor: pointer;
      font-family: Inter, Arial, sans-serif;
    }
    #qb-cancel { background: #f1f5f9; color: #475569; }
    #qb-cancel:hover { background: #e2e8f0; }
    #qb-confirm { background: #ef4444; color: #fff; }
    #qb-confirm:hover { background: #dc2626; }
    #qb-confirm:disabled { opacity: 0.5; cursor: default; }
  `;

  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  const html = `
    <button id="qb-btn" onclick="qbOpen()">✕ Завершить игру</button>
    <div id="qb-overlay" onclick="qbClose()">
      <div id="qb-box" onclick="event.stopPropagation()">
        <h2>Завершить игру?</h2>
        <p>Игра будет сброшена, все игроки и ответы удалены из базы данных. Это действие нельзя отменить.</p>
        <div class="qb-actions">
          <button id="qb-cancel" onclick="qbClose()">Отмена</button>
          <button id="qb-confirm" onclick="qbConfirm()">Завершить</button>
        </div>
      </div>
    </div>
  `;

  const wrap = document.createElement('div');
  wrap.innerHTML = html;
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(wrap));
  if (document.readyState !== 'loading') document.body.appendChild(wrap);

  window.qbOpen = function () {
    document.getElementById('qb-overlay').classList.add('open');
  };

  window.qbClose = function () {
    document.getElementById('qb-overlay').classList.remove('open');
  };

  window.qbConfirm = async function () {
    const btn = document.getElementById('qb-confirm');
    btn.disabled = true;
    btn.textContent = '...';
    try {
      await fetch('/game/quit', { method: 'POST' });
    } catch (_) {}
    window.location.href = '/config.html';
  };

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') qbClose();
  });
})();
