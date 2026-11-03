/* ACTU — application web installable. Aucune donnée n'est stockée sur le téléphone hormis vos réglages. */
'use strict';

const VERSION = '1.6.0';
const DATA = 'data/';
const REGIONS = {
  fr: { label: 'France', flag: '🇫🇷', color: 'var(--fr)', ink: '#fff' },
  eu: { label: 'Europe', flag: '🇪🇺', color: 'var(--eu)', ink: '#000' },
  us: { label: 'États-Unis', flag: '🇺🇸', color: 'var(--us)', ink: '#fff' },
  latam: { label: 'Amérique latine', flag: '🌎', color: 'var(--latam)', ink: '#000' },
};
const ORDER = ['fr', 'eu', 'us', 'latam'];
const PER_REGION = 3;
const ALL = 999; // « Tous les articles »
const CUSTOM_COLORS = ['#f59e0b', '#10b981', '#e879f9', '#38bdf8', '#f43f5e', '#a3e635'];

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const state = { index: null, themes: [], days: new Map(), loaded: new Map(), inited: new Set(), lastCheck: Date.now() };

/* ---------------------------------------------------------------- réglages (localStorage, protégé) */
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem('actu.' + key); return v === null ? fallback : JSON.parse(v); } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem('actu.' + key, JSON.stringify(value)); } catch { /* navigation privée */ }
  },
};

/* ---------------------------------------------------------------- outils */
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
/** Lien venant des données : uniquement http(s), sinon lien neutre. */
const href = (u) => (/^https?:\/\//i.test(u || '') ? esc(u) : '#');
const norm = (s) => ' ' + String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const todayISO = () => isoDate(new Date());
function isoDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function addDays(iso, n) {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + n);
  return isoDate(d);
}
const fmtLong = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
const fmtShort = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' });
const fmtTime = new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' });
const fmtNum = new Intl.NumberFormat('fr-FR');

function dayLabel(iso) {
  if (iso === todayISO()) return "Aujourd'hui";
  if (iso === addDays(todayISO(), -1)) return 'Hier';
  return cap(fmtLong.format(new Date(iso + 'T12:00:00')));
}
function when(isoString) {
  const d = new Date(isoString);
  if (isNaN(d)) return '';
  const h = (Date.now() - d) / 36e5;
  if (h >= 0 && h < 1) return `il y a ${Math.max(1, Math.round(h * 60))} min`;
  if (h >= 0 && h < 12) return `il y a ${Math.round(h)} h`;
  return `${fmtShort.format(d)}, ${fmtTime.format(d)}`;
}
function duration(sec) {
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}` : `${m} min`;
}

async function getJSON(path, fresh = false) {
  const res = await fetch(DATA + path, { cache: fresh ? 'no-cache' : 'default' });
  if (!res.ok) throw new Error(`${path} : ${res.status}`);
  return res.json();
}
function loadDay(date) {
  if (!state.days.has(date)) {
    const p = getJSON(`days/${date}.json`, date === state.index.days[0])
      .then((d) => { state.loaded.set(date, d); return d; })
      .catch((e) => { state.days.delete(date); throw e; });
    state.days.set(date, p);
  }
  return state.days.get(date);
}

let toastTimer;
function toast(html, ms = 3500) {
  const t = $('#toast');
  t.innerHTML = html;
  t.hidden = false;
  clearTimeout(toastTimer);
  if (ms) toastTimer = setTimeout(() => { t.hidden = true; }, ms);
}

async function share(title, url) {
  try {
    if (navigator.share) await navigator.share({ title, url });
    else { await navigator.clipboard.writeText(url); toast('Lien copié'); }
  } catch { /* partage annulé */ }
}

/* Images chargées seulement à l'approche de l'écran ; sans adresse de référent (certains sites bloquent sinon). */
const lazyIO = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    const img = e.target;
    lazyIO.unobserve(img);
    showImg(img);
  }
}, { rootMargin: '150% 0px' }) : null;
function showImg(img) {
  if (img.dataset.srcset) img.srcset = img.dataset.srcset;
  img.src = img.dataset.src;
}
function lazy(root) {
  $$('img[data-src]:not([data-obs])', root).forEach((img) => {
    img.dataset.obs = '1';
    img.addEventListener('load', () => img.classList.add('loaded'), { once: true });
    // image absente : l'adresse de secours (data-alt), sinon on la retire
    img.addEventListener('error', function retry() {
      if (!img.dataset.alt) { img.remove(); return; }
      img.removeAttribute('srcset');
      img.src = img.dataset.alt;
      delete img.dataset.alt;
      img.addEventListener('error', retry, { once: true });
    }, { once: true });
    if (lazyIO) lazyIO.observe(img); else showImg(img);
  });
}

/* ---------------------------------------------------------------- thèmes et centres d'intérêt */
function customThemes() {
  return store.get('custom', []).map((t, i) => ({ ...t, color: CUSTOM_COLORS[i % CUSTOM_COLORS.length], emoji: '✦', custom: true }));
}
function allThemes() { return [...state.themes, ...customThemes()]; }
function themeById(id) { return allThemes().find((t) => t.id === id); }
function interests() { return new Set(store.get('interests', state.themes.map((t) => t.id)).concat(customThemes().map((t) => t.id))); }
/** Régions du fil, dans l'ordre choisi : [{ id, on, n }] (n = nombre d'articles, ALL = tous). */
function regionPrefs() {
  let saved = store.get('regions', []);
  if (!Array.isArray(saved)) saved = [];
  // version 1.3 : les boutons des régions ne montraient pas s'ils étaient activés, des régions ont pu être masquées
  // sans le voir (France, Europe…) ; on les réaffiche toutes une fois
  if (store.get('regionsV', 1) < 2) {
    saved = saved.map((r) => ({ ...r, on: true }));
    store.set('regions', saved);
    store.set('regionsV', 2);
  }
  const list = saved.filter((r) => REGIONS[r.id]);
  for (const id of ORDER) if (!list.some((r) => r.id === id)) list.push({ id, on: true, n: PER_REGION });
  return list;
}

/* Traduction en français (option des Réglages) : faite chaque matin par le robot, gratuitement (modèles OPUS-MT). */
const LANG_FROM = { en: 'de l’anglais', es: 'de l’espagnol' };
function translating() { return store.get('translate', false); }
/** Titre et résumé à afficher : la traduction française si elle est demandée (réglage, ou bouton de l'article). */
function shown(a, useTr = translating()) {
  return useTr && a.tr ? { title: a.tr.t || a.title, summary: a.tr.s || a.summary, lang: a.tr.l } : { title: a.title, summary: a.summary, lang: null };
}

const rxCache = new Map();
function customRx(t) {
  const key = t.id + '|' + t.keywords.join(',');
  if (!rxCache.has(key)) {
    const parts = t.keywords.map((k) => norm(k.replace(/\*$/, '')).trim()).filter(Boolean)
      .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[a-z0-9]*');
    rxCache.set(key, parts.length ? new RegExp(' (?:' + parts.join('|') + ')(?= )') : null);
  }
  return rxCache.get(key);
}
/** Thèmes d'un article : ceux calculés par le robot + vos thèmes personnalisés. */
function themesOf(a) {
  if (!a._themes) {
    const text = norm(a.title + ' ' + a.summary);
    a._themes = [...a.themes, ...customThemes().filter((t) => customRx(t)?.test(text)).map((t) => t.id)];
  }
  return a._themes;
}
/** Les 3 articles d'une région, en tenant compte de vos centres d'intérêt et sans répéter une source. */
function pick(arts, n = PER_REGION) {
  const fav = interests();
  const ranked = arts.map((a) => {
    const th = themesOf(a);
    const hits = th.filter((t) => fav.has(t)).length;
    const bonus = hits ? 0.25 + 0.04 * Math.min(hits, 2) : (th.length ? -0.15 : 0);
    return { a, s: a.score + bonus + (a.full && reader.code() ? 0.08 : 0) };
  }).sort((x, y) => y.s - x.s);
  // d'abord une source différente par article, puis on complète si vous demandez plus d'articles
  const out = [];
  const sources = new Set();
  for (const { a } of ranked) {
    if (out.length >= n) break;
    if (!sources.has(a.source)) { sources.add(a.source); out.push(a); }
  }
  for (const { a } of ranked) {
    if (out.length >= n) break;
    if (!out.includes(a)) out.push(a);
  }
  return out.sort((x, y) => ranked.findIndex((r) => r.a === x) - ranked.findIndex((r) => r.a === y));
}
function chipsHTML(ids, max = 3) {
  return ids.slice(0, max).map((id) => {
    const t = themeById(id);
    return t ? `<span class="chip"><i>${t.emoji}</i>${esc(t.label)}</span>` : '';
  }).join('');
}

/* ---------------------------------------------------------------- 1. À la une */
const feed = { el: null, next: 0, loading: false, io: null, gen: 0 };

async function initFeed() {
  feed.el = $('#feed');
  feed.el.innerHTML = '';
  feed.next = 0;
  feed.gen++;  // un chargement lancé avant une reconstruction du fil sera ignoré
  feed.loading = false;
  feed.io?.disconnect();
  feed.io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) loadNextDay();
  }, { root: feed.el, rootMargin: '300% 0px' });
  if (!feed.onScroll) {  // sécurité si l'observateur ne se déclenche pas
    feed.onScroll = () => { if (feed.el.scrollTop + 4 * feed.el.clientHeight > feed.el.scrollHeight) loadNextDay(); };
    feed.el.addEventListener('scroll', feed.onScroll, { passive: true });
  }
  if (!state.index.days.length) {
    feed.el.innerHTML = '<div class="slide end-slide"><h2>Première édition en préparation</h2><p>Revenez après 10h.</p></div>';
    return;
  }
  await loadNextDay();
}

async function loadNextDay() {
  if (feed.loading || feed.next >= state.index.days.length) return;
  feed.loading = true;
  const gen = feed.gen;
  const date = state.index.days[feed.next++];
  try {
    const day = await loadDay(date);
    if (gen !== feed.gen) return;
    renderDay(day, feed.next === 1);
  } catch {
    if (gen !== feed.gen) return;
    feed.el.insertAdjacentHTML('beforeend', `<div class="slide end-slide"><h2>Hors connexion</h2><p>L'édition du ${esc(dayLabel(date).toLowerCase())} n'a pas pu être chargée.</p><button class="btn" data-action="reload">Réessayer</button></div>`);
  }
  feed.loading = false;
  if (feed.next >= state.index.days.length) {
    feed.el.insertAdjacentHTML('beforeend', '<div class="slide end-slide"><h2>Vous êtes à jour</h2><p>Il n’y a pas d’édition plus ancienne.<br>La prochaine arrive demain matin à 10h.</p></div>');
  }
}

function renderDay(day, isFirst) {
  const hidden = regionPrefs().filter((r) => !r.on);
  const regions = regionPrefs().filter((r) => r.on).map((r) => [r.id, pick(day.regions[r.id] || [], r.n)]).filter(([, l]) => l.length);
  const frag = document.createDocumentFragment();
  const intro = document.createElement('section');
  intro.className = 'slide intro';
  const updated = state.index.updated ? new Date(state.index.updated) : null;
  intro.innerHTML = `
    <div class="kicker">${esc(cap(fmtLong.format(new Date(day.date + 'T12:00:00'))))}</div>
    <h2>${isFirst && day.date === todayISO() ? 'L’essentiel du jour' : `L’édition ${day.date === addDays(todayISO(), -1) ? 'd’hier' : 'du ' + esc(fmtShort.format(new Date(day.date + 'T12:00:00')))}`}</h2>
    <p class="sub">${isFirst && updated ? `Mise à jour ${updated.toDateString() === new Date().toDateString() ? 'aujourd’hui' : 'le ' + esc(fmtShort.format(updated))} à ${esc(fmtTime.format(updated))} · prochaine demain à 10h` : 'Suite de votre fil : les articles de la veille.'}</p>
    <ol>${regions.map(([r, l]) => `<li style="--rc:${REGIONS[r].color}"><span class="sw"></span>${REGIONS[r].flag} ${REGIONS[r].label}<small>${l.length} article${l.length > 1 ? 's' : ''}</small></li>`).join('') || '<li>Aucune région choisie : voir Réglages</li>'}</ol>
    ${isFirst && hidden.length ? `<div class="hidden-regions">Masquée${hidden.length > 1 ? 's' : ''} : ${hidden.map((r) => REGIONS[r.id].flag + ' ' + REGIONS[r.id].label).join(', ')}<button class="btn" data-action="show-regions">Afficher</button></div>` : ''}
    <div class="hint"><svg viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6"/></svg>Glissez vers le haut</div>`;
  frag.append(intro);
  for (const [r, list] of regions) {
    list.forEach((a, i) => frag.append(articleSlide(a, r, i, list.length, day.date)));
  }
  feed.el.append(frag);
  lazy(feed.el);
  // le jour suivant se charge quand on approche de la fin de celui-ci
  const slides = $$('.slide', feed.el);
  feed.io.observe(slides[Math.max(0, slides.length - 4)]);
}

