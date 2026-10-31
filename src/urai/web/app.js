/* Urai App 3.0: logika tampilan.
   Semua pekerjaan berat dikerjakan Python (api.py). Tampilan memanggil window.pywebview.api.<nama>(),
   atau POST /api/<nama> saat dibuka di browser dengan ?dev=1 (devserver.py). Kabar proses diambil lewat poll().
   Semua teks tampilan ada di i18n.js; di sini dipanggil lewat T('kunci', { nilai }). */
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
    catch (e) { console.error(name, e); toast(T('err.generic')); return null; }
  }

  /* ---------- bahasa: kamus di i18n.js, angka mengikuti bahasa ---------- */
  const I18N = window.URAI_I18N || { en: {} };
  const LOC = () => (S.lang === 'id' ? 'id-ID' : 'en-US');
  // nilai { one, other } dipilih dari vars.n; angka di vars ditulis sesuai bahasa (1,234 atau 1.234)
  function T(key, vars) {
    const d = I18N[S.lang] || I18N.en;
    let s = d[key] != null ? d[key] : (I18N.en[key] != null ? I18N.en[key] : key);
    if (s && typeof s === 'object') s = vars && vars.n === 1 ? s.one : s.other;
    if (!vars) return s;
    return String(s).replace(/\{(\w+)\}/g, (m, k) => vars[k] == null ? m : typeof vars[k] === 'number' ? fmt(vars[k]) : String(vars[k]));
  }
  // elemen berikon: hanya simpul teks terakhir yang diganti, supaya ikon tidak ikut terhapus
  function setText(el, s) {
    if (!el.firstElementChild) { el.textContent = s; return; }
    const n = [...el.childNodes].reverse().find(x => x.nodeType === 3 && x.nodeValue.trim());
    if (n) n.nodeValue = s; else el.append(s);
  }
  function applyI18n(root = document) {
    $$('[data-i18n]', root).forEach(el => setText(el, T(el.dataset.i18n)));
    $$('[data-i18n-html]', root).forEach(el => { el.innerHTML = T(el.dataset.i18nHtml); });
    $$('[data-i18n-attr]', root).forEach(el => el.dataset.i18nAttr.split(';').forEach(p => {
      const [a, k] = p.split(':').map(x => x.trim());
      if (a && k) el.setAttribute(a, T(k));
    }));
  }

  /* ---------- bantuan kecil ---------- */
  const fmt = n => Number(n || 0).toLocaleString(LOC());
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const ic = (id, cls = '') => `<svg class="ic ${cls}"><use href="#i-${id}"/></svg>`;
  const baseName = name => String(name || '').replace(/\.[A-Za-z0-9]{2,5}$/, '');
  const sizeText = b => b >= 1048576 ? (b / 1048576).toLocaleString(LOC(), { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' MB' : b >= 1024 ? fmt(Math.round(b / 1024)) + ' KB' : fmt(b) + ' B';
  const clock = (t = Date.now()) => { const d = new Date(t), p = x => String(x).padStart(2, '0'); return p(d.getHours()) + (S.lang === 'id' ? '.' : ':') + p(d.getMinutes()); };
  const reduce = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const sep = p => (String(p).includes('\\') ? '\\' : '/');
  const lastParts = (p, n = 2) => { const s = sep(p); return String(p).split(/[\\/]/).filter(Boolean).slice(-n).join(` ${s} `); };
  const fileOf = p => String(p || '').split(/[\\/]/).pop();
  let debounceT = {};
  const debounce = (key, fn, ms) => { clearTimeout(debounceT[key]); debounceT[key] = setTimeout(fn, ms); };

  /* ---------- keadaan ---------- */
  const S = {
    lang: 'en',
    app: {}, providers: {}, models: {}, baseUrls: {}, keys: {}, tess: { available: false, langs: [], names: {} },
    set: {}, defaultDir: '', hasQris: false, hasSamples: true,
    items: [], busy: false, cancelling: false, done: null, sel: null, tab: 'view', rereading: null,
    progress: { done: 0, total: 0, current: null },
    texts: {}, pvShown: '',
    pane: 'general', dlg: { provider: 'gemini', typed: {}, models: {}, urls: {} },
    mm: { src: 'struct', kind: 'poin', view: 'map', busy: false, busyKey: '', busyText: '', cache: {}, style: null, edit: false, undo: {} },
    pick: new Set(),  // baris yang dicentang (pilih banyak); terpisah dari S.sel yang menentukan pratinjau
    ed: null,         // sedang mengedit hasil: { key, name, base, draft, rev, blk, saving }
  };
  const stateName = () => S.busy ? 'busy' : S.done ? 'done' : (S.items.length ? 'ready' : 'empty');
  const provName = p => (S.providers[p] || {}).name || T('ai.providerFallback');
  const langLabel = () => (S.set.langs || []).map(l => S.tess.names[l] || l).join(', ');
  const findItem = id => S.items.find(i => i.id === id);
  const isCombined = () => S.set.out_mode === 'combined';
  const combinedName = () => S.set.combined_name || T('combined.default');
  const currentKey = () => (isCombined() && !S.sel) ? 'ALL' : (S.sel || (S.items[0] && S.items[0].id) || '');

  function saveSet(patch) {
    Object.assign(S.set, patch);
    call('save_settings', patch).then(s => { if (s) S.set = s; }).catch(e => console.error(e));
  }

  /* ---------- tampilan Markdown (aman: semua teks di-escape) ---------- */
  function inline(s) {
    let t = esc(s);
    t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
    t = t.replace(/!\[([^\]]*)\]\([^)]*\)/g, (m, a) => `<span class="imgph">${ic('image')}${esc(T('md.image'))}${a && a !== 'image' ? ': ' + a : ''}</span>`);
    t = t.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1');
    t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/__(.+?)__/g, '<strong>$1</strong>');
    t = t.replace(/(^|[\s(])\*(?!\s)(.+?)(?<!\s)\*(?=[\s.,;:)!?]|$)/g, '$1<em>$2</em>');
    t = t.replace(/(^|[\s(])_(?!\s)(.+?)(?<!\s)_(?=[\s.,;:)!?]|$)/g, '$1<em>$2</em>');
    return t;
  }
  const PREVIEW_LIMIT = 250000;
  // edit = { blk } saat mengedit: tiap blok dibungkus dengan rentang baris sumbernya (data-l="awal,akhir", akhir tidak
  // termasuk) beserta tombol Edit/Hapus; blok yang sedang diedit diganti kotak teks. Teks sumber tidak pernah dibangun ulang dari HTML.
  function renderMd(md, edit) {
    let cut = false;
    if (md.length > PREVIEW_LIMIT) { md = md.slice(0, PREVIEW_LIMIT); cut = true; }
    const L = md.split('\n'); let h = '', i = 0, m;
    const block = /^(\s*#{1,6}\s|>|\s*\||\s*[-*+]\s|\s*\d+[.)]\s|---\s*$|\*\*\*\s*$|<!--|```|~~~)/;
    const tEd = edit ? esc(T('ed.block')) : '', tDel = edit ? esc(T('ed.del')) : '';
    const wrap = (out, s, e) => {
      if (edit.blk && edit.blk[0] === s) {
        return `<div class="eb ebon" data-l="${s},${e}"><div class="ebed"><textarea class="ebta" rows="${Math.min(Math.max(e - s + 1, 3), 18)}" spellcheck="false" aria-label="${esc(T('ed.blockAria'))}"></textarea>` +
          `<div class="ebacts"><button class="btn sm primary" type="button" data-eb="apply">${T('ed.apply')}</button><button class="btn sm" type="button" data-eb="cancel">${T('cancel')}</button><span class="fhint">${T('ed.keys')}</span></div></div></div>`;
      }
      return `<div class="eb" data-l="${s},${e}">${out}<span class="ebact"><button class="ebb" type="button" data-eb="edit" title="${tEd}" aria-label="${tEd}">${ic('edit')}</button>` +
        `<button class="ebb del" type="button" data-eb="del" title="${tDel}" aria-label="${tDel}">${ic('trash')}</button></span></div>`;
    };
    while (i < L.length) {
      const l = L[i], s = i;
      let out = '';
      if (!l.trim()) { i++; continue; }
      if (/^\s*(```|~~~)/.test(l)) {
        const fence = l.trim().slice(0, 3), code = []; i++;
        while (i < L.length && !L[i].trim().startsWith(fence)) { code.push(L[i]); i++; }
        i++; out = `<pre>${esc(code.join('\n'))}</pre>`;
      } else if ((m = l.match(/^\s*<!--\s*(.+?)\s*-->\s*$/))) { out = `<div class="slide">${esc(m[1].replace(/^Slide number:\s*(\S+)/i, (x, n) => T('md.slide', { n })))}</div>`; i++; }
      else if (/^\s*(---|\*\*\*|___)\s*$/.test(l)) { out = '<hr>'; i++; }
      else if ((m = l.match(/^\s*(#{1,6})\s+(.*)$/))) { const n = Math.min(m[1].length, 4); out = `<h${n}>${inline(m[2])}</h${n}>`; i++; }
      else if (l.startsWith('>')) { const q = []; while (i < L.length && L[i].startsWith('>')) { q.push(L[i].replace(/^>\s?/, '')); i++; } out = `<blockquote>${q.filter(x => x.trim()).map(inline).join('<br>')}</blockquote>`; }
      else if (/^\s*\|/.test(l)) {
        const rows = []; while (i < L.length && /^\s*\|/.test(L[i])) { rows.push(L[i].trim()); i++; }
        const cells = r => r.replace(/^\||\|$/g, '').split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, '|'));
        const body = rows.filter(r => !/^\|\s*:?-{2,}/.test(r)); const [hd, ...rs] = body;
        if (hd) out = `<div class="tbl"><table><thead><tr>${cells(hd).map(c => `<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>${rs.map(r => `<tr>${cells(r).map(c => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      } else if (/^\s*[-*+]\s+/.test(l) || /^\s*\d+[.)]\s+/.test(l)) {
        const ordered = /^\s*\d+[.)]\s+/.test(l), tag = ordered ? 'ol' : 'ul', re = ordered ? /^\s*\d+[.)]\s+/ : /^\s*[-*+]\s+/;
        const li = [];
        while (i < L.length && re.test(L[i])) {
          const ind = Math.min(4, Math.floor(L[i].match(/^\s*/)[0].replace(/\t/g, '  ').length / 2));
          li.push(`<li${ind ? ` style="margin-left:${ind * 1.2}em"` : ''}>${inline(L[i].replace(re, ''))}</li>`); i++;
        }
        const first = ordered ? parseInt(l.match(/^\s*(\d+)/)[1], 10) : 1;
        out = `<${tag}${first > 1 ? ` start="${first}"` : ''}>${li.join('')}</${tag}>`;
      } else {
        const p = []; while (i < L.length && L[i].trim() && (p.length === 0 || !block.test(L[i]))) { p.push(L[i]); i++; }
        out = `<p>${p.map(inline).join('<br>')}</p>`;
      }
      // blok terakhir pratinjau yang dipotong tidak utuh, jadi tidak ditawarkan untuk diedit (pakai tab Teks Markdown)
      if (out) h += edit && !(cut && i >= L.length) ? wrap(out, s, Math.min(i, L.length)) : out;
    }
    if (cut) h += `<blockquote class="cut">${T('pv.cut')}</blockquote>`;
    return h;
  }

  /* ---------- daftar dokumen ---------- */
  const badgeHTML = it => it.kind === 'yt' ? `<span class="badge b-yt" aria-hidden="true">${ic('play', 'fill')}</span>` : `<span class="badge b-${esc(it.kind)}" aria-hidden="true">${esc(it.badge || 'FILE')}</span>`;
  function statusHTML(it) {
    switch (it.status) {
      case 'wait': return `<span class="st wait">${ic('clock')}${T('stat.wait')}</span>`;
      case 'work': return `<span class="st work"><span class="spin"></span>${T('stat.work')}</span>`;
      case 'done': return `<span class="st ok">${ic('checkc')}${T('stat.words', { n: it.words || 0 })}</span>`;
      case 'warn': return `<span class="st warn">${ic('alert')}${T('stat.warn')}</span>`;
      case 'error': return `<span class="st err">${ic('xc')}${T('stat.error')}</span>`;
      default: return '<span></span>';
    }
  }
  const EXP_TIP = { aud: 'exp.aud', yt: 'exp.yt' };
  function metaHTML(it) {
    if (it.status === 'work' && it.sub) return `<span class="mt work">${esc(it.sub)}</span>`;
    if (it.status === 'warn') {
      const label = T(S.set.ocr_mode === 'off' ? 'fix.enable' : 'fix.reread');
      const fix = it.fix === 'ocr' && !S.busy && !S.rereading ? ` <button class="linkbtn" type="button" data-fix="${esc(it.id)}">${label}</button>` : '';
      return `<span class="mt warn">${esc(it.message)}${fix}</span>`;
    }
    if (it.status === 'error') return `<span class="mt err">${esc(it.message)}</span>`;
    let tag = '';
    const mode = S.set.ocr_mode;
    if (it.kind === 'pdf' && (it.scan || it.mixed)) {
      const what = T(it.scan ? 'tag.scan' : 'tag.mixed');
      const t = T({ off: 'tag.skip', offline: 'tag.offline', ai: 'tag.ai' }[mode], { what });
      tag = `<span class="tag scan${mode === 'off' ? ' off' : ''}">${ic('scan')}${esc(t)}</span>`;
    } else if (it.kind === 'img') {
      const t = T({ off: 'tag.imgOff', offline: 'tag.imgOffline', ai: 'tag.imgAi' }[mode]);
      tag = `<span class="tag scan${mode === 'off' ? ' off' : ''}">${ic('image')}${esc(t)}</span>`;
    }
    if (it.exp) tag += `<span class="tag exp" title="${esc(T(EXP_TIP[it.kind] || 'exp'))}">${T('exp')}</span>`;
    return `<span class="mt">${esc(it.meta)}${tag}</span>`;
  }
  function renderList() {
    const st = stateName();
    const click = st === 'done' ? ' click' : '';
    // daftar digambar ulang utuh; simpan dulu tombol yang sedang difokus supaya keyboard tidak kehilangan tempat
    const act = document.activeElement, actRow = act && act.closest ? act.closest('#files .row') : null;
    const actSel = actRow ? (['grip', 'rm', 'pick'].map(c => act.classList.contains(c) ? '.' + c : '').find(Boolean) || '') : '';
    const actId = actRow ? actRow.dataset.id : '';
    const gripTip = esc(T('row.grip')), rmTip = esc(T('row.rm')), busy = st === 'busy' ? ' disabled' : '';
    $('#files').innerHTML = S.items.map(it => {
      const sel = st === 'done' && S.sel === it.id ? ' sel' : '';
      return `<li class="row${sel}${click}" data-id="${esc(it.id)}">` +
        `<input class="pick" type="checkbox" data-pick="${esc(it.id)}" aria-label="${esc(T('list.pickAria', { name: it.display }))}"${S.pick.has(it.id) ? ' checked' : ''}${busy}>` +
        `<button class="grip" type="button" title="${gripTip}" aria-label="${esc(T('row.gripAria', { name: it.display }))}">${ic('grip')}</button>${badgeHTML(it)}` +
        `<span class="ftxt"><span class="nm" title="${esc(it.source)}">${esc(it.display)}</span>${metaHTML(it)}</span>` +
        `${statusHTML(it)}<button class="rm" type="button" data-rm="${esc(it.id)}" aria-label="${esc(T('row.rmAria', { name: it.display }))}" title="${rmTip}">${ic('x')}</button></li>`;
    }).join('');
    if (actSel) { const el = $(`#files .row[data-id="${CSS.escape(actId)}"] ${actSel}`); if (el) el.focus(); }
  }
  // bilah pilih banyak: centang "Pilih semua" bisa setengah (sebagian baris dipilih)
  function renderListBar() {
    const ids = new Set(S.items.map(i => i.id));
    [...S.pick].forEach(id => { if (!ids.has(id)) S.pick.delete(id); });
    const n = S.items.length, k = S.pick.size, all = $('#pickAll');
    all.checked = n > 0 && k === n; all.indeterminate = k > 0 && k < n; all.disabled = S.busy;
    $('#pickCount').textContent = k ? T('list.count', { n: k }) : '';
    $('#rmPicked').disabled = !k || S.busy;
    $('#clearAll').disabled = !n || S.busy;
  }
  function srcMeta() {
    if (!S.items.length) return T('src.none');
    const links = S.items.filter(i => i.is_link).length, files = S.items.length - links;
    const bytes = S.items.reduce((a, i) => a + (i.size || 0), 0);
    return [files ? T('src.files', { n: files }) : '', links ? T('src.links', { n: links }) : '', bytes ? sizeText(bytes) : ''].filter(Boolean).join(' · ');
  }

  /* ---------- panel kanan ---------- */
  function pathLabel() {
    if (S.set.location === 'same') return T('path.same');
    const d = S.set.custom_dir || S.defaultDir;
    if (!S.set.custom_dir || d === S.defaultDir) return T('path.default');
    return esc(lastParts(d, 3));
  }
  function renderSetup() {
    const n = S.items.length, mode = S.set.ocr_mode;
    $$('.opt[data-out]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.out === S.set.out_mode)));
    $$('.mode').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.ocr === mode)));
    $('#outSepSub').textContent = n ? T('out.sepSub', { n }) : T('out.sepSubAny');
    const cn = $('#cname');
    if (document.activeElement !== cn) cn.value = combinedName();
    const hint = $('#ocrHint');
    if (mode === 'off') hint.innerHTML = `${ic('off', 'warn')}<span class="txt">${T('hint.off')}</span>`;
    else if (mode === 'offline') {
      hint.innerHTML = S.tess.available
        ? `${ic('shield')}<span class="txt">${T('hint.offline', { langs: esc(langLabel()) })} <button class="linkbtn" type="button" data-open="offline">${T('hint.configure')}</button></span>`
        : `${ic('alert', 'warn')}<span class="txt">${T('hint.noTess')} <button class="linkbtn" type="button" data-open="offline">${T('hint.configure')}</button></span>`;
    } else {
      const p = S.set.provider, has = S.keys[p];
      hint.innerHTML = has
        ? `${ic('spark')}<span class="txt">${T('hint.ai', { prov: esc(provName(p)) })} <button class="linkbtn" type="button" data-open="ai">${T('hint.configure')}</button></span>`
        : `${ic('alert', 'warn')}<span class="txt">${T('hint.aiNoKey', { prov: esc(provName(p)) })} <button class="linkbtn" type="button" data-open="ai">${T('hint.enterKey')}</button></span>`;
    }
    const go = $('#go');
    go.disabled = n === 0 || S.busy;
    $('#goText').textContent = n === 0 ? T('go.empty') : T(isCombined() ? 'go.comb' : 'go.sep', { n });
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
    $('#pct').innerHTML = `${p}%<small>${T('prog.count', { i: Math.min(fin.length + 1, total), n: total })}</small>`;
    $('#pctBar').style.setProperty('--p', p + '%');
    $('#cur').innerHTML = cur
      ? `${badgeHTML(cur)}<div class="ftxt"><span class="nm">${esc(cur.display)}</span><span class="sub"><span class="spin"></span>${esc(cur.sub || T('prog.working'))}</span></div>`
      : `<span class="badge b-md">MD</span><div class="ftxt"><span class="nm">${T(S.cancelling ? 'prog.cancelling' : 'prog.saving')}</span><span class="sub">${T(S.cancelling ? 'prog.cancellingSub' : 'prog.savingSub')}</span></div>`;
    $('#doneList').innerHTML = fin.length ? `<li style="display:block"><span class="lbl">${T('prog.finished')}</span></li>` + fin.slice().reverse().map(i => {
      const k = i.status === 'warn' ? ['alert', 'w', T('prog.warn')] : i.status === 'error' ? ['xc', 'e', T('prog.error')] : ['checkc', '', T('stat.words', { n: i.words || 0 })];
      return `<li>${ic(k[0], k[1])}<span>${esc(i.display)}</span><span>${k[2]}</span></li>`;
    }).join('') : '';
    const c = $('#cancel');
    c.disabled = S.cancelling;
    $('#cancelText').textContent = T(S.cancelling ? 'prog.cancelBusy' : 'prog.cancel');
  }
  function folderLabel(dir) {
    if (!dir) return '';
    if (dir === S.defaultDir) return T('path.defaultPlain');
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
    $('#resMeta').textContent = [T('res.ok', { n: ok }), warn ? T('res.warn', { n: warn }) : '', err ? T('res.err', { n: err }) : ''].filter(Boolean).join(' · ');
    const total = S.items.reduce((a, i) => a + (i.words || 0), 0);
    if (isCombined()) {
      const name = d.combined_path ? fileOf(d.combined_path) : `${combinedName()}.md`;
      $('#outbox').innerHTML = `<span class="badge b-md">MD</span><div style="min-width:0"><div class="t" title="${esc(d.combined_path)}">${esc(name)}</div><div class="s">${T('res.combInfo', { n: d.combined_words || total, folder: esc(folderLabel(d.out_dir)) })}</div></div>`;
      $('#openFileText').textContent = T('res.openFile');
    } else {
      const saved = S.items.filter(i => i.output).length;
      $('#outbox').innerHTML = `<span class="badge b-md">MD</span><div style="min-width:0"><div class="t">${T('res.sepSaved', { n: saved })}</div><div class="s">${T('res.sepInfo', { n: total, folder: esc(folderLabel(d.out_dir)) })}</div></div>`;
      $('#openFileText').textContent = T('res.openThis');
    }
    $$('.tabs button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === S.tab)));
    const it = findItem(S.sel);
    if (isCombined()) $('#pvLabel').innerHTML = it ? `${T('pv.part', { name: esc(it.display) })} <button class="linkbtn" type="button" id="showAll">${T('pv.all')}</button>` : T('pv.whole');
    else $('#pvLabel').textContent = it ? it.display : '';
    const isMap = S.tab === 'map';
    $('#pvBody').hidden = isMap;
    $('#mmPanel').hidden = !isMap;
    if (isMap) renderMap(); else renderPreview();
    syncEdBar();
    const limit = 60000, big = total > limit, sm = $('#sizeMeter');
    sm.className = 'size' + (big ? ' big' : '');
    sm.innerHTML = `<span>${T('size.label')}</span><div class="bar"><i style="--p:${Math.max(3, Math.min(100, total / limit * 100))}%"></i></div><span><b>${T('stat.words', { n: total })}</b> · ${T(big ? 'size.big' : 'size.ok')}</span>`;
    $('#nudge').hidden = !(S.hasQris && (S.set.runs || 0) >= 5 && !S.set.supported);
  }
  async function renderPreview() {
    const body = $('#pvBody');
    if (S.ed) {
      // mode edit: kedua tab memakai draf yang sama; mengetik di tab Teks Markdown tidak menggambar ulang (rev tetap)
      const sig = `ed|${S.ed.key}|${S.tab}|${S.ed.rev}`;
      if (sig === S.pvShown) return;
      const keep = S.pvShown.startsWith(`ed|${S.ed.key}|${S.tab}|`) ? body.scrollTop : 0;
      S.pvShown = sig;
      body.classList.toggle('rawedit', S.tab === 'raw');
      if (S.tab === 'raw') {
        body.innerHTML = `<textarea class="edta" id="edRaw" spellcheck="false" aria-label="${esc(T('tab.raw'))}"></textarea>`;
        $('#edRaw').value = S.ed.draft;
      } else {
        body.innerHTML = `<div class="md editing">${renderMd(S.ed.draft, { blk: S.ed.blk })}</div>`;
        const ta = $('.ebta', body);
        if (ta) { ta.value = S.ed.draft.split('\n').slice(S.ed.blk[0], S.ed.blk[1]).join('\n'); ta.focus(); }
      }
      body.scrollTop = keep;
      return;
    }
    body.classList.remove('rawedit');
    const key = currentKey(), item = findItem(key);
    const sig = `${key}|${S.tab}|${item ? item.status + item.words : ''}`;
    if (sig === S.pvShown && S.texts[key] != null) return;
    S.pvShown = sig;
    const md = await textOf(key);
    if (S.pvShown !== sig) return;
    if (!md.trim()) {
      const msg = item && item.message ? item.message : T('pv.empty');
      body.innerHTML = `<div class="md"><blockquote>${esc(msg)}</blockquote></div>`;
    } else body.innerHTML = S.tab === 'view' ? `<div class="md">${renderMd(md)}</div>` : `<pre class="raw">${esc(md.length > PREVIEW_LIMIT ? md.slice(0, PREVIEW_LIMIT) + '\n\n' + T('pv.cutRaw') : md)}</pre>`;
    body.scrollTop = 0;
  }
  function ocrStatusLabel() {
    const m = S.set.ocr_mode;
    if (m === 'off') return T('sb.ocrOff');
    if (m === 'offline') return S.tess.available ? T('sb.ocrOffline', { langs: langLabel() }) : T('sb.ocrNoTess');
    return T('sb.ocrAi', { prov: provName(S.set.provider) });
  }
  function renderStatus() {
    const st = stateName(), n = S.items.length;
    const fin = S.items.filter(i => ['done', 'warn', 'error'].includes(i.status)).length;
    $('#sbLeft').textContent = {
      empty: () => T('sb.empty'),
      ready: () => T('sb.ready', { n }),
      busy: () => S.cancelling ? T('sb.cancelling') : T('sb.busy', { i: Math.min(fin + 1, n), n }),
      done: () => T('sb.done', { time: clock(S.done && S.done.at) }),
    }[st]();
    $('#sbMid').textContent = ocrStatusLabel();
  }
  let rafId = 0;
  function render() { if (!rafId) rafId = requestAnimationFrame(() => { rafId = 0; renderNow(); }); }
  function renderNow() {
    const st = stateName();
    win.dataset.state = st; win.dataset.out = S.set.out_mode || 'separate'; win.dataset.ocr = S.set.ocr_mode || 'offline';
    win.dataset.tess = S.tess.available ? '1' : '0';
    $('#srcMeta').textContent = srcMeta();
    renderListBar(); renderList(); renderSetup(); renderStatus();
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
    if (!res.ok) { toast(res.error || T('t.addFail')); return; }
    if (res.fresh) startFresh();
    S.items = res.items || S.items;
    if (res.cancelled) { render(); return; }
    const parts = [];
    if (res.added) parts.push(label ? T('t.addedFrom', { label, n: res.added }) : T('t.added', { n: res.added }));
    else if (!res.skipped) parts.push(label ? T('t.noneNew', { label }) : T('t.already'));
    if (res.skipped) parts.push(T('t.skipped', { n: res.skipped }));
    if (parts.length) toast(parts.join('. '));
    render();
  }
  function startFresh() { S.done = null; S.sel = null; S.texts = {}; S.pvShown = ''; S.mm.cache = {}; S.mm.undo = {}; S.ed = null; mmEditOff(true); shownMd = null; exitFull(); }
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
          toast(T('t.cancelled', { n: s.ok + s.warn }), 3800);
          break;
        }
        S.cancelling = false;
        s.at = Date.now();
        S.done = s;
        S.tab = 'view';
        S.sel = isCombined() ? null : ((S.items.find(i => i.status === 'done') || S.items[0] || {}).id || null);
        if (s.error === s.total) toast(T('t.allFailed'), 4000);
        else toast(isCombined() ? T('t.saved', { name: fileOf(s.combined_path) || T('t.combinedFile') }) : T('res.sepSaved', { n: S.items.filter(i => i.output).length }));
        break;
      }
      case 'failed': S.busy = false; S.cancelling = false; S.done = null; S.items = e.items || S.items; toast(e.error || T('t.failed'), 4000); break;
      case 'reread_done': {
        const it = findItem(e.id);
        S.rereading = null;
        delete S.texts[e.id]; delete S.texts.ALL; S.pvShown = '';
        Object.keys(S.mm.cache).forEach(k => { if (k.startsWith(e.id + '|') || k.startsWith('ALL|')) delete S.mm.cache[k]; });
        if (typeof e.combined_words === 'number' && S.done) S.done.combined_words = e.combined_words;
        if (it && e.ok) { if (!isCombined()) S.sel = it.id; toast(T('t.reread', { name: it.display })); }
        else if (it) toast(it.message || T('t.stillUnread'), 3600);
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
  // di keadaan selesai, menambah dokumen mengganti daftar: perubahan yang belum disimpan ditahan dulu
  const addFiles = async () => { if (edGuard()) return; onAdded(await safeCall('pick_files')); };
  const addFolder = async () => { if (edGuard()) return; const r = await safeCall('pick_folder'); onAdded(r, r && r.folder ? T('t.folder', { name: r.folder }) : ''); };
  $('#addFile').addEventListener('click', addFiles);
  $('#dzPick').addEventListener('click', addFiles);
  $('#addFolder').addEventListener('click', addFolder);
  $('#dzFolder').addEventListener('click', addFolder);
  $('#tryDemo').addEventListener('click', async () => { const r = await safeCall('add_samples'); onAdded(r, T('t.samples')); });

  $('#linkForm').addEventListener('submit', async e => {
    e.preventDefault();
    const inp = $('#linkInput'), v = inp.value.trim();
    if (!v) return;
    const res = await safeCall('add_link', v);
    if (!res) return;
    if (!res.ok) { toast(res.error); return; }
    if (res.fresh) startFresh();
    S.items = res.items; inp.value = ''; render(); toast(T('t.linkAdded'));
  });

  $('#files').addEventListener('click', async e => {
    if (e.target.closest('.pick')) return;  // kotak centang: ditangani event change, bukan memilih pratinjau
    const rm = e.target.closest('[data-rm]');
    if (rm) { if (edLocks([rm.dataset.rm])) return; const r = await safeCall('remove_item', rm.dataset.rm); if (r) afterRemove(r.items, [rm.dataset.rm]); return; }
    const fix = e.target.closest('[data-fix]');
    if (fix) {
      if (edLocks([fix.dataset.fix, 'ALL'])) return;
      saveSet({ ocr_mode: 'offline' });
      const r = await safeCall('reread', fix.dataset.fix);
      if (r && r.ok) { S.rereading = fix.dataset.fix; const it = findItem(fix.dataset.fix); if (it) { it.status = 'work'; it.sub = T('t.rereadSub'); } }
      else if (r) toast(r.error);
      render(); return;
    }
    if (e.target.closest('.grip')) return;
    const row = e.target.closest('.row');
    if (row && stateName() === 'done' && row.dataset.id !== S.sel) {
      if (edGuard()) return;
      S.ed = null; S.sel = row.dataset.id; S.pvShown = ''; render();
    }
  });
  $('#files').addEventListener('change', e => {
    const c = e.target.closest('.pick'); if (!c) return;
    if (c.checked) S.pick.add(c.dataset.pick); else S.pick.delete(c.dataset.pick);
    renderListBar();
  });

  /* ---------- pilih banyak: hapus yang dipilih, kosongkan daftar (file di komputer tidak ikut terhapus) ---------- */
  $('#pickAll').addEventListener('change', e => { S.pick = e.target.checked ? new Set(S.items.map(i => i.id)) : new Set(); render(); });
  function afterRemove(items, ids) {
    S.items = items || [];
    ids.forEach(id => { S.pick.delete(id); delete S.texts[id]; });
    Object.keys(S.mm.cache).forEach(k => { if (ids.some(id => k.startsWith(id + '|'))) { delete S.mm.cache[k]; delete S.mm.undo[k]; } });
    if (S.ed && ids.includes(S.ed.key)) S.ed = null;
    if (!S.items.length) startFresh();
    else if (S.done && S.sel && !findItem(S.sel)) {
      // baris yang sedang dipratinjau ikut dihapus: pilih baris lain
      S.sel = isCombined() ? null : (S.items.find(i => i.status === 'done') || S.items[0]).id;
      S.pvShown = '';
    }
    render();
  }
  $('#rmPicked').addEventListener('click', async () => {
    const ids = S.items.map(i => i.id).filter(id => S.pick.has(id));
    if (!ids.length || edLocks(ids)) return;
    const r = await safeCall('remove_items', ids);
    if (!r) return;
    if (!r.ok) { toast(r.error || T('err.generic')); return; }
    afterRemove(r.items, ids);
    toast(T('list.removed', { n: ids.length }), 3600);
  });
  // Kosongkan daftar butuh dua klik: klik pertama mengubah tombol jadi "Klik lagi untuk mengosongkan" selama 3 detik
  let clearT = 0;
  function disarmClear() { clearTimeout(clearT); clearT = 0; const b = $('#clearAll'); b.classList.remove('confirm'); setText(b, T('list.clear')); }
  $('#clearAll').addEventListener('click', () => {
    if (!clearT) { if (edGuard()) return; const b = $('#clearAll'); b.classList.add('confirm'); setText(b, T('list.clearAgain')); clearT = setTimeout(disarmClear, 3000); return; }
    disarmClear(); clearList(T('list.cleared'));
  });
  async function clearList(msg) {
    if (edGuard()) return;
    const r = await safeCall('clear');
    if (r && r.ok) { S.items = []; S.pick.clear(); startFresh(); render(); if (msg) toast(msg); }
    else if (r && r.error) toast(r.error);
  }

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
  // kosong = pakai nama bawaan sesuai bahasa (Combined / Gabungan)
  $('#cname').addEventListener('input', e => debounce('cname', () => { const v = e.target.value.trim(); saveSet({ combined_name: v === T('combined.default') ? '' : v }); }, 400));
  $('#sameFolder').addEventListener('change', e => { saveSet({ location: e.target.checked ? 'same' : 'custom' }); render(); });
  $('#changePath').addEventListener('click', async () => {
    const r = await safeCall('choose_output_dir');
    if (r && r.ok) { S.set = r.settings; render(); toast(T('t.savedTo', { path: lastParts(r.path, 2) })); }
  });
  $('#go').addEventListener('click', start);
  $('#cancel').addEventListener('click', () => { S.cancelling = true; call('cancel'); render(); });

  $$('.tabs button').forEach(b => b.addEventListener('click', () => {
    if (b.dataset.tab !== 'map' && S.mm.edit) mmEditOff();
    S.tab = b.dataset.tab; S.pvShown = ''; if (S.tab !== 'map') exitFull(); render();
  }));
  $('#pvLabel').addEventListener('click', e => { if (e.target.id === 'showAll') { S.sel = null; S.pvShown = ''; render(); } });
  $('#openFile').addEventListener('click', async () => {
    const d = S.done; if (!d) return;
    let path = '';
    if (isCombined()) path = d.combined_path;
    else { const it = findItem(S.sel) || S.items.find(i => i.output); path = it && it.output; if (it && !it.output) { toast(T('t.noOutput')); return; } }
    if (!path) { toast(T('t.noFile')); return; }
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
    toast(T('t.copyFail'));
  }
  $('#copyText').addEventListener('click', async () => {
    const md = S.ed && S.ed.key === currentKey() ? S.ed.draft : await textOf(currentKey());
    if (!md) { toast(T('t.nothingToCopy')); return; }
    copyText(md, T('t.copied'));
  });
  $('#again').addEventListener('click', () => clearList(''));
  $('#backSetup').addEventListener('click', async () => { if (edGuard()) return; const r = await safeCall('reset_results'); if (r && r.ok) { S.items = r.items; startFresh(); render(); } });
  $('#toMap').addEventListener('click', () => { S.tab = 'map'; render(); });

  /* ---------- edit hasil di Tampilan dan Teks Markdown ---------- */
  // yang bisa diedit: mode terpisah = dokumen terpilih yang punya file; mode gabung = seluruh file gabungan saja
  function edScope() {
    const d = S.done; if (!d) return null;
    if (isCombined()) return d.combined_path ? { key: 'ALL', name: fileOf(d.combined_path) } : null;
    const it = findItem(currentKey()); return it && it.output ? { key: it.id, name: fileOf(it.output) } : null;
  }
  const edDirty = () => !!S.ed && S.ed.draft !== S.ed.base;
  // aksi yang akan membuang draf ditahan dulu, sampai perubahan disimpan atau dibuang
  function edGuard() { if (!edDirty()) return false; toast(T('ed.blocked'), 3600); return true; }
  const edLocks = ids => !!S.ed && ids.includes(S.ed.key) && edGuard();
  function syncEdBar() {
    const here = !!S.done && S.tab !== 'map', on = !!S.ed && here, dirty = edDirty(), can = !!edScope(), btn = $('#edBtn');
    btn.hidden = !here || !!S.ed; btn.disabled = !can; btn.title = can ? '' : T('ed.noFile');
    $('#edBar').hidden = !on;
    if (!on) return;
    $('#edBar').classList.toggle('dirty', dirty);
    $('#edMsg').textContent = dirty ? T('ed.dirty') : T(S.tab === 'raw' ? 'ed.hintRaw' : 'ed.hintView');
    $('#edDiscard').hidden = !dirty; $('#edSave').hidden = !dirty; $('#edDone').hidden = dirty;
    $('#edSave').disabled = $('#edDiscard').disabled = !!S.ed.saving;
  }
  async function edStart() {
    if (isCombined() && S.sel) { S.sel = null; S.pvShown = ''; toast(T('ed.whole')); }
    const sc = edScope(); if (!sc) { toast(T('ed.noFile')); return; }
    const md = await textOf(sc.key);
    S.ed = { key: sc.key, name: sc.name, base: md, draft: md, rev: 1, blk: null, saving: false };
    S.pvShown = ''; render();
  }
  function edSetDraft(md, blk = null) { S.ed.draft = md; S.ed.blk = blk; S.ed.rev++; render(); }
  // ganti baris [s, e) dengan teks baru; bila dihapus, baris kosong ganda yang tersisa dirapikan
  function spliceLines(md, s, e, text) {
    const L = md.split('\n'), add = text === '' ? [] : text.replace(/\r\n?/g, '\n').split('\n');
    L.splice(s, e - s, ...add);
    if (!add.length && s < L.length && !L[s].trim() && (s === 0 || !L[s - 1].trim())) L.splice(s, 1);
    return L.join('\n');
  }
  async function edSave() {
    const ed = S.ed; if (!ed || ed.saving || !edDirty()) return;
    const draft = ed.draft;
    ed.saving = true; syncEdBar();
    const r = await safeCall('save_result', ed.key, draft);
    ed.saving = false;
    if (r && r.ok) {
      S.texts = { [ed.key]: draft };  // teks lain dibaca ulang dari Python bila dibutuhkan
      if (r.items) S.items = r.items;
      if (S.done && typeof r.combined_words === 'number') S.done.combined_words = r.combined_words;
      Object.keys(S.mm.cache).forEach(k => { if (k.startsWith(ed.key + '|') || k.startsWith('ALL|')) { delete S.mm.cache[k]; delete S.mm.undo[k]; } });
      shownMd = null; ed.base = draft;
      toast(T('ed.saved', { name: r.name || ed.name }));
    } else if (r) toast(r.error || T('t.saveFail'), 4000);
    render();
  }
  $('#edBtn').addEventListener('click', edStart);
  $('#edSave').addEventListener('click', edSave);
  $('#edDiscard').addEventListener('click', () => { if (S.ed) edSetDraft(S.ed.base); });
  $('#edDone').addEventListener('click', () => { S.ed = null; S.pvShown = ''; render(); });
  $('#pvBody').addEventListener('input', e => { if (e.target.id === 'edRaw' && S.ed) { S.ed.draft = e.target.value; syncEdBar(); } });
  $('#pvBody').addEventListener('click', e => {
    const b = e.target.closest('[data-eb]'); if (!b || !S.ed) return;
    const [s, en] = b.closest('.eb').dataset.l.split(',').map(Number), act = b.dataset.eb, ta = $('#pvBody .ebta');
    if (act === 'apply') edSetDraft(spliceLines(S.ed.draft, s, en, ta.value));
    else if (act === 'cancel') edSetDraft(S.ed.draft);
    else if (ta) ta.focus();  // satu bagian sekali edit: terapkan atau batalkan dulu yang sedang terbuka
    else if (act === 'edit') edSetDraft(S.ed.draft, [s, en]);
    else if (act === 'del') edSetDraft(spliceLines(S.ed.draft, s, en, ''));
  });
  $('#pvBody').addEventListener('keydown', e => {
    if (!e.target.classList.contains('ebta')) return;
    const go = sel => { e.preventDefault(); e.stopPropagation(); $('#pvBody ' + sel).click(); };
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') go('[data-eb="apply"]');
    else if (e.key === 'Escape') go('[data-eb="cancel"]');
  });

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && stateName() === 'ready' && !openDialog()) { e.preventDefault(); start(); }
    const k = (e.ctrlKey || e.metaKey) && !e.altKey ? e.key.toLowerCase() : '';
    if (k === 's' && S.ed && S.done && !openDialog()) { e.preventDefault(); edSave(); }
    if (k === 'z' && !e.shiftKey && S.mm.edit && S.tab === 'map' && S.done && !openDialog() && !/^(INPUT|TEXTAREA)$/.test((document.activeElement || {}).tagName || '')) { e.preventDefault(); mmUndo(); }
    if (e.key === 'Escape') { if (openDialog()) closeDialogs(); else if (!$('#mmMenu').hidden) $('#mmMenu').hidden = true; else if (!$('#mmNodeEd').hidden) closeNodeEd(); else if (!$('#mmStyle').hidden) closeStyle(); else exitFull(); }
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
    $('#dropTitle').textContent = T(S.busy ? 'drop.busy' : 'drop.title');
    $('#dropSub').textContent = S.busy ? T('drop.busySub') : (n ? T('drop.items', { n }) : T('drop.sub')) + (S.done ? T('drop.replace') : '');
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
      if (res && res.ok) { if (res.fresh) startFresh(); S.items = res.items; render(); toast(T('t.linkAdded')); }
      else if (res) toast(res.error);
      return;
    }
    dragDepth = 0; win.dataset.drag = '0';
    if (DEV) toast(T('t.devDrop'));
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

  // Pengaturan: Umum (bahasa, tema) langsung berlaku; Baca offline dan AI disimpan lewat tombol Simpan
  function setPane(p) {
    S.pane = p;
    const gen = p === 'general';
    $$('#dTabs button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.pane === p)));
    $('#pane-general').hidden = !gen; $('#pane-offline').hidden = p !== 'offline'; $('#pane-ai').hidden = p !== 'ai';
    $('#d-sub').textContent = T(gen ? 'set.subGeneral' : 'set.subScan');
    $('#dCancel').hidden = gen; $('#dSave').hidden = gen; $('#dDone').hidden = !gen;
    $('#dSave').textContent = T(p === S.set.ocr_mode ? 'set.save' : 'set.saveUse');
    setMsg('#testMsg', '');
  }
  function setMsg(sel, text, kind = '') { const el = $(sel); el.textContent = text; el.className = 'fmsg' + (kind ? ' ' + kind : ''); }
  const themeName = () => (['light', 'dark'].includes(S.set.theme) ? S.set.theme : 'system');
  function syncGeneral() {
    $$('#uiLang button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === S.lang)));
    $$('#uiTheme button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === themeName())));
  }
  function fillProvider() {
    const p = S.dlg.provider, has = S.keys[p];
    $$('#prov [data-p]').forEach(b => {
      b.setAttribute('aria-pressed', String(b.dataset.p === p));
      let dot = b.querySelector('.kdot');
      if (S.keys[b.dataset.p] && !dot) { dot = document.createElement('span'); dot.className = 'kdot'; b.append(dot); }
      if (!S.keys[b.dataset.p] && dot) dot.remove(); else if (dot) dot.title = T('ai.keySaved');
    });
    const key = $('#apiKey');
    key.value = S.dlg.typed[p] || '';
    key.placeholder = T(has ? 'ai.keyPhSaved' : 'ai.keyPh');
    const link = (S.providers[p] || {}).has_link;
    $('#keyHint').innerHTML = (link ? `${T('ai.noKeyYet')} <button class="linkbtn" type="button" data-link="key_${esc(p)}">${T('ai.getKey')}</button>` : T('ai.ownServer')) +
      (has ? ` · <button class="linkbtn" type="button" id="forgetKey">${T('ai.forget')}</button>` : '');
    $('#aiSendNote').innerHTML = T('ai.sendNote', { prov: `<b>${esc(provName(p))}</b>` });
    $('#modelName').value = S.dlg.models[p] != null ? S.dlg.models[p] : (S.models[p] || '');
    $('#modelName').placeholder = (S.providers[p] || {}).model || T('ai.modelPh');
    $('#baseUrl').value = S.dlg.urls[p] != null ? S.dlg.urls[p] : (S.baseUrls[p] || '');
    if (p === 'other') $('#advBox').open = true;
    setMsg('#testMsg', '');
  }
  // isian yang belum disimpan dicatat dulu, supaya tidak hilang saat ganti penyedia atau ganti bahasa
  const keepTyped = () => { const p = S.dlg.provider; S.dlg.typed[p] = $('#apiKey').value; S.dlg.models[p] = $('#modelName').value; S.dlg.urls[p] = $('#baseUrl').value; };
  function buildChips(sel) {
    const names = S.tess.names || {}, have = S.tess.langs || [], tip = esc(T('off.langMissing'));
    $('#langChips').innerHTML = Object.keys(names).map(l => {
      const dis = S.tess.available && !have.includes(l);
      return `<label class="chk" title="${dis ? tip : ''}"><input type="checkbox" value="${esc(l)}"${sel.includes(l) && !dis ? ' checked' : ''}${dis ? ' disabled' : ''}>${esc(names[l])}</label>`;
    }).join('');
  }
  function openSettings(pane) {
    S.dlg = { provider: S.set.provider || 'gemini', typed: {}, models: {}, urls: {} };
    buildChips(S.set.langs || []);
    $$('#qSeg button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === S.set.quality)));
    $('#ocrEmbedded').checked = !!S.set.embedded;
    $('#tessMissing').hidden = !!S.tess.available;
    syncGeneral();
    fillProvider();
    setPane(pane || (S.set.ocr_mode === 'ai' ? 'ai' : 'offline'));
    openDlg('dlgSettings');
  }
  $('#btnSettings').addEventListener('click', () => openSettings('general'));
  $('#dTabs').addEventListener('click', e => { const b = e.target.closest('button'); if (b) setPane(b.dataset.pane); });
  $('#uiLang').addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b || b.dataset.v === S.lang) return;
    const r = await safeCall('set_language', b.dataset.v);
    if (!r) return;
    if (!r.ok) { toast(r.error || T('err.generic')); return; }
    S.set = r.settings || S.set; S.app = r.app || S.app; S.providers = r.providers || S.providers; S.tess = r.tesseract || S.tess;
    if (r.items) S.items = r.items;
    applyLang(S.set.lang || b.dataset.v);
    render();
  });
  $('#uiTheme').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; saveSet({ theme: b.dataset.v }); applyTheme(); syncGeneral(); });
  $('#qSeg').addEventListener('click', e => { const b = e.target.closest('button'); if (b) $$('#qSeg button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); });
  $('#prov').addEventListener('click', e => {
    const b = e.target.closest('[data-p]'); if (!b) return;
    keepTyped();
    S.dlg.provider = b.dataset.p; fillProvider();
  });
  $('#keyEye').addEventListener('click', () => { const k = $('#apiKey'); k.type = k.type === 'password' ? 'text' : 'password'; });
  $('#keyHint').addEventListener('click', async e => {
    if (e.target.id !== 'forgetKey') return;
    const r = await safeCall('forget_key', S.dlg.provider);
    if (r) { S.keys = r.keys; fillProvider(); setMsg('#testMsg', T('ai.forgotten'), 'ok'); render(); }
  });
  $('#testConn').addEventListener('click', async () => {
    const p = S.dlg.provider;
    setMsg('#testMsg', T('ai.connecting'), 'busy');
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
    else if (S.pane === 'offline') { setMsg('#testMsg', T('set.needLang'), 'err'); return; }
    // Bagian AI selalu disimpan bila diisi, supaya API key untuk Rangkuman AI bisa disimpan dari tab mana pun.
    const p = S.dlg.provider, key = $('#apiKey').value.trim(), model = $('#modelName').value.trim(), url = $('#baseUrl').value.trim();
    if (S.pane === 'ai') {
      if (!key && !S.keys[p]) { setMsg('#testMsg', T('set.needKey'), 'err'); $('#apiKey').focus(); return; }
      if (p === 'other' && !url) { setMsg('#testMsg', T('set.needUrl'), 'err'); $('#advBox').open = true; return; }
      if (p === 'other' && !model) { setMsg('#testMsg', T('set.needModel'), 'err'); $('#advBox').open = true; return; }
    }
    if (S.pane === 'ai' || key || p !== S.set.provider) {
      const r = await safeCall('set_ai', p, key, model, url);
      if (!r || !r.ok) { setMsg('#testMsg', (r && r.error) || T('t.saveFail'), 'err'); return; }
      S.keys = r.keys; S.models = r.models; S.baseUrls = r.base_urls; S.set = r.settings;
    }
    saveSet(patch);
    closeDialogs(); render();
    toast(S.pane === 'ai' ? T('t.aiOn', { prov: provName(p) }) : T('t.offlineOn'));
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
    $('#supText').textContent = T(S.hasQris ? 'sup.text' : 'sup.textPending');
    $('#supDone').hidden = !S.hasQris;
    openDlg('dlgSupport');
  }
  $('#btnSupport').addEventListener('click', openSupport);
  $('#nudgeSupport').addEventListener('click', openSupport);
  $('#supDone').addEventListener('click', () => { closeDialogs(); saveSet({ supported: true }); $('#nudge').hidden = true; toast(T('t.thanks')); });

  // Tentang
  $('#btnAbout').addEventListener('click', () => { setMsg('#updMsg', ''); $('#getUpd').hidden = true; openDlg('dlgAbout'); });
  $('#openRepo').addEventListener('click', () => call('open_link', 'repo'));
  $('#chkUpd').addEventListener('click', async () => {
    setMsg('#updMsg', T('about.checking'), 'busy');
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
  const KINDS = ['poin', 'notulen', 'lengkap'];
  const KIND_LABEL = { poin: 'kind.poin', notulen: 'kind.notulen', lengkap: 'kind.lengkap' };
  const KIND_HINT = { poin: 'kind.poinHint', notulen: 'kind.notulenHint', lengkap: 'kind.lengkapHint' };
  const mmKey = currentKey;
  const mmCacheKey = () => `${mmKey()}|${S.mm.src}|${S.mm.src === 'ai' ? S.mm.kind : '-'}`;
  const mmTitle = () => { const k = mmKey(); if (k === 'ALL') return combinedName(); const it = findItem(k); return it ? baseName(it.display) : T('mm.title'); };

  let MM = null, shownMd = null, TR = null;
  const transformer = () => TR || (TR = new window.markmap.Transformer(window.markmap.builtInPlugins.filter(p => !/^(hljs|katex|npmUrl)$/.test(p.name))));
  /* markmap mengukur svg; jangan fit/render saat tersembunyi (ukuran nol membuat transform NaN) */
  const mmVisible = () => { const r = $('#mmSvg').getBoundingClientRect(); return r.width > 20 && r.height > 20; };
  const mmFit = () => { if (MM && mmVisible()) MM.fit(); };
  const fitSoon = () => setTimeout(mmFit, 410);
  const MM_OPTS = { duration: 350, spacingVertical: 8, paddingX: 10, autoFit: false };
  // HTML mentah dinetralkan, dan tautan dijadikan teks biasa: jendela aplikasi tidak boleh berpindah ke situs lain.
  // Jumlah baris tidak berubah, supaya nomor baris cabang (payload.lines dari markmap) tetap cocok dengan kerangka aslinya.
  const safeMd = md => md.replace(/!\[([^\]\n]*)\]\([^)\n]*\)/g, '$1').replace(/\[([^\]\n]+)\]\([^)\n]*\)/g, '$1').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  function renderMap() {
    const key = mmKey(), it = findItem(key), ai = S.mm.src === 'ai';
    $('#mmScope').textContent = key === 'ALL' ? T('mm.scopeAll', { n: S.items.length }) : T('mm.scope', { name: it ? it.display : '-' });
    $$('#mmSetup .opt').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.src === S.mm.src)));
    $$('#mmKind button').forEach(b => { b.setAttribute('aria-pressed', String(b.dataset.k === S.mm.kind)); b.disabled = !ai; });
    $('#mmKindGrp').classList.toggle('dim', !ai);
    $('#mmKindHint').textContent = ai ? T(KIND_HINT[S.mm.kind] || 'kind.poinHint') : T('mm.kindAiOnly');
    const words = key === 'ALL' ? S.items.reduce((a, i) => a + (i.words || 0), 0) : (it ? it.words : 0);
    const note = $('#mmNote'), p = S.set.provider;
    if (ai && !S.keys[p]) { note.className = 'note warn'; note.innerHTML = `${ic('alert')}<span>${T('mm.noteNoKey', { prov: esc(provName(p)), btn: `<button class="linkbtn" type="button" id="mmSetKey">${T('hint.enterKey')}</button>` })}</span>`; }
    else if (ai) { note.className = 'note warn'; note.innerHTML = `${ic('alert')}<span>${T('mm.noteSend', { words: T('stat.words', { n: words || 0 }), prov: esc(provName(p)) })}</span>`; }
    else { note.className = 'note ok'; note.innerHTML = `${ic('shield')}<span>${T('mm.noteLocal')}</span>`; }
    $('#mmGoText').textContent = T(ai ? 'mm.goAi' : 'mm.goStruct');
    $('#mmGo').disabled = !words && key !== 'ALL' && !(it && it.status === 'done');
    const ck = mmCacheKey(), md = S.mm.cache[ck], busy = S.mm.busy && S.mm.busyKey === ck;
    $('#mmSetup').hidden = !!md || busy;
    $('#mmBusy').hidden = !busy;
    $('#mmBusyText').textContent = S.mm.busyText || T('mm.busy');
    $('#mmReady').hidden = !md || busy;
    if (md && !busy) requestAnimationFrame(() => showMap(md));
  }
  function showMap(md) {
    $('#mmSrcTag').innerHTML = S.mm.src === 'ai' ? `${ic('spark')}${T('mm.srcAi', { kind: T(KIND_LABEL[S.mm.kind] || 'kind.poin') })}` : `${ic('grip')}${T('mm.struct')}`;
    $('#mmWarn').hidden = S.mm.src !== 'ai';
    $('#mmPlace').hidden = S.mm.src === 'ai';
    $$('#mmView button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === S.mm.view)));
    const asText = S.mm.view === 'text', taOn = asText && S.mm.edit, ta = $('#mmTa');
    $('#mmText').innerHTML = renderMd(md);
    $('#mmText').hidden = !asText || taOn;
    if (taOn && ta.hidden) ta.value = md;  // diisi saat baru dibuka; ketikan yang belum diterapkan tidak ditimpa
    ta.hidden = !taOn;
    syncMmEd();
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
    S.mm.busy = true; S.mm.busyKey = ck; S.mm.busyText = T(S.mm.src === 'ai' ? 'mm.busyAi' : 'mm.busyStruct');
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
      S.mm.cache[ck] = e.md; delete S.mm.undo[ck];
      if (S.mm.busyKey === ck) S.mm.busy = false;
    } else if (e.state === 'error') {
      S.mm.busy = false;
      toast(e.error || T('mm.fail'), 4200);
    }
    if (S.done && S.tab === 'map') renderMap();
  }

  /* ---------- edit mind map: ganti nama atau hapus cabang, atau ubah kerangkanya di tampilan Teks ---------- */
  // tiap cabang membawa rentang baris sumbernya dari markmap (payload.lines = "awal,akhir"), jadi yang diubah hanya baris itu
  const HEAD_RE = /^(\s{0,3}#{1,6}\s+)(.*?)(?:\s+#+)?\s*$/, ITEM_RE = /^(\s*(?:[-*+]|\d+[.)])\s+)(.*)$/;
  const lineText = l => { const m = l.match(HEAD_RE) || l.match(ITEM_RE); return m ? m[2] : l.trim(); };
  const withText = (l, t) => { const m = l.match(HEAD_RE) || l.match(ITEM_RE); return (m ? m[1] : l.match(/^\s*/)[0]) + t; };
  // cabang judul berakhir di judul berikutnya yang setingkat atau lebih tinggi; rentang butir daftar sudah mencakup anak-anaknya
  function branchEnd(L, s, e) {
    const lv = (L[s].match(/^\s{0,3}(#{1,6})\s/) || [])[1];
    if (!lv) return e;
    let j = s + 1;
    while (j < L.length && !((L[j].match(/^\s{0,3}(#{1,6})\s/) || [, '#######'])[1].length <= lv.length)) j++;
    return j;
  }
  let mmNode = null;  // cabang yang sedang diedit: { s, e, root }
  const mmTaDirty = () => !$('#mmTa').hidden && $('#mmTa').value !== (S.mm.cache[mmCacheKey()] || '');
  function syncMmEd() {
    const on = S.mm.edit, text = S.mm.view === 'text';
    $('#mmEdit').setAttribute('aria-pressed', String(on));
    $('#mmEdBar').hidden = !on;
    $('.mmstage').classList.toggle('editing', on);
    if (!on) return;
    $('#mmEdMsg').textContent = T(text ? 'mm.edHintText' : 'mm.edHint');
    $('#mmApply').hidden = !text; $('#mmApply').disabled = !mmTaDirty();
    $('#mmUndo').disabled = !(S.mm.undo[mmCacheKey()] || []).length;
  }
  // quiet: matikan tanpa menerapkan isi kotak teks (dipakai saat hasil diganti)
  function mmEditOff(quiet) {
    closeNodeEd();
    if (!quiet && mmTaDirty()) mmChange($('#mmTa').value);
    S.mm.edit = false; $('#mmTa').hidden = true;
    const md = S.mm.cache[mmCacheKey()];
    if (!quiet && md && S.done && S.tab === 'map') showMap(md); else syncMmEd();
  }
  function mmChange(md) {
    const ck = mmCacheKey(), old = S.mm.cache[ck];
    if (old == null || md === old) return;
    const u = S.mm.undo[ck] = S.mm.undo[ck] || []; u.push(old); if (u.length > 30) u.shift();
    mmCommit(md);
  }
  function mmUndo() { const u = S.mm.undo[mmCacheKey()]; if (!u || !u.length) return; closeNodeEd(); mmCommit(u.pop()); }
  async function mmCommit(md) {
    const key = mmKey(), src = S.mm.src, kind = S.mm.kind;
    S.mm.cache[mmCacheKey()] = md;
    mmRedraw(md);
    const r = await safeCall('update_summary', key, src, kind, md);  // ekspor dan pembukaan ulang memakai kerangka yang sudah diedit
    if (r && r.ok === false) toast(r.error || T('t.saveFail'));
  }
  // gambar ulang tanpa mengubah zoom
  function mmRedraw(md) {
    $('#mmText').innerHTML = renderMd(md);
    const ta = $('#mmTa'); if (!ta.hidden && ta.value !== md) ta.value = md;
    if (MM && mmVisible()) { shownMd = md; MM.setData(transformer().transform(safeMd(md)).root); }
    else shownMd = null;
    syncMmEd();
  }
  function openNodeEd(g, d, node) {
    const md = S.mm.cache[mmCacheKey()] || '', ed = $('#mmNodeEd'), inp = $('#mmNodeIn');
    mmNode = node;
    inp.value = lineText(md.split('\n')[node.s]);
    $('#mmRename').disabled = !inp.value.trim();
    $('#mmDelBranch').hidden = node.root;
    $('#mmNodeHint').textContent = T(node.root ? 'mm.rootOnly' : 'mm.delHint');
    ed.hidden = false;
    // letakkan di bawah cabang (atau di atasnya bila tidak muat), tetap di dalam area mind map
    const st = $('.mmstage').getBoundingClientRect(), r = g.getBoundingClientRect(), w = ed.offsetWidth, h = ed.offsetHeight;
    let y = r.bottom - st.top + 6;
    if (y + h > st.height - 8) y = Math.max(8, r.top - st.top - h - 6);
    ed.style.left = Math.max(8, Math.min(r.left - st.left, st.width - w - 8)) + 'px'; ed.style.top = y + 'px';
    inp.focus(); inp.select();
    if (MM && MM.setHighlight) MM.setHighlight(d);
  }
  function closeNodeEd() {
    if ($('#mmNodeEd').hidden) return;
    $('#mmNodeEd').hidden = true; mmNode = null;
    if (MM && MM.setHighlight) MM.setHighlight(null);
  }
  $('#mmSvg').addEventListener('click', e => {
    if (!S.mm.edit || !MM || e.target.closest('circle')) return;  // lingkaran tetap untuk melipat/membuka cabang
    const g = e.target.closest('g.markmap-node'); if (!g) return;
    const d = window.d3.select(g).datum(), lines = d && d.payload && d.payload.lines;
    const [s, en] = String(lines || '').split(',').map(Number), n = (S.mm.cache[mmCacheKey()] || '').split('\n').length;
    if (!lines || !(s >= 0 && s < n)) { toast(T('mm.noLine'), 3600); return; }
    openNodeEd(g, d, { s, e: en > s ? en : s + 1, root: d === MM.state.data || !String((d.state || {}).path || '').includes('.') });
  });
  $('#mmNodeIn').addEventListener('input', e => { $('#mmRename').disabled = !e.target.value.trim(); });
  $('#mmRename').addEventListener('click', () => {
    const n = mmNode, t = $('#mmNodeIn').value.replace(/\s+/g, ' ').trim(); if (!n || !t) return;
    const L = (S.mm.cache[mmCacheKey()] || '').split('\n'); L[n.s] = withText(L[n.s], t);
    closeNodeEd(); mmChange(L.join('\n'));
  });
  $('#mmDelBranch').addEventListener('click', () => {
    const n = mmNode; if (!n || n.root) return;
    const md = S.mm.cache[mmCacheKey()] || '';
    closeNodeEd(); mmChange(spliceLines(md, n.s, branchEnd(md.split('\n'), n.s, n.e), ''));
  });
  $('#mmNodeCancel').addEventListener('click', closeNodeEd);
  $('#mmNodeEd').addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.id === 'mmNodeIn') { e.preventDefault(); $('#mmRename').click(); }
    else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeNodeEd(); }
  });
  $('#mmEdit').addEventListener('click', () => {
    if (S.mm.edit) { mmEditOff(); return; }
    S.mm.edit = true;
    const md = S.mm.cache[mmCacheKey()]; if (md) showMap(md); else syncMmEd();
  });
  $('#mmEdDone').addEventListener('click', () => mmEditOff());
  $('#mmUndo').addEventListener('click', mmUndo);
  $('#mmApply').addEventListener('click', () => { if (mmTaDirty()) mmChange($('#mmTa').value); });
  $('#mmTa').addEventListener('input', syncMmEd);
  $('#mmTa').addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); $('#mmApply').click(); } });

  const syncFull = () => { $('#mmFull').textContent = T(win.classList.contains('mmfull') ? 'mm.unfull' : 'mm.full'); };
  function exitFull() {
    if (!win.classList.contains('mmfull')) return;
    closeStyle(true); closeNodeEd();
    win.classList.remove('mmfull'); syncFull();
    requestAnimationFrame(mmFit);
  }
  $$('#mmSetup .opt').forEach(b => b.addEventListener('click', () => { S.mm.src = b.dataset.src; renderMap(); }));
  $('#mmKind').addEventListener('click', e => { const b = e.target.closest('button'); if (b && !b.disabled) { S.mm.kind = b.dataset.k; renderMap(); } });
  $('#mmNote').addEventListener('click', e => { if (e.target.id === 'mmSetKey') openSettings('ai'); });
  $('#mmGo').addEventListener('click', genMap);
  $('#mmStop').addEventListener('click', () => { call('cancel_summary'); S.mm.busy = false; renderMap(); });
  $('#mmRedo').addEventListener('click', () => {
    call('forget_summary', mmKey(), S.mm.src, S.mm.kind);
    mmEditOff(true); delete S.mm.cache[mmCacheKey()]; delete S.mm.undo[mmCacheKey()]; shownMd = null; exitFull(); renderMap();
  });
  $('#mmView').addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    closeNodeEd(); if (mmTaDirty()) mmChange($('#mmTa').value);  // isi kotak teks diterapkan sebelum pindah tampilan
    S.mm.view = b.dataset.v; const md = S.mm.cache[mmCacheKey()]; if (md) showMap(md);
  });
  $('#mmIn').addEventListener('click', () => { if (MM && mmVisible()) MM.rescale(1.25); });
  $('#mmOut').addEventListener('click', () => { if (MM && mmVisible()) MM.rescale(0.8); });
  $('#mmFit').addEventListener('click', mmFit);
  $('#mmFold').addEventListener('click', () => { const st = S.mm.style; st.expand = st.expand === -1 ? 2 : -1; applyStyle(true); });
  $('#mmFull').addEventListener('click', () => {
    if (win.classList.contains('mmfull')) { exitFull(); return; }
    autoFull = false; closeNodeEd();
    win.classList.add('mmfull'); syncFull();
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
      toast(T('mm.pngBusy'));
      try { payload.png = await mmPng(4000); } catch (err) { console.error(err); toast(T('mm.pngFail')); return; }
    }
    const r = await safeCall('export_map', f, payload);
    if (r && r.ok) toast(T('t.saved', { name: r.name })); else if (r && !r.cancelled) toast(r.error || T('t.saveFail'));
  });

  /* ---------- gaya mind map: warna dan lebar per sub ---------- */
  const PALETTES = {
    pelangi: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
    urai: ['#2e5be6', '#0b7f74', '#d9480f', '#7b4fd6', '#c2255c', '#1d6f42', '#b7791f', '#0e7490'],
    lembut: ['#6c8ef5', '#4fb3a9', '#f08c5a', '#a98be8', '#e07aa5', '#7fb069', '#e2b45a', '#5ab0d8'],
    mono: ['#64748b'],
  };
  const LV_LABEL = ['sty.lv0', 'sty.sub1', 'sty.sub2', 'sty.sub3', 'sty.lv4'];
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
    st.widths.forEach((w, i) => { $('#stW' + i).value = w; $('#stWv' + i).textContent = fmt(w) + ' px'; });
    $('#stMaxW').value = st.maxWidth; $('#stMaxWv').textContent = fmt(st.maxWidth) + ' px';
    $('#stGap').value = st.spacingH; $('#stGapv').textContent = fmt(st.spacingH) + ' px';
    $('#mmFold').textContent = T(st.expand === -1 ? 'mm.fold' : 'mm.unfold');
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
    if (!win.classList.contains('mmfull')) { win.classList.add('mmfull'); syncFull(); autoFull = true; }
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
  // tabel warna per sub digambar dari JS; dibuat ulang saat bahasa berganti
  function buildLevels() {
    $('#stLevels').innerHTML = LV_LABEL.map((k, i) => {
      const l = T(k);
      return `<tr><td>${esc(l)}</td><td><input type="color" id="stC${i}" aria-label="${esc(T('sty.colorOf', { l }))}"></td><td><input type="range" id="stW${i}" min="0.5" max="8" step="0.25" aria-label="${esc(T('sty.widthOf', { l }))}"></td><td class="val" id="stWv${i}"></td></tr>`;
    }).join('');
  }
  buildLevels();
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
    if (!text) throw new Error('empty mind map');
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
    const orient = T(P.orient === 'land' ? 'pdf.landLow' : 'pdf.portLow');
    $('#pdfInfo').innerHTML = `<b>${P.size === 'F4' ? 'F4 (folio)' : P.size} ${orient}</b>${w} × ${h} mm · ${T('pdf.pages', { n: pages })}<br>${T('pdf.file', { name: esc(`${mmTitle()} - mind map.pdf`) })}`;
  }
  async function openPdf() {
    if (!MM || !shownMd) { toast(T('pdf.needMap')); return; }
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
    setMsg('#pdfMsg', T('pdf.preparing'), 'busy'); $('#pdfSave').disabled = true;
    let png;
    try { png = await mmPng(P.size === 'A3' ? 6000 : 4500); }
    catch (err) { console.error(err); setMsg('#pdfMsg', T('pdf.imgFail'), 'err'); $('#pdfSave').disabled = false; return; }
    const r = await safeCall('export_map', 'pdf', { md, title: mmTitle(), style: S.mm.style, ai: S.mm.src === 'ai', png, pdf: P });
    $('#pdfSave').disabled = false;
    if (r && r.ok) { closeDialogs(); toast(T('pdf.saved', { name: r.name })); }
    else if (r && r.cancelled) setMsg('#pdfMsg', '');
    else setMsg('#pdfMsg', (r && r.error) || T('pdf.fail'), 'err');
  });

  /* ---------- tema: Sistem (ikut Windows, langsung berubah), Terang, atau Gelap ---------- */
  const mq = matchMedia('(prefers-color-scheme: dark)');
  const applyTheme = () => { const t = themeName(); win.dataset.mode = t === 'system' ? (mq.matches ? 'dark' : 'light') : t; };
  applyTheme();
  try { mq.addEventListener('change', applyTheme); } catch (_) { mq.addListener(applyTheme); }
  new ResizeObserver(() => { if (MM && S.tab === 'map' && S.done) debounce('fit', mmFit, 200); }).observe($('.mmstage'));

  /* ---------- bahasa tampilan ---------- */
  // teks yang berasal dari data aplikasi (versi, pengembang, repo, nama penerima QRIS)
  function fillApp() {
    const a = S.app || {}, m = a.merchant || '';
    $('#tagline').textContent = a.tagline || T('tagline');
    $('#sbRight').textContent = T('sb.right', { name: a.name || 'Urai App', version: String(a.version || '') });
    $('#aboutVer').textContent = T('about.version', { v: String(a.version || '') }) + (a.commit ? ' · ' + a.commit.slice(0, 7) : '');
    $('#aboutCredit').textContent = T('about.credit', { year: String(a.year || ''), dev: a.developer || '' });
    $('#aboutRepo').textContent = a.repo ? a.repo.replace(/^https:\/\//, '') : T('about.repoNone');
    $('#openRepo').hidden = !a.repo;
    $('#payeeName').textContent = m;
    $('#payeeCheck').innerHTML = T('sup.check', { name: `<b>${esc(m)}</b>` });
    $('#qrImg').alt = T('sup.qrAlt', { name: m });
  }
  function applyLang(l) {
    S.lang = I18N[l] ? l : 'en';
    document.documentElement.lang = S.lang;
    applyI18n();
    buildLevels();
    if (S.mm.style) syncStyleUI();
    syncFull();
    fillApp();
    disarmClear(); closeNodeEd(); syncMmEd();
    S.pvShown = '';
    if (!$('#dlgSettings').hidden) {
      keepTyped(); buildChips($$('#langChips input:checked').map(i => i.value));
      fillProvider(); syncGeneral(); setPane(S.pane);
    }
  }

  /* ---------- mulai ---------- */
  async function boot() {
    applyI18n();
    try { await waitBridge(); }
    catch (_) { $('#boot').textContent = T('boot.noBridge'); return; }
    let b;
    try { b = await call('init'); }
    catch (e) { console.error(e); $('#boot').textContent = T('boot.failed'); return; }
    S.app = b.app; S.set = b.settings; S.providers = b.providers; S.models = b.models; S.baseUrls = b.base_urls; S.keys = b.keys;
    S.tess = b.tesseract; S.defaultDir = b.default_dir; S.items = b.items || []; S.hasQris = b.has_qris; S.hasSamples = b.has_samples;
    S.mm.src = S.set.mm_src || (S.keys[S.set.provider] ? 'ai' : 'struct');
    S.mm.kind = KINDS.includes(S.set.mm_kind) ? S.set.mm_kind : 'poin';
    S.mm.style = loadStyle(S.set.mm_style);
    $('#tryWrap').hidden = !S.hasSamples;
    applyTheme();
    applyLang(S.set.lang);
    renderNow();
    $('#boot').hidden = true;
    pollLoop();
    call('ready').catch(() => {});
    if (S.items.length) toast(T('t.added', { n: S.items.length }));
  }
  boot();
})();
