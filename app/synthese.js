/* ACTU — Synthèse de recherche par un agent IA, sur le modèle de l'épreuve de synthèse de textes de la BCE (ESCP, HEC).
   On choisit 1 à 5 publications dans l'onglet Recherche ; « Synthèse » ouvre une demande GitHub pré-remplie, que l'on
   valide. Le robot (robot/synthese.py) lit les textes, rédige fiches, synthèse et dialogue critique avec l'IA libre et
   gratuite, chiffre le résultat avec le code de lecture ; l'application le récupère et l'affiche.
   Un article : fiche de lecture, résumé et regard critique. Plusieurs : la fiche de chacun, une synthèse de 300 mots
   (± 10 %) — une question générale, trois sous-questions qui confrontent tous les auteurs —, relue par un « jury »,
   puis les articles se répondent et se critiquent. */
'use strict';

const Synthese = (() => {
  const REPO = 'thias-user/actu';
  const RESULT = (id) => `https://raw.githubusercontent.com/${REPO}/main/app/data/syntheses/${id}.bin`;
  const MAX = 5;
  const h = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const key = (p) => (p.url || p.title || '').toLowerCase();
  const ref = (p) => `${p.authors || 'auteur non précisé'} (${p.year || 's. d.'}), « ${p.title} »${p.venue ? ', ' + p.venue : ''}`;
  // un mot : groupe de lettres ou de chiffres séparé par une espace ou une apostrophe (« l’homme » = 2) ; mot composé = 1
  const words = (t) => (String(t).replace(/aujourd[’']hui/gi, 'aujourdhui').replace(/[’']/g, ' ').match(/[\p{L}\p{N}]+(?:-[\p{L}\p{N}]+)*/gu) || []).length;
  let pollTimer = null;

  /* ------------------------------------------------------------ sélection */
  const selected = () => store.get('synth-sel', []);
  const pending = () => store.get('synth-wait', []);
  function isSelected(p) { return selected().some((x) => key(x) === key(p)); }
  function toggle(p) {
    let sel = selected();
    if (sel.some((x) => key(x) === key(p))) sel = sel.filter((x) => key(x) !== key(p));
    else if (sel.length >= MAX) { toast(`${MAX} articles au plus par synthèse`); return; }
    else sel = sel.concat([{ title: p.title, authors: p.authors, year: p.year, venue: p.venue, url: p.url, pdf: p.pdf, abstract: p.abstract }]);
    store.set('synth-sel', sel);
    bar();
  }
  /** Barre en bas de l'onglet Recherche : articles choisis, synthèses en préparation, synthèses gardées. */
  function bar() {
    const el = document.getElementById('rs-bar');
    if (!el) return;
    const sel = selected(), wait = pending(), hist = store.get('synth-hist', []);
    const parts = [];
    if (wait.length) parts.push(`<button class="btn" data-sy="waiting">⏳ ${wait.length} synthèse${wait.length > 1 ? 's' : ''} en préparation</button>`);
    if (sel.length) {
      parts.push(`<span>${sel.length} article${sel.length > 1 ? 's' : ''} choisi${sel.length > 1 ? 's' : ''}</span>
        <button class="btn" data-sy="clear">Vider</button><button class="btn primary" data-sy="start">${sel.length > 1 ? 'Synthèse et comparaison' : 'Synthèse'}</button>`);
    } else if (!wait.length) {
      parts.push(`<span class="small">Choisissez 1 à ${MAX} articles (＋ Synthèse) : un agent IA en fait une synthèse sur le modèle de l’épreuve de la BCE</span>`);
    }
    if (hist.length && !sel.length) parts.push(`<button class="btn" data-sy="history">Mes synthèses (${hist.length})</button>`);
    el.innerHTML = parts.join('');
    el.hidden = false;
    document.querySelectorAll('[data-pick]').forEach((b) => {
      const on = sel.some((x) => key(x) === b.dataset.pick);
      b.setAttribute('aria-pressed', String(on));
      b.textContent = on ? '✓ Choisi' : '＋ Synthèse';
    });
    if (wait.length) poll(); else { clearTimeout(pollTimer); pollTimer = null; }
  }

  /* ------------------------------------------------------------ demande au robot */
  function start() {
    const sel = selected();
    if (!sel.length) return;
    if (!reader.code()) { toast('Saisissez d’abord votre code de lecture dans Réglages : la synthèse est chiffrée avec lui.', 5000); return; }
    const id = new Date().toISOString().slice(0, 10) + '-' + Math.random().toString(36).slice(2, 8);
    const papers = sel.map((p) => ({ title: p.title, authors: p.authors, year: p.year, venue: p.venue, url: p.url, pdf: p.pdf,
      abstract: p.url && /10\.\d{4,9}\//.test(p.url) ? '' : (p.abstract || '').slice(0, 600) }));  // le robot relit les résumés par le DOI
    const body = `Demande envoyée par ACTU (onglet Recherche). Validez avec « Submit new issue » : le robot fait la synthèse puis ferme cette demande.\n\n\`\`\`json\n${JSON.stringify({ id, papers }, null, 1)}\n\`\`\``;
    const title = `Synthèse ACTU ${id} — ${sel.length} article${sel.length > 1 ? 's' : ''}`;
    const url = `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
    store.set('synth-wait', pending().concat([{ id, papers, asked: Date.now() }]));
    store.set('synth-sel', []);
    bar();
    window.open(url, '_blank', 'noopener');
    waiting();
  }

  async function decrypt(buf) {
    const k = await reader.getKey();
    let plain;
    try { plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: buf.slice(0, 12) }, k, buf.slice(12)); } catch { throw new Error('badcode'); }
    const stream = new Blob([plain]).stream().pipeThrough(new DecompressionStream('gzip'));
    return JSON.parse(await new Response(stream).text());
  }
  /** Regarde chaque minute si le robot a fini ; une synthèse prête passe dans « Mes synthèses ». */
  async function check() {
    const wait = pending();
    let changed = false;
    for (const w of wait) {
      try {
        const res = await fetch(RESULT(w.id) + '?t=' + Math.floor(Date.now() / 60000), { cache: 'no-store' });
        if (!res.ok) continue;
        const job = await decrypt(new Uint8Array(await res.arrayBuffer()));
        const hist = store.get('synth-hist', []).filter((x) => x.id !== job.id);
        hist.unshift(job);
        store.set('synth-hist', hist.slice(0, 15));
        store.set('synth-wait', pending().filter((x) => x.id !== w.id));
        changed = true;
        toast(job.error ? 'La synthèse n’a pas pu être faite' : 'Synthèse prête · onglet Recherche', 5000);
        if (document.querySelector('.synth-wait')) showResult(job);
      } catch (e) {
        if (e.message === 'badcode') { toast('Synthèse illisible : le code de lecture ne correspond pas'); }
      }
    }
    if (changed) bar();
    if (document.querySelector('.synth-wait') && !changed) waiting(true);
  }
  function poll() {
    if (pollTimer) return;
    const tick = async () => { await check(); pollTimer = pending().length ? setTimeout(tick, 60000) : null; };
    pollTimer = setTimeout(tick, 1500);
  }

  /* ------------------------------------------------------------ affichage */
  function waiting(refresh) {
    const wait = pending();
    if (!wait.length) { bar(); return; }
    const html = `<div class="sheet-content synth synth-wait">
      <div class="meta"><b>Synthèse par l’IA</b><span class="dot">en préparation</span></div>
      <h1>Le robot prépare ${wait.length > 1 ? 'vos synthèses' : 'votre synthèse'}</h1>
      <ol class="synth-steps">
        <li class="done"><i>1</i><span>Dans GitHub, validez la demande avec <b>« Submit new issue »</b> (une seule fois).</span></li>
        <li class="cur"><i>2</i><span>Le robot lit les textes en accès libre, rédige les fiches, la synthèse sur le modèle de la BCE, la fait relire et corriger par un « jury », puis fait dialoguer les articles. L’IA gratuite répond une fois toutes les 45 secondes : comptez 10 à 20 minutes.</span></li>
        <li><i>3</i><span>La synthèse s’affiche ici toute seule (ACTU vérifie chaque minute) et reste dans « Mes synthèses ».</span></li>
      </ol>
      ${wait.map((w) => `<div class="synth-fiche"><b>Demandée ${h(new Date(w.asked).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }))}</b>
        <ul>${w.papers.map((p) => `<li>${h(ref(p))}</li>`).join('')}</ul>
        <button class="btn" data-sy="reopen" data-id="${h(w.id)}">Rouvrir la demande GitHub</button><button class="btn" data-sy="cancel" data-id="${h(w.id)}">Ne plus attendre</button></div>`).join('')}
      <p class="synth-note">Vous pouvez fermer cette fenêtre et continuer à lire ACTU.</p>
    </div>`;
    if (refresh) { const box = document.querySelector('.synth-wait'); if (box) box.outerHTML = html; }
    else openSheet(html);
    waiting.last = wait;
  }
  const list = (xs) => (xs?.length ? `<ul>${xs.map((x) => `<li>${h(x)}</li>`).join('')}</ul>` : '');
  function showResult(job) {
    if (!job) return;
    const n = job.papers.length;
    let main = '';
    if (job.error) {
      main = `<h1>La synthèse n’a pas pu être faite</h1><p class="synth-err">${h(job.error)}</p><p>Vous pouvez la redemander : choisissez de nouveau les articles.</p>`;
    } else {
      const o = job.out;
      const fiches = job.papers.map((p, i) => ({ p, f: o['fiche' + i] || {}, src: o['read' + i] || {} }));
      const fichesHTML = fiches.map(({ p, f, src }) => `<details class="synth-fiche"><summary><b>${h(f.auteur)}</b> — ${h(p.title)}</summary>
        <p class="small">${h(ref(p))} · lu à partir du ${h(src.full ? 'texte intégral' : 'résumé des auteurs')}</p>
        <p><b>Thèse.</b> ${h(f.these)}</p><p>${h(f.resume)}</p>
        ${f.arguments?.length ? `<p><b>Idées clés</b></p>${list(f.arguments)}` : ''}
        <p><b>Démarche.</b> ${h(f.methode)}</p><p><b>Limites.</b> ${h(f.limites)}</p>
        ${p.url ? `<a class="btn" href="${href(p.url)}" target="_blank" rel="noopener">Ouvrir l’article</a>` : ''}</details>`).join('');
      if (n === 1) {
        const a = o.one || {};
        main = `<h1>${h(a.titre || fiches[0].f.these)}</h1>
          <div class="synth-text"><p>${h(a.resume)}</p></div><p class="small">${words(a.resume || '')} mots</p>
          <h2>Regard critique</h2>
          <p><b>Ce qui est solide</b></p>${list(a.forces)}<p><b>Ce qui fragilise ou limite</b></p>${list(a.limites)}
          ${a.portee ? `<p><b>Portée.</b> ${h(a.portee)}</p>` : ''}${a.questions?.length ? `<p><b>Questions ouvertes</b></p>${list(a.questions)}` : ''}
          <h2>Fiche de lecture</h2>${fichesHTML}`;
      } else {
        const r = o.review || {}, d = o.dialogue || {}, paras = String(r.text || '').split(/\n\s*\n/).filter((x) => x.trim());
        main = `<h1>${h(o.plan?.problematique || 'Synthèse')}</h1>
          <p class="small">Synthèse sur le modèle de l’épreuve de la BCE · ${r.words} mots${r.jury?.note != null ? ` · note du jury (IA) : ${h(r.jury.note)}/20` : ''}${r.errs?.length ? ' · encore perfectible : ' + h(r.errs.join(' ')) : ''}</p>
          <div class="synth-text">${paras.map((x) => `<p>${h(x)}</p>`).join('')}</div>
          ${r.jury ? `<details><summary>L’avis du jury (IA)</summary>${r.jury.points_forts?.length ? `<p><b>Points forts</b></p>${list(r.jury.points_forts)}` : ''}${r.jury.defauts?.length ? `<p><b>Encore perfectible</b></p>${list(r.jury.defauts)}` : ''}</details>` : ''}
          <h2>Les articles se répondent et se critiquent</h2>
          ${(d.reponses || []).map((x) => `<p><b>${h(x.auteur)}.</b> ${h(x.critique)}</p>`).join('')}
          ${d.accords?.length ? `<p><b>Points d’accord</b></p>${list(d.accords)}` : ''}
          ${d.desaccords?.length ? `<p><b>Désaccords</b></p>${list(d.desaccords)}` : ''}
          ${d.angles_morts?.length ? `<p><b>Angles morts</b></p>${list(d.angles_morts)}` : ''}
          ${d.questions?.length ? `<p><b>Questions ouvertes</b></p>${list(d.questions)}` : ''}
          <h2>Fiches de lecture</h2>${fichesHTML}`;
      }
    }
    openSheet(`<div class="sheet-content synth">
      <div class="meta"><b>Synthèse par l’IA</b><span class="dot">${n} article${n > 1 ? 's' : ''}</span><span class="dot">${h(new Date(job.finished || Date.now()).toLocaleDateString('fr-FR'))}</span></div>
      ${main}
      <p class="synth-note">Rédigé par ${h(job.model || 'une IA libre')} à partir des textes en accès libre ou, à défaut, des résumés des auteurs. Une IA peut se tromper : vérifiez sur les articles avant de citer.</p>
      <div class="acts"><button class="btn" data-sy="copy">Copier le texte</button><button class="btn" data-sy="history">Mes synthèses</button></div>
    </div>`);
  }
  function history() {
    const hist = store.get('synth-hist', []);
    openSheet(`<div class="sheet-content synth"><h1>Mes synthèses</h1>
      ${hist.length ? hist.map((j, i) => `<button class="synth-item" data-sy="open" data-i="${i}"><b>${h(j.error ? 'Synthèse impossible' : j.out?.plan?.problematique || j.out?.one?.titre || j.papers[0].title)}</b>
        <small>${j.papers.length} article${j.papers.length > 1 ? 's' : ''} · ${h(new Date(j.finished).toLocaleDateString('fr-FR'))}</small></button>`).join('') : '<p class="empty">Aucune synthèse pour l’instant.</p>'}
    </div>`);
  }

  document.addEventListener('click', (ev) => {
    const pick = ev.target.closest('[data-pick]');
    if (pick) {
      const p = (window.rsPapers || new Map()).get(pick.dataset.pick);
      if (p) toggle(p);
      return;
    }
    const b = ev.target.closest('[data-sy]');
    if (!b) return;
    const a = b.dataset.sy;
    if (a === 'start') start();
    else if (a === 'clear') { store.set('synth-sel', []); bar(); }
    else if (a === 'waiting') { waiting(); check(); }
    else if (a === 'reopen') {
      const w = pending().find((x) => x.id === b.dataset.id);
      if (w) { store.set('synth-sel', w.papers); store.set('synth-wait', pending().filter((x) => x.id !== w.id)); start(); }
    } else if (a === 'cancel') { store.set('synth-wait', pending().filter((x) => x.id !== b.dataset.id)); bar(); waiting(true); if (!pending().length) closeSheet(); }
    else if (a === 'history') history();
    else if (a === 'open') showResult(store.get('synth-hist', [])[+b.dataset.i]);
    else if (a === 'copy') {
      const t = document.querySelector('.synth')?.innerText || '';
      navigator.clipboard?.writeText(t).then(() => toast('Texte copié'), () => toast('Copie impossible'));
    }
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden && pending().length) check(); });

  return { bar, key, isSelected, words };
})();