function articleSlide(a, region, i, n, date) {
  const t = shown(a);
  const el = document.createElement('article');
  el.className = 'slide';
  el.style.setProperty('--rc', REGIONS[region].color);
  el.style.setProperty('--ink', REGIONS[region].ink);
  el.tabIndex = 0;
  const posts = a.posts?.length || 0;
  el.innerHTML = `
    <canvas class="scene" aria-hidden="true"></canvas>
    <div class="shade"></div>
    <header class="slide-top">
      <span class="pill region">${REGIONS[region].flag} ${REGIONS[region].label} · ${i + 1}/${n}</span>
      <span class="pill">${esc(dayLabel(date))}</span>
    </header>
    <div class="slide-body">
      <div class="meta"><b>${esc(a.source)}</b><span class="dot">${esc(when(a.date))}</span>${t.lang ? '<span class="dot">traduit</span>' : ''}</div>
      <h2 class="headline">${esc(t.title)}</h2>
      ${t.summary ? `<p class="dek">${esc(t.summary)}</p>` : ''}
      <div class="chips">${chipsHTML(themesOf(a))}</div>
      <div class="cta">${a.full ? 'Lire l’article en entier' : 'Lire l’article'}<svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg></div>
    </div>
    <aside class="rail">
      ${a.coverage > 1 ? `<div title="Sources qui traitent ce sujet"><span class="round"><svg viewBox="0 0 24 24"><use href="#i-layers"/></svg></span>${a.coverage}</div>` : ''}
      ${posts ? `<div title="Publications sur les réseaux"><span class="round"><svg viewBox="0 0 24 24"><use href="#i-chat"/></svg></span>${posts}</div>` : ''}
      <button data-share aria-label="Partager"><span class="round"><svg viewBox="0 0 24 24"><use href="#i-share"/></svg></span>Partager</button>
    </aside>`;
  el.addEventListener('click', (ev) => {
    if (ev.target.closest('[data-share]')) { ev.stopPropagation(); share(a.title, a.url); return; }
    openArticle(a, region, date);
  });
  el.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') openArticle(a, region, date); });
  Pixel.mount($('canvas', el), a.scene || Pixel.fallback(a), a.id, { width: 80, ground: 0.5, labelY: 0.12 });
  return el;
}

/* ---------------------------------------------------------------- feuille de détail */
const sheet = { el: null, body: null, open: false };

function openSheet(html, after) {
  sheet.body.innerHTML = html;
  sheet.body.scrollTop = 0;
  sheet.el.classList.add('open');
  sheet.el.setAttribute('aria-hidden', 'false');
  if (!sheet.open) history.pushState({ sheet: true }, '');
  sheet.open = true;
  lazy(sheet.body);
  after?.(sheet.body);
}
function closeSheet(fromHistory = false) {
  if (!sheet.open) return;
  sheet.open = false;
  sheet.el.classList.remove('open');
  sheet.el.setAttribute('aria-hidden', 'true');
  setTimeout(() => { if (!sheet.open) sheet.body.innerHTML = ''; }, 350); // coupe aussi les vidéos
  if (!fromHistory && history.state?.sheet) history.back();
}

