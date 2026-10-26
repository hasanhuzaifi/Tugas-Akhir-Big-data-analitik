// Peta panas sel (Leaflet). Sel digambar sendiri; ubin peta dasar opsional (hanya bila ada internet).
const Peta = (() => {
  const CELL = 0.005, STOPS = ['#FFF3B0', '#FDBE4B', '#F26B38', '#C4262E', '#6E0F1A'];
  const hex = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const panas = t => { t = Math.max(0, Math.min(1, t)) * 4; const i = Math.min(3, Math.floor(t)); return 'rgb(' + mix(hex(STOPS[i]), hex(STOPS[i + 1]), t - i) + ')'; };
  // selisih: biru (B lebih padat) - abu - merah (A lebih padat)
  const selisih = d => { const A = [196, 38, 46], B = [20, 120, 181], N = [236, 239, 242], t = Math.min(1, Math.abs(d)); return 'rgb(' + mix(N, d >= 0 ? A : B, t) + ')'; };
  function buat(el) {
    const m = L.map(el, { zoomControl: true, preferCanvas: true, attributionControl: true }).setView([41.84, -87.68], 11);
    m.layerSel = L.layerGroup().addTo(m);
    return m;
  }
  // cells: [{la,lo,n}], warna: fungsi(n)->css, tip: fungsi(sel)->teks
  function gambar(m, cells, warna, tip) {
    m.layerSel.clearLayers();
    for (const c of cells) {
      const r = L.rectangle([[c.la - CELL / 2, c.lo - CELL / 2], [c.la + CELL / 2, c.lo + CELL / 2]],
        { stroke: false, fillColor: warna(c), fillOpacity: .78, interactive: !!tip });
      if (tip) r.bindTooltip(tip(c), { sticky: true });
      r.addTo(m.layerSel);
    }
  }
  return { CELL, panas, selisih, buat, gambar, STOPS };
})();
