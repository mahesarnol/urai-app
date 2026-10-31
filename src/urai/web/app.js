/* Urai App 3.0: logika tampilan.
   Semua pekerjaan berat dikerjakan Python (api.py). Tampilan memanggil window.pywebview.api.<nama>(),
   atau POST /api/<nama> saat dibuka di browser dengan ?dev=1 (devserver.py). Kabar proses diambil lewat poll(). */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const win = $('#win');
  const DEV = new URLSearchParams(location.search).has('dev');

  /* ---------- jembatan ke Python ---------- */
  function waitBridge(timeout = 20000) {
    return new Promise((resolve, reject) => {
      if (DEV) { resolve(); return; }
      const ok = () => window.pywebview && window.pywebview.api && typeof window.pywebview.api.init === 'function';
      if (ok()) { resolve(); return; }
      const t0 = Date.now();
      window.addEventListener('pywebviewready', () => resolve(), { once: true });
      const tick = () => { if (ok()) resolve(); else if (Date.now() - t0 > timeout) reject(new Error('bridge')); else setTimeout(tick, 100); };
      setTimeout(tick, 100);
    });
  }
  async function call(name, ...args) {
    if (!DEV) return window.pywebview.api[name](...args);
    const r = await fetch('/api/' + name, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(args) });
    const j = await r.json();
    if (j.error) throw new Error(j.error);
    return j.result;
  }
  async function safeCall(name, ...args) {
    try { return await call(name, ...args); }
    catch (e) { console.error(name, e); toast('Terjadi kesalahan. Coba lagi, atau tutup dan buka ulang Urai App.'); return null; }
  }

  /* ---------- bantuan kecil ---------- */
  const fmt = n => Number(n || 0).toLocaleString('id-ID');
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const ic = (id, cls = '') => `<svg class="ic ${cls}"><use href="#i-${id}"/></svg>`;
  const baseName = name => String(name || '').replace(/\.[A-Za-z0-9]{2,5}$/, '');
  const sizeText = b => b >= 1048576 ? (b / 1048576).toFixed(1).replace('.', ',') + ' MB' : b >= 1024 ? Math.round(b / 1024) + ' KB' : b + ' B';
  const now = () => { const d = new Date(), p = x => String(x).padStart(2, '0'); return { date: `${p(d.getDate())}-${p(d.getMonth() + 1)}-${d.getFullYear()}`, time: `${p(d.getHours())}.${p(d.getMinutes())}` }; };
  const reduce = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const sep = p => (String(p).includes('\\') ? '\\' : '/');
  const lastParts = (p, n = 2) => { const s = sep(p); return String(p).split(/[\\/]/).filter(Boolean).slice(-n).join(` ${s} `); };
  const fileOf = p => String(p || '').split(/[\\/]/).pop();
  let debounceT = {};
  const debounce = (key, fn, ms) => { clearTimeout(debounceT[key]); debounceT[key] = setTimeout(fn, ms); };

  /* ---------- keadaan ---------- */
  const S = {
    app: {}, providers: {}, models: {}, baseUrls: {}, keys: {}, tess: { available: false, langs: [], names: {} },
    set: {}, defaultDir: '', hasQris: false, hasSamples: true,
    items: [], busy: false, cancelling: false, done: null, sel: null, tab: 'view', rereading: null,
    progress: { done: 0, total: 0, current: null },
    texts: {}, pvShown: '',
    pane: 'offline', dlg: { provider: 'gemini', typed: {}, models: {}, urls: {} },
    mm: { src: 'struct', kind: 'umum', view: 'map', busy: false, busyKey: '', busyText: '', cache: {}, style: null },
  };
  const stateName = () => S.busy ? 'busy' : S.done ? 'done' : (S.items.length ? 'ready' : 'empty');
  const provName = p => (S.providers[p] || {}).name || 'penyedia AI';
  const langLabel = () => (S.set.langs || []).map(l => S.tess.names[l] || l).join(', ');
  const findItem = id => S.items.find(i => i.id === id);
  const isCombined = () => S.set.out_mode === 'combined';
  const currentKey = () => (isCombined() && !S.sel) ? 'ALL' : (S.sel || (S.items[0] && S.items[0].id) || '');

  function saveSet(patch) {
    Object.assign(S.set, patch);
    call('save_settings', patch).then(s => { if (s) S.set = s; }).catch(e => console.error(e));
  }

  /* ---------- tampilan Markdown (aman: semua teks di-escape) ---------- */
  function inline(s) {
    let t = esc(s);
    t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
    t = t.replace(/!\[([^\]]*)\]\([^)]*\)/g, (m, a) => `<span class="imgph">${ic('image')}Gambar${a && a !== 'image' ? ': ' + a : ''}</span>`);
    t = t.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1');
    t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/__(.+?)__/g, '<strong>$1</strong>');
    t = t.replace(/(^|[\s(])\*(?!\s)(.+?)(?<!\s)\*(?=[\s.,;:)!?]|$)/g, '$1<em>$2</em>');
    t = t.replace(/(^|[\s(])_(?!\s)(.+?)(?<!\s)_(?=[\s.,;:)!?]|$)/g, '$1<em>$2</em>');
    return t;
  }
  const PREVIEW_LIMIT = 250000;
  function renderMd(md) {
    let cut = false;
    if (md.length > PREVIEW_LIMIT) { md = md.slice(0, PREVIEW_LIMIT); cut = true; }
    const L = md.split('\n'); let h = '', i = 0, m;
    const block = /^(\s*#{1,6}\s|>|\s*\||\s*[-*+]\s|\s*\d+[.)]\s|---\s*$|\*\*\*\s*$|<!--|```|~~~)/;
    while (i < L.length) {
      const l = L[i];
      if (!l.trim()) { i++; continue; }
      if (/^\s*(```|~~~)/.test(l)) {
        const fence = l.trim().slice(0, 3), code = []; i++;
        while (i < L.length && !L[i].trim().startsWith(fence)) { code.push(L[i]); i++; }
        i++; h += `<pre>${esc(code.join('\n'))}</pre>`; continue;
      }
      if ((m = l.match(/^\s*<!--\s*(.+?)\s*-->\s*$/))) { h += `<div class="slide">${esc(m[1].replace(/^Slide number:\s*/i, 'Slide '))}</div>`; i++; continue; }
      if (/^\s*(---|\*\*\*|___)\s*$/.test(l)) { h += '<hr>'; i++; continue; }
      if ((m = l.match(/^\s*(#{1,6})\s+(.*)$/))) { const n = Math.min(m[1].length, 4); h += `<h${n}>${inline(m[2])}</h${n}>`; i++; continue; }
      if (l.startsWith('>')) { const q = []; while (i < L.length && L[i].startsWith('>')) { q.push(L[i].replace(/^>\s?/, '')); i++; } h += `<blockquote>${q.filter(x => x.trim()).map(inline).join('<br>')}</blockquote>`; continue; }
      if (/^\s*\|/.test(l)) {
        const rows = []; while (i < L.length && /^\s*\|/.test(L[i])) { rows.push(L[i].trim()); i++; }
        const cells = r => r.replace(/^\||\|$/g, '').split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, '|'));
        const body = rows.filter(r => !/^\|\s*:?-{2,}/.test(r)); const [hd, ...rs] = body;
        if (hd) h += `<div class="tbl"><table><thead><tr>${cells(hd).map(c => `<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>${rs.map(r => `<tr>${cells(r).map(c => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
        continue;
      }
      if (/^\s*[-*+]\s+/.test(l) || /^\s*\d+[.)]\s+/.test(l)) {
        const ordered = /^\s*\d+[.)]\s+/.test(l), tag = ordered ? 'ol' : 'ul', re = ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*+]\s+/;
        const li = [];
        while (i < L.length && re.test(L[i])) {
          const ind = Math.min(4, Math.floor(L[i].match(/^\s*/)[0].replace(/\t/g, '  ').length / 2));
          li.push(`<li${ind ? ` style="margin-left:${ind * 1.2}em"` : ''}>${inline(L[i].replace(re, ''))}</li>`); i++;
        }
        const first = ordered ? parseInt(l.match(/^\s*(\d+)/)[1], 10) : 1;
        h += `<${tag}${first > 1 ? ` start="${first}"` : ''}>${li.join('')}</${tag}>`; continue;
      }
      const p = []; while (i < L.length && L[i].trim() && (p.length === 0 || !block.test(L[i]))) { p.push(L[i]); i++; }
      h += `<p>${p.map(inline).join('<br>')}</p>`;
    }
    if (cut) h += `<blockquote class="cut">Pratinjau dipotong karena dokumen sangat panjang. Isi lengkap ada di file .md yang tersimpan.</blockquote>`;
    return h;
  }

  /* ---------- daftar dokumen ---------- */
  const badgeHTML = it => it.kind === 'yt' ? `<span class="badge b-yt" aria-hidden="true">${ic('play', 'fill')}</span>` : `<span class="badge b-${esc(it.kind)}" aria-hidden="true">${esc(it.badge || 'FILE')}</span>`;
  function statusHTML(it) {
    switch (it.status) {
      case 'wait': return `<span class="st wait">${ic('clock')}Menunggu</span>`;
      case 'work': return `<span class="st work"><span class="spin"></span>Memproses</span>`;
      case 'done': return `<span class="st ok">${ic('checkc')}${fmt(it.words)} kata</span>`;
      case 'warn': return `<span class="st warn">${ic('alert')}Perlu dicek</span>`;
      case 'error': return `<span class="st err">${ic('xc')}Gagal</span>`;
      default: return '<span></span>';
    }
  }
  const EXP_TIP = {
    aud: 'Eksperimental: rekaman dikirim ke layanan pengenal suara Google untuk diubah jadi teks.',
    yt: 'Eksperimental: bergantung pada layanan YouTube yang bisa berubah sewaktu-waktu.',
  };
  function metaHTML(it) {
    if (it.status === 'work' && it.sub) return `<span class="mt work">${esc(it.sub)}</span>`;
    if (it.status === 'warn') {
      const label = S.set.ocr_mode === 'off' ? 'Aktifkan baca scan offline' : 'Baca ulang dengan OCR offline';
      const fix = it.fix === 'ocr' && !S.busy && !S.rereading ? ` <button class="linkbtn" type="button" data-fix="${esc(it.id)}">${label}</button>` : '';
      return `<span class="mt warn">${esc(it.message)}${fix}</span>`;
    }
    if (it.status === 'error') return `<span class="mt err">${esc(it.message)}</span>`;
    let tag = '';
    const mode = S.set.ocr_mode;
    if (it.kind === 'pdf' && (it.scan || it.mixed)) {
      const what = it.scan ? 'Hasil scan' : 'Sebagian halaman hasil scan';
      const t = { off: `${what}, akan dilewati`, offline: `${what}, dibaca offline`, ai: `${what}, dibaca AI` }[mode];
      tag = `<span class="tag scan${mode === 'off' ? ' off' : ''}">${ic('scan')}${t}</span>`;
    } else if (it.kind === 'img') {
      const t = { off: 'Gambar, teks tidak dibaca', offline: 'Gambar, dibaca offline', ai: 'Gambar, dibaca AI' }[mode];
      tag = `<span class="tag scan${mode === 'off' ? ' off' : ''}">${ic('image')}${t}</span>`;
    }
    if (it.exp) tag += `<span class="tag exp" title="${esc(EXP_TIP[it.kind] || 'Eksperimental')}">Eksperimental</span>`;
    return `<span class="mt">${esc(it.meta)}${tag}</span>`;
  }
  function renderList() {
    const st = stateName();
    const click = st === 'done' ? ' click' : '';
    // daftar digambar ulang utuh; simpan dulu tombol yang sedang difokus supaya keyboard tidak kehilangan tempat
    const act = document.activeElement, actRow = act && act.closest ? act.closest('#files .row') : null;
    const actSel = actRow ? (act.classList.contains('grip') ? '.grip' : act.classList.contains('rm') ? '.rm' : '') : '';
    const actId = actRow ? actRow.dataset.id : '';
    $('#files').innerHTML = S.items.map(it => {
      const sel = st === 'done' && S.sel === it.id ? ' sel' : '';
      return `<li class="row${sel}${click}" data-id="${esc(it.id)}">` +
        `<button class="grip" type="button" title="Seret untuk mengatur urutan" aria-label="Pindahkan ${esc(it.display)}. Tekan panah atas atau bawah.">${ic('grip')}</button>${badgeHTML(it)}` +
        `<span class="ftxt"><span class="nm" title="${esc(it.source)}">${esc(it.display)}</span>${metaHTML(it)}</span>` +
        `${statusHTML(it)}<button class="rm" type="button" data-rm="${esc(it.id)}" aria-label="Hapus ${esc(it.display)} dari daftar" title="Hapus dari daftar">${ic('x')}</button></li>`;
    }).join('');
    if (actSel) { const el = $(`#files .row[data-id="${CSS.escape(actId)}"] ${actSel}`); if (el) el.focus(); }
  }
  function srcMeta() {
    if (!S.items.length) return 'Belum ada dokumen';
    const links = S.items.filter(i => i.is_link).length, files = S.items.length - links;
    const bytes = S.items.reduce((a, i) => a + (i.size || 0), 0);
    return [files ? `${fmt(files)} file` : '', links ? `${links} link` : '', bytes ? sizeText(bytes) : ''].filter(Boolean).join(' · ');
  }

  /* ---------- panel kanan ---------- */
  function pathLabel() {
    if (S.set.location === 'same') return 'Folder yang sama dengan file asli';
    const d = S.set.custom_dir || S.defaultDir;
    if (!S.set.custom_dir || d === S.defaultDir) return 'Dokumen<em>›</em>Urai App';
    return esc(lastParts(d, 3));
  }
  function renderSetup() {
    const n = S.items.length, mode = S.set.ocr_mode;
    $$('.opt[data-out]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.out === S.set.out_mode)));
    $$('.mode').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.ocr === mode)));
    $('#outSepSub').textContent = `${n ? fmt(n) : 'Beberapa'} file .md, nama sama dengan aslinya`;
    const cn = $('#cname');
    if (document.activeElement !== cn) cn.value = S.set.combined_name || 'Gabungan';
    const hint = $('#ocrHint');
    if (mode === 'off') hint.innerHTML = `${ic('off', 'warn')}<span class="txt">Gambar dan PDF hasil scan dilewati. Hanya teks yang bisa dipilih di dokumen yang diambil.</span>`;
    else if (mode === 'offline') {
      hint.innerHTML = S.tess.available
        ? `${ic('shield')}<span class="txt">Dibaca di komputer ini, tanpa internet. Bahasa: ${esc(langLabel())}. <button class="linkbtn" type="button" data-open="offline">Atur</button></span>`
        : `${ic('alert', 'warn')}<span class="txt">Mesin baca scan offline tidak ditemukan. Pasang ulang Urai App, atau pilih AI. <button class="linkbtn" type="button" data-open="offline">Atur</button></span>`;
    } else {
      const p = S.set.provider, has = S.keys[p];
      hint.innerHTML = has
        ? `${ic('spark')}<span class="txt">Lebih akurat dan bisa menjelaskan grafik. Gambar dikirim ke ${esc(provName(p))}. <button class="linkbtn" type="button" data-open="ai">Atur</button></span>`
        : `${ic('alert', 'warn')}<span class="txt">Mode AI butuh API key ${esc(provName(p))}. <button class="linkbtn" type="button" data-open="ai">Isi API key</button></span>`;
    }
    const go = $('#go');
    go.disabled = n === 0 || S.busy;
    $('#goText').textContent = n === 0 ? 'Tambahkan dokumen dulu' : isCombined() ? `Gabungkan ${fmt(n)} dokumen jadi 1 file` : `Ubah ${fmt(n)} dokumen ke Markdown`;
    $('#sameFolder').checked = S.set.location === 'same';
    $('#pathText').innerHTML = pathLabel();
    $('#pathText').title = S.set.location === 'same' ? '' : (S.set.custom_dir || S.defaultDir);
    $('#changePath').disabled = S.set.location === 'same';
  }
  function renderProgress() {
    const total = S.items.length || 1;
    const fin = S.items.filter(i => ['done', 'warn', 'error'].includes(i.status));
    const cur = S.items.find(i => i.status === 'work');
    const p = Math.min(100, Math.round(((fin.length + (cur ? 0.5 : 0)) / total) * 100));
    $('#pct').innerHTML = `${p}%<small>dokumen ${fmt(Math.min(fin.length + 1, total))} dari ${fmt(total)}</small>`;
    $('#pctBar').style.setProperty('--p', p + '%');
    $('#cur').innerHTML = cur
      ? `${badgeHTML(cur)}<div class="ftxt"><span class="nm">${esc(cur.display)}</span><span class="sub"><span class="spin"></span>${esc(cur.sub || 'Memproses…')}</span></div>`
      : `<span class="badge b-md">MD</span><div class="ftxt"><span class="nm">${S.cancelling ? 'Membatalkan' : 'Menyimpan hasil'}</span><span class="sub">${S.cancelling ? 'Menunggu halaman yang sedang dibaca' : 'Hampir selesai'}</span></div>`;
    $('#doneList').innerHTML = fin.length ? `<li style="display:block"><span class="lbl">Sudah selesai</span></li>` + fin.slice().reverse().map(i => {
      const k = i.status === 'warn' ? ['alert', 'w', 'perlu dicek'] : i.status === 'error' ? ['xc', 'e', 'gagal'] : ['checkc', '', fmt(i.words) + ' kata'];
      return `<li>${ic(k[0], k[1])}<span>${esc(i.display)}</span><span>${k[2]}</span></li>`;
    }).join('') : '';
    const c = $('#cancel');
    c.disabled = S.cancelling;
    c.lastChild.textContent = S.cancelling ? 'Membatalkan…' : 'Batalkan';
  }
  function folderLabel(dir) {
    if (!dir) return '';
    if (dir === S.defaultDir) return 'Dokumen › Urai App';
    return lastParts(dir, 2);
  }
  async function textOf(key) {
    if (!key) return '';
    if (S.texts[key] == null) S.texts[key] = (await safeCall('result_text', key)) || '';
    return S.texts[key];
  }
  function renderResult() {
    const d = S.done;
    if (!d) return;
    const ok = S.items.filter(i => i.status === 'done').length, warn = S.items.filter(i => i.status === 'warn').length, err = S.items.filter(i => i.status === 'error').length;
    $('#resMeta').textContent = [`${fmt(ok)} berhasil`, warn ? `${fmt(warn)} perlu dicek` : '', err ? `${fmt(err)} gagal` : ''].filter(Boolean).join(' · ');
    const total = S.items.reduce((a, i) => a + (i.words || 0), 0);
    if (isCombined()) {
      const name = d.combined_path ? fileOf(d.combined_path) : `${S.set.combined_name || 'Gabungan'}.md`;
      $('#outbox').innerHTML = `<span class="badge b-md">MD</span><div style="min-width:0"><div class="t" title="${esc(d.combined_path)}">${esc(name)}</div><div class="s">${fmt(d.combined_words || total)} kata · tersimpan di ${esc(folderLabel(d.out_dir))}</div></div>`;
      $('#openFileText').textContent = 'Buka file';
    } else {
      const saved = S.items.filter(i => i.output).length;
      $('#outbox').innerHTML = `<span class="badge b-md">MD</span><div style="min-width:0"><div class="t">${fmt(saved)} file .md tersimpan</div><div class="s">${fmt(total)} kata total · di ${esc(folderLabel(d.out_dir))}</div></div>`;
      $('#openFileText').textContent = 'Buka file ini';
    }
    $$('.tabs button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === S.tab)));
    const it = findItem(S.sel);
    if (isCombined()) $('#pvLabel').innerHTML = it ? `Bagian: ${esc(it.display)} <button class="linkbtn" type="button" id="showAll">Lihat semua</button>` : 'Seluruh file gabungan';
    else $('#pvLabel').textContent = it ? it.display : '';
    const isMap = S.tab === 'map';
    $('#pvBody').hidden = isMap;
    $('#mmPanel').hidden = !isMap;
    if (isMap) renderMap(); else renderPreview();
    const limit = 60000, big = total > limit, sm = $('#sizeMeter');
    sm.className = 'size' + (big ? ' big' : '');
    sm.innerHTML = `<span>Ukuran</span><div class="bar"><i style="--p:${Math.max(3, Math.min(100, total / limit * 100))}%"></i></div><span><b>${fmt(total)} kata</b> · ${big ? 'besar, pertimbangkan simpan terpisah' : 'nyaman diunggah ke asisten AI'}</span>`;
    $('#nudge').hidden = !(S.hasQris && (S.set.runs || 0) >= 5 && !S.set.supported);
  }
  async function renderPreview() {
    const key = currentKey(), item = findItem(key);
    const sig = `${key}|${S.tab}|${item ? item.status + item.words : ''}`;
    if (sig === S.pvShown && S.texts[key] != null) return;
    S.pvShown = sig;
    const md = await textOf(key);
    if (S.pvShown !== sig) return;
    const body = $('#pvBody');
    if (!md.trim()) {
      const msg = item && item.message ? item.message : 'Tidak ada teks yang bisa diambil.';
      body.innerHTML = `<div class="md"><blockquote>${esc(msg)}</blockquote></div>`;
    } else body.innerHTML = S.tab === 'view' ? `<div class="md">${renderMd(md)}</div>` : `<pre class="raw">${esc(md.length > PREVIEW_LIMIT ? md.slice(0, PREVIEW_LIMIT) + '\n\n… (pratinjau dipotong)' : md)}</pre>`;
    body.scrollTop = 0;
  }
  function ocrStatusLabel() {
    const m = S.set.ocr_mode;
    if (m === 'off') return 'Baca scan: mati';
    if (m === 'offline') return S.tess.available ? `Baca scan: offline (${langLabel()})` : 'Baca scan: offline tidak tersedia';
    return `Baca scan: AI (${provName(S.set.provider)})`;
  }
  function renderStatus() {
    const st = stateName(), n = S.items.length;
    const fin = S.items.filter(i => ['done', 'warn', 'error'].includes(i.status)).length;
    $('#sbLeft').textContent = {
      empty: 'Siap. Tambahkan dokumen untuk mulai.',
      ready: `${fmt(n)} dokumen siap diubah`,
      busy: S.cancelling ? 'Membatalkan…' : `Memproses dokumen ${fmt(Math.min(fin + 1, n))} dari ${fmt(n)}`,
      done: `Selesai pukul ${S.done && S.done.time || now().time}`,
    }[st];
    $('#sbMid').textContent = ocrStatusLabel();
  }
  let rafId = 0;
  function render() { if (!rafId) rafId = requestAnimationFrame(() => { rafId = 0; renderNow(); }); }
  function renderNow() {
    const st = stateName();
    win.dataset.state = st; win.dataset.out = S.set.out_mode || 'separate'; win.dataset.ocr = S.set.ocr_mode || 'offline';
    win.dataset.tess = S.tess.available ? '1' : '0';
    $('#srcMeta').textContent = srcMeta();
    renderList(); renderSetup(); renderStatus();
    if (st === 'busy') renderProgress();
    if (st === 'done') renderResult();
  }

  /* ---------- pesan singkat ---------- */
  let toastT;
  function toast(msg, ms = 2800) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), ms); }

  /* ---------- kabar dari Python ---------- */
  function upsert(item) { const k = S.items.findIndex(i => i.id === item.id); if (k >= 0) S.items[k] = item; }
  function onAdded(res, label) {
    if (!res) return;
    if (!res.ok) { toast(res.error || 'Tidak bisa menambahkan.'); return; }
    if (res.fresh) startFresh();
    S.items = res.items || S.items;
    if (res.cancelled) { render(); return; }
    const parts = [];
    if (res.added) parts.push(label ? `${label} · ${fmt(res.added)} dokumen ditambahkan` : `${fmt(res.added)} dokumen ditambahkan`);
    else if (!res.skipped) parts.push(label ? `${label}: tidak ada dokumen baru yang didukung` : 'Dokumen sudah ada di daftar');
    if (res.skipped) parts.push(`${fmt(res.skipped)} dilewati (format tidak didukung)`);
    if (parts.length) toast(parts.join('. '));
    render();
  }
  function startFresh() { S.done = null; S.sel = null; S.texts = {}; S.pvShown = ''; S.mm.cache = {}; shownMd = null; exitFull(); }
  function handle(e) {
    switch (e.type) {
      case 'items': S.items = e.items; break;
      case 'item': { const { type, ...it } = e; upsert(it); if (S.done) S.pvShown = ''; break; }
      case 'progress': S.progress = e; break;
      case 'dropped': onAdded(e); return;
      case 'finished': {
        S.busy = false; S.items = e.items || S.items; S.texts = {}; S.pvShown = '';
        const s = e.summary;
        S.set.runs = s.runs;
        if (s.cancelled) {
          S.cancelling = false; S.done = null;
          call('reset_results').then(r => { if (r && r.items) { S.items = r.items; render(); } });
          toast(`Dibatalkan. ${fmt(s.ok + s.warn)} dokumen yang sudah selesai tetap tersimpan.`, 3800);
          break;
        }
        S.cancelling = false;
        s.time = now().time;
        S.done = s;
        S.tab = 'view';
        S.sel = isCombined() ? null : ((S.items.find(i => i.status === 'done') || S.items[0] || {}).id || null);
        if (s.error === s.total) toast('Semua dokumen gagal diubah. Lihat keterangan di daftar.', 4000);
        else toast(isCombined() ? `Tersimpan: ${fileOf(s.combined_path) || 'file gabungan'}` : `${fmt(S.items.filter(i => i.output).length)} file .md tersimpan`);
        break;
      }
      case 'failed': S.busy = false; S.cancelling = false; S.done = null; S.items = e.items || S.items; toast(e.error || 'Proses gagal.', 4000); break;
      case 'reread_done': {
        const it = findItem(e.id);
        S.rereading = null;
        delete S.texts[e.id]; delete S.texts.ALL; S.pvShown = '';
        Object.keys(S.mm.cache).forEach(k => { if (k.startsWith(e.id + '|') || k.startsWith('ALL|')) delete S.mm.cache[k]; });
        if (typeof e.combined_words === 'number' && S.done) S.done.combined_words = e.combined_words;
        if (it && e.ok) { if (!isCombined()) S.sel = it.id; toast(`${it.display} dibaca ulang dengan OCR offline`); }
        else if (it) toast(it.message || 'Dokumen tetap tidak terbaca.', 3600);
        break;
      }
      case 'mm': onMapEvent(e); return;
      default: return;
    }
    render();
  }
  async function pollLoop() {
    try {
      const evs = await call('poll');
      (evs || []).forEach(e => { try { handle(e); } catch (err) { console.error('event', e && e.type, err); } });
    } catch (err) { console.warn('poll', err); }
    setTimeout(pollLoop, (S.busy || S.mm.busy || S.rereading) ? 150 : 400);
  }

  /* ---------- aksi utama ---------- */
  async function start() {
    if (S.busy || !S.items.length || stateName() !== 'ready') return;
    const res = await safeCall('start');
    if (!res) return;
    if (!res.ok) { toast(res.error); if (res.open) openSettings(res.open); return; }
    startFresh();
    S.busy = true; S.cancelling = false; S.progress = { done: 0, total: S.items.length, current: null };
    S.items.forEach(i => { i.status = 'wait'; i.sub = ''; });
    render();
  }
  const addFiles = async () => onAdded(await safeCall('pick_files'));
  const addFolder = async () => { const r = await safeCall('pick_folder'); onAdded(r, r && r.folder ? `Folder "${r.folder}"` : ''); };
  $('#addFile').addEventListener('click', addFiles);
  $('#dzPick').addEventListener('click', addFiles);
  $('#addFolder').addEventListener('click', addFolder);
  $('#dzFolder').addEventListener('click', addFolder);
  $('#tryDemo').addEventListener('click', async () => { const r = await safeCall('add_samples'); onAdded(r, 'File contoh'); });

  $('#linkForm').addEventListener('submit', async e => {
    e.preventDefault();
    const inp = $('#linkInput'), v = inp.value.trim();
    if (!v) return;
    const res = await safeCall('add_link', v);
    if (!res) return;
    if (!res.ok) { toast(res.error); return; }
    if (res.fresh) startFresh();
    S.items = res.items; inp.value = ''; render(); toast('Link ditambahkan ke daftar');
  });

  $('#files').addEventListener('click', async e => {
    const rm = e.target.closest('[data-rm]');
    if (rm) { const r = await safeCall('remove_item', rm.dataset.rm); if (r) { S.items = r.items; render(); } return; }
    const fix = e.target.closest('[data-fix]');
    if (fix) {
      saveSet({ ocr_mode: 'offline' });
      const r = await safeCall('reread', fix.dataset.fix);
      if (r && r.ok) { S.rereading = fix.dataset.fix; const it = findItem(fix.dataset.fix); if (it) { it.status = 'work'; it.sub = 'OCR offline · membaca ulang'; } }
      else if (r) toast(r.error);
      render(); return;
    }
    if (e.target.closest('.grip')) return;
    const row = e.target.closest('.row');
    if (row && stateName() === 'done') { S.sel = row.dataset.id; S.pvShown = ''; render(); }
  });

  $$('.opt[data-out]').forEach(b => b.addEventListener('click', () => {
    if (S.busy) return;
    saveSet({ out_mode: b.dataset.out });
    render();
  }));
  $$('.mode').forEach(b => b.addEventListener('click', () => {
    const m = b.dataset.ocr;
    if (m === 'ai' && !S.keys[S.set.provider]) { openSettings('ai'); return; }
    saveSet({ ocr_mode: m }); render();
  }));
  $('#ocrHint').addEventListener('click', e => { const b = e.target.closest('[data-open]'); if (b) openSettings(b.dataset.open); });
  $('#cname').addEventListener('input', e => debounce('cname', () => saveSet({ combined_name: e.target.value.trim() || 'Gabungan' }), 400));
  $('#sameFolder').addEventListener('change', e => { saveSet({ location: e.target.checked ? 'same' : 'custom' }); render(); });
  $('#changePath').addEventListener('click', async () => {
    const r = await safeCall('choose_output_dir');
    if (r && r.ok) { S.set = r.settings; render(); toast(`Hasil disimpan ke ${lastParts(r.path, 2)}`); }
  });
  $('#go').addEventListener('click', start);
  $('#cancel').addEventListener('click', () => { S.cancelling = true; call('cancel'); render(); });

  $$('.tabs button').forEach(b => b.addEventListener('click', () => { S.tab = b.dataset.tab; S.pvShown = ''; if (S.tab !== 'map') exitFull(); render(); }));
  $('#pvLabel').addEventListener('click', e => { if (e.target.id === 'showAll') { S.sel = null; S.pvShown = ''; render(); } });
  $('#openFile').addEventListener('click', async () => {
    const d = S.done; if (!d) return;
    let path = '';
    if (isCombined()) path = d.combined_path;
    else { const it = findItem(S.sel) || S.items.find(i => i.output); path = it && it.output; if (it && !it.output) { toast('Dokumen ini tidak menghasilkan file karena tidak ada teks yang terbaca.'); return; } }
    if (!path) { toast('Belum ada file yang tersimpan.'); return; }
    const r = await safeCall('open_output', path);
    if (r && !r.ok) toast(r.error);
  });
  $('#openFolder').addEventListener('click', async () => {
    const d = S.done; if (!d) return;
    const it = findItem(S.sel);
    const path = (it && it.output) || d.combined_path || d.out_dir;
    const r = await safeCall('open_folder', path || '');
    if (r && !r.ok) toast(r.error);
  });
  async function copyText(text, okMsg) {
    try { await navigator.clipboard.writeText(text); toast(okMsg); return; } catch (_) { /* coba lewat Python */ }
    if (await safeCall('copy_text', text)) { toast(okMsg); return; }
    toast('Teks tidak bisa disalin otomatis. Pilih teksnya lalu tekan Ctrl + C.');
  }
  $('#copyText').addEventListener('click', async () => {
    const md = await textOf(currentKey());
    if (!md) { toast('Tidak ada teks untuk disalin.'); return; }
    copyText(md, 'Teks Markdown disalin');
  });
  $('#again').addEventListener('click', async () => { const r = await safeCall('clear'); if (r && r.ok) { S.items = []; startFresh(); render(); } });
  $('#backSetup').addEventListener('click', async () => { const r = await safeCall('reset_results'); if (r && r.ok) { S.items = r.items; startFresh(); render(); } });
  $('#toMap').addEventListener('click', () => { S.tab = 'map'; render(); });

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && stateName() === 'ready' && !openDialog()) { e.preventDefault(); start(); }
    if (e.key === 'Escape') { if (openDialog()) closeDialogs(); else if (!$('#mmMenu').hidden) $('#mmMenu').hidden = true; else if (!$('#mmStyle').hidden) closeStyle(); else exitFull(); }
  });

  /* ---------- atur urutan: seret pegangan, atau panah atas/bawah ---------- */
  let dragRow = null;
  const filesEl = $('#files');
  filesEl.addEventListener('pointerdown', e => { const g = e.target.closest('.grip'); if (g && stateName() === 'ready') g.closest('.row').draggable = true; });
  filesEl.addEventListener('dragstart', e => {
    const row = e.target.closest('.row');
    if (!row || !row.draggable) return;
    dragRow = row; e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/x-urai-row', row.dataset.id);
    requestAnimationFrame(() => row.classList.add('dragging'));
  });
  filesEl.addEventListener('dragover', e => {
    if (!dragRow) return;
    e.preventDefault();
    const row = e.target.closest('.row');
    if (!row || row === dragRow) return;
    const r = row.getBoundingClientRect();
    filesEl.insertBefore(dragRow, e.clientY > r.top + r.height / 2 ? row.nextSibling : row);
  });
  filesEl.addEventListener('dragend', async () => {
    if (!dragRow) return;
    dragRow.classList.remove('dragging'); dragRow.draggable = false; dragRow = null;
    await saveOrder($$('.row', filesEl).map(r => r.dataset.id));
  });
  filesEl.addEventListener('keydown', async e => {
    const g = e.target.closest('.grip');
    if (!g || stateName() !== 'ready' || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
    e.preventDefault();
    const ids = S.items.map(i => i.id), id = g.closest('.row').dataset.id, k = ids.indexOf(id), j = k + (e.key === 'ArrowUp' ? -1 : 1);
    if (j < 0 || j >= ids.length) return;
    [ids[k], ids[j]] = [ids[j], ids[k]];
    await saveOrder(ids);
  });
  async function saveOrder(ids) {
    const byId = Object.fromEntries(S.items.map(i => [i.id, i]));
    S.items = ids.map(i => byId[i]).filter(Boolean);
    renderNow();  // langsung terlihat; urutan di Python menyusul
    const r = await safeCall('reorder', ids);
    if (r && r.items) S.items = r.items;
    render();
  }

  /* ---------- jendela tidak pernah membuka tautan di dalam dirinya ---------- */
  ['click', 'auxclick'].forEach(t => document.addEventListener(t, e => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (a) { e.preventDefault(); e.stopPropagation(); }
  }, true));

  /* ---------- tarik file dari File Explorer, atau link dari browser ---------- */
  let dragDepth = 0;
  const hasFiles = e => e.dataTransfer && [...(e.dataTransfer.types || [])].includes('Files');
  const droppedLink = e => {
    const dt = e.dataTransfer; if (!dt) return '';
    const raw = dt.getData('text/uri-list') || dt.getData('text/plain') || '';
    return (raw.split(/\r?\n/).find(l => /^https?:\/\//i.test(l.trim())) || '').trim();
  };
  document.addEventListener('dragenter', e => {
    if (!hasFiles(e)) return;
    e.preventDefault(); dragDepth++;
    const n = e.dataTransfer.items ? e.dataTransfer.items.length : 0;
    $('#dropTitle').textContent = S.busy ? 'Tunggu proses selesai dulu' : 'Lepaskan untuk menambahkan';
    $('#dropSub').textContent = S.busy ? 'Dokumen bisa ditambahkan setelah proses selesai.' : (n ? `${fmt(n)} item dari File Explorer` : 'File atau folder dari File Explorer') + (S.done ? '. Daftar sebelumnya diganti.' : '');
    win.dataset.drag = '1';
  });
  // dragover dan drop selalu dicegah: tanpa ini, link atau file yang dilepas membuat jendela membuka halaman itu
  document.addEventListener('dragover', e => { e.preventDefault(); if (hasFiles(e)) e.dataTransfer.dropEffect = S.busy ? 'none' : 'copy'; });
  document.addEventListener('dragleave', e => { if (!hasFiles(e)) return; dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) win.dataset.drag = '0'; });
  document.addEventListener('drop', async e => {
    e.preventDefault();
    if (dragRow) return;
    if (!hasFiles(e)) {
      const url = droppedLink(e);
      if (!url || S.busy) return;
      const res = await safeCall('add_link', url);
      if (res && res.ok) { if (res.fresh) startFresh(); S.items = res.items; render(); toast('Link ditambahkan ke daftar'); }
      else if (res) toast(res.error);
      return;
    }
    dragDepth = 0; win.dataset.drag = '0';
    if (DEV) toast('Mode pengembangan: tarik-lepas hanya bekerja di aplikasi. Pakai tombol File.');
  });

  /* ---------- dialog ---------- */
  const openDialog = () => $$('.scrim').find(s => !s.hidden);
  function closeDialogs() { $$('.scrim').forEach(s => { s.hidden = true; }); }
  function openDlg(id) {
    closeDialogs(); $('#mmMenu').hidden = true;
    const s = $('#' + id); s.hidden = false;
    const f = s.querySelector('[data-close]'); if (f) f.focus();
  }
  win.addEventListener('click', e => { if (e.target.closest('[data-close]')) closeDialogs(); });
  $$('.scrim').forEach(s => s.addEventListener('mousedown', e => { if (e.target === s) closeDialogs(); }));
  document.addEventListener('click', e => { const b = e.target.closest('[data-link]'); if (b) call('open_link', b.dataset.link); });

  // Pengaturan baca scan
  function setPane(p) {
    S.pane = p;
    $$('#dTabs button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.pane === p)));
    $('#pane-offline').hidden = p !== 'offline'; $('#pane-ai').hidden = p !== 'ai';
    $('#dSave').textContent = p === S.set.ocr_mode ? 'Simpan' : 'Simpan & pakai mode ini';
    setMsg('#testMsg', '');
  }
  function setMsg(sel, text, kind = '') { const el = $(sel); el.textContent = text; el.className = 'fmsg' + (kind ? ' ' + kind : ''); }
  function fillProvider() {
    const p = S.dlg.provider, has = S.keys[p];
    $$('#prov [data-p]').forEach(b => {
      b.setAttribute('aria-pressed', String(b.dataset.p === p));
      const dot = b.querySelector('.kdot');
      if (S.keys[b.dataset.p] && !dot) b.insertAdjacentHTML('beforeend', '<span class="kdot" title="API key tersimpan"></span>');
      if (!S.keys[b.dataset.p] && dot) dot.remove();
    });
    const key = $('#apiKey');
    key.value = S.dlg.typed[p] || '';
    key.placeholder = has ? 'Tersimpan di komputer ini. Isi lagi untuk mengganti.' : 'Tempel API key di sini';
    const link = (S.providers[p] || {}).has_link;
    $('#keyHint').innerHTML = (link ? `Belum punya? <button class="linkbtn" type="button" data-link="key_${esc(p)}">Buka halaman pembuatan API key</button>` : 'Isi API key dari server pilihan Anda.') +
      (has ? ` · <button class="linkbtn" type="button" id="forgetKey">Hapus API key tersimpan</button>` : '');
    $('#provName').textContent = provName(p);
    $('#modelName').value = S.dlg.models[p] != null ? S.dlg.models[p] : (S.models[p] || '');
    $('#modelName').placeholder = (S.providers[p] || {}).model || 'nama model';
    $('#baseUrl').value = S.dlg.urls[p] != null ? S.dlg.urls[p] : (S.baseUrls[p] || '');
    if (p === 'other') $('#advBox').open = true;
    setMsg('#testMsg', '');
  }
  function openSettings(pane) {
    S.dlg = { provider: S.set.provider || 'gemini', typed: {}, models: {}, urls: {} };
    const names = S.tess.names || {}, have = S.tess.langs || [];
    $('#langChips').innerHTML = Object.keys(names).map(l => {
      const dis = S.tess.available && !have.includes(l);
      return `<label class="chk" title="${dis ? 'Bahasa ini belum terpasang' : ''}"><input type="checkbox" value="${esc(l)}"${(S.set.langs || []).includes(l) && !dis ? ' checked' : ''}${dis ? ' disabled' : ''}>${esc(names[l])}</label>`;
    }).join('');
    $$('#qSeg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === S.set.quality)));
    $('#ocrEmbedded').checked = !!S.set.embedded;
    $('#tessMissing').hidden = !!S.tess.available;
    fillProvider();
    setPane(pane || (S.set.ocr_mode === 'ai' ? 'ai' : 'offline'));
    openDlg('dlgSettings');
  }
  $('#btnSettings').addEventListener('click', () => openSettings());
  $('#dTabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b) setPane(b.dataset.pane); });
  $('#qSeg').addEventListener('click', e => { const b = e.target.closest('button'); if (b) $$('#qSeg button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); });
  $('#prov').addEventListener('click', e => {
    const b = e.target.closest('[data-p]'); if (!b) return;
    const p = S.dlg.provider;
    S.dlg.typed[p] = $('#apiKey').value; S.dlg.models[p] = $('#modelName').value; S.dlg.urls[p] = $('#baseUrl').value;
    S.dlg.provider = b.dataset.p; fillProvider();
  });
  $('#keyEye').addEventListener('click', () => { const k = $('#apiKey'); k.type = k.type === 'password' ? 'text' : 'password'; });
  $('#keyHint').addEventListener('click', async e => {
    if (e.target.id !== 'forgetKey') return;
    const r = await safeCall('forget_key', S.dlg.provider);
    if (r) { S.keys = r.keys; fillProvider(); setMsg('#testMsg', 'API key dihapus dari komputer ini', 'ok'); render(); }
  });
  $('#testConn').addEventListener('click', async () => {
    const p = S.dlg.provider;
    setMsg('#testMsg', 'Menghubungi…', 'busy');
    $('#testConn').disabled = true;
    const r = await safeCall('test_ai', p, $('#apiKey').value.trim(), $('#modelName').value.trim(), $('#baseUrl').value.trim());
    $('#testConn').disabled = false;
    if (r) setMsg('#testMsg', r.message, r.ok ? 'ok' : 'err'); else setMsg('#testMsg', '');
  });
  $('#dSave').addEventListener('click', async () => {
    const langs = $$('#langChips input:checked').map(i => i.value);
    const quality = ($('#qSeg [aria-pressed="true"]') || {}).dataset?.v || 'fast';
    const patch = { quality, embedded: $('#ocrEmbedded').checked, ocr_mode: S.pane };
    if (langs.length) patch.langs = langs;
    else if (S.pane === 'offline') { setMsg('#testMsg', 'Pilih minimal satu bahasa.', 'err'); return; }
    // Bagian AI selalu disimpan bila diisi, supaya API key untuk Rangkuman AI bisa disimpan dari tab mana pun.
    const p = S.dlg.provider, key = $('#apiKey').value.trim(), model = $('#modelName').value.trim(), url = $('#baseUrl').value.trim();
    if (S.pane === 'ai') {
      if (!key && !S.keys[p]) { setMsg('#testMsg', 'Isi API key dulu.', 'err'); $('#apiKey').focus(); return; }
      if (p === 'other' && !url) { setMsg('#testMsg', 'Isi alamat server di bagian Lanjutan.', 'err'); $('#advBox').open = true; return; }
      if (p === 'other' && !model) { setMsg('#testMsg', 'Isi nama model di bagian Lanjutan.', 'err'); $('#advBox').open = true; return; }
    }
    if (S.pane === 'ai' || key || p !== S.set.provider) {
      const r = await safeCall('set_ai', p, key, model, url);
      if (!r || !r.ok) { setMsg('#testMsg', (r && r.error) || 'Gagal menyimpan.', 'err'); return; }
      S.keys = r.keys; S.models = r.models; S.baseUrls = r.base_urls; S.set = r.settings;
    }
    saveSet(patch);
    closeDialogs(); render();
    toast(S.pane === 'ai' ? `Mode AI aktif (${provName(p)})` : 'Mode offline aktif');
  });

  // Dukung
  (function buildQR() {
    const N = 25; let seed = 20261031, h = '';
    const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
    const finder = (r, c, R, C) => { const y = r - R, x = c - C; if (y < 0 || x < 0 || y > 6 || x > 6) return null; return y === 0 || y === 6 || x === 0 || x === 6 || (y >= 2 && y <= 4 && x >= 2 && x <= 4); };
    for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
      let on = finder(r, c, 0, 0); if (on === null) on = finder(r, c, 0, N - 7); if (on === null) on = finder(r, c, N - 7, 0);
      const sepz = (r <= 7 && c <= 7) || (r <= 7 && c >= N - 8) || (r >= N - 8 && c <= 7);
      if (on === null) on = sepz ? false : rnd() < 0.46;
      h += on ? '<i class="on"></i>' : '<i></i>';
    }
    $('#qrGrid').innerHTML = h;
  })();
  function openSupport() {
    $('#qrImg').hidden = !S.hasQris; $('#qrPlaceholder').hidden = S.hasQris;
    if (S.hasQris && !$('#qrImg').src) $('#qrImg').src = 'img/qris.png';
    $('#supText').textContent = S.hasQris
      ? 'Kalau Urai App membantu pekerjaan Anda, scan QRIS ini dari aplikasi bank atau dompet digital apa pun. Nominal bebas.'
      : 'QRIS resmi sedang disiapkan dan akan dipasang di versi berikutnya. Terima kasih sudah berniat mendukung.';
    $('#supDone').hidden = !S.hasQris;
    openDlg('dlgSupport');
  }
  $('#btnSupport').addEventListener('click', openSupport);
  $('#nudgeSupport').addEventListener('click', openSupport);
  $('#supDone').addEventListener('click', () => { closeDialogs(); saveSet({ supported: true }); $('#nudge').hidden = true; toast('Terima kasih! Ajakan dukungan tidak akan muncul lagi.'); });

  // Tentang
  $('#btnAbout').addEventListener('click', () => { setMsg('#updMsg', ''); $('#getUpd').hidden = true; openDlg('dlgAbout'); });
  $('#copyMail').addEventListener('click', () => copyText(S.app.email, 'Alamat email disalin'));
  $('#openRepo').addEventListener('click', () => call('open_link', 'repo'));
  $('#chkUpd').addEventListener('click', async () => {
    setMsg('#updMsg', 'Memeriksa…', 'busy');
    const r = await safeCall('check_update');
    if (!r) { setMsg('#updMsg', ''); return; }
    setMsg('#updMsg', r.message, r.ok ? 'ok' : 'err');
    $('#getUpd').hidden = !r.newer;
  });
  $('#getUpd').addEventListener('click', () => call('open_link', 'releases'));
  $('#openLic').addEventListener('click', async () => { const r = await safeCall('open_notices'); if (r && !r.ok) toast(r.error); });

  // Panduan
  $('#btnHelp').addEventListener('click', () => openDlg('dlgHelp'));

  /* ---------- rangkuman + mind map ---------- */
  const KIND_LABEL = { umum: 'Umum', notulen: 'Notulen', laporan: 'Laporan' };
  const KIND_HINT = { umum: 'Poin utama dari isi dokumen.', notulen: 'Masalah, keputusan, dan tindak lanjut.', laporan: 'Temuan, aktor, dan rekomendasi.' };
  const mmKey = currentKey;
  const mmCacheKey = () => `${mmKey()}|${S.mm.src}|${S.mm.src === 'ai' ? S.mm.kind : '-'}`;
  const mmTitle = () => { const k = mmKey(); if (k === 'ALL') return S.set.combined_name || 'Gabungan'; const it = findItem(k); return it ? baseName(it.display) : 'Mind map'; };

  let MM = null, shownMd = null, TR = null;
  const transformer = () => TR || (TR = new window.markmap.Transformer(window.markmap.builtInPlugins.filter(p => !/^(hljs|katex|npmUrl)$/.test(p.name))));
  /* markmap mengukur svg; jangan fit/render saat tersembunyi (ukuran nol membuat transform NaN) */
  const mmVisible = () => { const r = $('#mmSvg').getBoundingClientRect(); return r.width > 20 && r.height > 20; };
  const mmFit = () => { if (MM && mmVisible()) MM.fit(); };
  const fitSoon = () => setTimeout(mmFit, 410);
  const MM_OPTS = { duration: 350, spacingVertical: 8, paddingX: 10, autoFit: false };
  // HTML mentah dinetralkan, dan tautan dijadikan teks biasa: jendela aplikasi tidak boleh berpindah ke situs lain
  const safeMd = md => md.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  function renderMap() {
    const key = mmKey(), it = findItem(key), ai = S.mm.src === 'ai';
    $('#mmScope').textContent = key === 'ALL' ? `Cakupan: seluruh file gabungan, ${fmt(S.items.length)} dokumen` : `Cakupan: ${it ? it.display : '-'}`;
    $$('#mmSetup .opt').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.src === S.mm.src)));
    $$('#mmKind button').forEach(b => { b.setAttribute('aria-pressed', String(b.dataset.k === S.mm.kind)); b.disabled = !ai; });
    $('#mmKindGrp').classList.toggle('dim', !ai);
    $('#mmKindHint').textContent = ai ? KIND_HINT[S.mm.kind] : 'Hanya berlaku untuk Rangkuman AI.';
    const words = key === 'ALL' ? S.items.reduce((a, i) => a + (i.words || 0), 0) : (it ? it.words : 0);
    const note = $('#mmNote'), p = S.set.provider;
    if (ai && !S.keys[p]) { note.className = 'note warn'; note.innerHTML = `${ic('alert')}<span>Rangkuman AI butuh API key ${esc(provName(p))}. <button class="linkbtn" type="button" id="mmSetKey">Isi API key</button>, atau pakai Struktur dokumen yang gratis.</span>`; }
    else if (ai) { note.className = 'note warn'; note.innerHTML = `${ic('alert')}<span>Seluruh teks, sekitar <b>${fmt(words)} kata</b>, akan dikirim ke <b>${esc(provName(p))}</b>. Untuk data responden atau dokumen rahasia, pakai Struktur dokumen.</span>`; }
    else { note.className = 'note ok'; note.innerHTML = `${ic('shield')}<span>Diproses di komputer ini tanpa internet. Hasil terbaik untuk dokumen yang punya judul dan subjudul, seperti Word dan PowerPoint.</span>`; }
    $('#mmGoText').textContent = ai ? 'Buat rangkuman AI' : 'Buat mind map';
    $('#mmGo').disabled = !words && key !== 'ALL' && !(it && it.status === 'done');
    const ck = mmCacheKey(), md = S.mm.cache[ck], busy = S.mm.busy && S.mm.busyKey === ck;
    $('#mmSetup').hidden = !!md || busy;
    $('#mmBusy').hidden = !busy;
    $('#mmBusyText').textContent = S.mm.busyText || 'Meringkas…';
    $('#mmReady').hidden = !md || busy;
    if (md && !busy) requestAnimationFrame(() => showMap(md));
  }
  function showMap(md) {
    $('#mmSrcTag').innerHTML = S.mm.src === 'ai' ? `${ic('spark')}Rangkuman AI · ${KIND_LABEL[S.mm.kind]}` : `${ic('grip')}Struktur dokumen`;
    $('#mmWarn').hidden = S.mm.src !== 'ai';
    $('#mmPlace').hidden = S.mm.src === 'ai';
    $$('#mmView button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === S.mm.view)));
    const asText = S.mm.view === 'text';
    $('#mmText').innerHTML = renderMd(md);
    $('#mmText').hidden = !asText;
    $('#mmSvg').style.visibility = asText ? 'hidden' : '';
    if (!window.markmap || !window.markmap.Markmap) { $('#mmText').hidden = false; return; }
    if (!mmVisible()) return;
    if (md === shownMd && MM) { mmFit(); return; }
    shownMd = md;
    const { root } = transformer().transform(safeMd(md));
    if (!MM) { MM = window.markmap.Markmap.create($('#mmSvg'), mmOptions(), root); setTimeout(mmFit, 60); }
    else { MM.setOptions(mmOptions()); MM.setData(root).then(fitSoon); }
    syncStyleUI();
  }
  async function genMap() {
    const key = mmKey(), ck = mmCacheKey();
    if (!key) return;
    S.mm.busy = true; S.mm.busyKey = ck; S.mm.busyText = S.mm.src === 'ai' ? 'Membaca isi dokumen…' : 'Membaca judul dan daftar…';
    saveSet({ mm_src: S.mm.src, mm_kind: S.mm.kind });
    renderMap();
    const r = await safeCall('summarize', key, S.mm.src, S.mm.kind);
    if (!r || !r.ok) {
      S.mm.busy = false; renderMap();
      if (r) { toast(r.error, 3800); if (r.open) openSettings(r.open); }
    }
  }
  function onMapEvent(e) {
    if (e.state === 'progress') { S.mm.busyText = e.text; if (!$('#mmBusy').hidden) $('#mmBusyText').textContent = e.text; return; }
    if (e.state === 'done') {
      const ck = `${e.key}|${e.src}|${e.src === 'ai' ? e.kind : '-'}`;
      S.mm.cache[ck] = e.md;
      if (S.mm.busyKey === ck) S.mm.busy = false;
    } else if (e.state === 'error') {
      S.mm.busy = false;
      toast(e.error || 'Rangkuman gagal dibuat.', 4200);
    }
    if (S.done && S.tab === 'map') renderMap();
  }
  function exitFull() {
    if (!win.classList.contains('mmfull')) return;
    closeStyle(true);
    win.classList.remove('mmfull'); $('#mmFull').textContent = 'Layar penuh';
    requestAnimationFrame(mmFit);
  }
  $$('#mmSetup .opt').forEach(b => b.addEventListener('click', () => { S.mm.src = b.dataset.src; renderMap(); }));
  $('#mmKind').addEventListener('click', e => { const b = e.target.closest('button'); if (b && !b.disabled) { S.mm.kind = b.dataset.k; renderMap(); } });
  $('#mmNote').addEventListener('click', e => { if (e.target.id === 'mmSetKey') openSettings('ai'); });
  $('#mmGo').addEventListener('click', genMap);
  $('#mmStop').addEventListener('click', () => { call('cancel_summary'); S.mm.busy = false; renderMap(); });
  $('#mmRedo').addEventListener('click', () => {
    call('forget_summary', mmKey(), S.mm.src, S.mm.kind);
    delete S.mm.cache[mmCacheKey()]; shownMd = null; exitFull(); renderMap();
  });
  $('#mmView').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; S.mm.view = b.dataset.v; const md = S.mm.cache[mmCacheKey()]; if (md) showMap(md); });
  $('#mmIn').addEventListener('click', () => { if (MM && mmVisible()) MM.rescale(1.25); });
  $('#mmOut').addEventListener('click', () => { if (MM && mmVisible()) MM.rescale(0.8); });
  $('#mmFit').addEventListener('click', mmFit);
  $('#mmFold').addEventListener('click', () => { const st = S.mm.style; st.expand = st.expand === -1 ? 2 : -1; applyStyle(true); });
  $('#mmFull').addEventListener('click', () => {
    if (win.classList.contains('mmfull')) { exitFull(); return; }
    autoFull = false;
    win.classList.add('mmfull'); $('#mmFull').textContent = 'Kecilkan';
    requestAnimationFrame(mmFit);
  });
  $('#mmSave').addEventListener('click', e => { e.stopPropagation(); $('#mmMenu').hidden = !$('#mmMenu').hidden; });
  document.addEventListener('click', e => { if (!e.target.closest('#mmMenu, #mmSave')) $('#mmMenu').hidden = true; });
  $('#mmMenu').addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    $('#mmMenu').hidden = true;
    const f = b.dataset.f, md = S.mm.cache[mmCacheKey()];
    if (!md) return;
    if (f === 'pdf') { openPdf(); return; }
    const payload = { md, title: mmTitle(), style: S.mm.style, ai: S.mm.src === 'ai' };
    if (f === 'png') {
      toast('Menyiapkan gambar…');
      try { payload.png = await mmPng(4000); } catch (err) { console.error(err); toast('Gambar mind map tidak bisa dibuat. Coba simpan sebagai HTML atau PDF.'); return; }
    }
    const r = await safeCall('export_map', f, payload);
    if (r && r.ok) toast(`Tersimpan: ${r.name}`); else if (r && !r.cancelled) toast(r.error || 'Gagal menyimpan.');
  });

  /* ---------- gaya mind map: warna dan lebar per sub ---------- */
  const PALETTES = {
    pelangi: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
    urai: ['#2e5be6', '#0b7f74', '#d9480f', '#7b4fd6', '#c2255c', '#1d6f42', '#b7791f', '#0e7490'],
    lembut: ['#6c8ef5', '#4fb3a9', '#f08c5a', '#a98be8', '#e07aa5', '#7fb069', '#e2b45a', '#5ab0d8'],
    mono: ['#64748b'],
  };
  const LV_LABEL = ['Judul utama', 'Sub 1', 'Sub 2', 'Sub 3', 'Sub 4 dst.'];
  const levelsFrom = t => { const p = PALETTES[t]; return [0, 1, 2, 3, 4].map(i => p[i % p.length]); };
  const defStyle = () => ({ theme: 'pelangi', mode: 'branch', freeze: 0, levels: levelsFrom('pelangi'), widths: [2.5, 1.75, 1.5, 1.25, 1], maxWidth: 260, spacingH: 70, expand: -1 });
  function loadStyle(saved) {
    const d = defStyle();
    if (!saved || typeof saved !== 'object') return d;
    const st = { ...d };
    if (PALETTES[saved.theme]) st.theme = saved.theme;
    if (['branch', 'level'].includes(saved.mode)) st.mode = saved.mode;
    if ([0, 1, 2, 3].includes(saved.freeze)) st.freeze = saved.freeze;
    if (Array.isArray(saved.levels) && saved.levels.length === 5 && saved.levels.every(c => /^#[0-9a-f]{6}$/i.test(c))) st.levels = saved.levels;
    if (Array.isArray(saved.widths) && saved.widths.length === 5 && saved.widths.every(w => w > 0 && w <= 12)) st.widths = saved.widths;
    if (saved.maxWidth >= 80 && saved.maxWidth <= 800) st.maxWidth = saved.maxWidth;
    if (saved.spacingH >= 10 && saved.spacingH <= 300) st.spacingH = saved.spacingH;
    if ([-1, 2, 3, 4].includes(saved.expand)) st.expand = saved.expand;
    return st;
  }
  /* kedalaman markmap: judul utama = 1, sub 1 = 2, dst. path = id cabang dari akar, dipisah titik */
  const lvIdx = n => Math.min(Math.max(n.state.depth - 1, 0), 4);
  function mmOptions() {
    const st = S.mm.style;
    let color;
    if (st.mode === 'level') color = n => st.levels[lvIdx(n)];
    else {
      const sc = window.d3.scaleOrdinal(PALETTES[st.theme]);
      color = n => sc(st.freeze ? n.state.path.split('.').slice(0, st.freeze + 1).join('.') : n.state.path);
    }
    return { ...MM_OPTS, color, lineWidth: n => st.widths[lvIdx(n)], maxWidth: st.maxWidth, spacingHorizontal: st.spacingH, initialExpandLevel: st.expand };
  }
  function syncStyleUI() {
    const st = S.mm.style;
    const press = (sel, v) => $$(sel + ' button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === String(v))));
    press('#stTheme', st.theme); press('#stMode', st.mode); press('#stFreeze', st.freeze); press('#stExpand', st.expand);
    $('#stFreezeF').classList.toggle('dim', st.mode !== 'branch');
    st.levels.forEach((c, i) => { $('#stC' + i).value = c; });
    st.widths.forEach((w, i) => { $('#stW' + i).value = w; $('#stWv' + i).textContent = String(w).replace('.', ',') + ' px'; });
    $('#stMaxW').value = st.maxWidth; $('#stMaxWv').textContent = st.maxWidth + ' px';
    $('#stGap').value = st.spacingH; $('#stGapv').textContent = st.spacingH + ' px';
    $('#mmFold').textContent = st.expand === -1 ? 'Lipat' : 'Buka';
  }
  let styleT;
  function applyStyle(immediate) {
    syncStyleUI();
    debounce('style', () => saveSet({ mm_style: S.mm.style }), 700);
    clearTimeout(styleT);
    styleT = setTimeout(() => {
      if (!MM || !shownMd || !mmVisible()) return;
      MM.setOptions(mmOptions());
      MM.setData(transformer().transform(safeMd(shownMd)).root).then(fitSoon);
    }, immediate ? 0 : 140);
  }
  let autoFull = false;  // layar penuh dibuka otomatis oleh panel gaya; ditutup lagi bersama panelnya
  function openStyle() {
    if (!MM) return;
    if (!win.classList.contains('mmfull')) { win.classList.add('mmfull'); $('#mmFull').textContent = 'Kecilkan'; autoFull = true; }
    $('#mmStyle').hidden = false; $('.mmstage').classList.add('styling');
    syncStyleUI(); requestAnimationFrame(mmFit);
  }
  function closeStyle(quiet) {
    if ($('#mmStyle').hidden) return;
    $('#mmStyle').hidden = true; $('.mmstage').classList.remove('styling');
    if (autoFull && !quiet) { autoFull = false; exitFull(); return; }
    autoFull = false;
    if (!quiet) requestAnimationFrame(mmFit);
  }
  $('#stLevels').innerHTML = LV_LABEL.map((l, i) => `<tr><td>${l}</td><td><input type="color" id="stC${i}" aria-label="Warna ${l}"></td><td><input type="range" id="stW${i}" min="0.5" max="8" step="0.25" aria-label="Tebal garis ${l}"></td><td class="val" id="stWv${i}"></td></tr>`).join('');
  const segPick = (id, fn) => $(id).addEventListener('click', e => { const b = e.target.closest('button'); if (b) { fn(b.dataset.v); applyStyle(true); } });
  segPick('#stTheme', v => { S.mm.style.theme = v; S.mm.style.levels = levelsFrom(v); });
  segPick('#stMode', v => { S.mm.style.mode = v; });
  segPick('#stFreeze', v => { S.mm.style.freeze = Number(v); S.mm.style.mode = 'branch'; });
  segPick('#stExpand', v => { S.mm.style.expand = Number(v); });
  $('#stLevels').addEventListener('input', e => {
    const t = e.target, i = Number(t.id.slice(3));
    if (t.type === 'color') { S.mm.style.levels[i] = t.value; S.mm.style.mode = 'level'; }
    else S.mm.style.widths[i] = Number(t.value);
    applyStyle();
  });
  $('#stMaxW').addEventListener('input', e => { S.mm.style.maxWidth = Number(e.target.value); applyStyle(); });
  $('#stGap').addEventListener('input', e => { S.mm.style.spacingH = Number(e.target.value); applyStyle(); });
  $('#stReset').addEventListener('click', () => { S.mm.style = defStyle(); applyStyle(true); });
  $('#mmStyleBtn').addEventListener('click', () => { if ($('#mmStyle').hidden) openStyle(); else closeStyle(); });
  $('#mmStyleClose').addEventListener('click', () => closeStyle());

  /* ---------- gambar mind map (untuk PNG dan PDF) ---------- */
  let fontCssP = null;
  function fontCss() {
    if (fontCssP) return fontCssP;
    const load = (w) => fetch(`fonts/plus-jakarta-sans-latin-${w}-normal.woff2`).then(r => r.blob()).then(b => new Promise(res => { const fr = new FileReader(); fr.onload = () => res(`@font-face{font-family:"Plus Jakarta Sans";font-weight:${w};src:url(${fr.result}) format("woff2")}`); fr.readAsDataURL(b); }));
    fontCssP = Promise.all([load(500), load(700)]).then(a => a.join('')).catch(() => '');
    return fontCssP;
  }
  /* salinan mind map yang sedang tampil sebagai SVG mandiri, dengan warna kertas putih */
  async function mmSnapshotSvg() {
    const svg = $('#mmSvg'), g = svg && svg.querySelector('g');
    if (!MM || !g) return '';
    const bb = g.getBBox(), pad = 24;
    if (!bb.width || !bb.height) return '';
    const c = svg.cloneNode(true);
    c.querySelector('g').removeAttribute('transform');
    c.removeAttribute('id'); c.removeAttribute('style');
    c.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    c.setAttribute('viewBox', `${bb.x - pad} ${bb.y - pad} ${bb.width + pad * 2} ${bb.height + pad * 2}`);
    c.setAttribute('width', Math.round(bb.width + pad * 2));
    c.setAttribute('height', Math.round(bb.height + pad * 2));
    const font = '"Plus Jakarta Sans", "Segoe UI", sans-serif';
    [['--markmap-text-color', '#1f2937'], ['--markmap-circle-open-bg', '#ffffff'], ['--markmap-highlight-bg', '#e8eeff'], ['--markmap-font', `500 13px/1.45 ${font}`],
      ['--markmap-code-bg', '#f1f5f9'], ['--markmap-code-color', '#334155'], ['color', '#1f2937'], ['background', '#ffffff'], ['font-family', font]].forEach(([k, v]) => c.style.setProperty(k, v));
    const css = await fontCss();
    if (css) { const st = document.createElementNS('http://www.w3.org/2000/svg', 'style'); st.textContent = css; c.insertBefore(st, c.firstChild); }
    return new XMLSerializer().serializeToString(c);
  }
  const svgUrl = text => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(text);
  async function mmPng(maxSide) {
    const text = await mmSnapshotSvg();
    if (!text) throw new Error('mind map kosong');
    const img = new Image();
    img.src = svgUrl(text);
    await img.decode();
    const w = img.naturalWidth, h = img.naturalHeight;
    const k = Math.max(1, Math.min(4, maxSide / Math.max(w, h)));
    const cv = document.createElement('canvas');
    cv.width = Math.round(w * k); cv.height = Math.round(h * k);
    const ctx = cv.getContext('2d');
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.drawImage(img, 0, 0, cv.width, cv.height);
    return cv.toDataURL('image/png');
  }

  /* ---------- simpan mind map sebagai PDF ---------- */
  const PAPER = { A4: [297, 210], A3: [420, 297], F4: [330, 215] };
  const PDF = () => S.set.pdf || { size: 'A4', orient: 'land', title: true, label: true, text: false };
  function renderPdf() {
    const P = PDF();
    $$('#pdfSize button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === P.size)));
    $$('#pdfOrient button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === P.orient)));
    let [w, h] = PAPER[P.size];
    if (P.orient === 'port') [w, h] = [h, w];
    const s = Math.min(196 / w, 150 / h), paper = $('#pdfPaper');
    paper.style.width = Math.round(w * s) + 'px'; paper.style.height = Math.round(h * s) + 'px';
    const ai = S.mm.src === 'ai';
    $('#pdfHead').hidden = !$('#pdfTitle').checked;
    $('#pdfLabelRow').hidden = !ai;
    $('#pdfLbl').hidden = !$('#pdfLabel').checked || !ai;
    const pages = 1 + ($('#pdfText').checked ? 1 : 0);
    $('#pdfInfo').innerHTML = `<b>${P.size === 'F4' ? 'F4 (folio)' : P.size} ${P.orient === 'land' ? 'mendatar' : 'tegak'}</b>${w} × ${h} mm · ${pages}${pages > 1 ? '+' : ''} halaman<br>Nama file: ${esc(mmTitle())} - mind map.pdf`;
  }
  async function openPdf() {
    if (!MM || !shownMd) { toast('Buat mind map dulu, lalu simpan sebagai PDF.'); return; }
    const P = PDF();
    $('#pdfTitle').checked = P.title !== false; $('#pdfLabel').checked = P.label !== false; $('#pdfText').checked = !!P.text;
    setMsg('#pdfMsg', ''); $('#pdfSave').disabled = false;
    const img = $('#pdfImg'), text = await mmSnapshotSvg();
    img.hidden = !text; if (text) img.src = svgUrl(text);
    renderPdf();
    openDlg('dlgPdf');
  }
  const pdfPatch = patch => { S.set.pdf = { ...PDF(), ...patch }; renderPdf(); };
  $('#pdfSize').addEventListener('click', e => { const b = e.target.closest('button'); if (b) pdfPatch({ size: b.dataset.v }); });
  $('#pdfOrient').addEventListener('click', e => { const b = e.target.closest('button'); if (b) pdfPatch({ orient: b.dataset.v }); });
  ['#pdfTitle', '#pdfLabel', '#pdfText'].forEach(s => $(s).addEventListener('change', () => pdfPatch({ title: $('#pdfTitle').checked, label: $('#pdfLabel').checked, text: $('#pdfText').checked })));
  $('#pdfSave').addEventListener('click', async () => {
    const P = PDF(), md = S.mm.cache[mmCacheKey()];
    if (!md) return;
    setMsg('#pdfMsg', 'Menyiapkan PDF…', 'busy'); $('#pdfSave').disabled = true;
    let png;
    try { png = await mmPng(P.size === 'A3' ? 6000 : 4500); }
    catch (err) { console.error(err); setMsg('#pdfMsg', 'Gambar mind map tidak bisa dibuat.', 'err'); $('#pdfSave').disabled = false; return; }
    const r = await safeCall('export_map', 'pdf', { md, title: mmTitle(), style: S.mm.style, ai: S.mm.src === 'ai', png, pdf: P });
    $('#pdfSave').disabled = false;
    if (r && r.ok) { closeDialogs(); toast(`PDF tersimpan: ${r.name}`); }
    else if (r && r.cancelled) setMsg('#pdfMsg', '');
    else setMsg('#pdfMsg', (r && r.error) || 'Gagal menyimpan PDF.', 'err');
  });

  /* ---------- tema mengikuti Windows ---------- */
  const mq = matchMedia('(prefers-color-scheme: dark)');
  const applyTheme = () => { win.dataset.mode = mq.matches ? 'dark' : 'light'; };
  applyTheme();
  try { mq.addEventListener('change', applyTheme); } catch (_) { mq.addListener(applyTheme); }
  new ResizeObserver(() => { if (MM && S.tab === 'map' && S.done) debounce('fit', mmFit, 200); }).observe($('.mmstage'));

  /* ---------- mulai ---------- */
  async function boot() {
    try { await waitBridge(); }
    catch (_) { $('#boot').textContent = 'Tampilan tidak terhubung ke Urai App. Tutup jendela ini lalu buka Urai App lagi.'; return; }
    let b;
    try { b = await call('init'); }
    catch (e) { console.error(e); $('#boot').textContent = 'Urai App gagal dimuat. Tutup lalu buka lagi.'; return; }
    S.app = b.app; S.set = b.settings; S.providers = b.providers; S.models = b.models; S.baseUrls = b.base_urls; S.keys = b.keys;
    S.tess = b.tesseract; S.defaultDir = b.default_dir; S.items = b.items || []; S.hasQris = b.has_qris; S.hasSamples = b.has_samples;
    S.mm.src = S.set.mm_src || (S.keys[S.set.provider] ? 'ai' : 'struct');
    S.mm.kind = S.set.mm_kind || 'umum';
    S.mm.style = loadStyle(S.set.mm_style);
    $('#tryWrap').hidden = !S.hasSamples;
    $('#tagline').textContent = S.app.tagline;
    $('#sbRight').textContent = `${S.app.name} ${S.app.version} · dibangun di atas MarkItDown dari Microsoft`;
    $('#aboutVer').textContent = `Versi ${S.app.version}${S.app.commit ? ' · ' + S.app.commit.slice(0, 7) : ''}`;
    $('#aboutCredit').textContent = `© ${S.app.year} ${S.app.developer}. Urai App adalah perangkat lunak open source berlisensi MIT. Dibangun di atas MarkItDown, proyek open source dari Microsoft (lisensi MIT). Urai App tidak berafiliasi dengan Microsoft.`;
    $('#aboutMail').textContent = S.app.email;
    $('#aboutSocial').textContent = S.app.social;
    if (S.app.repo) { $('#aboutRepo').textContent = S.app.repo.replace(/^https:\/\//, ''); $('#openRepo').hidden = false; }
    $('#payeeName').textContent = S.app.merchant; $('#payeeName2').textContent = S.app.merchant;
    syncStyleUI();
    renderNow();
    $('#boot').hidden = true;
    pollLoop();
    call('ready').catch(() => {});
    if (S.items.length) toast(`${fmt(S.items.length)} dokumen ditambahkan`);
  }
  boot();
})();