function openArticle(a, region, date, opts = {}) {
  const r = REGIONS[region];
  const useTr = !!a.tr && (opts.tr ?? translating());
  const t = shown(a, useTr);
  const unavailable = a.full === false
    ? `<p class="small">${a.paywall ? 'Ce journal réserve cet article à ses abonnés : il se lit sur son site.' : 'Ce journal ne permet pas la lecture dans ACTU : l’article se lit sur son site.'}</p>` : '';
  openSheet(`
    ${a.image ? `<img class="hero" data-src="${esc(a.image)}" alt="" referrerpolicy="no-referrer">` : ''}
    <div class="sheet-content" style="--rc:${r.color};--ink:${r.ink}">
      <div class="meta"><span class="pill region">${r.flag} ${r.label}</span><b>${esc(a.source)}</b><span class="dot">${esc(cap(fmtLong.format(new Date(a.date))))} à ${esc(fmtTime.format(new Date(a.date)))}</span></div>
      ${a.tr ? `<div class="tr-bar">${useTr ? `🌐 Traduit automatiquement ${LANG_FROM[a.tr.l] || ''}` : '🌐 Article en langue étrangère'}<button class="btn" data-tr>${useTr ? 'Voir l’original' : 'Traduire en français'}</button></div>` : ''}
      <h1>${esc(t.title)}</h1>
      ${t.summary ? `<p class="lead">${esc(t.summary)}</p>` : ''}
      <div class="chips" style="margin-bottom:18px">${chipsHTML(themesOf(a), 4)}</div>
      <div id="fulltext">${a.full ? '<p class="status">Chargement de l’article…</p>' : ''}</div>
      <a class="btn ${a.full ? '' : 'primary'}" href="${href(a.url)}" target="_blank" rel="noopener">${a.full ? 'Voir l’article sur le site de ' : 'Lire l’article sur '}${esc(a.source)}<svg viewBox="0 0 24 24"><use href="#i-ext"/></svg></a>
      <div class="btn-row"><button class="btn" data-share>Partager<svg viewBox="0 0 24 24"><use href="#i-share"/></svg></button></div>
      ${unavailable}
      ${a.also?.length ? `<p class="small">Sujet aussi traité par : ${a.also.map(esc).join(', ')}.</p>` : ''}
      <h3 class="section-title">En un coup d’œil</h3>
      <div class="mm-box"></div>
      <p class="small">Schéma fait automatiquement à partir de l’article${reader.code() ? '' : ' (version courte : saisissez votre code de lecture dans Réglages pour la version complète)'}, complété par Wikipédia et les éditions précédentes d’ACTU.</p>
      <h3 class="section-title">Sur les réseaux</h3>
      ${a.posts?.length ? `<div class="posts">${a.posts.map(postHTML).join('')}</div>`
        : '<p class="small">Aucune publication pertinente des chaînes d’information et créateurs suivis (HugoDécrypte, Ulyces, franceinfo, Le Monde, AFP…) pour l’instant. ACTU vérifie à nouveau chaque matin.</p>'}
    </div>`, (body) => {
    $('[data-share]', body).addEventListener('click', () => share(a.title, a.url));
    $('[data-tr]', body)?.addEventListener('click', () => openArticle(a, region, date, { tr: !useTr }));
    bindPosts(body);
    if (a.full) showFullText(a, date, $('#fulltext', body), useTr);
    playStory(a, region, date, $('.mm-box', body), useTr);
  });
}

/* ---------------------------------------------------------------- lecture intégrale (textes chiffrés avec votre code) */
const reader = {
  files: new Map(), key: null, keyFor: '',
  code() { return store.get('readcode', ''); },
  async getKey() {
    const code = this.code().toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (!code) throw new Error('nocode');
    if (this.key && this.keyFor === code) return this.key;
    const enc = new TextEncoder();
    const base = await crypto.subtle.importKey('raw', enc.encode(code), 'PBKDF2', false, ['deriveKey']);
    this.key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: enc.encode('actu-lecture-v1'), iterations: 150000, hash: 'SHA-256' },
      base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
    this.keyFor = code;
    return this.key;
  },
  texts(date) { return this.load('texts', date); },
  stories(date) { return this.load('stories', date); },
  load(kind, date) {
    const id = kind + '/' + date;
    if (!this.files.has(id)) {
      const job = (async () => {
        if (typeof DecompressionStream === 'undefined') throw new Error('old');
        const key = await this.getKey();
        const res = await fetch(`${DATA}${kind}/${date}.bin`, { cache: date === state.index.days[0] ? 'no-cache' : 'default' });
        if (res.status === 404) return {};
        if (!res.ok) throw new Error('net');
        const buf = new Uint8Array(await res.arrayBuffer());
        let plain;
        try { plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: buf.slice(0, 12) }, key, buf.slice(12)); } catch { throw new Error('badcode'); }
        const stream = new Blob([plain]).stream().pipeThrough(new DecompressionStream('gzip'));
        return JSON.parse(await new Response(stream).text());
      })();
      job.catch(() => this.files.delete(id));
      this.files.set(id, job);
    }
    return this.files.get(id);
  },
  reset() { this.files.clear(); this.key = null; this.keyFor = ''; },
};
/* ---------------------------------------------------------------- « En un coup d'œil » */
const TOPIC_ACTION = { guerre: 'attaque', diplomatie: 'negocie', election: 'vote', gouvernement: 'annonce', manifestation: 'manifeste', justice: 'juge',
  police: 'arrete', catastrophe: 'accident', climat: 'avertit', espace: 'lance', sante: 'sante', science: 'decouvre', cyber: 'attaque', tech: 'lance',
  energie: 'hausse', bourse: 'hausse', economie: 'hausse', agriculture: 'annonce', migration: 'aide', education: 'annonce', religion: 'annonce',
  transport: 'accident', f1: 'victoire', sport: 'victoire', musique: 'annonce', mode: 'annonce', culture: 'annonce' };
const ACTION_VERB = { attaque: 'ATTAQUE', negocie: 'NEGOCIE', vote: 'VOTE', annonce: 'ANNONCE', manifeste: 'MOBILISATION', juge: 'JUSTICE',
  arrete: 'ENQUETE', accident: 'DRAME', avertit: 'ALERTE', lance: 'LANCEMENT', sante: 'SANTE', decouvre: 'DECOUVERTE', hausse: 'HAUSSE',
  baisse: 'BAISSE', aide: 'AIDE', victoire: 'GAGNE' };
const GROUP = { politician: 'Gouvernement', citizen: 'Habitants', police: 'Police', firefighter: 'Secours', doctor: 'Médecins', athlete: 'Athlètes',
  racer: 'Pilotes', soldier: 'Armée', business: 'Entreprises', worker: 'Salariés', protester: 'Manifestants', student: 'Élèves', teacher: 'Enseignants',
  judge: 'Justice', scientist: 'Chercheurs', artist: 'Artistes', musician: 'Musiciens', model: 'Mannequins', hacker: 'Pirates', farmer: 'Agriculteurs',
  astronaut: 'Astronautes', priest: 'Église', journalist: 'Journalistes' };
/** Schéma court tiré du titre et du résumé (quand le code de lecture n'est pas saisi). */
function storyFrom(a, region, date) {
  const sc = a.scene || Pixel.fallback(a);
  const country = sc.country || { fr: 'fr', us: 'us', eu: 'eu' }[region] || 'latam';
  const names = [...new Set((a.title + ' ' + a.summary).match(/\b[A-ZÉÈÀÂÎÔÛÇ][a-zà-ÿ'’-]+(?:\s+[A-ZÉÈÀÂÎÔÛÇ][a-zà-ÿ'’-]+)+/g) || [])].slice(0, 3);
  const cast = (sc.cast || ['citizen']).slice(0, 2);
  const actors = names.length ? names.map((name) => ({ name, role: cast[0], country, kind: 'nom' }))
    : [...new Set(cast)].map((role) => ({ name: GROUP[role] || 'Habitants', role, country, group: true }));
  const kind = sc.dir === 'down' ? 'baisse' : TOPIC_ACTION[sc.topic] || 'annonce';
  const all = (a.summary || '').split(/(?<=[.!?])\s+/).filter((x) => x.length > 20);
  const whole = all.filter((x) => !/(…|\.\.\.|\[…\])\W*$/.test(x));  // phrase coupée par le journal : écartée
  const sentences = whole.length ? whole : all;
  const place = sc.city ? cap(sc.city.toLowerCase()) : (Pixel.countryName(country) ? cap(Pixel.countryName(country).toLowerCase()) : 'Dans le monde');
  return {
    place: { country, city: sc.city || '', label: place, date: cap(fmtLong.format(new Date(date + 'T12:00:00'))), iso: date },
    profile: country,
    actors,
    action: { who: 0, verb: ACTION_VERB[kind] || 'ANNONCE', kind, target: -1 },
    links: [],
    consequences: [{ text: sentences[1] || `À suivre dans ${a.source}${a.also?.length ? ', ' + a.also.slice(0, 2).join(', ') : ''}.`, kind: 'autre' }],
    captions: { quoi: sentences[0] || a.summary || a.title },
    context: null,
    related: [],
    sources: [a.source, ...(a.also || [])],
  };
}
async function playStory(a, region, date, box, useTr = false) {
  let story = null;
  if (reader.code()) { try { story = (await reader.stories(date))[a.id] || null; } catch { story = null; } }
  if (story && useTr) story = translatedStory(story);
  const t = shown(a, useTr);
  story = story || storyFrom({ ...a, title: t.title, summary: t.summary }, region, date);
  const profiles = await loadProfiles();
  if (!box.isConnected) return;
  MindMap.mount(box, story, { color: REGIONS[region].color, onRelated: openRelated, profiles });
}
/** Le pays en bref (pouvoir, économie, société) : public, préparé chaque semaine par le robot. */
let profilesP = null;
function loadProfiles() {
  profilesP = profilesP || getJSON('profiles.json').then((d) => d.pays || {}).catch(() => { profilesP = null; return {}; });
  return profilesP;
}
/** Le schéma avec ses textes traduits par le robot (phrases de l'article, fiches Wikipédia étrangères). */
function translatedStory(st) {
  const tr = st.tr;
  if (!tr) return st;
  return {
    ...st,
    captions: { ...st.captions, quoi: tr.quoi || st.captions?.quoi, liens: tr.liens || st.captions?.liens },
    consequences: (st.consequences || []).map((c, i) => ({ ...c, text: tr.cons?.[i] || c.text })),
    actors: (st.actors || []).map((x, i) => ({
      ...x,
      does: tr.does?.[i] || x.does,
      wiki: x.wiki && tr.act?.[i] ? { ...x.wiki, x: tr.act[i] } : x.wiki,
    })),
    when: (st.when || []).map((w, i) => ({ ...w, t: tr.when?.[i] || w.t })),
    how: (st.how || []).map((w, i) => ({ ...w, t: tr.how?.[i] || w.t })),
    why: st.why?.facts ? { ...st.why, facts: st.why.facts.map((f, i) => tr.why?.[i] || f) } : st.why,
    critique: (st.critique || []).map((c, i) => ({ ...c, q: tr.crit?.[i] || c.q, l: c.l?.map((x) => ({ ...x, t: x.tt || x.t })) })),
    context: st.context && tr.ctx ? { ...st.context, x: tr.ctx } : st.context,
  };
}
/** Un article lié (jours précédents) touché dans le schéma : on l'ouvre. */
async function openRelated(rel) {
  try {
    const day = await loadDay(rel.d);
    const a = (day.regions[rel.r] || []).find((x) => x.id === rel.id);
    if (a) openArticle(a, rel.r, rel.d); else toast('Cet article n’est plus disponible');
  } catch { toast('Hors connexion'); }
}

