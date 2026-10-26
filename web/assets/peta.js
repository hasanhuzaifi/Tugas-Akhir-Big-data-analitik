// Peta Leaflet: peta dasar jalan (opsional, butuh internet), lapisan heatmap halus (leaflet.heat) atau kotak sel, layar penuh.
const Peta = (() => {
  const CELL = 0.005, STOPS = ['#FFF3B0', '#FDBE4B', '#F26B38', '#C4262E', '#6E0F1A'];
  const hex = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const panas = t => { t = Math.max(0, Math.min(1, t)) * 4; const i = Math.min(3, Math.floor(t)); return 'rgb(' + mix(hex(STOPS[i]), hex(STOPS[i + 1]), t - i) + ')'; };
  // selisih: biru (B lebih padat) - abu - merah (A lebih padat)
  const selisih = d => { const A = [196, 38, 46], B = [20, 120, 181], N = [236, 239, 242], t = Math.min(1, Math.abs(d)); return 'rgb(' + mix(N, d >= 0 ? A : B, t) + ')'; };
  function buat(el, opt = {}) {
    const m = L.map(el, { zoomControl: true, preferCanvas: true, scrollWheelZoom: !opt.statis, minZoom: 9, maxZoom: 18, zoomSnap: .5 }).setView([41.84, -87.68], 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap', maxZoom: 19, className: 'dasar' }).addTo(m);
    m.layerSel = L.layerGroup().addTo(m); m.heat = null;
    if (opt.fs) {
      const C = L.Control.extend({ options: { position: 'topleft' }, onAdd() {
        const b = L.DomUtil.create('a', 'leaflet-bar peta-fs'); b.href = '#'; b.title = 'Layar penuh'; b.setAttribute('role', 'button'); b.setAttribute('aria-label', 'Layar penuh'); b.textContent = '⛶';
        const toggle = on => { m.getContainer().classList.toggle('fs', on); document.body.classList.toggle('fs-lock', on); setTimeout(() => m.invalidateSize(), 50); };
        L.DomEvent.on(b, 'click', e => { L.DomEvent.preventDefault(e); toggle(!m.getContainer().classList.contains('fs')); });
        document.addEventListener('keydown', e => { if (e.key === 'Escape') toggle(false); });
        return b; } });
      new C().addTo(m);
    }
    return m;
  }
  function bersih(m) { m.layerSel.clearLayers(); if (m.heat) { m.removeLayer(m.heat); m.heat = null; } }
  // cells: [{la,lo,n}], warna: fungsi(sel)->css, tip: fungsi(sel)->teks
  function gambar(m, cells, warna, tip) {
    bersih(m);
    for (const c of cells) {
      const r = L.rectangle([[c.la - CELL / 2, c.lo - CELL / 2], [c.la + CELL / 2, c.lo + CELL / 2]],
        { stroke: false, fillColor: warna(c), fillOpacity: .72, interactive: !!tip });
      if (tip) r.bindTooltip(tip(c), { sticky: true });
      r.addTo(m.layerSel);
    }
  }
  // heatmap halus: pts [[la,lo,0..1]]
  function halus(m, pts, radius = 16, blur = 20) {
    bersih(m);
    m.heat = L.heatLayer(pts, { radius, blur, max: .55, minOpacity: .3, gradient: { .15: STOPS[0], .4: STOPS[1], .6: STOPS[2], .8: STOPS[3], 1: STOPS[4] } }).addTo(m);
  }
  return { CELL, panas, selisih, buat, gambar, halus, STOPS };
})();
