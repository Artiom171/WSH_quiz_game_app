// Justified image grid for image questions (host screen + config preview).
// Splits the figures into rows (keeping their order) and picks the split that makes
// the images as large as possible inside the container, then sizes every image exactly.
(function () {
  const GAP = 24;      // between images, rows and the footer
  const RADIUS = 18;   // image corner radius (matches the page CSS)

  // All ways to split n items into k consecutive non-empty rows, as row lengths
  function splits(n, k) {
    const res = [];
    (function rec(start, rowsLeft, acc) {
      if (rowsLeft === 1) { res.push([...acc, n - start]); return; }
      for (let len = 1; len <= n - start - (rowsLeft - 1); len++) rec(start + len, rowsLeft - 1, [...acc, len]);
    })(0, k, []);
    return res;
  }

  // joined: one seamless row (rebus), images touch each other
  function bestLayout(aspects, capHs, W, H, joined) {
    const n = aspects.length;
    const gap = joined ? 0 : GAP;
    let best = null;
    for (let k = 1; k <= (joined ? 1 : n); k++) {
      for (const lengths of splits(n, k)) {
        let i = 0, sumH = 0, sumCap = 0;
        const rows = lengths.map(len => {
          const idx = [];
          for (let j = 0; j < len; j++) idx.push(i + j);
          i += len;
          const S = idx.reduce((s, j) => s + aspects[j], 0);
          const h = (W - gap * (len - 1)) / S;           // row height when it fills the width
          const cap = Math.max(0, ...idx.map(j => capHs[j]));
          sumH += h; sumCap += cap;
          return { idx, S, h };
        });
        const avail = H - sumCap - GAP * (k - 1);
        if (avail <= 0) continue;
        const scale = Math.min(1, avail / sumH);         // shrink all rows to fit the height
        rows.forEach(r => { r.h *= scale; });
        const area = rows.reduce((s, r) => s + r.h * r.h * r.S, 0);
        if (!best || area > best.area * 1.001) best = { rows, area };
      }
    }
    return best;
  }

  function outerHeight(el) {
    const cs = getComputedStyle(el);
    return el.offsetHeight + (parseFloat(cs.marginTop) || 0) + (parseFloat(cs.marginBottom) || 0);
  }

  function layout(box, footer, joined) {
    const figs = [...box.querySelectorAll('figure')];
    const W = box.clientWidth;
    const H = box.clientHeight - (footer ? outerHeight(footer) + GAP : 0);
    if (!figs.length || !W || H <= 0) return;
    const aspects = figs.map(f => {
      const img = f.querySelector('img');
      return img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 1.5;
    });
    const capHs = figs.map(f => {
      const cap = f.querySelector('figcaption');
      return cap ? cap.offsetHeight + (parseFloat(getComputedStyle(f).rowGap) || 0) : 0;
    });
    const best = bestLayout(aspects, capHs, W, H, joined);
    if (!best) return;
    // rebuild only the rows; the footer is moved in once and then stays put,
    // so its reveal animation does not restart on every relayout
    box.querySelectorAll(':scope > .img-grid-row').forEach(r => r.remove());
    const anchor = footer && footer.parentNode === box ? footer : null;
    best.rows.forEach(r => {
      const row = document.createElement('div');
      row.className = 'img-grid-row';
      row.style.cssText = `display:flex; justify-content:center; gap:${joined ? 0 : GAP}px;`;
      r.idx.forEach((j, pos) => {
        const w = Math.floor(r.h * aspects[j]) + 'px';
        const img = figs[j].querySelector('img');
        img.style.width = w;
        img.style.height = Math.floor(r.h) + 'px';
        if (joined) {  // round only the outer corners of the strip
          const first = pos === 0, last = pos === r.idx.length - 1;
          img.style.borderRadius = `${first ? RADIUS : 0}px ${last ? RADIUS : 0}px ${last ? RADIUS : 0}px ${first ? RADIUS : 0}px`;
        } else {
          img.style.borderRadius = '';
        }
        figs[j].style.width = w;  // captions wrap within their image
        row.appendChild(figs[j]);
      });
      box.insertBefore(row, anchor);
    });
    if (footer && !anchor) box.appendChild(footer);
  }

  // Lays out `box` now, after each image loads, and whenever the box is resized.
  // `footer` (optional, e.g. the question text) is kept right under the images,
  // so images and text stay together as one centered group.
  // `joined` (rebus questions): all images in one row, touching, no gaps.
  window.setupImageGrid = function (box, footer, joined = false) {
    box.style.display = 'flex';
    box.style.flexDirection = 'column';
    box.style.justifyContent = 'center';
    box.style.alignItems = 'center';
    box.style.gap = GAP + 'px';
    // second pass re-measures captions once their figure widths are set
    const run = () => { layout(box, footer, joined); layout(box, footer, joined); };
    box.querySelectorAll('img').forEach(img => {
      img.addEventListener('load', run);
      img.addEventListener('error', run);
    });
    if (box._gridObserver) box._gridObserver.disconnect();
    box._gridObserver = new ResizeObserver(run);
    box._gridObserver.observe(box);
    run();
  };
})();