async function showFullText(a, date, box, useTr = false) {
  if (!reader.code()) {
    box.innerHTML = '<div class="unlock"><p>Le texte complet de cet article se lit directement dans ACTU.</p><button class="btn primary" data-action="settings">Saisir mon code de lecture</button></div>';
    return;
  }
  try {
    let text = (await reader.texts(date))[a.id];
    if (!text) { box.innerHTML = ''; return; }
    let note = '', translated = false;
    if (useTr) {
      let fr = '';
      try { fr = (await reader.load('texts-fr', date))[a.id] || ''; } catch { fr = ''; }
      if (fr) { text = fr; translated = true; note = ' · traduction automatique'; }
      else note = ' · traduction du texte complet pas encore prête, texte original';
    }
    let paras = text.split('\n').filter(Boolean);
    const lead = norm(shown(a, translated).summary).trim().slice(0, 40);
    if (lead && paras.length && norm(paras[0]).trim().startsWith(lead)) paras = paras.slice(1);
    box.innerHTML = `<div class="article-text">${paras.map((p) => `<p>${esc(p)}</p>`).join('')}
      <p class="small">Texte © ${esc(a.source)} · copie privée pour votre lecture personnelle${note}.</p></div>`;
  } catch (e) {
    const msg = { badcode: 'Code de lecture incorrect : vérifiez-le dans Réglages.', old: 'Mettez à jour iOS (16.4 ou plus) pour lire les articles ici.', nocode: '' }[e.message];
    box.innerHTML = `<p class="small">${msg ?? 'Texte indisponible pour le moment (connexion ?).'}</p>`;
  }
}

function postHTML(p) {
  if (p.kind === 'yt') {
    return `<div class="post">
      <button class="yt" data-yt="${esc(p.id)}" aria-label="Lire la vidéo ${esc(p.title)}">
        <img data-src="https://i.ytimg.com/vi/${esc(p.id)}/hqdefault.jpg" alt="" referrerpolicy="no-referrer">
        <span class="play"><span><svg viewBox="0 0 24 24"><use href="#i-play"/></svg></span></span>
      </button>
      <div class="post-info"><div class="who"><b>${esc(p.author)}</b> · YouTube · ${esc(when(p.date))}</div><p>${esc(p.title)}</p></div>
    </div>`;
  }
  return `<div class="post"><div class="post-info">
      <div class="who">${p.avatar ? `<img data-src="${esc(p.avatar)}" alt="" referrerpolicy="no-referrer">` : ''}<b>${esc(p.author)}</b> · Bluesky · ${esc(when(p.date))}</div>
      <p>${esc(p.text)}</p>
      ${p.link && p.link_title ? `<a class="linkcard" href="${href(p.link)}" target="_blank" rel="noopener">${p.thumb ? `<img data-src="${esc(p.thumb)}" alt="" referrerpolicy="no-referrer">` : ''}<span>${esc(p.link_title)}</span></a>` : ''}
      <a class="open" href="${href(p.url)}" target="_blank" rel="noopener">Voir la publication<svg viewBox="0 0 24 24"><use href="#i-ext"/></svg></a>
    </div></div>`;
}
function ytFrame(id) {
  // YouTube exige de connaître le site qui intègre la vidéo (sinon « erreur 153 ») : on transmet l'origine.
  return `<iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&playsinline=1&rel=0&origin=${encodeURIComponent(location.origin)}" title="Vidéo YouTube" referrerpolicy="strict-origin-when-cross-origin" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>`;
}
function bindPosts(root) {
  $$('[data-yt]', root).forEach((b) => b.addEventListener('click', () => {
    const box = document.createElement('div');
    box.className = 'yt';
    box.innerHTML = ytFrame(b.dataset.yt);
    b.replaceWith(box);
  }, { once: true }));
}

/* ---------------------------------------------------------------- 2. Explorer */
const ex = { theme: '', shown: 60, items: [] };

function initExplore() {
  const regionSel = $('#ex-region');
  regionSel.innerHTML = '<option value="">Toutes</option>' + ORDER.map((r) => `<option value="${r}">${REGIONS[r].flag} ${REGIONS[r].label}</option>`).join('');
  renderThemeChips();
  for (const id of ['ex-period', 'ex-region', 'ex-source', 'ex-sort']) $('#' + id).addEventListener('change', () => { ex.shown = 60; refreshExplore(id === 'ex-period'); });
  let t;
  $('#ex-q').addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => { ex.shown = 60; renderExplore(); }, 200); });
  $('#ex-list').addEventListener('click', (ev) => {
    const row = ev.target.closest('[data-i]');
    if (row) { const it = ex.view[+row.dataset.i]; openArticle(it.a, it.region, it.date); }
    if (ev.target.closest('[data-more]')) { ex.shown += 60; renderExplore(); }
  });
  refreshExplore(true);
}
function renderThemeChips() {
  const box = $('#ex-themes');
  box.innerHTML = `<button class="chip" data-theme="" aria-pressed="${!ex.theme}">Tous</button>` +
    allThemes().map((t) => `<button class="chip" data-theme="${esc(t.id)}" aria-pressed="${ex.theme === t.id}">${t.emoji} ${esc(t.label)}</button>`).join('');
  box.onclick = (ev) => {
    const b = ev.target.closest('[data-theme]');
    if (!b) return;
    ex.theme = b.dataset.theme;
    $$('[data-theme]', box).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    ex.shown = 60;
    renderExplore();
  };
}
async function refreshExplore(reload) {
  const list = $('#ex-list');
  if (reload) {
    const n = +$('#ex-period').value;
    const since = addDays(todayISO(), -(n - 1));
    const dates = state.index.days.filter((d) => d >= since);
    list.innerHTML = '<p class="status">Chargement…</p>';
    const days = await Promise.allSettled(dates.map(loadDay));
    ex.items = [];
    for (const res of days) {
      if (res.status !== 'fulfilled') continue;
      const day = res.value;
      for (const r of ORDER) {
        const arts = day.regions[r] || [];
        const top = new Set(pick(arts).map((a) => a.id));
        for (const a of arts) ex.items.push({ a, region: r, date: day.date, top: top.has(a.id) });
      }
    }
    const srcSel = $('#ex-source');
    const current = srcSel.value;
    const sources = [...new Set(ex.items.map((i) => i.a.source))].sort((x, y) => x.localeCompare(y, 'fr'));
    srcSel.innerHTML = '<option value="">Toutes</option>' + sources.map((s) => `<option${s === current ? ' selected' : ''}>${esc(s)}</option>`).join('');
  }
  renderExplore();
}
function renderExplore() {
  const q = norm($('#ex-q').value).trim();
  const region = $('#ex-region').value;
  const source = $('#ex-source').value;
  const sort = $('#ex-sort').value;
  let items = ex.items.filter((it) => (!region || it.region === region) && (!source || it.a.source === source) &&
    (!ex.theme || themesOf(it.a).includes(ex.theme)) && (!q || norm(it.a.title + ' ' + it.a.summary + ' ' + it.a.source + ' ' + (it.a.tr ? it.a.tr.t + ' ' + it.a.tr.s : '')).includes(' ' + q)));
  const order = allThemes().map((t) => t.id);
  const keyOf = {
    date: (it) => dayLabel(it.date), 'date-asc': (it) => dayLabel(it.date), score: () => '',
    source: (it) => it.a.source,
    theme: (it) => { const t = themeById(themesOf(it.a)[0]); return t ? `${t.emoji} ${t.label}` : 'Autres sujets'; },
  }[sort];
  const cmp = {
    date: (x, y) => y.a.date.localeCompare(x.a.date),
    'date-asc': (x, y) => x.a.date.localeCompare(y.a.date),
    score: (x, y) => (y.top - x.top) || (y.a.score - x.a.score),
    source: (x, y) => x.a.source.localeCompare(y.a.source, 'fr') || y.a.date.localeCompare(x.a.date),
    theme: (x, y) => {
      const ix = order.indexOf(themesOf(x.a)[0]), iy = order.indexOf(themesOf(y.a)[0]);
      return ((ix < 0 ? 99 : ix) - (iy < 0 ? 99 : iy)) || y.a.date.localeCompare(x.a.date);
    },
  }[sort];
  items.sort(cmp);
  ex.view = items;
  const list = $('#ex-list');
  if (!items.length) { list.innerHTML = '<p class="empty">Aucun article ne correspond.<br>Essayez une période plus longue ou un autre thème.</p>'; return; }
  let html = `<p class="status">${items.length} article${items.length > 1 ? 's' : ''}</p>`;
  let last = null;
  items.slice(0, ex.shown).forEach((it, i) => {
    const k = keyOf(it);
    if (k && k !== last) { html += `<div class="group-h">${esc(k)}</div>`; last = k; }
    const r = REGIONS[it.region];
    html += `<button class="row" data-i="${i}" style="--rc:${r.color}">
      ${it.a.image ? `<img class="thumb" data-src="${esc(it.a.image)}" alt="" referrerpolicy="no-referrer">` : `<span class="thumb ph">${esc(it.a.source.charAt(0))}</span>`}
      <span class="txt">
        <span class="m"><span class="rdot"></span>${r.label} · <b>${esc(it.a.source)}</b> · ${esc(when(it.a.date))}${it.top ? ' · <b style="color:var(--accent)">À la une</b>' : ''}</span>
        <span class="t">${esc(shown(it.a).title)}</span>
        <span class="chips">${chipsHTML(themesOf(it.a), 2)}</span>
      </span></button>`;
  });
  if (items.length > ex.shown) html += '<button class="btn more" data-more>Afficher plus</button>';
  list.innerHTML = html;
  lazy(list);
}

