/* தொல்காப்பியம் reader — hash-routed single page, no dependencies.
   Layout: அதிகாரம் tabs on top, இயல் list on the left, sutras on the right.
   Data: window.THOL (structure + sutras), window.THOL_DICT (entries + key index). */
(function () {
  'use strict';

  const D = window.THOL, DICT = window.THOL_DICT, NOTES = window.THOL_NOTES || {};
  const $ = (sel, root) => (root || document).querySelector(sel);
  const main = $('#main'), side = $('#side'), tabs = $('#tabs'), tip = $('#tip');
  if (!D || !DICT) { main.innerHTML = '<p class="muted">data/thol.js and data/dict.js are missing. Run <code>python3 scripts/build.py</code>.</p>'; return; }

  // ------------------------------------------------------------ indexes
  const sutraByG = new Map(D.sutras.map(s => [s.g, s]));
  const atikById = new Map(), iyalById = new Map();
  D.atikarams.forEach(a => { atikById.set(a.id, a); a.iyals.forEach(i => { i.a = a.id; iyalById.set(i.id, i); }); });
  const entryById = new Map(DICT.entries.map(e => [e.id, e]));
  const TOTAL = D.sutras.length;
  const IYAL_COUNT = D.atikarams.reduce((n, a) => n + (a.id === 'payiram' ? 0 : a.iyals.length), 0);
  const DEFAULT_ATIK = D.atikarams.find(a => a.id !== 'payiram').id;

  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const nfc = s => (s || '').normalize('NFC').trim();

  $('#stats').textContent = `${TOTAL} நூற்பாக்கள் · ${IYAL_COUNT} இயல்கள் · 3 அதிகாரங்கள் · அகராதி ${DICT.entries.length} சொற்கள்`;

  // ------------------------------------------------------------ helpers
  function entriesFor(key) { return (DICT.index[key] || []).map(id => entryById.get(id)).filter(Boolean); }
  const num = s => s.n ? s.n : 'பாயிரம்';   // sequence number; the prologue is unnumbered
  function locOf(s) { const iy = iyalById.get(s.i), a = atikById.get(s.a); return { a, iy, label: s.n ? `${iy.name} ${s.n}` : iy.name }; }
  function setTitle(t) { document.title = (t ? t + ' · ' : '') + 'தொல்காப்பியம்'; }
  function mainType(e) { const t = e.senses.find(s => s.type); return t ? t.type : ''; }

  function markText(escaped, q) {
    if (!q) return escaped;
    const i = escaped.indexOf(esc(q));
    if (i < 0) return escaped;
    return escaped.slice(0, i) + '<mark>' + escaped.slice(i, i + q.length) + '</mark>' + escaped.slice(i + q.length);
  }
  function renderVerse(s, opts) {
    const hl = opts && opts.hl;
    return '<div class="verse">' + s.tokens.map(line =>
      '<div class="line">' + line.map(t => {
        let surf = esc(t[0]);
        if (hl) surf = markText(surf, hl);
        return t[1] ? `<span class="w" data-k="${esc(t[1])}" tabindex="0">${surf}</span>` : `<span class="w">${surf}</span>`;
      }).join(' ') + '</div>').join('') + '</div>';
  }
  // transcription marks: ⟨?⟩ uncertain reading, ⟨sic⟩ misprint kept as printed
  function noteText(t) {
    return esc(t).replace(/⟨\?⟩/g, '<span class="unsure" title="ஐயமான வாசிப்பு · uncertain reading">?</span>')
      .replace(/⟨sic⟩/g, '<span class="sic" title="அச்சில் உள்ளபடி · as printed">sic</span>');
  }
  // sutra title as printed in the 1961 edition
  function cardTitle(s) {
    const t = (NOTES[s.g] || {}).tt;
    return t ? `<h2 class="sutra-title">${noteText(t)}</h2>` : '';
  }
  function renderNotes(s) {
    const n = NOTES[s.g];
    if (!n) return '';
    const other = (no, label) => no && no !== String(s.n) ? ` · ${label} ${esc(no)}` : '';
    let html = '';
    if (n.tc) {
      html += `<section class="comm comm-ta">
        <h2>தெளிவுரை</h2>
        <p class="src">புலியூர்க் கேசிகன் தெளிவுரை, 1961${other(n.te, 'அப்பதிப்பில் நூற்பா')}</p>
        ${n.tt ? `<h3>${noteText(n.tt)}</h3>` : ''}
        ${n.tc.map(p => `<p>${noteText(p)}</p>`).join('')}
      </section>`;
    }
    if (n.en || n.tr) {
      html += `<section class="comm comm-en" lang="en">
        <h2>English</h2>
        <p class="src">V. Murugan, <i>Tolkāppiyam in English</i>, 2001${other(n.ee, 'sutra')}</p>
        ${n.et ? `<h3>${esc(n.et)}</h3>` : ''}
        ${n.tr ? `<div class="translit">${n.tr.map(l => `<div>${esc(l)}</div>`).join('')}</div>` : ''}
        ${n.en ? `<div class="trans">${n.en.map(l => `<div>${esc(l)}</div>`).join('')}</div>` : ''}
      </section>`;
    }
    return `<div class="comms">${html}</div>`;
  }
  function crumbs(parts) {
    return '<nav class="crumbs">' + parts.map((p, i) => (i ? '<span class="sep">›</span>' : '') +
      (p.href ? `<a href="${p.href}">${esc(p.text)}</a>` : `<span>${esc(p.text)}</span>`)).join('') + '</nav>';
  }

  // ------------------------------------------------------------ tabs (அதிகாரம்) + sidebar (இயல்)
  function renderTabs(activeId) {
    tabs.innerHTML = D.atikarams.map(a => {
      const n = a.iyals.reduce((x, i) => x + i.count, 0);
      const href = a.id === 'payiram' ? '#/s/1' : `#/a/${a.id}`;
      return `<a href="${href}" class="${a.id === activeId ? 'active' : ''}">${esc(a.name)}${a.id === 'payiram' ? '' : `<span class="n">${n}</span>`}</a>`;
    }).join('') + `<span class="gap"></span><a href="#/d" class="dict ${activeId === 'dict' ? 'active' : ''}">அகராதி</a>`;
  }
  function renderIyalSide(a, activeIyal) {
    side.innerHTML = `<h2>${esc(a.name)} · இயல்கள்</h2><ul class="side-list">` +
      a.iyals.map(i => `<li><a href="#/i/${i.id}" class="${i.id === activeIyal ? 'active' : ''}"><span class="idx">${i.id}</span><span class="name">${esc(i.name)}</span><span class="n">${i.count}</span></a></li>`).join('') + '</ul>';
  }

  // ------------------------------------------------------------ book views
  function viewAtikaram(id) {
    const a = atikById.get(id); if (!a) return notFound();
    viewIyal(a.iyals[0].id);
  }
  function viewIyal(id, curG) {
    const iy = iyalById.get(id); if (!iy) return notFound();
    const a = atikById.get(iy.a);
    setTitle(iy.name); renderTabs(a.id); renderIyalSide(a, iy.id);
    const list = [];
    for (let g = iy.first_g; g <= iy.last_g; g++) {
      const s = sutraByG.get(g);
      list.push(`<article class="sutra-card ${g === curG ? 'cur' : ''}" id="g${g}" data-g="${g}" title="நூற்பாவையும் உரையையும் காண சொடுக்கவும்"><div class="num"><a href="#/s/${g}" title="நூற்பா ${num(s)} – தனியாகக் காண">${num(s)}</a></div><div class="body">${cardTitle(s)}${renderVerse(s)}</div></article>`);
    }
    main.innerHTML = crumbs([{ text: a.name, href: `#/a/${a.id}` }, { text: iy.name }]) +
      `<div class="page-head"><h1 class="page-title">${esc(iy.name)}</h1><span class="page-sub">${iy.count} நூற்பாக்கள் · முழு நூலில் ${iy.first_g}–${iy.last_g}</span></div>` +
      '<p class="hint">அடிக்கோடிட்ட சொல்லின் மேல் சுட்டியை வைத்தால் பொருள் தோன்றும்; சொடுக்கினால் நிலைக்கும். நூற்பாவின் மற்ற பகுதியைச் சொடுக்கினால் அது உரையுடன் தனியாகத் திறக்கும்.</p>' +
      list.join('');
  }
  function viewSutra(g) {
    const s = sutraByG.get(g); if (!s) return notFound();
    const { a, iy } = locOf(s);
    setTitle(`${iy.name} ${num(s)}`); renderTabs(a.id); renderIyalSide(a, iy.id);
    const prev = sutraByG.get(g - 1), next = sutraByG.get(g + 1);
    const pagerLink = (t, cls, dir) => t ? `<a class="${cls}" href="#/s/${t.g}"><span class="dir">${dir}</span><span class="lbl">${esc(locOf(t).label)}</span><span class="prev-text">${esc(t.lines[0])}</span></a>` : '<span class="spacer"></span>';
    let strip = '';
    for (let k = iy.first_g; k <= iy.last_g; k++) strip += `<a href="#/s/${k}" class="${k === g ? 'cur' : ''}">${num(sutraByG.get(k))}</a>`;
    main.innerHTML = crumbs([{ text: a.name, href: `#/a/${a.id}` }, { text: iy.name, href: `#/i/${iy.id}` }, { text: `நூற்பா ${num(s)}` }]) +
      `<article class="sutra-view">
        <div class="head"><h1>${esc(iy.name)} · நூற்பா ${num(s)}</h1><span class="gnum">முழு நூலில் ${g}/${TOTAL}</span></div>
        ${renderVerse(s)}
      </article>
      ${renderNotes(s)}
      <div class="pager">${pagerLink(prev, 'prev', '← முன்')}${pagerLink(next, 'next', 'அடுத்து →')}</div>
      <div class="numstrip">${strip}</div>
      <p class="kbd-hint"><kbd>←</kbd> <kbd>→</kbd> முன் / அடுத்த நூற்பா · <kbd>/</kbd> தேடு · <kbd>Esc</kbd> மூடு · <a href="#/i/${iy.id}">இயல் முழுவதும்</a></p>`;
  }

  // ------------------------------------------------------------ dictionary
  const TAMIL_ORDER = 'அஆஇஈஉஊஎஏஐஒஓஔஃகஙசஞடணதநபமயரலவழளறனஜஷஸஹ';
  function firstLetter(lemma) { const c = lemma.charAt(0); return TAMIL_ORDER.includes(c) ? c : '•'; }
  const letterGroups = (() => {
    const m = new Map();
    DICT.entries.forEach(e => { const L = firstLetter(e.lemma); if (!m.has(L)) m.set(L, []); m.get(L).push(e); });
    return [...m.entries()].sort((x, y) => TAMIL_ORDER.indexOf(x[0]) - TAMIL_ORDER.indexOf(y[0]));
  })();
  function renderDictSide(curLetter, q) {
    side.innerHTML = `<form class="lookup" id="lookupform"><input type="search" id="lookup" placeholder="சொல்லைத் தேடு…" value="${esc(q || '')}" autocomplete="off" spellcheck="false" aria-label="அகராதியில் சொல் தேடு"></form>
      <h2>எழுத்து வரிசை</h2><div class="letters">` +
      letterGroups.map(([L, es]) => `<a href="#/d/l/${encodeURIComponent(L)}" class="${L === curLetter ? 'cur' : ''}" title="${es.length}">${esc(L)}</a>`).join('') + '</div>';
    $('#lookupform').addEventListener('submit', ev => { ev.preventDefault(); const v = nfc($('#lookup').value); location.hash = v ? '#/d/w/' + encodeURIComponent(v) : '#/d'; });
  }
  function headwordList(es, q) {
    return `<ul class="headwords">${es.map(e => `<li><a href="#/d/e/${e.id}">${q ? markText(esc(e.head), q) : esc(e.head)}</a><span class="t">${esc(mainType(e))}</span></li>`).join('')}</ul>`;
  }
  function viewDict(letter) {
    if (!letter) letter = letterGroups[0][0];
    const grp = letterGroups.find(x => x[0] === letter);
    setTitle('அகராதி ' + letter); renderTabs('dict'); renderDictSide(letter);
    main.innerHTML = crumbs([{ text: 'அகராதி', href: '#/d' }, { text: letter }]) +
      `<div class="page-head"><h1 class="page-title">அகராதி · ${esc(letter)}</h1><span class="page-sub">${grp ? grp[1].length : 0} சொற்கள் · மொத்தம் ${DICT.entries.length}</span></div>` +
      (grp ? headwordList(grp[1]) : '<p class="muted">இல்லை</p>');
  }
  function lookupEntries(q) {
    const exact = entriesFor(q), seen = new Set(exact.map(e => e.id)), starts = [], contains = [];
    DICT.entries.forEach(e => {
      if (seen.has(e.id)) return;
      if (e.lemma.startsWith(q) || e.keys.some(k => k.startsWith(q))) starts.push(e);
      else if (e.lemma.includes(q) || e.keys.some(k => k.includes(q)) || e.senses.some(s => s.meaning.includes(q))) contains.push(e);
    });
    return { exact, rest: starts.concat(contains) };
  }
  function viewDictWord(q) {
    q = nfc(q); setTitle('அகராதி: ' + q); renderTabs('dict'); renderDictSide('', q);
    if (!q) return viewDict('');
    const { exact, rest } = lookupEntries(q);
    main.innerHTML = crumbs([{ text: 'அகராதி', href: '#/d' }, { text: q }]) +
      `<div class="page-head"><h1 class="page-title">“${esc(q)}”</h1><span class="page-sub">${exact.length + rest.length} சொற்கள்</span></div>` +
      (exact.length ? exact.map(e => `<article class="card entry" style="margin-bottom:14px">${renderEntryFull(e)}</article>`).join('') : '') +
      (rest.length ? `<div class="results"><h2>ஒத்த சொற்கள் · ${rest.length}</h2>${headwordList(rest.slice(0, 200), q)}</div>` : '') +
      (!exact.length && !rest.length ? '<p class="muted">அகராதியில் இல்லை.</p>' : '');
  }
  function viewEntry(id) {
    const e = entryById.get(id); if (!e) return notFound();
    const L = firstLetter(e.lemma);
    setTitle(e.head); renderTabs('dict'); renderDictSide(L);
    main.innerHTML = crumbs([{ text: 'அகராதி', href: '#/d' }, { text: L, href: `#/d/l/${encodeURIComponent(L)}` }, { text: e.head }]) +
      `<article class="card entry">${renderEntryFull(e)}</article>`;
  }
  function refHtml(sn) {
    if (!sn.ref) return '';
    if (sn.ref_g) { const t = sutraByG.get(sn.ref_g); const { label } = locOf(t); return `<span class="ref"><a href="#/s/${sn.ref_g}" title="${esc(t.lines[0])}">${esc(sn.ref)}</a> → ${esc(label)}</span>`; }
    return `<span class="ref">${esc(sn.ref)}</span>`;
  }
  function senseHtml(sn) {
    return `<div class="sense">${sn.type ? `<span class="wtype">${esc(sn.type)}</span>` : ''}${sn.no ? `<span class="no muted">${esc(sn.no)}.</span>` : ''}<span class="meaning">${esc(sn.meaning)}</span>${refHtml(sn)}</div>`;
  }
  function renderEntryFull(e) {
    return `<h1>${esc(e.head)}${e.lemma !== e.head ? `<span class="lemma">${esc(e.lemma)}</span>` : ''}</h1>` + e.senses.map(senseHtml).join('');
  }

  // ------------------------------------------------------------ search (top bar)
  function viewSearch(q) {
    q = nfc(q); setTitle('தேடல்: ' + q); renderTabs(''); $('#q').value = q;
    if (!q) { side.innerHTML = ''; main.innerHTML = '<p class="muted">தேடற்சொல்லை உள்ளிடுங்கள்.</p>'; return; }
    const { exact, rest } = lookupEntries(q);
    const dictHits = exact.concat(rest).slice(0, 60);
    const sutraHits = D.sutras.filter(s => s.lines.join(' ').includes(q));
    const perAtik = D.atikarams.map(a => ({ a, n: sutraHits.filter(s => s.a === a.id).length })).filter(x => x.n);
    side.innerHTML = `<h2>தேடல்</h2><ul class="side-list">` +
      perAtik.map(x => `<li><a href="#/q/${encodeURIComponent(q)}/${x.a.id}"><span class="name">${esc(x.a.name)}</span><span class="n">${x.n}</span></a></li>`).join('') +
      `<li><a href="#/d/w/${encodeURIComponent(q)}"><span class="name">அகராதி</span><span class="n">${exact.length + rest.length}</span></a></li></ul>`;
    const shown = sutraHits.slice(0, 300);
    main.innerHTML = `<div class="page-head"><h1 class="page-title">“${esc(q)}”</h1><span class="page-sub">${sutraHits.length} நூற்பாக்கள் · ${exact.length + rest.length} அகராதிச் சொற்கள்</span></div><div class="results">` +
      (dictHits.length ? `<h2>அகராதி</h2>${headwordList(dictHits, q)}` : '') +
      `<h2>நூற்பாக்கள்${sutraHits.length > 300 ? ' · முதல் 300' : ''}</h2>` +
      (shown.length ? shown.map(s => { const { a, iy } = locOf(s); return `<a class="result" href="#/s/${s.g}"><div class="where">${esc(a.name)} › ${esc(iy.name)} › ${num(s)}</div>${renderVerse(s, { hl: q })}</a>`; }).join('') : '<p class="muted">எதுவும் இல்லை.</p>') +
      '</div>';
  }
  function viewSearchAtik(q, aid) {
    q = nfc(q); const a = atikById.get(aid); if (!a) return viewSearch(q);
    setTitle('தேடல்: ' + q); renderTabs(a.id); $('#q').value = q;
    const hits = D.sutras.filter(s => s.a === aid && s.lines.join(' ').includes(q));
    const perIyal = a.iyals.map(i => ({ i, n: hits.filter(s => s.i === i.id).length })).filter(x => x.n);
    side.innerHTML = `<h2>${esc(a.name)} · தேடல்</h2><ul class="side-list"><li><a href="#/q/${encodeURIComponent(q)}"><span class="name">எல்லா அதிகாரமும்</span></a></li>` +
      perIyal.map(x => `<li><a href="#/i/${x.i.id}"><span class="idx">${x.i.id}</span><span class="name">${esc(x.i.name)}</span><span class="n">${x.n}</span></a></li>`).join('') + '</ul>';
    main.innerHTML = `<div class="page-head"><h1 class="page-title">“${esc(q)}” · ${esc(a.name)}</h1><span class="page-sub">${hits.length} நூற்பாக்கள்</span></div><div class="results">` +
      hits.slice(0, 300).map(s => { const { iy } = locOf(s); return `<a class="result" href="#/s/${s.g}"><div class="where">${esc(iy.name)} › ${num(s)}</div>${renderVerse(s, { hl: q })}</a>`; }).join('') + '</div>';
  }

  function notFound() { setTitle(''); renderTabs(''); side.innerHTML = ''; main.innerHTML = '<h1 class="page-title">பக்கம் இல்லை</h1><p><a href="#/">முகப்பிற்குத் திரும்பு</a></p>'; }

  // ------------------------------------------------------------ gloss popup: hover preview, click to pin
  let tipTimer = null, tipWord = null, pinned = false;
  function tipHtml(es, full) {
    const body = es.slice(0, full ? es.length : 2).map(e => {
      const head = `<div class="head"><a href="#/d/e/${e.id}" title="அகராதியில் காண">${esc(e.head)}</a>${e.lemma !== e.head ? `<span class="lemma">${esc(e.lemma)}</span>` : ''}</div>`;
      if (full) return `<div class="ent">${head}${e.senses.map(senseHtml).join('')}</div>`;
      const sn = e.senses[0], more = e.senses.length - 1;
      const m = sn.meaning.length > 150 ? sn.meaning.slice(0, 150) + '…' : sn.meaning;
      return `<div class="ent">${head}<div class="m">${sn.type ? `<span class="wtype">${esc(sn.type)}</span>` : ''}${esc(m)}</div>${more > 0 ? `<div class="more">+${more} பொருள்கள்</div>` : ''}</div>`;
    }).join('');
    return (full ? '<button type="button" class="tip-close" aria-label="மூடு">&times;</button>' : '') + body +
      (!full && es.length > 2 ? `<div class="more">மேலும் ${es.length - 2} சொற்கள்…</div>` : '') +
      (full ? '' : '<div class="more">சொடுக்கினால் முழுப் பொருளும் நிலைக்கும்</div>');
  }
  function placeTip(el) {
    const r = el.getBoundingClientRect(), tw = tip.offsetWidth, th = tip.offsetHeight;
    const left = Math.min(Math.max(12, r.left), window.innerWidth - tw - 12);
    let top = r.bottom + 8;
    if (top + th > window.innerHeight - 8 && r.top - th - 8 > 0) top = r.top - th - 8;
    tip.style.left = left + 'px'; tip.style.top = top + 'px';
  }
  function showTip(el, full) {
    const es = entriesFor(el.dataset.k); if (!es.length) return;
    clearTimeout(tipTimer);
    if (tipWord && tipWord !== el) tipWord.classList.remove('active');
    tipWord = el; el.classList.add('active');
    pinned = !!full;
    tip.classList.toggle('pinned', pinned);
    tip.innerHTML = tipHtml(es, full);
    tip.hidden = false;
    tip.scrollTop = 0;
    placeTip(el);
  }
  function hideTip(delay, force) {
    clearTimeout(tipTimer);
    if (pinned && !force) return;
    tipTimer = setTimeout(() => { tip.hidden = true; pinned = false; tip.classList.remove('pinned'); if (tipWord) tipWord.classList.remove('active'); tipWord = null; }, delay || 0);
  }
  document.addEventListener('mouseover', ev => {
    if (pinned) return;
    const w = ev.target.closest('.w[data-k]');
    if (w) { showTip(w, false); return; }
    if (ev.target.closest('#tip')) clearTimeout(tipTimer);
  });
  document.addEventListener('mouseout', ev => {
    if (pinned) return;
    if (ev.target.closest('.w[data-k]') || ev.target.closest('#tip')) {
      const to = ev.relatedTarget;
      if (to && (to.closest('#tip') || to === tipWord)) return;
      hideTip(140);
    }
  });
  document.addEventListener('focusin', ev => { if (pinned) return; const w = ev.target.closest('.w[data-k]'); if (w) showTip(w, false); });
  document.addEventListener('focusout', ev => { if (!pinned && ev.target.closest('.w[data-k]')) hideTip(100); });
  document.addEventListener('click', ev => {
    const w = ev.target.closest('.w[data-k]');
    if (w) { ev.preventDefault(); if (pinned && tipWord === w) { hideTip(0, true); } else showTip(w, true); return; }
    if (ev.target.closest('.tip-close')) { hideTip(0, true); return; }
    if (pinned && !ev.target.closest('#tip')) { hideTip(0, true); return; }
    const card = ev.target.closest('.sutra-card[data-g]');
    if (card && !ev.target.closest('a') && !String(window.getSelection() || '')) location.hash = '#/s/' + card.dataset.g;
  });
  document.addEventListener('keydown', ev => {
    const inField = /^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName);
    if (ev.key === 'Escape') { hideTip(0, true); if (inField) ev.target.blur(); return; }
    if (inField || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === '/') { ev.preventDefault(); $('#q').focus(); $('#q').select(); return; }
    if (ev.key === 'Enter' && ev.target.matches('.w[data-k]')) { ev.preventDefault(); showTip(ev.target, true); return; }
    const m = location.hash.match(/^#\/s\/(\d+)$/);
    if (m) {
      const g = +m[1];
      if (ev.key === 'ArrowLeft' && sutraByG.has(g - 1)) location.hash = '#/s/' + (g - 1);
      if (ev.key === 'ArrowRight' && sutraByG.has(g + 1)) location.hash = '#/s/' + (g + 1);
    }
  });
  window.addEventListener('scroll', () => { if (!tip.hidden && !pinned) hideTip(0); }, { passive: true });
  window.addEventListener('resize', () => { if (!tip.hidden && tipWord) placeTip(tipWord); });

  // ------------------------------------------------------------ top search + router
  $('#searchform').addEventListener('submit', ev => { ev.preventDefault(); const q = nfc($('#q').value); location.hash = q ? '#/q/' + encodeURIComponent(q) : '#/'; });

  function route() {
    hideTip(0, true);
    const parts = location.hash.replace(/^#\/?/, '').split('/').map(p => { try { return decodeURIComponent(p); } catch (e) { return p; } });
    const [r, x, y] = parts;
    if (!r) viewAtikaram(DEFAULT_ATIK);
    else if (r === 'a') viewAtikaram(x);
    else if (r === 'i') viewIyal(x);
    else if (r === 's') viewSutra(+x);
    else if (r === 'd') { if (x === 'e') viewEntry(+y); else if (x === 'w') viewDictWord(y); else viewDict(x === 'l' ? y : ''); }
    else if (r === 'q') { if (y) viewSearchAtik(x, y); else viewSearch(x); }
    else notFound();
    if (r !== 'q') $('#q').value = '';
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  route();
})();
