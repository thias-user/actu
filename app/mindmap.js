/* ACTU — « En un coup d'œil » : schéma de pensée animé de l'article, au format rectangle, avec plein écran.
   Les cases (où, quand, qui, quoi, comment, pourquoi, liens, pour comprendre, et après) apparaissent une à une ;
   la caméra s'approche de chacune pour qu'on la lise, puis recule sur le schéma entier. Touchez une case du schéma
   entier pour l'agrandir. En plein écran, le schéma reste droit ; le bouton « Paysage » le fait pivoter. */
'use strict';

const MindMap = (() => {
  const W = 1320;            // largeur du plan (unités du schéma) ; la hauteur suit le contenu
  const PAD = 32, GAP = 96;  // marges et espace entre les rangées (pour les traits)
  const KIND = {
    ou: ['#38bdf8', '📍', 'Où ?'], quand: ['#22d3ee', '🗓️', 'Quand ?'], qui: ['#a78bfa', '👤', 'Qui ?'], quoi: ['#fbbf24', '⚡', 'Quoi ?'],
    comment: ['#a3e635', '🛠️', 'Comment ?'], pourquoi: ['#f87171', '❓', 'Pourquoi ?'], liens: ['#f472b6', '🔗', 'Liens'],
    ctx: ['#34d399', '📚', 'Pour comprendre'], critique: ['#e879f9', '🧐', 'Regard critique'], apres: ['#fb923c', '➜', 'Et après ?'],
  };
  const CRIT = { opinion: '💬', titre: '🏷️', sources: '📰', recoupe: '✅', medias: '🗞️', anonyme: '🕶️', doute: '❔', version: '⚖️',
    voix: '🎙️', termes: '🔤', chiffres: '🔢', angles: '🕳️', anciennete: '⏳', suivi: '🧵', perspective: '🔭' };
  const NATURE = { oppose: ['#f87171', 'contre'], accuse: ['#fb923c', 'accuse'], negocie: ['#facc15', 'négocie avec'],
    aide: ['#60a5fa', 'soutient'], allie: ['#4ade80', 'allié de'], depend: ['#cbd5e1', 'lié à'] };
  const VERB = { ATTAQUE: ['💥', 'Attaque'], NEGOCIE: ['🤝', 'Négociation'], VOTE: ['🗳️', 'Vote'], GAGNE: ['🏆', 'Victoire'], PERD: ['📉', 'Défaite'],
    ACCORD: ['✍️', 'Accord'], JUSTICE: ['⚖️', 'Justice'], ARRESTATION: ['🚔', 'Arrestation'], ENQUETE: ['🔎', 'Enquête'], DRAME: ['🚨', 'Drame'],
    MOBILISATION: ['📣', 'Mobilisation'], ALERTE: ['⚠️', 'Alerte'], DECOUVERTE: ['🔬', 'Découverte'], LANCEMENT: ['🚀', 'Lancement'],
    HAUSSE: ['📈', 'Hausse'], BAISSE: ['📉', 'Baisse'], AIDE: ['🤲', 'Aide'], HOMMAGE: ['🕯️', 'Hommage'], ANNONCE: ['📢', 'Annonce'],
    DEMISSION: ['🚪', 'Démission'], SANTE: ['🩺', 'Santé'] };
  const CONS = { hausse: '📈', baisse: '📉', alerte: '⚠️', election: '🗳️', loi: '📜', argent: '💶', sante: '🩺', guerre: '⚔️', paix: '🕊️',
    justice: '⚖️', climat: '🌍', emploi: '👷', autre: '➜' };
  const PROFILE = { pouvoir: ['🏛️', 'Pouvoir'], economie: ['💶', 'Économie'], societe: ['👥', 'Société'], lecture: ['🔎', 'En résumé'] };
  const ROLE = { politician: 'Responsable politique', soldier: 'Militaires', judge: 'Justice', police: 'Police', athlete: 'Sport', racer: 'Pilote',
    scientist: 'Recherche', doctor: 'Santé', business: 'Entreprise', musician: 'Musique', artist: 'Culture', protester: 'Militants',
    citizen: 'Habitants', firefighter: 'Secours', worker: 'Salariés', student: 'Élèves', teacher: 'Enseignants', hacker: 'Pirates informatiques',
    farmer: 'Agriculteurs', astronaut: 'Espace', priest: 'Religion', journalist: 'Médias', model: 'Mode' };
  const MONTHS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
  const SPECIAL_FLAG = { eu: '🇪🇺', nato: '🛡️', latam: '🌎' };
  const h = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const flag = (c) => SPECIAL_FLAG[c] || (/^[a-z]{2}$/.test(c || '') ? String.fromCodePoint(...[...c.toUpperCase()].map((x) => 127397 + x.charCodeAt(0))) : '');
  const shortDate = (iso) => { const [y, m, d] = iso.split('-').map(Number); return `${d === 1 ? '1er' : d} ${MONTHS[m - 1]}${y !== new Date().getFullYear() ? ' ' + y : ''}`; };
  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
  const wikiLink = (w) => (w?.u ? `<a class="mm-src" href="${h(w.u)}" target="_blank" rel="noopener">Wikipédia${w.l && w.l !== 'fr' ? ` (${h(w.l)})` : ''}</a>` : '');
  const head = (k, extra = '') => `<div class="mm-h" style="--k:${KIND[k][0]}">${KIND[k][1]} ${KIND[k][2]}${extra}</div>`;
  const ICONS = {
    prev: '<svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg>', next: '<svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>',
    pause: '<svg viewBox="0 0 24 24"><path d="M9 5v14M15 5v14"/></svg>', play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
    again: '<svg viewBox="0 0 24 24"><path d="M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4"/></svg>',
    full: '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    rotate: '<svg viewBox="0 0 24 24"><rect x="7" y="3" width="10" height="18" rx="2"/><path d="M2 14a8 8 0 0 0 5 6M22 10a8 8 0 0 0-5-6"/></svg>',
  };

  /* ------------------------------------------------------------ contenu : une case par question */
  function cards(story, profiles) {
    const out = [];
    const p = story.place || {};
    const [label, date] = p.label ? [p.label, p.date] : String(story.captions?.ou || '').split(' · ');
    out.push({ id: 'ou', kind: 'ou', step: 'ou', row: 'b', html: `${head('ou')}
      ${p.wiki?.img ? `<img class="mm-pic" src="${h(p.wiki.img)}" alt="" referrerpolicy="no-referrer" loading="lazy">` : ''}
      <b class="mm-t">${h(flag(p.country))} ${h(label || 'Dans le monde')}</b>
      ${p.wiki?.d ? `<p class="mm-d">${h(p.wiki.d)}</p>` : ''}
      ${p.wiki?.x ? `<p class="mm-x">${h(p.wiki.x)}</p>` : ''}` });

    // quand : dates citées par l'article, articles liés des autres jours, et le jour de l'article
    const rel = story.related || [];
    const times = (story.when || []).map((w) => ({ k: w.k, d: w.d, html: h(w.t) }))
      .concat(rel.map((r, i) => ({ k: r.d, d: shortDate(r.d), html: `<button class="mm-item" data-rel="${i}"><span><b>${h(r.s)}</b> · ${h(r.t)}</span></button>` })));
    if (p.iso || date) times.push({ k: (p.iso || '9999') + '~', d: p.iso ? shortDate(p.iso) : date, html: '<b>Date de l’article</b>', now: true });
    times.sort((a, b) => (a.k < b.k ? -1 : a.k > b.k ? 1 : 0));
    out.push({ id: 'quand', kind: 'quand', step: 'quand', row: 'b', html: `${head('quand')}
      <ol class="mm-tl">${times.map((t) => `<li${t.now ? ' class="now"' : ''}><time>${h(t.d)}</time><div>${t.html}</div></li>`).join('')}</ol>` });

    const actors = story.actors || [];
    actors.forEach((a, i) => {
      const w = a.wiki;
      const name = w?.t || a.name;
      const sub = w?.d || (a.kind === 'pays' ? 'Pays' : ROLE[a.role] || '');
      const place = a.kind === 'pays' || a.kind === 'org' || a.group;
      const avatar = w?.img ? `<img src="${h(w.img)}" alt="" referrerpolicy="no-referrer" loading="lazy">` : `<span>${(place && flag(a.country)) || (a.group ? '👥' : '👤')}</span>`;
      out.push({ id: 'qui-' + i, kind: 'qui', step: 'qui-' + i, row: 'a', html: `${head('qui', actors.length > 1 ? ` <small>${i + 1}/${actors.length}</small>` : '')}
        <div class="mm-who"><div class="mm-av">${avatar}</div><div><b class="mm-t">${h(name)}</b>${sub ? `<small>${h(sub)}</small>` : ''}</div></div>
        ${a.does ? `<p class="mm-does"><span>Dans cette histoire</span>${h(a.does)}</p>` : ''}
        ${w?.x ? `<p class="mm-x">${h(w.x)}</p>` : ''}${wikiLink(w)}` });
    });

    const act = story.action || {};
    const [icon, verb] = VERB[act.verb] || ['📰', 'Actualité'];
    const who = actors[act.who]?.wiki?.t || actors[act.who]?.name;
    const target = act.target >= 0 ? (actors[act.target]?.wiki?.t || actors[act.target]?.name) : '';
    out.push({ id: 'quoi', kind: 'quoi', step: 'quoi', row: 'b', html: `${head('quoi')}
      <div class="mm-verb"><span>${icon}</span>${h(verb)}${who ? ` <small>${h(who)}${target ? ` → ${h(target)}` : ''}</small>` : ''}</div>
      <p class="mm-q">${h(story.captions?.quoi || '')}</p>` });

    const how = story.how || [];
    if (how.length) {
      out.push({ id: 'comment', kind: 'comment', step: 'comment', row: 'c', html: `${head('comment')}
        ${how.map((x) => `<p class="mm-c"><i>${x.k === 'chiffre' ? '🔢' : '🛠️'}</i><span>${h(x.t)}</span></p>`).join('')}` });
    }
    const why = story.why;
    if (why) {
      let body;
      if (why.facts?.length) {
        body = `<div class="mm-sub">D’après les sources</div>${why.facts.map((f) => `<p class="mm-c"><i>📌</i><span>${h(f)}</span></p>`).join('')}`;
      } else if (why.hyp?.length) {
        body = `<div class="mm-warn">Hypothèses — les sources n’expliquent pas pourquoi. Pistes possibles, à vérifier :</div>
          <ol class="mm-hyp">${why.hyp.map((x) => `<li>${h(x)}</li>`).join('')}</ol>`;
      } else {
        body = '<p class="mm-x">Les sources n’expliquent pas pourquoi, et elles donnent trop peu d’éléments pour avancer des hypothèses sérieuses.</p>';
      }
      out.push({ id: 'pourquoi', kind: 'pourquoi', step: 'pourquoi', row: 'c', html: `${head('pourquoi', why.hyp?.length ? ' <small class="mm-badge">Hypothèses</small>' : '')}${body}` });
    }
    const links = (story.links || []).filter((l) => actors[l.from] && actors[l.to]);
    if (links.length) {
      out.push({ id: 'liens', kind: 'liens', step: 'liens', row: 'c', html: `${head('liens')}
        ${links.map((l) => { const [c, t] = NATURE[l.nature] || NATURE.depend; const n = (x) => actors[x].wiki?.t || actors[x].name;
          return `<div class="mm-rel"><b>${h(n(l.from))}</b><span style="--c:${c}">${h(t)} →</span><b>${h(n(l.to))}</b></div>`; }).join('')}
        ${story.captions?.liens && !/^Sujet aussi traité/.test(story.captions.liens) ? `<p class="mm-x">${h(story.captions.liens)}</p>` : ''}` });
    }

    // pour comprendre : le sujet (Wikipédia) et le pays en bref (pouvoir, économie, société)
    const ctx = story.context, also = (story.sources || []).slice(1);
    const prof = story.profile && profiles?.[story.profile];
    if (ctx || prof || also.length) {
      out.push({ id: 'ctx', kind: 'ctx', step: 'ctx', row: 'd', html: `${head('ctx')}
        ${ctx ? `<b class="mm-t">${h(ctx.t)}</b><p class="mm-x">${h(ctx.x)}</p>${wikiLink(ctx)}` : ''}
        ${prof ? `<div class="mm-sub">${h(flag(prof.code))} ${h(cap(prof.nom))} en bref</div>
          ${prof.lignes.map((l) => { const [ic, t] = PROFILE[l.k] || ['•', '']; return `<p class="mm-c mm-prof"><i>${ic}</i><span><b>${h(t)}.</b> ${h(l.t)}</span></p>`; }).join('')}
          <p class="mm-s">Sources : ${h(prof.sources)}.</p>` : ''}
        ${also.length ? `<p class="mm-s">Aussi traité par ${h(also.join(', '))}.</p>` : ''}` });
    }
    // regard critique : comment l'information est construite (sources, doutes, versions, angle, recoupement)
    const crit = story.critique || [];
    if (crit.length) {
      out.push({ id: 'critique', kind: 'critique', step: 'critique', row: 'd', html: `${head('critique')}
        ${crit.map((c) => `<div class="mm-c mm-crit"><i>${CRIT[c.k] || '•'}</i><div>${h(c.t)}
          ${c.q ? `<q class="mm-quote">${h(c.q)}</q>` : ''}
          ${c.l ? `<ul class="mm-titles">${c.l.map((x) => `<li><b>${h(x.s)}</b> « ${h(x.t)} »</li>`).join('')}</ul>` : ''}</div></div>`).join('')}` });
    }
    const cons = story.consequences?.length ? story.consequences : [{ text: story.captions?.consequences || '', kind: 'autre' }];
    out.push({ id: 'apres', kind: 'apres', step: 'apres', row: 'e', html: `${head('apres')}
      ${cons.filter((c) => c.text).map((c) => `<p class="mm-c"><i>${CONS[c.kind] || '➜'}</i><span>${h(c.text)}</span></p>`).join('')}` });
    return { list: out, links };
  }

  /* ------------------------------------------------------------ mise en page du plan et traits */
  // écran étroit (téléphone tenu droit) : les cases l'une sous l'autre, assez larges pour être lues sans loupe
  function column(world, list) {
    const CW = 470, pad = 18, gap = 58;
    for (const c of list) { c.w = CW - 2 * pad; c.el.style.width = c.w + 'px'; }
    for (const c of list) c.h = c.el.offsetHeight;
    let y = pad;
    const paths = [];
    list.forEach((c, i) => {
      c.x = pad; c.y = y;
      if (i) paths.push(`<path class="mm-line" data-step="${c.step}" pathLength="1" d="M${CW / 2} ${y - gap + 6} L${CW / 2} ${y - 6}"/>`);
      y += c.h + gap;
    });
    const H = y - gap + pad;
    for (const c of list) { c.el.style.left = c.x + 'px'; c.el.style.top = c.y + 'px'; }
    world.style.width = CW + 'px';
    world.style.height = H + 'px';
    world.querySelector('svg').outerHTML = `<svg class="mm-svg" width="${CW}" height="${H}" style="width:${CW}px;height:${H}px" viewBox="0 0 ${CW} ${H}" aria-hidden="true">${paths.join('')}</svg>`;
    return { W: CW, H };
  }

  function layout(world, list, links, narrow) {
    if (narrow) return column(world, list);
    world.style.width = W + 'px';
    const byId = Object.fromEntries(list.map((c) => [c.id, c]));
    const rowOf = (r) => list.filter((c) => c.row === r);
    const rowA = rowOf('a');
    const lower = ['c', 'd', 'e'].map(rowOf).filter((r) => r.length);  // rangées sous le « Quoi »
    const n = rowA.length;
    const aw = n <= 2 ? 440 : n === 3 ? 400 : 300, gx = n === 4 ? 28 : 36;
    rowA.forEach((c) => { c.w = aw; });
    const [ou, quoi, quand] = ['ou', 'quoi', 'quand'].map((id) => byId[id]);
    ou.w = 300; quoi.w = 480; quand.w = 380;
    for (const row of lower) {
      const cw = Math.min(680, (W - 2 * PAD - (row.length - 1) * 40) / row.length);
      row.forEach((c) => { c.w = cw; });
    }
    for (const c of list) c.el.style.width = c.w + 'px';
    for (const c of list) c.h = c.el.offsetHeight;
    const arcs = links.length ? 84 : 0;
    const yA = PAD + arcs;
    const totalA = n * aw + (n - 1) * gx;
    rowA.forEach((c, i) => { c.x = (W - totalA) / 2 + i * (aw + gx); c.y = yA; });
    const hA = n ? Math.max(...rowA.map((c) => c.h)) : 0;
    const yB = n ? yA + hA + GAP : PAD;
    const gapB = (W - 2 * PAD - ou.w - quoi.w - quand.w) / 2;  // où | quoi | quand, espacés également
    ou.x = PAD; quoi.x = PAD + ou.w + gapB; quand.x = quoi.x + quoi.w + gapB;
    [ou, quoi, quand].forEach((c) => { c.y = yB; });
    const hB = Math.max(ou.h, quoi.h, quand.h);
    let y = yB + hB + GAP;
    for (const row of lower) {
      const total = row.reduce((s, c) => s + c.w, 0) + (row.length - 1) * 40;
      row.forEach((c, i) => { c.x = (W - total) / 2 + row.slice(0, i).reduce((s, x) => s + x.w + 40, 0); c.y = y; });
      y += Math.max(...row.map((c) => c.h)) + GAP;
    }
    const H = y - GAP + PAD;
    for (const c of list) { c.el.style.left = c.x + 'px'; c.el.style.top = c.y + 'px'; }
    world.style.height = H + 'px';

    // traits : qui → quoi, où ↔ quoi ↔ quand, quoi → comment / pourquoi / liens → pour comprendre / regard critique → et après
    const paths = [];
    const curve = (x1, y1, x2, y2, step) => paths.push(`<path class="mm-line" data-step="${step}" pathLength="1" d="M${x1} ${y1} C${x1} ${(y1 + y2) / 2} ${x2} ${(y1 + y2) / 2} ${x2} ${y2}"/>`);
    const side = (x1, y1, x2, y2, step) => paths.push(`<path class="mm-line" data-step="${step}" pathLength="1" d="M${x1} ${y1} C${(x1 + x2) / 2} ${y1} ${(x1 + x2) / 2} ${y2} ${x2} ${y2}"/>`);
    const qx = quoi.x + quoi.w / 2;
    const mid = (c) => c.x + c.w / 2;
    rowA.forEach((c) => curve(mid(c), c.y + c.h, qx, quoi.y, 'quoi'));
    const yy = (a) => a.y + Math.min(a.h, quoi.h) / 2;
    side(ou.x + ou.w, yy(ou), quoi.x, yy(ou), 'quoi');
    side(quoi.x + quoi.w, yy(quand), quand.x, yy(quand), 'quoi');
    // chaque case part de la case la plus proche de la rangée du dessus (le « Quoi » pour la première)
    let above = [quoi];
    for (const row of lower) {
      row.forEach((c, i) => {
        const from = above.reduce((best, x) => (Math.abs(mid(x) - mid(c)) < Math.abs(mid(best) - mid(c)) ? x : best), above[0]);
        const spread = above.length === 1 ? (i - (row.length - 1) / 2) * 60 : 0;
        curve(Math.min(from.x + from.w - 20, Math.max(from.x + 20, mid(from) + spread)), from.y + from.h, mid(c), c.y, c.step);
      });
      above = row;
    }
    const labels = [];
    links.forEach((l, k) => {
      const a = byId['qui-' + l.from], b = byId['qui-' + l.to];
      if (!a || !b) return;
      const [color, text] = NATURE[l.nature] || NATURE.depend;
      const x1 = mid(a) + 14 * k, x2 = mid(b) - 14 * k, top = yA - 30 - 22 * k - Math.min(30, Math.abs(x2 - x1) / 30);
      paths.push(`<path class="mm-line mm-arc" data-step="liens" pathLength="1" style="stroke:${color}" d="M${x1} ${yA} C${x1} ${top - 26} ${x2} ${top - 26} ${x2} ${yA - 8}"/>`);
      paths.push(`<path class="mm-tip" data-step="liens" style="fill:${color}" d="M${x2 - 9} ${yA - 20} L${x2 + 9} ${yA - 20} L${x2} ${yA - 4} Z"/>`);
      const mx = (x1 + x2) / 2, my = top - 6, tw = text.length * 11 + 26;
      labels.push(`<g class="mm-tag" data-step="liens"><rect x="${mx - tw / 2}" y="${my - 17}" width="${tw}" height="32" rx="16" style="fill:${color}"/><text x="${mx}" y="${my + 5}">${h(text)}</text></g>`);
    });
    world.querySelector('svg').outerHTML = `<svg class="mm-svg" width="${W}" height="${H}" style="width:${W}px;height:${H}px" viewBox="0 0 ${W} ${H}" aria-hidden="true">${paths.join('')}${labels.join('')}</svg>`;
    return { W, H };
  }

  /* ------------------------------------------------------------ lecteur */
  let fsOpen = null;          // lecteur actuellement en plein écran

  function mount(root, story, opts = {}) {
    const { list, links } = cards(story, opts.profiles);
    const steps = [];
    const has = (id) => list.some((c) => c.id === id);
    steps.push({ key: 'ou', label: 'Où ?' }, { key: 'quand', label: 'Quand ?' });
    list.filter((c) => c.kind === 'qui').forEach((c, i, all) => steps.push({ key: c.id, label: all.length > 1 ? `Qui ? ${i + 1}/${all.length}` : 'Qui ?' }));
    steps.push({ key: 'quoi', label: 'Quoi ?' });
    if (has('comment')) steps.push({ key: 'comment', label: 'Comment ?' });
    if (has('pourquoi')) steps.push({ key: 'pourquoi', label: 'Pourquoi ?' });
    if (has('liens')) steps.push({ key: 'liens', label: 'Liens' });
    if (has('ctx')) steps.push({ key: 'ctx', label: 'Pour comprendre' });
    if (has('critique')) steps.push({ key: 'critique', label: 'Regard critique' });
    steps.push({ key: 'apres', label: 'Et après ?' });
    steps.push({ key: 'all', label: 'Vue d’ensemble' });
    const order = Object.fromEntries(steps.map((s, i) => [s.key, i]));

    root.classList.add('mm');
    root.style.setProperty('--mc', opts.color || '#fbbf24');
    root.innerHTML = `<div class="mm-stage" role="region" aria-label="Schéma de l’article, étape par étape">
        <div class="mm-world" style="width:${W}px"><svg></svg>${list.map((c) => `<section class="mm-node mm-${c.kind}" data-id="${c.id}" data-step="${c.step}" style="--k:${KIND[c.kind][0]}">${c.html}</section>`).join('')}</div>
        <div class="mm-bars">${steps.map(() => '<i></i>').join('')}</div>
        <div class="mm-top"><button class="mm-btn mm-pill" data-mm="rotate" aria-label="Passer en paysage">${ICONS.rotate}<span>Paysage</span></button><button class="mm-btn" data-mm="close" aria-label="Quitter le plein écran">${ICONS.close}</button></div>
        <div class="mm-ctl">
          <button class="mm-btn" data-mm="prev" aria-label="Étape précédente">${ICONS.prev}</button>
          <button class="mm-btn" data-mm="play" aria-label="Pause">${ICONS.pause}</button>
          <button class="mm-btn" data-mm="next" aria-label="Étape suivante">${ICONS.next}</button>
          <span class="mm-lbl"></span>
          <button class="mm-btn" data-mm="full" aria-label="Plein écran">${ICONS.full}</button>
        </div>
        <div class="mm-hint">Touchez une case pour l’agrandir</div>
      </div>`;
    const stage = root.querySelector('.mm-stage');
    const world = stage.querySelector('.mm-world');
    list.forEach((c) => { c.el = world.querySelector(`[data-id="${c.id}"]`); });
    const isNarrow = () => stage.clientWidth < 600;
    let narrow = isNarrow();
    let dims = layout(world, list, links, narrow);
    const relayout = (force) => {
      if (!force && isNarrow() === narrow) return;
      narrow = isNarrow();
      dims = layout(world, list, links, narrow);
    };
    const nodes = [...world.querySelectorAll('.mm-node')];
    const bars = [...stage.querySelectorAll('.mm-bars i')];
    const lbl = stage.querySelector('.mm-lbl');
    const playBtn = stage.querySelector('[data-mm="play"]');
    const rotBtn = stage.querySelector('[data-mm="rotate"]');

    let cur = 0, paused = false, held = true, focus = null, timer = null, panTimer = null, started = 0, remaining = 0, dur = 0;
    let landscape = false;    // plein écran tourné en paysage (au choix de la personne)

    function view() {
      // zone utile : sous les barres de progression (et les boutons du plein écran), au-dessus des commandes
      const vw = stage.clientWidth, vh = stage.clientHeight;
      const top = fsOpen === ctl ? 66 : 22;
      return { x: 0, y: top, w: vw, h: Math.max(60, vh - top - (fsOpen === ctl ? 70 : 54)) };
    }
    function aim(rect, instant) {
      const v = view(), m = 22;
      const sw = v.w / (rect.w + 2 * m), sh = v.h / (rect.h + 2 * m);
      let s = Math.min(sw, sh, 1.05);
      const tall = rect !== whole() && sh < sw * 0.7 && sh < 0.55;
      if (tall) s = Math.min(sw * 0.92, 1.05); // case très haute : on la parcourt de haut en bas
      const tx = v.x + v.w / 2 - s * (rect.x + rect.w / 2);
      const yTop = v.y + m - s * rect.y;
      const yMid = v.y + v.h / 2 - s * (rect.y + rect.h / 2);
      clearTimeout(panTimer);
      world.style.transition = instant ? 'none' : '';
      world.style.transform = `translate(${tx}px, ${tall ? yTop : yMid}px) scale(${s})`;
      if (tall && !paused && !held) {
        const yEnd = v.y + v.h - m - s * (rect.y + rect.h);
        panTimer = setTimeout(() => {
          world.style.transition = `transform ${Math.max(1500, remaining - 2200)}ms linear`;
          world.style.transform = `translate(${tx}px, ${yEnd}px) scale(${s})`;
        }, 1400);
      }
    }
    const whole = () => (whole.r && whole.r.h === dims.H && whole.r.w === dims.W ? whole.r : (whole.r = { x: 0, y: 0, w: dims.W, h: dims.H }));
    const rectOf = (c) => ({ x: c.x, y: c.y, w: c.w, h: c.h });
    function textLength(key) {
      return list.filter((c) => c.step === key).reduce((n, c) => n + c.el.textContent.replace(/\s+/g, ' ').length, 0);
    }
    function render(instant) {
      const key = steps[cur].key;
      stage.classList.toggle('all', key === 'all' && !focus);
      for (const el of nodes) {
        const k = order[el.dataset.step];
        el.classList.toggle('on', k <= cur || key === 'all');
        el.classList.toggle('cur', el.dataset.step === key || el.dataset.id === focus);
      }
      for (const el of world.querySelectorAll('[data-step]:not(.mm-node)')) el.classList.toggle('on', order[el.dataset.step] <= cur);
      bars.forEach((b, i) => { b.className = i < cur ? 'done' : i === cur ? 'on' : ''; b.style.removeProperty('--d'); });
      lbl.textContent = `${cur + 1}/${steps.length} · ${steps[cur].label}`;
      const c = focus ? list.find((x) => x.id === focus) : list.find((x) => x.step === key);
      aim(c ? rectOf(c) : whole(), instant);
    }
    function schedule() {
      clearTimeout(timer);
      if (paused || held || focus) return;
      const key = steps[cur].key;
      if (key === 'all') { setPlay(); return; }
      started = Date.now();
      timer = setTimeout(() => go(cur + 1), remaining);
      const bar = bars[cur];
      bar.style.setProperty('--d', dur + 'ms');
      bar.style.setProperty('--done', String(1 - remaining / dur));
    }
    function go(i, keepPaused) {
      cur = Math.max(0, Math.min(steps.length - 1, i));
      focus = null;
      const key = steps[cur].key;
      dur = remaining = key === 'all' ? 0 : Math.min(18000, Math.max(5000, 3200 + textLength(key) * 42));
      if (!keepPaused && paused && key !== 'all') { paused = false; }
      render();
      schedule();
      setPlay();
    }
    function setPlay() {
      const end = steps[cur].key === 'all';
      stage.classList.toggle('paused', paused || held || end);
      playBtn.innerHTML = end ? ICONS.again : paused ? ICONS.play : ICONS.pause;
      playBtn.setAttribute('aria-label', end ? 'Revoir' : paused ? 'Lecture' : 'Pause');
    }
    function pause() {
      if (paused) return;
      paused = true;
      clearTimeout(timer); clearTimeout(panTimer);
      remaining = Math.max(800, remaining - (Date.now() - started));
      bars[cur].style.setProperty('--done', String(1 - remaining / dur));
      setPlay();
    }
    function resume() {
      if (steps[cur].key === 'all') { go(0); return; }
      paused = false; focus = null;
      render();
      schedule();
      setPlay();
    }
    function hold(on) {   // hors de l'écran : on attend
      if (on === held) return;
      if (on && !paused) { clearTimeout(timer); clearTimeout(panTimer); remaining = Math.max(800, remaining - (Date.now() - started)); }
      held = on;
      if (!on) { render(); schedule(); }
      setPlay();
    }

    /* plein écran : le schéma passe par-dessus l'application, droit ; « Paysage » le fait pivoter si le téléphone est tenu droit */
    const layer = document.createElement('div');
    layer.className = 'mm-fs-layer';
    function fit() {
      const upright = innerHeight > innerWidth;
      const rot = !!layer.isConnected && landscape && upright;
      layer.classList.toggle('rot', rot);
      layer.classList.toggle('wide', !upright);
      rotBtn.querySelector('span').textContent = rot ? 'Portrait' : 'Paysage';
      rotBtn.setAttribute('aria-label', rot ? 'Revenir en portrait' : 'Passer en paysage');
      if (layer.isConnected) {
        stage.style.width = (rot ? innerHeight : innerWidth) + 'px';
        stage.style.height = (rot ? innerWidth : innerHeight) + 'px';
        stage.style.transform = rot ? `translateX(${innerWidth}px) rotate(90deg)` : 'none';
      } else {
        stage.style.width = stage.style.height = stage.style.transform = '';
      }
      relayout();
      render(true);
    }
    function enterFs() {
      if (fsOpen) return;
      fsOpen = ctl;
      landscape = false;  // toujours droit d'abord
      root.style.minHeight = root.offsetHeight + 'px';  // la place du schéma reste réservée dans l'article
      layer.style.setProperty('--mc', opts.color || '#fbbf24');
      document.body.append(layer);
      layer.append(stage);
      document.documentElement.classList.add('mm-lock');
      history.pushState({ mmfs: true }, '');
      fit();
      if (held) hold(false);
    }
    function exitFs() {
      if (fsOpen !== ctl) return false;
      fsOpen = null;
      root.append(stage);
      root.style.minHeight = '';
      layer.remove();
      document.documentElement.classList.remove('mm-lock');
      fit();
      return true;
    }

    stage.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-mm]');
      if (b) {
        ev.stopPropagation();
        const a = b.dataset.mm;
        if (a === 'prev') go(cur - 1, paused);
        else if (a === 'next') go(cur + 1, paused);
        else if (a === 'play') (paused || steps[cur].key === 'all' ? resume : pause)();
        else if (a === 'full') (fsOpen === ctl ? (history.state?.mmfs ? history.back() : exitFs()) : enterFs());
        else if (a === 'close') { if (history.state?.mmfs) history.back(); else exitFs(); }
        else if (a === 'rotate') { landscape = !landscape; fit(); }
        return;
      }
      const relBtn = ev.target.closest('[data-rel]');
      if (relBtn) {
        ev.stopPropagation();
        const item = story.related[+relBtn.dataset.rel];
        if (fsOpen === ctl) { if (history.state?.mmfs) history.back(); else exitFs(); }
        setTimeout(() => opts.onRelated?.(item), 60);
        return;
      }
      if (ev.target.closest('a')) return;
      if (steps[cur].key === 'all' || focus) {
        // schéma entier : une case touchée s'agrandit ; touchée de nouveau, on revient au schéma entier
        const node = ev.target.closest('.mm-node');
        focus = node && node.dataset.id !== focus ? node.dataset.id : null;
        if (focus) pause();
        render();
        return;
      }
      const r = stage.getBoundingClientRect();
      const rot = layer.classList.contains('rot');
      const x = rot ? ev.clientY - r.top : ev.clientX - r.left;
      go(x < (rot ? r.height : r.width) / 3 ? cur - 1 : cur + 1, paused);
    });

    const io = 'IntersectionObserver' in window ? new IntersectionObserver(([e]) => { if (fsOpen !== ctl) hold(!(e.isIntersecting && e.intersectionRatio > 0.35)); },
      { threshold: [0, 0.35, 0.7] }) : null;
    if (io) io.observe(root); else held = false;
    const ro = 'ResizeObserver' in window ? new ResizeObserver(() => { relayout(); render(true); }) : null;
    ro?.observe(stage);
    const onResize = () => { if (fsOpen === ctl) fit(); };
    window.addEventListener('resize', onResize);
    // les photos arrivent après coup : la mise en page se refait à leur taille finale
    for (const img of world.querySelectorAll('img')) img.addEventListener('load', () => { relayout(true); render(true); }, { once: true });
    const watch = setInterval(() => {  // la fiche de l'article est fermée : on arrête tout
      if (!root.isConnected && fsOpen !== ctl) { clearInterval(watch); clearTimeout(timer); clearTimeout(panTimer); io?.disconnect(); ro?.disconnect(); window.removeEventListener('resize', onResize); }
    }, 2000);

    const ctl = { exitFs, pause, go };
    go(0);
    render(true);
    return ctl;
  }

  /** Quitte le plein écran (bouton retour) ; renvoie true s'il était ouvert. */
  function exitFullscreen() { return fsOpen ? fsOpen.exitFs() : false; }
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && fsOpen) { ev.stopImmediatePropagation(); if (history.state?.mmfs) history.back(); else fsOpen.exitFs(); } }, true);

  return { mount, exitFullscreen };
})();