/* ---------------------------------------------------------------- 3. Le 20h */
async function initReplay() {
  const box = $('#replay-list');
  box.innerHTML = '<p class="status">Chargement…</p>';
  let data;
  try { data = await getJSON('replays.json', true); } catch { box.innerHTML = '<p class="empty">Replays indisponibles hors connexion.</p>'; return; }
  const jt = (item, cls, name) => item
    ? `<a class="jt ${cls}" href="${href(item.url)}" target="_blank" rel="noopener">
        ${item.image ? `<img data-src="${esc(item.image)}" alt="" referrerpolicy="no-referrer">` : ''}
        <span class="logo">${name}</span>
        <span class="lbl"><b>Le 20h</b><span>${item.minutes ? item.minutes + ' min · ' : ''}Regarder ↗</span></span></a>`
    : `<a class="jt ${cls} missing" href="${href(cls === 'tf1' ? data.tf1_page : data.f2_page)}" target="_blank" rel="noopener"><span class="logo">${name}</span>Édition pas encore référencée.<br>Ouvrir la page des replays ↗</a>`;
  box.innerHTML = data.days.map((d) => `
    <section>
      <h2 class="day-h">${esc(dayLabel(d.date))}${d.date === todayISO() || d.date === addDays(todayISO(), -1) ? '' : ''}</h2>
      <div class="jt-grid">${jt(d.tf1, 'tf1', 'TF1')}${jt(d.f2, 'f2', 'France 2')}</div>
      ${d.tf1_topics?.length ? `<details class="topics"><summary>Les sujets du 20h de TF1 (${d.tf1_topics.length})</summary>
        <div class="topic-row">${d.tf1_topics.map((t) => `<a class="topic" href="${href(t.url)}" target="_blank" rel="noopener">
          ${t.image ? `<img data-src="${esc(t.image)}" alt="" referrerpolicy="no-referrer">` : ''}<b>${esc(t.title)}</b><span>${t.minutes ? t.minutes + ' min' : ''}</span></a>`).join('')}</div></details>` : ''}
    </section>`).join('') + `
    <div class="links">
      <a class="btn" href="${href(data.tf1_page)}" target="_blank" rel="noopener">Tous les replays du 20h sur TF1+</a>
      <a class="btn" href="${href(data.f2_page)}" target="_blank" rel="noopener">Tous les replays du 20h sur france.tv</a>
    </div>`;
  lazy(box);
  $$('details', box).forEach((d) => d.addEventListener('toggle', () => lazy(d)));
}

/* ---------------------------------------------------------------- 4. ARTE */
const arte = { data: null, subject: '', region: '', sort: 'date', shown: 0, list: [], io: null };

async function initArte() {
  const grid = $('#arte-grid');
  grid.innerHTML = '<p class="status">Chargement des reportages…</p>';
  try { arte.data = await getJSON('arte.json'); } catch { grid.innerHTML = '<p class="empty">Reportages indisponibles hors connexion.</p>'; return; }
  const subjects = arte.data.subjects.filter((s) => s.count > 0);
  const box = $('#arte-subjects');
  box.innerHTML = `<button class="chip" data-s="" aria-pressed="true">Tous <small>${arte.data.videos.length}</small></button>` +
    subjects.map((s) => `<button class="chip" data-s="${esc(s.id)}" aria-pressed="false">${esc(s.label)} <small>${s.count}</small></button>`).join('');
  box.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-s]');
    if (!b) return;
    arte.subject = b.dataset.s;
    $$('[data-s]', box).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    renderArte();
  });
  const regions = (arte.data.regions || []).filter((r) => r.count > 0);
  const rbox = $('#arte-regions');
  rbox.innerHTML = regions.length ? `<button class="chip" data-r="" aria-pressed="true">🌐 Toutes les régions</button>` +
    regions.map((r) => `<button class="chip" data-r="${esc(r.id)}" aria-pressed="false">${esc(r.label)} <small>${r.count}</small></button>`).join('') : '';
  rbox.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-r]');
    if (!b) return;
    arte.region = b.dataset.r;
    $$('[data-r]', rbox).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    renderArte();
  });
  $('#arte-sort').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-sort]');
    if (!b) return;
    setArteSort(b.dataset.sort);
    renderArte();
  });
  let t;
  $('#arte-q').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      // une recherche se classe d'abord par pertinence ; sans recherche, on revient au tri choisi avant
      const searching = !!$('#arte-q').value.trim();
      $('[data-sort="score"]').hidden = !searching;
      if (searching && !arte.searching) { arte.before = arte.sort; setArteSort('score'); }
      if (!searching && arte.searching) setArteSort(arte.before || 'date');
      arte.searching = searching;
      renderArte();
    }, 200);
  });
  grid.addEventListener('click', (ev) => {
    const c = ev.target.closest('[data-v]');
    if (c) openVideo(arte.list[+c.dataset.v]);
  });
  arte.io = new IntersectionObserver((e) => { if (e[0].isIntersecting) moreArte(); }, { root: $('#view-arte'), rootMargin: '600px 0px' });
  arte.io.observe($('#arte-more'));
  renderArte();
}
function setArteSort(sort) {
  arte.sort = sort;
  $$('[data-sort]', $('#arte-sort')).forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.sort === sort)));
}

/* Recherche ARTE : chaque mot cherché (pluriel, féminin, faute de frappe légère) dans le titre, l'émission, les mots-clés
   et la description ; le titre compte le plus. Tous les mots doivent être trouvés, sinon on montre les plus proches. */
