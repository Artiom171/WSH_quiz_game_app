// Image grid for question/answer images (host screen + config preview).
// Several images get identical frames: the frame shape is the average of the images'
// shapes (so each is cropped as little as possible) and the number of columns is the
// one that makes the frames largest inside the container. A single image keeps its shape.
(function () {
  const GAP = 24;      // between images, rows and the footer
  const RADIUS = 18;   // image corner radius (matches the page CSS)

  // Frame shape for several images: geometric mean of their aspect ratios, kept sane
  function frameAspect(aspects) {
    const mean = Math.exp(aspects.reduce((s, a) => s + Math.log(a), 0) / aspects.length);
    return Math.min(2.2, Math.max(0.6, mean));
  }

  // Equal frames in rows of `cols` (keeping order); picks the column count with the
  // largest frames. joined: one seamless row (rebus), frames touch each other
  function bestLayout(aspects, capHs, W, H, joined) {
    const n = aspects.length;
    const aspect = n === 1 ? aspects[0] : frameAspect(aspects);
    const gap = joined ? 0 : GAP;
    const capH = Math.max(0, ...capHs);
    let best = null;
    for (let cols = joined ? n : 1; cols <= n; cols++) {
      const rowsCount = Math.ceil(n / cols);
      const availH = H - rowsCount * capH - GAP * (rowsCount - 1);
      if (availH <= 0) continue;
      const w = Math.min((W - gap * (cols - 1)) / cols, (availH / rowsCount) * aspect);
      if (!best || w > best.w * 1.001) best = { cols, w };
    }
    if (!best) return null;
    const h = best.w / aspect;
    const rows = [];
    for (let i = 0; i < n; i += best.cols) {
      const idx = [];
      for (let j = i; j < Math.min(n, i + best.cols); j++) idx.push(j);
      rows.push({ idx, h, w: best.w });
    }
    return { rows, cover: n > 1 };
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
        const w = Math.floor(r.w) + 'px';
        const img = figs[j].querySelector('img');
        img.style.width = w;
        img.style.height = Math.floor(r.h) + 'px';
        // several images: fill the shared frame, cropping a little; aim above center for faces
        img.style.objectFit = best.cover ? 'cover' : '';
        img.style.objectPosition = best.cover ? 'center 30%' : '';
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
  // Several images always get identical frames.
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