const ARTE_STOP = new Set('le la les l un une des du de d et ou en au aux a the of and in on sur pour par avec dans est qui que quoi'.split(' '));
function stem(w) {
  if (w.length > 5 && w.endsWith('aux')) return w.slice(0, -3) + 'al';
  if (w.length > 3 && /[sx]$/.test(w)) w = w.slice(0, -1);
  if (w.length > 4 && w.endsWith('e')) w = w.slice(0, -1);
  return w;
}
function nearWord(a, b) {  // au plus une lettre de différence (oubli, ajout ou erreur)
  if (Math.abs(a.length - b.length) > 1) return false;
  let i = 0, j = 0, diff = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { i++; j++; continue; }
    if (++diff > 1) return false;
    if (a.length > b.length) i++; else if (b.length > a.length) j++; else { i++; j++; }
  }
  return diff + (a.length - i) + (b.length - j) <= 1;
}
function arteWords(v) {
  if (!v._w) {
    const words = (s) => norm(s).trim().split(' ').filter(Boolean).map(stem);
    v._w = [words(v.title), words([v.program, v.channel, ...(v.tags || []), ...(v.playlists || [])].join(' ')), words(v.desc)];
  }
  return v._w;
}
function arteScore(v, terms, phrase) {
  const fields = arteWords(v), weight = [3, 2, 1];
  let total = 0, found = 0;
  for (const t of terms) {
    let best = 0;
    fields.forEach((ws, f) => {
      for (const w of ws) {
        const s = w === t ? 1 : w.startsWith(t) ? 0.8 : t.length >= 5 && nearWord(w.slice(0, t.length + 1), t) || (t.length >= 5 && nearWord(w, t)) ? 0.5 : 0;
        if (s * weight[f] > best) best = s * weight[f];
      }
    });
    if (best) { found++; total += best; }
  }
  if (phrase && norm(v.title).includes(phrase)) total += 3;
  else if (phrase && norm(v.desc).includes(phrase)) total += 1;
  return { total, found };
}
function renderArte() {
  const raw = $('#arte-q').value.trim();
  const terms = [...new Set(norm(raw).trim().split(' ').filter((w) => w && !ARTE_STOP.has(w)).map(stem))];
  const phrase = terms.length > 1 ? norm(raw) : '';
  const sorters = {
    date: (a, b) => (b.date || '').localeCompare(a.date || ''),
    views: (a, b) => (b.views || 0) - (a.views || 0),
    long: (a, b) => b.duration - a.duration,
    score: (a, b) => b._score - a._score || (b.date || '').localeCompare(a.date || ''),
  };
  let pool = arte.data.videos.filter((v) => (!arte.subject || v.subjects.includes(arte.subject)) &&
    (!arte.region || (v.regions || []).includes(arte.region)));
  arte.partial = false;
  if (terms.length) {
    for (const v of pool) { const s = arteScore(v, terms, phrase); v._score = s.total; v._found = s.found; }
    let hits = pool.filter((v) => v._found === terms.length);
    if (!hits.length && terms.length > 1) {  // aucun reportage n'a tous les mots : ceux qui en ont le plus
      const most = Math.max(0, ...pool.map((v) => v._found));
      hits = most ? pool.filter((v) => v._found === most) : [];
      arte.partial = hits.length > 0;
    }
    pool = hits;
  }
  arte.terms = terms;
  arte.list = pool.sort(sorters[arte.sort] || sorters.date);
  arte.shown = 0;
  $('#arte-grid').innerHTML = !arte.list.length ? '<p class="empty">Aucun reportage ne correspond.</p>'
    : arte.partial ? '<p class="status">Aucun reportage ne contient tous ces mots : voici les plus proches.</p>' : '';
  moreArte();
}
/** Passage de la description où apparaît un mot cherché, mots trouvés surlignés. */
function arteSnippet(v) {
  if (!v.desc || !arte.terms?.length) return '';
  const words = v.desc.split(/(\s+)/);
  const hit = (w) => { const n = stem(norm(w).trim()); return n && arte.terms.some((t) => n.startsWith(t)); };
  const at = words.findIndex(hit);
  if (at < 0) return '';
  const start = Math.max(0, at - 14), part = words.slice(start, at + 30);
  return (start ? '… ' : '') + part.map((w) => (hit(w) ? `<mark>${esc(w)}</mark>` : esc(w))).join('') + (at + 30 < words.length ? ' …' : '');
}
function moreArte() {
  if (!arte.data || arte.shown >= arte.list.length) return;
  const label = Object.fromEntries(arte.data.subjects.concat(arte.data.regions || []).map((s) => [s.id, s.label]));
  const slice = arte.list.slice(arte.shown, arte.shown + 24);
  const yt = (id, f) => `https://i.ytimg.com/vi/${esc(id)}/${f}.jpg`;
  const html = slice.map((v, k) => {
    const snip = arteSnippet(v);
    return `
    <button class="vcard" data-v="${arte.shown + k}">
      <span class="vthumb"><img data-src="${yt(v.id, 'sddefault')}" data-srcset="${yt(v.id, 'sddefault')} 640w, ${yt(v.id, 'hq720')} 1280w"
        sizes="(min-width: 700px) 340px, 100vw" data-alt="${yt(v.id, 'hqdefault')}" alt="" referrerpolicy="no-referrer"><span class="dur">${duration(v.duration)}</span></span>
      <span class="vt">${esc(v.title)}</span>${snip ? `<span class="vd">${snip}</span>` : ''}
      <span class="vm">${esc(v.program || v.channel)} · ${v.date ? esc(fmtShort.format(new Date(v.date + 'T12:00:00'))) : ''}${v.views ? ' · ' + fmtNum.format(v.views) + ' vues' : ''}</span>
      <span class="vm">${v.subjects.concat(v.regions || []).map((s) => esc(label[s] || s)).join(' · ')}</span>
    </button>`;
  }).join('');
  arte.shown += slice.length;
  const grid = $('#arte-grid');
  grid.insertAdjacentHTML('beforeend', html);
  lazy(grid);
}
function openVideo(v) {
  openSheet(`
    <div class="player">${ytFrame(v.id)}</div>
    <div class="sheet-content">
      <div class="meta"><b>${esc(v.program || v.channel)}</b><span class="dot">${duration(v.duration)}</span>${v.date ? `<span class="dot">${esc(fmtShort.format(new Date(v.date + 'T12:00:00')))}</span>` : ''}</div>
      <h1>${esc(v.title)}</h1>
      ${v.desc ? `<p class="lead">${esc(v.desc)}</p>` : ''}
      <a class="btn" href="https://www.youtube.com/watch?v=${esc(v.id)}" target="_blank" rel="noopener">Ouvrir dans YouTube<svg viewBox="0 0 24 24"><use href="#i-ext"/></svg></a>
    </div>`);
}

/* ---------------------------------------------------------------- 5. Recherche */
const rs = { curated: null, theme: '' };
const OA_SELECT = 'id,display_name,publication_year,authorships,primary_location,cited_by_count,doi,open_access,language,abstract_inverted_index';

async function initResearch() {
  $('#rs-form').addEventListener('submit', (ev) => { ev.preventDefault(); $('#rs-q').blur(); runSearch(); });
  for (const id of ['rs-lang', 'rs-sort', 'rs-since']) $('#' + id).addEventListener('change', () => { if ($('#rs-q').value.trim()) runSearch(); });
  $('#rs-q').addEventListener('search', () => { if (!$('#rs-q').value.trim()) renderCurated(); });
  try { rs.curated = await getJSON('research.json'); } catch { rs.curated = null; }
  renderCurated();
  Synthese.bar();
}
const rsPapers = window.rsPapers = new Map();  // articles affichés, pour la synthèse par l'IA (synthese.js)
function paperHTML(p) {
  const link = p.pdf || p.url;
  const lang = (p.lang || '').slice(0, 2).toUpperCase();
  const k = Synthese.key(p);
  rsPapers.set(k, p);
  return `<article class="paper">
    <button class="pick" data-pick="${esc(k)}" aria-pressed="${Synthese.isSelected(p)}">${Synthese.isSelected(p) ? '✓ Choisi' : '＋ Synthèse'}</button>
    <a class="t" href="${href(link)}" target="_blank" rel="noopener">${esc(p.title)}</a>
    <div class="m">${esc(p.authors || 'Auteurs non précisés')}${p.year ? ' · ' + p.year : ''}${p.venue ? ' · <i>' + esc(p.venue) + '</i>' : ''}</div>
    <div class="badges">${p.cited != null ? `<span class="badge">Cité ${fmtNum.format(p.cited)} fois</span>` : ''}${p.pdf ? '<span class="badge oa">Accès libre</span>' : ''}${lang ? `<span class="badge">${lang}</span>` : ''}<span class="badge">${esc(p.src)}</span></div>
    ${p.abstract ? `<details><summary>Résumé</summary><p>${esc(p.abstract)}</p></details>` : ''}
    <div class="acts">${p.pdf ? `<a href="${href(p.pdf)}" target="_blank" rel="noopener">Lire le texte<svg viewBox="0 0 24 24"><use href="#i-ext"/></svg></a>` : ''}${p.url && p.url !== p.pdf ? `<a href="${href(p.url)}" target="_blank" rel="noopener">Fiche de l’article<svg viewBox="0 0 24 24"><use href="#i-ext"/></svg></a>` : ''}</div>
  </article>`;
}
function renderCurated() {
  const box = $('#rs-results');
  const c = rs.curated;
  if (!c) { box.innerHTML = '<p class="empty">Tapez des mots-clés pour chercher parmi des millions de publications scientifiques (OpenAlex, HAL).</p>'; return; }
  const ids = Object.keys(c.themes).filter((id) => c.themes[id].length);
  if (!rs.theme || !ids.includes(rs.theme)) rs.theme = ids[0];
  const upd = new Date(c.updated);
  box.innerHTML = `
    <p class="status">Sélection du trimestre · mise à jour le ${esc(fmtShort.format(upd))} · prochaine le ${esc(fmtShort.format(new Date(c.next + 'T12:00:00')))}</p>
    <div class="chips scroll-x" id="rs-themes" style="margin-bottom:6px">${ids.map((id) => { const t = themeById(id); return `<button class="chip filters-chip" data-t="${id}" aria-pressed="${id === rs.theme}">${t ? t.emoji + ' ' + esc(t.label) : id}</button>`; }).join('')}</div>
    <div id="rs-curated"></div>`;
  const draw = () => {
    let html = '', last = '';
    for (const p of c.themes[rs.theme]) {
      if (p.group !== last) { html += `<div class="group-h">${esc(p.group)}</div>`; last = p.group; }
      html += paperHTML(p);
    }
    $('#rs-curated').innerHTML = html;
  };
  $('#rs-themes').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-t]');
    if (!b) return;
    rs.theme = b.dataset.t;
    $$('[data-t]', $('#rs-themes')).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    draw();
  });
  draw();
}
function oaAbstract(inv) {
  if (!inv) return '';
  const words = [];
  for (const [w, ps] of Object.entries(inv)) for (const p of ps) words[p] = w;
  return words.filter(Boolean).join(' ');
}
async function searchOpenAlex(q, lang, sort, since) {
  const clean = q.replace(/[,|:]/g, ' ').trim();
  const f = ['type:article|review', lang ? 'language:' + lang : 'language:fr|en', `to_publication_date:${todayISO()}`];
  if (since) f.push(`from_publication_date:${since}-01-01`);
  let url = 'https://api.openalex.org/works?per_page=25&select=' + OA_SELECT;
  if (sort === 'relevance') url += `&search=${encodeURIComponent(clean)}&filter=${f.join(',')}`;
  else if (sort === 'cited') url += `&filter=title.search:${encodeURIComponent(clean)},${f.join(',')}&sort=cited_by_count:desc`;
  else url += `&filter=title_and_abstract.search:${encodeURIComponent(clean)},${f.join(',')}&sort=publication_date:desc`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('OpenAlex ' + res.status);
  const d = await res.json();
  return d.results.map((w) => ({
    title: w.display_name, year: w.publication_year, cited: w.cited_by_count, lang: w.language, src: 'OpenAlex',
    authors: (w.authorships || []).slice(0, 3).map((a) => a.author?.display_name).filter(Boolean).join(', ') + ((w.authorships || []).length > 3 ? ' et al.' : ''),
    venue: w.primary_location?.source?.display_name, url: w.doi || w.primary_location?.landing_page_url || w.id,
    pdf: w.open_access?.oa_url, abstract: oaAbstract(w.abstract_inverted_index),
  }));
}
async function searchHAL(q, lang, sort, since) {
  const params = new URLSearchParams({ q, wt: 'json', rows: '10', fl: 'title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,doiId_s,abstract_s,fileMain_s,language_s' });
  params.append('fq', 'docType_s:(ART OR COMM OR OUV OR COUV)');
  if (lang) params.append('fq', 'language_s:' + lang);
  params.append('fq', `producedDateY_i:[${since || '*'} TO ${new Date().getFullYear()}]`);
  if (sort === 'recent') params.set('sort', 'producedDate_tdate desc');
  const res = await fetch('https://api.archives-ouvertes.fr/search/?' + params);
  if (!res.ok) throw new Error('HAL ' + res.status);
  const d = await res.json();
  return d.response.docs.map((x) => ({
    title: (x.title_s || [''])[0], year: x.producedDateY_i, cited: null, lang: (x.language_s || [''])[0], src: 'HAL',
    authors: (x.authFullName_s || []).slice(0, 3).join(', ') + ((x.authFullName_s || []).length > 3 ? ' et al.' : ''),
    venue: x.journalTitle_s, url: x.doiId_s ? 'https://doi.org/' + x.doiId_s : x.uri_s, pdf: x.fileMain_s,
    abstract: (x.abstract_s || [''])[0] || '',
  }));
}
async function searchCrossref(q) {
  const res = await fetch(`https://api.crossref.org/works?query.bibliographic=${encodeURIComponent(q)}&rows=20&select=title,author,issued,container-title,is-referenced-by-count,DOI,abstract`);
  if (!res.ok) throw new Error('Crossref ' + res.status);
  const d = await res.json();
  return d.message.items.map((w) => ({
    title: (w.title || [''])[0], year: w.issued?.['date-parts']?.[0]?.[0], cited: w['is-referenced-by-count'], lang: '', src: 'Crossref',
    authors: (w.author || []).slice(0, 3).map((a) => [a.given, a.family].filter(Boolean).join(' ')).join(', '),
    venue: (w['container-title'] || [])[0], url: 'https://doi.org/' + w.DOI, pdf: null,
    abstract: (w.abstract || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(),
  }));
}
let searchSeq = 0;
async function runSearch() {
  const q = $('#rs-q').value.trim();
  if (!q) { renderCurated(); return; }
  const box = $('#rs-results');
  const seq = ++searchSeq;
  const lang = $('#rs-lang').value, sort = $('#rs-sort').value, since = $('#rs-since').value;
  box.innerHTML = '<p class="status">Recherche en cours…</p>';
  const [oa, hal] = await Promise.allSettled([searchOpenAlex(q, lang, sort, since), searchHAL(q, lang, sort, since)]);
  let found = oa.status === 'fulfilled' ? oa.value : [];
  if (oa.status !== 'fulfilled') { try { found = await searchCrossref(q); } catch { /* rien */ } }
  if (hal.status === 'fulfilled') found = found.concat(hal.value);
  const seen = new Set();
  let papers = found.filter((p) => {
    const key = norm(p.title).slice(0, 70);
    if (!p.title || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  if (sort === 'recent') papers.sort((a, b) => (b.year || 0) - (a.year || 0));
  if (seq !== searchSeq) return;
  box.innerHTML = papers.length
    ? `<p class="status">${papers.length} résultats pour « ${esc(q)} »</p>` + papers.map(paperHTML).join('')
    : `<p class="empty">Aucun résultat pour « ${esc(q)} ».<br>Essayez d’autres mots, en français ou en anglais.</p>`;
}

/* ---------------------------------------------------------------- réglages */
function openSettings() {
  const fav = interests();
  const custom = customThemes();
  const idx = state.index;
  openSheet(`<div class="settings">
    <h2>Réglages</h2>
    <h3>Mes régions</h3>
    <p class="small">Choisissez les régions du fil « À la une », leur ordre et le nombre d’articles par jour.</p>
    <div id="st-regions">${regionPrefs().map((r, i, all) => `<div class="reg-row${r.on ? '' : ' off'}" data-id="${r.id}">
      <button class="chip" data-tog aria-pressed="${r.on}"><span class="nm">${REGIONS[r.id].flag} ${REGIONS[r.id].label}</span><em>${r.on ? 'Affichée' : 'Masquée'}</em></button>
      <select data-n aria-label="Nombre d’articles">${[1, 2, 3, 5, 10, 20, ALL].map((n) => `<option value="${n}"${n === r.n ? ' selected' : ''}>${n === ALL ? 'Tous' : n}</option>`).join('')}</select>
      <button class="icon-btn" data-move="-1" aria-label="Monter"${i === 0 ? ' disabled' : ''}>↑</button>
      <button class="icon-btn" data-move="1" aria-label="Descendre"${i === all.length - 1 ? ' disabled' : ''}>↓</button>
    </div>`).join('')}</div>
    <h3>Traduction</h3>
    <p class="small">Lire en français les articles en anglais (Europe, États-Unis) et en espagnol (Amérique latine) : titres, résumés, textes complets et schémas. Traduction automatique et gratuite, préparée chaque matin par le robot. Dans chaque article, un bouton permet de revenir au texte d’origine.</p>
    <div class="reg-row" id="st-translate"><button class="chip" data-tog aria-pressed="${translating()}"><span class="nm">🌐 Traduire en français</span><em>${translating() ? 'Activée' : 'Désactivée'}</em></button></div>
    <h3>Lecture intégrale</h3>
    <p class="small">Votre code de lecture personnel permet de lire les articles en accès libre en entier dans ACTU. Il se saisit une seule fois.</p>
    <form id="st-code-form">
      <label class="field"><span>Code de lecture</span><input id="st-code" value="${esc(reader.code())}" placeholder="XXXX-XXXX-XXXX-XXXX" autocapitalize="characters" autocomplete="off" spellcheck="false"></label>
      <button class="btn" style="width:100%">Enregistrer le code</button>
      <p class="small" id="st-code-msg"></p>
    </form>
    <h3>Mes centres d’intérêt</h3>
    <p class="small">Les articles de ces thèmes passent en priorité dans « À la une ».</p>
    <div class="chips" id="st-fav">${state.themes.map((t) => `<button class="chip" data-id="${t.id}" aria-pressed="${fav.has(t.id)}">${t.emoji} ${esc(t.label)}</button>`).join('')}</div>
    <h3>Mes thèmes personnalisés</h3>
    <div id="st-custom">${custom.map((t, i) => `<div class="custom"><div><b>✦ ${esc(t.label)}</b><small>${esc(t.keywords.join(', '))}</small></div><button class="icon-btn" data-del="${i}" aria-label="Supprimer ${esc(t.label)}"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg></button></div>`).join('') || '<p class="small">Aucun pour l’instant.</p>'}</div>
    <form id="st-form">
      <label class="field"><span>Nom du thème</span><input id="st-name" placeholder="ex. Climat" required maxlength="30"></label>
      <label class="field"><span>Mots-clés, séparés par des virgules (français, anglais ou espagnol)</span><input id="st-kw" placeholder="ex. climat, CO2, réchauffement, climate" required></label>
      <button class="btn" style="width:100%">Ajouter ce thème</button>
    </form>
    <h3>Mises à jour</h3>
    <div class="kv"><span>Dernière édition</span><span>${idx?.updated ? esc(cap(fmtLong.format(new Date(idx.updated)))) + ' à ' + esc(fmtTime.format(new Date(idx.updated))) : '—'}</span></div>
    <div class="kv"><span>Prochaine</span><span>Chaque matin à 10h</span></div>
    <div class="kv"><span>Recherche scientifique</span><span>Tous les 3 mois</span></div>
    <div class="btn-row"><button class="btn" data-action="reload">Actualiser maintenant</button></div>
    <h3>Stockage</h3>
    <p class="small">ACTU ne garde sur ce téléphone que vos réglages (quelques octets) et la coquille de l’application (≈ 100 Ko) pour démarrer vite. Articles, vidéos et images sont lus en direct sur internet.</p>
    <div class="btn-row"><button class="btn" id="st-clear">Vider le cache</button></div>
    <h3>Installer sur l’iPhone</h3>
    <p class="small">Dans Safari : touchez le bouton Partager, puis « Sur l’écran d’accueil ». L’icône ACTU apparaît comme une application.</p>
    <h3>À propos</h3>
    <p class="small">Sélection automatique parmi ${'≈ 90'} flux de journaux (France ; Europe en anglais ; États-Unis ; Amérique latine en espagnol), publications YouTube et Bluesky des médias et créateurs d’information, replays TF1+ et france.tv, ARTE sur YouTube, OpenAlex et HAL. Version ${VERSION}.</p>
  </div>`, (body) => {
    const saveRegions = () => {
      store.set('regions', $$('.reg-row', body).map((row) => ({ id: row.dataset.id, on: $('[data-tog]', row).getAttribute('aria-pressed') === 'true', n: +$('[data-n]', row).value })));
      state.dirty = true;
    };
    $('#st-regions', body).addEventListener('click', (ev) => {
      const tog = ev.target.closest('[data-tog]');
      if (tog) {
        const on = tog.getAttribute('aria-pressed') !== 'true';
        tog.setAttribute('aria-pressed', String(on));
        $('em', tog).textContent = on ? 'Affichée' : 'Masquée';
        tog.closest('.reg-row').classList.toggle('off', !on);
        saveRegions();
      }
      const mv = ev.target.closest('[data-move]');
      if (mv) {
        const row = mv.closest('.reg-row');
        if (+mv.dataset.move < 0 && row.previousElementSibling) row.parentNode.insertBefore(row, row.previousElementSibling);
        if (+mv.dataset.move > 0 && row.nextElementSibling) row.parentNode.insertBefore(row.nextElementSibling, row);
        saveRegions();
        const scroll = sheet.body.scrollTop;
        openSettings();
        sheet.body.scrollTop = scroll;
      }
    });
    $('#st-regions', body).addEventListener('change', saveRegions);
    $('#st-translate', body).addEventListener('click', (ev) => {
      const tog = ev.target.closest('[data-tog]');
      if (!tog) return;
      const on = tog.getAttribute('aria-pressed') !== 'true';
      tog.setAttribute('aria-pressed', String(on));
      $('em', tog).textContent = on ? 'Activée' : 'Désactivée';
      store.set('translate', on);
      state.dirty = true;
    });
    $('#st-code-form', body).addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const msg = $('#st-code-msg', body);
      store.set('readcode', $('#st-code', body).value.trim().toUpperCase());
      reader.reset();
      state.dirty = true;
      if (!reader.code()) { msg.textContent = 'Code effacé.'; return; }
      msg.textContent = 'Vérification…';
      try { await reader.texts(state.index.days[0]); msg.textContent = '✓ Code valide : les articles libres se lisent maintenant en entier.'; }
      catch (e) { msg.textContent = e.message === 'badcode' ? '✗ Code incorrect.' : e.message === 'old' ? 'Mettez à jour iOS (16.4 ou plus).' : 'Impossible de vérifier (connexion ?).'; }
    });
    $('#st-fav', body).addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-id]');
      if (!b) return;
      const on = b.getAttribute('aria-pressed') !== 'true';
      b.setAttribute('aria-pressed', String(on));
      store.set('interests', $$('#st-fav [aria-pressed="true"]', body).map((x) => x.dataset.id));
      state.dirty = true;
    });
    $('#st-custom', body).addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-del]');
      if (!b) return;
      const list = store.get('custom', []);
      list.splice(+b.dataset.del, 1);
      store.set('custom', list);
      state.dirty = true;
      openSettings();
    });
    $('#st-form', body).addEventListener('submit', (ev) => {
      ev.preventDefault();
      const label = $('#st-name', body).value.trim();
      const keywords = $('#st-kw', body).value.split(/[,;]+/).map((k) => k.trim()).filter(Boolean);
      if (!label || !keywords.length) return;
      const list = store.get('custom', []);
      list.push({ id: 'c-' + norm(label).trim().replace(/ /g, '-') + '-' + Date.now().toString(36), label, keywords });
      store.set('custom', list);
      state.dirty = true;
      toast(`Thème « ${esc(label)} » ajouté`);
      openSettings();
    });
    $('#st-clear', body).addEventListener('click', async () => {
      try { for (const k of await caches.keys()) await caches.delete(k); } catch { /* pas de cache */ }
      location.reload();
    });
  });
}
/** Après un changement de réglages : on reconstruit les vues concernées. */
function applySettings() {
  if (!state.dirty) return;
  state.dirty = false;
  for (const a of allLoadedArticles()) delete a._themes;
  initFeed();
  if (state.inited.has('explore')) { renderThemeChips(); refreshExplore(true); }
}
function* allLoadedArticles() {
  for (const d of state.loaded.values()) for (const r of Object.values(d.regions)) yield* r;
}

/* ---------------------------------------------------------------- onglets */
const INIT = { explore: initExplore, replay: initReplay, arte: initArte, research: initResearch };
function showTab(name) {
  document.body.classList.toggle('on-feed', name === 'feed');
  $$('.view').forEach((v) => v.classList.toggle('active', v.id === 'view-' + name));
  $$('.tabbar button').forEach((b) => (b.dataset.tab === name ? b.setAttribute('aria-current', 'page') : b.removeAttribute('aria-current')));
  if (INIT[name] && !state.inited.has(name)) { state.inited.add(name); INIT[name](); }
}

/* ---------------------------------------------------------------- démarrage */
async function checkUpdate() {
  try {
    const idx = await getJSON('index.json', true);
    if (state.index && idx.updated !== state.index.updated) {
      toast('Nouvelle édition disponible <button data-action="reload">Afficher</button>', 0);
    }
  } catch { /* hors connexion */ }
}

async function boot() {
  sheet.el = $('#sheet');
  sheet.body = $('#sheet-body');
  document.addEventListener('click', (ev) => {
    const act = ev.target.closest('[data-action]')?.dataset.action;
    if (act === 'close') closeSheet();
    else if (act === 'settings') openSettings();
    else if (act === 'reload') location.reload();
    else if (act === 'show-regions') { store.set('regions', regionPrefs().map((r) => ({ ...r, on: true }))); initFeed(); }
    else if (act === 'hide-install') { $('#install').hidden = true; store.set('installHidden', true); }
    const tab = ev.target.closest('[data-tab]')?.dataset.tab;
    if (tab) {
      if (tab === 'feed' && $('#view-feed').classList.contains('active')) feed.el.scrollTo({ top: 0, behavior: 'smooth' });
      showTab(tab);
    }
  });
  window.addEventListener('popstate', () => {
    if (MindMap.exitFullscreen()) return;  // retour : on quitte d'abord le plein écran du schéma
    if (sheet.open) { closeSheet(true); applySettings(); }
  });
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') closeSheet(); });
  sheet.el.addEventListener('transitionend', () => { if (!sheet.open) applySettings(); });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && Date.now() - state.lastCheck > 20 * 60e3) { state.lastCheck = Date.now(); checkUpdate(); }
  });

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const standalone = navigator.standalone || matchMedia('(display-mode: standalone)').matches;
  if (isIOS && !standalone && !store.get('installHidden', false)) $('#install').hidden = false;

  try {
    const [index, themes] = await Promise.all([getJSON('index.json', true), fetch('themes.json').then((r) => r.json())]);
    state.index = index;
    state.themes = themes;
  } catch {
    $('#feed').innerHTML = '<div class="slide end-slide"><h2>Pas de connexion</h2><p>ACTU a besoin d’internet pour charger les articles.</p><button class="btn" data-action="reload">Réessayer</button></div>';
    return;
  }
  initFeed();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
}

boot();
