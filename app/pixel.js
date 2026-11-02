/* ACTU — petites scènes pixel art animées qui résument un article.
   Tout est dessiné sur le téléphone à partir d'une courte description (décor, costumes, objet, drapeaux, étiquette)
   préparée par le robot : aucune image à télécharger. Seule la scène visible est animée (≈ 8 images/seconde). */
'use strict';

const Pixel = (() => {
  const FPS = 8;
  /* ------------------------------------------------------------ hasard reproductible */
  function hash(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) h = Math.imul(h ^ str.charCodeAt(i), 16777619);
    return h >>> 0;
  }
  function rng(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* ------------------------------------------------------------ palettes (inspirées des couchers de soleil pixel art) */
  const SKIES = {
    day: { sky: ['#6fb7ee', '#8cc6f1', '#a9d4f3', '#c6e2f5', '#e2f0f8'], sun: '#fff3b0', far: '#9fb3d9', mid: '#6f86c2', near: '#4d5f9e', ground: '#5d7a4a', ground2: '#4a6339' },
    sunset: { sky: ['#93bdeb', '#afc3ee', '#d2d3f1', '#f1dfe8', '#fbd4d1'], sun: '#ff8a8a', far: '#9aa6cf', mid: '#5c64a8', near: '#4f2d47', ground: '#5a2027', ground2: '#46181e' },
    dusk: { sky: ['#3d3b6e', '#5c4f8b', '#8a6aa4', '#c38aa9', '#efb4a3'], sun: '#ff9d6b', far: '#6a5a8e', mid: '#4a3f70', near: '#2f2745', ground: '#3a2a3a', ground2: '#2a1d2b' },
    night: { sky: ['#0a0f2e', '#111a44', '#1a2758', '#26346b', '#33427a'], sun: '#f4f0cf', far: '#26315e', mid: '#1c2449', near: '#121733', ground: '#1d2236', ground2: '#151928' },
    grey: { sky: ['#5f636e', '#767b87', '#8e929d', '#a6aab3', '#bdc0c7'], sun: '#d9d4c7', far: '#7b7f88', mid: '#5f626b', near: '#46484f', ground: '#4b4540', ground2: '#3a3531' },
  };
  const SKIN = ['#f2c9a0', '#e0ac69', '#c68642', '#8d5524', '#ffdcb5'];
  const HAIR = ['#2b1d14', '#4a3121', '#7a4b2a', '#d1a85a', '#141414', '#9a9a9a'];
  const SHIRT = ['#d9534f', '#3b7dd8', '#f0ad4e', '#5cb85c', '#9b59b6', '#e67e22', '#1abc9c'];

  /* ------------------------------------------------------------ police 3×5 pour l'étiquette */
  const FONT = {
    A: '010101111101101', B: '110101110101110', C: '011100100100011', D: '110101101101110', E: '111100110100111',
    F: '111100110100100', G: '011100101101011', H: '101101111101101', I: '111010010010111', J: '001001001101010',
    K: '101101110101101', L: '100100100100111', M: '101111111101101', N: '110101101101101', O: '010101101101010',
    P: '110101110100100', Q: '010101101110011', R: '110101110101101', S: '011100010001110', T: '111010010010010',
    U: '101101101101111', V: '101101101101010', W: '101101111111101', X: '101101010101101', Y: '101101010010010',
    Z: '111001010100111', 0: '111101101101111', 1: '010110010010111', 2: '110001010100111', 3: '110001010001110',
    4: '101101111001001', 5: '111100110001110', 6: '011100111101111', 7: '111001010010010', 8: '111101111101111',
    9: '111101111001110', '-': '000000111000000', ' ': '000000000000000', '.': '000000000000010', '!': '010010010000010',
  };

  /* ------------------------------------------------------------ drapeaux (bandes simplifiées) */
  const FLAGS = {
    fr: ['v', '#1c3f94', '#ffffff', '#e1242b'], de: ['h', '#000000', '#dd0000', '#ffce00'], it: ['v', '#009246', '#ffffff', '#ce2b37'],
    es: ['h', '#aa151b', '#f1bf00', '#aa151b'], ua: ['h', '#0057b7', '#ffd700'], ru: ['h', '#ffffff', '#0039a6', '#d52b1e'],
    pl: ['h', '#ffffff', '#dc143c'], be: ['v', '#000000', '#fdda24', '#ef3340'], ie: ['v', '#169b62', '#ffffff', '#ff883e'],
    nl: ['h', '#ae1c28', '#ffffff', '#21468b'], bg: ['h', '#ffffff', '#00966e', '#d62612'], se: ['cross', '#006aa7', '#fecc00'],
    us: ['us'], gb: ['cross', '#012169', '#c8102e', '#ffffff'], eu: ['eu'], nato: ['nato'], mx: ['v', '#006847', '#ffffff', '#ce1126'],
    ar: ['h', '#74acdf', '#ffffff', '#74acdf'], br: ['br'], co: ['h', '#fcd116', '#fcd116', '#003893', '#ce1126'],
    ve: ['h', '#ffcc00', '#00247d', '#cf142b'], cl: ['h', '#ffffff', '#d52b1e'], pe: ['v', '#d91023', '#ffffff', '#d91023'],
    cn: ['h', '#de2910'], jp: ['dot', '#ffffff', '#bc002d'], il: ['h', '#ffffff', '#0038b8', '#ffffff'], ir: ['h', '#239f40', '#ffffff', '#da0000'],
    in: ['h', '#ff9933', '#ffffff', '#138808'], tr: ['dot', '#e30a17', '#ffffff'], ca: ['v', '#d52b1e', '#ffffff', '#d52b1e'],
    cu: ['h', '#002a8f', '#ffffff', '#002a8f'], ps: ['h', '#000000', '#ffffff', '#007a3d'], lb: ['h', '#ed1c24', '#ffffff', '#ed1c24'],
  };

  /* ------------------------------------------------------------ outils de dessin */
  function painter(ctx) {
    const p = (x, y, c, w = 1, h = 1) => { ctx.fillStyle = c; ctx.fillRect(x | 0, y | 0, w, h); };
    // sprite : lignes de caractères, chaque lettre = une couleur de la palette, '.' = transparent
    p.sprite = (rows, pal, x, y, flip = false) => {
      for (let j = 0; j < rows.length; j++) {
        const r = rows[j];
        for (let i = 0; i < r.length; i++) {
          const c = pal[r[i]];
          if (c) p(x + (flip ? r.length - 1 - i : i), y + j, c);
        }
      }
    };
    p.text = (str, x, y, c) => {
      let cx = x;
      for (const ch of str) {
        const g = FONT[ch] || FONT[' '];
        for (let k = 0; k < 15; k++) if (g[k] === '1') p(cx + (k % 3), y + ((k / 3) | 0), c);
        cx += 4;
      }
    };
    return p;
  }
  const textWidth = (s) => s.length * 4 - 1;
  const strip = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9 .!-]/g, '');

  /* ------------------------------------------------------------ ciel tramé (bandes + damier de transition) */
  function sky(p, W, H, pal, horizon) {
    const bands = pal.sky;
    const bh = Math.ceil(horizon / bands.length);
    for (let y = 0; y < horizon; y++) {
      const b = Math.min(bands.length - 1, (y / bh) | 0);
      const inEdge = y % bh >= bh - 3 && b < bands.length - 1;
      if (!inEdge) { p(0, y, bands[b], W, 1); continue; }
      const k = y % bh - (bh - 3); // 0,1,2 : trame de plus en plus dense
      for (let x = 0; x < W; x++) {
        const next = k === 0 ? (x % 4 === 0 && y % 2 === 0) : k === 1 ? (x + y) % 2 === 0 : (x % 4 !== 1);
        p(x, y, next ? bands[b + 1] : bands[b]);
      }
    }
  }
  function disc(p, cx, cy, R, color) {
    for (let y = -R; y <= R; y++) { const w = Math.round(Math.sqrt(R * R - y * y)); p(cx - w, cy + y, color, w * 2 + 1, 1); }
  }
  function ridge(p, W, top, base, color, r, rough, bottom) {
    const a1 = r() * 6, a2 = r() * 6, f1 = 0.05 + r() * 0.08, f2 = 0.15 + r() * 0.2;
    for (let x = 0; x < W; x++) {
      const h = Math.sin(x * f1 + a1) * rough + Math.sin(x * f2 + a2) * rough * 0.35;
      const y = Math.round(base - (base - top) * 0.5 - h);
      p(x, y, color, 1, bottom - y);
    }
  }

  /* ------------------------------------------------------------ personnages */
  // tête 7×5, buste 7×4, jambes 7×3 ; S peau, H cheveux, E yeux, T haut, A accent, L bas, F chaussures, X/Y/Z couleurs du costume
  const HEADS = {
    hair: ['..HHH..', '.HHHHH.', '.HSSSH.', '.SESES.', '..SSS..'],
    long: ['..HHH..', '.HHHHH.', 'HHSSSHH', 'HSESESH', 'H.SSS.H'],
    helmet: ['..XXX..', '.XXXXX.', 'XXXXXXX', '.SESES.', '..SSS..'],
    cap: ['..XXX..', '.XXXXXX', '.HSSS..', '.SESES.', '..SSS..'],
    hard: ['..YYY..', '.YYYYY.', 'YYYYYYY', '.SESES.', '..SSS..'],
    straw: ['..YYY..', 'YYYYYYY', '.HSSSH.', '.SESES.', '..SSS..'],
    beret: ['.XXX...', 'XXXXXX.', '.HSSSH.', '.SESES.', '..SSS..'],
    wig: ['..WWW..', '.WWWWW.', 'WWSSSWW', 'WSESESW', 'W.SSS.W'],
    bubble: ['..WWW..', '.WZZZW.', 'WZZZZZW', 'WZZZZZW', '.WWWWW.'],
    hood: ['..XXX..', '.XXXXX.', 'XXSSSXX', 'XSESESX', '.XSSSX.'],
    band: ['..HHH..', '.YYYYY.', '.HSSSH.', '.SESES.', '..SSS..'],
    zucchetto: ['..WWW..', '.HHHHH.', '.HSSSH.', '.SESES.', '..SSS..'],
    fire: ['..XXX..', '.XXXXX.', 'XXXXXXX', '.SESES.', '.YSSSY.'],
    racer: ['..XXX..', '.XXXXX.', 'XZZZZZX', 'XXXXXXX', '.XXXXX.'],
  };
  const BODIES = {
    plain: ['.TTTTT.', 'TTTTTTT', 'TTTTTTT', 'S.TTT.S'],
    suit: ['.TWAWT.', 'TTWATTT', 'TTTATTT', 'S.TTT.S'],
    coat: ['.WWWWW.', 'WWWAWWW', 'WWWWWWW', 'S.WWW.S'],
    cross: ['.WWWWW.', 'WWAWWWW', 'WAAAWWW', 'S.WAW.S'],
    camo: ['.TTZTT.', 'TZTTTZT', 'TTTZTTT', 'S.TZT.S'],
    badge: ['.TTTTT.', 'TTYTTTT', 'TTTTTTT', 'S.ZZZ.S'],
    vest: ['.YYTYY.', 'YYTTTYY', 'WWWWWWW', 'S.YYY.S'],
    stripes: ['.WWWWW.', 'TTTTTTT', 'WWWWWWW', 'S.TTT.S'],
    robe: ['.TTTTT.', 'TTTWTTT', 'TTTTTTT', 'STTTTTS'],
    jersey: ['.TTTTT.', 'TTWTWTT', 'TTWWWTT', 'S.TTT.S'],
    dress: ['.TTTTT.', '.TTTTT.', 'TTTTTTT', 'STTTTTS'],
    space: ['.WWWWW.', 'WWZZWWW', 'WWWWWWW', 'W.WWW.W'],
    overall: ['.TTTTT.', 'TXTTTXT', 'TXXXXXT', 'S.XXX.S'],
  };
  const LEGS = { pants: ['.LLLLL.', '.LL.LL.', '.FF.FF.'], skirt: ['TTTTTTT', '..S.S..', '..F.F..'], robe: ['.TTTTT.', '.TTTTT.', '.FF.FF.'] };
  // costume : tête, buste, jambes, couleurs (T haut, A accent, L bas, X Y Z), objet tenu
  const COSTUMES = {
    citizen: { head: 'hair', body: 'plain', legs: 'pants', L: '#34495e' },
    journalist: { head: 'hair', body: 'suit', legs: 'pants', T: '#5b6472', A: '#3b7dd8', L: '#2c3e50', item: 'mic' },
    politician: { head: 'hair', body: 'suit', legs: 'pants', T: '#22283a', A: '#c0392b', L: '#1b2030', item: 'case' },
    business: { head: 'hair', body: 'suit', legs: 'pants', T: '#4b5563', A: '#2563eb', L: '#374151', item: 'case' },
    soldier: { head: 'helmet', body: 'camo', legs: 'pants', T: '#5d6b3a', Z: '#3e4826', X: '#4b5a2a', L: '#55613a', F: '#2a2a1f' },
    police: { head: 'cap', body: 'badge', legs: 'pants', T: '#24427a', X: '#1a2f57', Y: '#f1c40f', Z: '#111827', L: '#1a2f57' },
    doctor: { head: 'hair', body: 'cross', legs: 'pants', A: '#e74c3c', L: '#2bb3a0' },
    scientist: { head: 'hair', body: 'coat', legs: 'pants', A: '#3498db', L: '#555c66', item: 'flaskhand' },
    athlete: { head: 'band', body: 'jersey', legs: 'pants', Y: '#ffffff', L: '#f2c9a0' },
    racer: { head: 'racer', body: 'jersey', legs: 'pants', X: '#d62828', Z: '#9ad1ff', T: '#d62828', L: '#d62828' },
    worker: { head: 'hard', body: 'vest', legs: 'pants', T: '#3b5b8c', Y: '#f39c12', L: '#2f4a73' },
    farmer: { head: 'straw', body: 'overall', legs: 'pants', T: '#c0392b', X: '#3d6fb6', Y: '#e8c46a', L: '#3d6fb6' },
    judge: { head: 'wig', body: 'robe', legs: 'robe', T: '#151515', item: 'gavelhand' },
    astronaut: { head: 'bubble', body: 'space', legs: 'pants', Z: '#5aa9e6', L: '#e8e8e8', F: '#9aa4b0' },
    hacker: { head: 'hood', body: 'plain', legs: 'pants', T: '#262b33', X: '#1d2128', L: '#1d2128', item: 'laptophand' },
    artist: { head: 'beret', body: 'stripes', legs: 'pants', T: '#1f3b73', X: '#151515', L: '#2c2c2c', item: 'brush' },
    musician: { head: 'hair', body: 'plain', legs: 'pants', T: '#151515', L: '#2c2c54', item: 'guitarhand' },
    model: { head: 'long', body: 'dress', legs: 'skirt', T: '#c2185b' },
    protester: { head: 'hair', body: 'plain', legs: 'pants', L: '#2c3e50', item: 'sign' },
    firefighter: { head: 'fire', body: 'vest', legs: 'pants', X: '#c0392b', T: '#2d2d2d', Y: '#f1c40f', L: '#2d2d2d' },
    student: { head: 'hair', body: 'plain', legs: 'pants', L: '#3b5998', item: 'bag' },
    teacher: { head: 'hair', body: 'suit', legs: 'pants', T: '#6d4c41', A: '#f5f5f5', L: '#4e342e', item: 'bookhand' },
    priest: { head: 'zucchetto', body: 'robe', legs: 'robe', T: '#f4f4f4', W: '#f4f4f4' },
  };
  const ITEMS = {
    mic: { rows: ['K', 'K', 'G'], pal: { K: '#222', G: '#888' }, dx: 7, dy: 7 },
    case: { rows: ['.GG.', 'BBBB', 'BBBB'], pal: { G: '#3a2a1a', B: '#7a5230' }, dx: 6, dy: 9 },
    flaskhand: { rows: ['.W.', '.W.', 'GGG'], pal: { W: '#dfe8ee', G: '#4cd964' }, dx: 7, dy: 6 },
    gavelhand: { rows: ['BBB', '.B.', '.B.'], pal: { B: '#8b5a2b' }, dx: 7, dy: 5 },
    laptophand: { rows: ['CCCC', 'GGGG'], pal: { C: '#5ff', G: '#666' }, dx: 6, dy: 8 },
    brush: { rows: ['R', 'B', 'B'], pal: { R: '#e74c3c', B: '#8b5a2b' }, dx: 7, dy: 5 },
    guitarhand: { rows: ['...K', '..K.', 'OOO.', 'OKO.', 'OOO.'], pal: { K: '#3b2a1a', O: '#d2691e' }, dx: 3, dy: 5 },
    sign: { rows: ['WWWWWW', 'WRRRRW', 'WWWWWW', '..B...', '..B...', '..B...'], pal: { W: '#f5f5f5', R: '#e74c3c', B: '#8b5a2b' }, dx: 4, dy: -4 },
    bag: { rows: ['RR', 'RR', 'RR'], pal: { R: '#c0392b' }, dx: -1, dy: 5 },
    bookhand: { rows: ['BBB', 'WWW'], pal: { B: '#2e86de', W: '#fff' }, dx: 6, dy: 8 },
  };

  function drawPerson(p, x, y, costume, look, frame, walking, facing) {
    const c = COSTUMES[costume] || COSTUMES.citizen;
    const pal = {
      S: look.skin, H: look.hair, E: '#1b1b1b', W: c.W || '#f4f4f4', T: c.T || look.shirt, A: c.A || '#ffffff',
      L: c.L || '#34495e', F: c.F || '#1f1f1f', X: c.X || '#333', Y: c.Y || '#f1c40f', Z: c.Z || '#222',
    };
    const blink = (frame + look.phase * 7) % 40 === 0;
    const bob = (((frame + look.phase) >> 1) % 2);
    const head = HEADS[c.head].map((r, j) => (j === 3 && blink ? r.replace(/E/g, 'S') : r));
    let legs = LEGS[c.legs];
    if (walking && frame % 2) legs = legs.map((r, j) => (j > 0 ? r.replace('.FF.FF.', 'FF...FF').replace('.LL.LL.', 'LL...LL') : r));
    const flip = facing < 0;
    p.sprite(head, pal, x, y + bob, flip);
    p.sprite(BODIES[c.body], pal, x, y + 5 + bob, flip);
    p.sprite(legs, pal, x, y + 9, flip);
    const it = c.item && ITEMS[c.item];
    if (it) {
      const lift = c.item === 'sign' ? (((frame + look.phase * 3) >> 2) % 2) * -1 : 0;
      p.sprite(it.rows, it.pal, flip ? x + 6 - it.dx - it.rows[0].length + 1 : x + it.dx, y + it.dy + bob + lift, flip);
    }
  }

  /* ------------------------------------------------------------ décors */
  function stars(p, W, H, r, frame, n = 26) {
    for (let i = 0; i < n; i++) {
      const x = (r() * W) | 0, y = (r() * H) | 0, tw = (frame + i * 5) % 23 < 2;
      p(x, y, tw ? '#ffffff' : '#c9d3ff');
    }
  }
  function clouds(p, W, y0, frame, r, color) {
    for (let i = 0; i < 3; i++) {
      const w = 12 + ((r() * 14) | 0), y = y0 + ((r() * 14) | 0), speed = 0.15 + r() * 0.2;
      const x = ((r() * (W + 40) + frame * speed) % (W + 40)) - 30;
      p(x + 3, y, color, w - 6, 1); p(x + 1, y + 1, color, w - 2, 1); p(x, y + 2, color, w, 2);
    }
  }
  function buildings(p, W, ground, r, color, frame, lit, broken) {
    let x = -2;
    let i = 0;
    while (x < W) {
      const w = 6 + ((r() * 9) | 0), h = 10 + ((r() * 26) | 0);
      const top = ground - h;
      if (broken) {
        for (let k = 0; k < w; k++) p(x + k, top + ((r() * 6) | 0), color, 1, ground - top);
      } else p(x, top, color, w, h);
      for (let wy = top + 3; wy < ground - 3; wy += 4) {
        for (let wx = x + 1; wx < x + w - 1; wx += 3) {
          const on = lit && ((wx * 7 + wy * 3 + ((frame / 6) | 0) * (i % 3 === 0 ? 1 : 0)) % 5 !== 0);
          if (!broken || r() > 0.5) p(wx, wy, on ? '#ffd56b' : 'rgba(0,0,0,.22)', 1, 2);
        }
      }
      x += w + 1 + ((r() * 3) | 0);
      i++;
    }
  }
  function pine(p, x, base, h, color, trunk, sway) {
    p(x, base - 2, trunk, 1, 2);
    for (let j = 0; j < h; j++) {
      const half = Math.floor((j / h) * 3.2) + (j % 2);
      const off = j < h / 2 ? sway : 0;
      p(x - half + off, base - 2 - (h - j), color, half * 2 + 1, 1);
    }
  }

  const BACKDROPS = {
    mountains(s) { const { p, W, G, pal, r } = s; ridge(p, W, G - 34, G - 6, pal.far, r, 7, G); ridge(p, W, G - 22, G - 2, pal.mid, r, 5, G); },
    forest(s) { const { p, W, G, pal, r } = s; ridge(p, W, G - 30, G - 8, pal.far, r, 6, G); },
    // ville : les immeubles (et leurs fenêtres qui s'allument) sont dessinés à chaque image par LIVE
    city(s) { const { p, W, G, pal, r } = s; ridge(p, W, G - 30, G - 14, pal.far, r, 4, G); },
    night(s) { const { p, W, G, pal, r } = s; ridge(p, W, G - 30, G - 14, pal.far, r, 4, G); },
    ruins(s) { const { p, W, G, pal, r } = s; buildings(p, W, G, r, pal.near, 0, false, true); },
    factory(s) {
      const { p, W, G, pal, r } = s;
      ridge(p, W, G - 26, G - 10, pal.far, r, 4, G);
      for (let x = 4; x < W; x += 22) { p(x, G - 14, pal.mid, 16, 14); p(x + 2, G - 30, pal.near, 3, 16); p(x + 9, G - 24, pal.near, 3, 10); }
    },
    parliament(s) {
      const { p, W, G, pal } = s, cx = (W / 2) | 0, c = '#e9e4d8', d = '#c9c2b2';
      p(cx - 22, G - 14, c, 44, 14); p(cx - 24, G - 16, d, 48, 2);
      for (let x = cx - 20; x < cx + 20; x += 5) p(x, G - 13, d, 2, 13);
      p(cx - 9, G - 22, c, 18, 6); p(cx - 6, G - 27, c, 12, 5); p(cx - 3, G - 30, c, 6, 3); p(cx, G - 38, '#555', 1, 8);
      s.flagTop = [cx + 1, G - 38];
      p(0, G - 6, pal.mid, cx - 24, 6); p(cx + 24, G - 6, pal.mid, W - cx - 24, 6);
    },
    court(s) {
      const { p, W, G } = s, cx = (W / 2) | 0, c = '#ddd6c8', d = '#b9b1a1';
      p(cx - 20, G - 16, c, 40, 16);
      for (let j = 0; j < 7; j++) p(cx - 22 + j * 3, G - 23 + j, c, 44 - j * 6, 1);
      for (let x = cx - 17; x < cx + 17; x += 6) p(x, G - 15, d, 2, 15);
    },
    hospital(s) {
      const { p, W, G, pal, r } = s, cx = (W / 2) | 0;
      buildings(p, W, G, r, pal.far, 0, false, false);
      p(cx - 16, G - 30, '#f2f2f2', 32, 30);
      for (let y = G - 26; y < G - 4; y += 5) for (let x = cx - 13; x < cx + 13; x += 5) p(x, y, '#9cc7e8', 3, 3);
      s.crossAt = [cx, G - 38];
    },
    field(s) { const { p, W, G, pal, r } = s; ridge(p, W, G - 24, G - 6, pal.far, r, 5, G); },
    desert(s) {
      const { p, W, G, r } = s;
      ridge(p, W, G - 16, G - 4, '#d9a066', r, 4, G); ridge(p, W, G - 10, G, '#c88a4f', r, 3, G);
    },
    sea(s) { const { p, W, G } = s; p(0, G - 12, '#2f6fb0', W, 12); },
    space(s) {
      const { p, W, G } = s;
      disc(p, W - 22, 30, 7, '#c97b4a'); disc(p, W - 24, 28, 3, '#dd9a6a'); p(W - 34, 31, '#e8b98a', 24, 1);
      p(0, G - 4, '#2a3b6e', W, 4);
    },
    stadium(s) {
      const { p, W, G } = s;
      for (let k = 0; k < 4; k++) p(0, G - 26 + k * 6, k % 2 ? '#3a3f55' : '#2f3346', W, 6);
      p(6, G - 40, '#888', 1, 14); p(W - 7, G - 40, '#888', 1, 14); p(4, G - 42, '#fffbe0', 5, 2); p(W - 9, G - 42, '#fffbe0', 5, 2);
    },
    stage(s) { const { p, W, G } = s; p(0, G - 3, '#3a2a2a', W, 3); },
  };
  const GROUND = {
    city: '#4a4f5c', night: '#262a38', ruins: '#4a4038', factory: '#55525a', parliament: '#7b8a5e', court: '#8a8170',
    hospital: '#6d7a6a', field: '#8fae4c', desert: '#e0b072', sea: '#d8c08a', space: '#3a3f5c', stadium: '#3f9b4a', stage: '#1a1414',
  };

  /* éléments animés propres à chaque décor */
  const LIVE = {
    forest(s, f) {
      const { p, W, G, rr } = s, r = rr(11);
      for (let i = 0; i < 9; i++) {
        const x = ((i + 0.5) * W) / 9 + ((r() * 6) | 0) - 3, h = 14 + ((r() * 10) | 0);
        const sway = Math.round(Math.sin(f * 0.35 + i) * 1);
        pine(p, x | 0, G, h, i % 2 ? '#2f5d3a' : '#3b6e44', '#4a3423', sway);
      }
      const l = rr(12);
      for (let i = 0; i < 6; i++) { const x = (l() * W + f * 1.4) % W, y = (l() * (G - 10) + f * 0.6) % (G - 4); p(x, y, '#9bc46b'); }
    },
    city(s, f) { const { p, W, G, rr } = s; buildings(p, W, G, rr(3), s.pal.mid, f, s.time === 'night' || s.time === 'dusk', false); },
    night(s, f) { const { p, W, G, rr } = s; buildings(p, W, G, rr(3), s.pal.mid, f, true, false); },
    ruins(s, f) {
      const { p, W, G, rr } = s, r = rr(5);
      for (let c = 0; c < 3; c++) {
        const x0 = 10 + ((r() * (W - 20)) | 0);
        for (let k = 0; k < 7; k++) { const y = G - 10 - ((f * 0.8 + k * 5) % 34), x = x0 + Math.round(Math.sin((y + c) * 0.25) * 2); p(x, y, 'rgba(60,60,60,.55)', 3, 2); }
      }
      if (f % 37 < 2) p(0, G - 3, 'rgba(255,140,60,.35)', W, 3);
    },
    factory(s, f) {
      const { p, W, G } = s;
      for (let x = 4; x < W; x += 22) for (let k = 0; k < 5; k++) {
        const y = G - 32 - ((f * 0.7 + k * 4) % 22);
        p(x + 1 + Math.round(Math.sin(y * 0.3) * 1.5), y, 'rgba(230,230,230,.6)', 4, 2);
      }
    },
    field(s, f) {
      const { p, W, G } = s;
      for (let row = 0; row < 3; row++) for (let x = (row * 2) % 4; x < W; x += 4) {
        const sway = Math.round(Math.sin(f * 0.4 + x * 0.3 + row) * 1);
        p(x + sway, G - 3 + row * 3, row % 2 ? '#d8b45a' : '#c9a24a', 1, 3);
      }
    },
    desert(s, f) {
      const { p, W, G } = s;
      for (let y = G - 22; y < G - 14; y += 2) if ((y + f) % 6 < 2) p((f * 3 + y * 5) % W, y, 'rgba(255,240,200,.35)', 8, 1);
    },
    sea(s, f) {
      const { p, W, G } = s;
      for (let y = G - 11; y < G; y += 3) for (let x = -4; x < W; x += 9) p(x + ((f + y) % 9), y, '#7fb6e6', 4, 1);
    },
    space(s, f) { stars(s.p, s.W, s.G - 6, s.rr(9), f, 34); },
    stadium(s, f) {
      const { p, W, G } = s;
      for (let k = 0; k < 4; k++) for (let x = 1; x < W; x += 2) {
        const jump = ((x * 13 + k * 7 + f) % 11) < 2 ? 1 : 0;
        p(x, G - 25 + k * 6 - jump, SHIRT[(x * 3 + k) % SHIRT.length]);
      }
      p(0, G, '#f5f5f5', W, 1); p((W / 2) | 0, G, '#f5f5f5', 1, 6);
    },
    stage(s, f) {
      const { ctx, W, G } = s;
      for (let k = 0; k < 3; k++) {
        const x = W * (0.2 + k * 0.3) + Math.sin(f * 0.15 + k * 2) * 14;
        ctx.fillStyle = ['rgba(255,80,160,.18)', 'rgba(80,200,255,.18)', 'rgba(255,220,90,.18)'][k];
        ctx.beginPath(); ctx.moveTo(W * (0.2 + k * 0.3), 0); ctx.lineTo(x - 9, G); ctx.lineTo(x + 9, G); ctx.fill();
      }
    },
    hospital(s, f) { const [cx, cy] = s.crossAt, c = f % 16 < 8 ? '#e53935' : '#ff6f61'; s.p(cx - 1, cy - 4, c, 3, 9); s.p(cx - 4, cy - 1, c, 9, 3); },
  };

  /* ------------------------------------------------------------ objets animés */
  function flag(s, code, x, top, f) {
    const { p } = s, def = FLAGS[code];
    if (!def) return;
    p(x, top, '#5a5a5a', 1, 18);
    const fw = 11, fh = 7;
    for (let i = 0; i < fw; i++) {
      const wave = Math.round(Math.sin(f * 0.6 - i * 0.7) * 0.8);
      for (let j = 0; j < fh; j++) {
        let c;
        const [kind, ...cols] = def;
        if (kind === 'v') c = cols[Math.min(cols.length - 1, ((i / fw) * cols.length) | 0)];
        else if (kind === 'h') c = cols[Math.min(cols.length - 1, ((j / fh) * cols.length) | 0)];
        else if (kind === 'dot') { const dx = i - 5, dy = j - 3; c = dx * dx + dy * dy < 5 ? cols[1] : cols[0]; }
        else if (kind === 'cross') c = (i === 4 || j === 3) ? cols[1] : (cols[2] && (i === 3 || i === 5 || j === 2 || j === 4) ? cols[2] : cols[0]);
        else if (kind === 'us') c = i < 5 && j < 4 ? '#3c3b6e' : (j % 2 ? '#ffffff' : '#b22234');
        else if (kind === 'eu') c = ((i - 5) ** 2 + (j - 3) ** 2 >= 5 && (i - 5) ** 2 + (j - 3) ** 2 <= 7) ? '#ffcc00' : '#003399';
        else if (kind === 'nato') c = (i === 5 || j === 3) ? '#ffffff' : '#004990';
        else if (kind === 'br') { const dx = Math.abs(i - 5), dy = Math.abs(j - 3); c = dx + dy * 1.6 < 3 ? '#002776' : dx + dy * 1.6 < 5 ? '#ffdf00' : '#009c3b'; }
        p(x + 1 + i, top + j + wave, c);
      }
    }
  }
  const PROPS = {
    tank(s, f) {
      const { p, W, G } = s, x = 6 + ((f * 0.5) % (W + 30)) - 18;
      p(x + 2, G - 7, '#4b5a2a', 12, 4); p(x + 5, G - 10, '#3e4826', 6, 3); p(x + 11, G - 9, '#3e4826', 8, 1);
      p(x, G - 3, '#2a2f1f', 16, 3); for (let k = 0; k < 4; k++) p(x + 2 + k * 4 + (f % 2), G - 2, '#6b6b5a');
      if (f % 24 < 2) p(x + 19, G - 10, '#ffb347', 3, 3);
    },
    handshake(s, f) { if (f % 12 < 6) s.p((s.W / 2) | 0, s.G - 20, '#ffd56b', 1, 1); },
    ballot(s, f) {
      const { p, W, G } = s, x = ((W / 2) | 0) - 5;
      p(x, G - 9, '#e8eef5', 11, 9); p(x + 3, G - 9, '#333', 5, 1); p(x + 1, G - 6, '#3b7dd8', 9, 2);
      const y = G - 20 + ((f % 12) * 1);
      if (f % 12 < 11) p(x + 4, y, '#ffffff', 3, 4);
    },
    podium(s) { const { p, W, G } = s, x = ((W / 2) | 0) + 6; p(x, G - 9, '#6b4423', 8, 9); p(x + 1, G - 8, '#f1c40f', 6, 2); p(x + 3, G - 12, '#222', 1, 3); },
    sign() {},
    gavel(s, f) {
      const { p, W, G } = s, x = ((W / 2) | 0) + 8, up = f % 8 < 4;
      p(x, G - 4, '#6b4423', 10, 4);
      p(x + 3, up ? G - 12 : G - 8, '#8b5a2b', 6, 3); p(x + 8, up ? G - 11 : G - 7, '#8b5a2b', 5, 1);
    },
    siren(s, f) {
      const { p, W, G } = s, x = W - 30;
      p(x, G - 7, '#f5f5f5', 20, 5); p(x + 4, G - 10, '#f5f5f5', 11, 3); p(x, G - 5, '#24427a', 20, 1);
      p(x + 7, G - 12, f % 4 < 2 ? '#ff3b30' : '#3b82f6', 5, 2);
      p(x + 3, G - 2, '#111', 4, 2); p(x + 13, G - 2, '#111', 4, 2);
    },
    fire(s, f) {
      const { p, W, G, rr } = s, r = rr(f % 4 + 20), x0 = W - 34;
      p(x0, G - 18, '#5b4b44', 18, 18);
      for (let k = 0; k < 14; k++) {
        const x = x0 + ((r() * 18) | 0), h = 3 + ((r() * 9) | 0);
        p(x, G - 18 - h, k % 3 ? '#ff8c1a' : '#ffd23f', 2, h);
      }
    },
    tree(s, f) {
      const { p, W, G } = s, x = W - 22;
      p(x + 5, G - 10, '#5b3a1e', 3, 10);
      const sway = Math.round(Math.sin(f * 0.4) * 1);
      p(x + sway, G - 22, '#3f8a3f', 13, 12); p(x + 2 + sway, G - 25, '#4fa34f', 9, 4);
    },
    rocket(s, f) {
      const { p, W, G } = s, x = W - 26, y = G - 22 - ((f * 1.5) % (G + 10));
      p(x + 2, y, '#e8e8e8', 4, 12); p(x + 3, y - 2, '#e74c3c', 2, 2); p(x, y + 9, '#e74c3c', 2, 3); p(x + 6, y + 9, '#e74c3c', 2, 3);
      p(x + 2, y + 12, f % 2 ? '#ffd23f' : '#ff8c1a', 4, 3 + (f % 3));
    },
    cross(s, f) { const { p, W, G } = s, x = W - 22; p(x, G - 10, '#ffffff', 10, 8); p(x + 4, G - 9, '#e53935', 2, 6); p(x + 2, G - 7, '#e53935', 6, 2); if (f % 10 < 5) p(x - 6, G - 6, '#2bb3a0', 4, 2); },
    flask(s, f) {
      const { p, W, G } = s, x = W - 26;
      p(x, G - 6, '#6b4423', 16, 6); p(x + 3, G - 14, '#dfe8ee', 3, 8); p(x + 2, G - 9, '#4cd964', 5, 3);
      p(x + 10, G - 12, '#dfe8ee', 3, 6); p(x + 10, G - 9, '#9b59b6', 3, 3);
      for (let k = 0; k < 3; k++) p(x + 3 + (k % 2), G - 16 - ((f + k * 3) % 8), 'rgba(76,217,100,.8)');
    },
    laptop(s, f) {
      const { p, W, G } = s, x = W - 30;
      p(x, G - 12, '#2b2b2b', 16, 10); p(x + 1, G - 11, '#0c1f12', 14, 8); p(x - 2, G - 2, '#555', 20, 2);
      for (let k = 0; k < 3; k++) p(x + 2, G - 10 + k * 2, '#39ff88', 3 + ((f + k * 5) % 9), 1);
      if (f % 10 < 5) p(x + 6, G - 18, '#ff3b30', 4, 4);
    },
    robot(s, f) {
      const { p, W, G } = s, x = W - 26 + Math.round(Math.sin(f * 0.25) * 4);
      p(x, G - 14, '#b0bec5', 9, 7); p(x + 2, G - 12, f % 12 < 1 ? '#b0bec5' : '#00e5ff', 2, 2); p(x + 5, G - 12, '#00e5ff', 2, 2);
      p(x + 4, G - 17, '#78909c', 1, 3); p(x + 3, G - 18, f % 6 < 3 ? '#ff3b30' : '#ffd23f', 3, 1);
      p(x + 1, G - 7, '#90a4ae', 7, 5); p(x + 1, G - 2, '#607d8b', 2, 2); p(x + 6, G - 2, '#607d8b', 2, 2);
    },
    barrel(s, f) {
      const { p, W, G } = s, x = W - 34, a = Math.sin(f * 0.35) * 3;
      p(x + 8, G - 14, '#333', 2, 14); p(x + 2, G - 16 + Math.round(a), '#444', 16, 2); p(x, G - 15 + Math.round(a), '#222', 3, 5);
      p(x + 20, G - 7, '#2c3e50', 6, 7); p(x + 20, G - 5, '#e67e22', 6, 1);
    },
    coins(s, f) {
      const { p, W, G } = s, x = W - 26;
      for (let k = 0; k < 4; k++) p(x, G - 2 - k * 2, '#f1c40f', 8, 1), p(x, G - 1 - k * 2, '#c99a06', 8, 1);
      for (let k = 0; k < 3; k++) { const y = (f * 1.2 + k * 9) % (G - 10); p(x + 2 + k * 2, y, '#ffd84d', 3, 2); }
    },
    chart(s, f) {
      const { p, W, G } = s, x = W - 34, top = G - 26, up = s.spec.dir !== 'down';
      p(x, top, '#f5f5f5', 26, 18); p(x - 1, top + 18, '#6b4423', 2, 8); p(x + 25, top + 18, '#6b4423', 2, 8);
      const n = Math.min(22, (f % 30) + 2), col = up ? '#27ae60' : '#e53935';
      for (let i = 0; i < n; i++) {
        const t = i / 21, yy = up ? 15 - t * 12 + Math.sin(i * 1.3) * 1.5 : 3 + t * 12 + Math.sin(i * 1.3) * 1.5;
        p(x + 2 + i, top + Math.round(yy), col);
      }
    },
    tractor(s, f) {
      const { p, W, G } = s, x = ((f * 0.6) % (W + 30)) - 22;
      p(x + 4, G - 9, '#c0392b', 12, 5); p(x + 10, G - 14, '#c0392b', 6, 5); p(x + 11, G - 13, '#9cc7e8', 4, 3);
      p(x + 2, G - 6, '#222', 6, 6); p(x + 13, G - 4, '#222', 4, 4);
    },
    boat(s, f) {
      const { p, W, G } = s, x = W - 34, y = G - 13 + (f % 8 < 4 ? 0 : 1);
      p(x, y, '#8b5a2b', 18, 3); p(x + 2, y + 3, '#6b4423', 14, 1); p(x + 8, y - 9, '#555', 1, 9); p(x + 9, y - 8, '#f5f5f5', 6, 6);
    },
    book(s, f) { const { p, W, G } = s, x = W - 24; p(x, G - 3, '#2e86de', 12, 3); p(x + 1, G - 6, '#e74c3c', 10, 3); p(x + 2, G - 9, '#27ae60', 8, 3); if (f % 16 < 8) p(x + 4, G - 12, '#fff', 4, 2); },
    dove(s, f) {
      const { p, W } = s, x = ((f * 1.2) % (W + 20)) - 10, y = 30 + Math.round(Math.sin(f * 0.3) * 3), wing = f % 4 < 2;
      p(x, y, '#ffffff', 6, 2); p(x + 5, y - 1, '#ffffff', 2, 2); p(x + 2, wing ? y - 3 : y + 2, '#ffffff', 3, 2);
    },
    plane(s, f) {
      const { p, W } = s, x = ((f * 1.8) % (W + 40)) - 20, y = 26;
      p(x, y, '#f5f5f5', 16, 3); p(x + 14, y + 1, '#9cc7e8', 2, 1); p(x + 6, y - 3, '#d0d0d0', 4, 3); p(x + 6, y + 3, '#d0d0d0', 4, 3); p(x, y - 3, '#e53935', 2, 3);
      p(x - 6, y + 1, 'rgba(255,255,255,.5)', 6, 1);
    },
    car(s, f) {
      const { p, W, G } = s, x = ((f * 4) % (W + 40)) - 22;
      p(x, G - 5, '#d62828', 16, 3); p(x + 5, G - 7, '#d62828', 6, 2); p(x + 6, G - 7, '#9ad1ff', 3, 1); p(x + 14, G - 4, '#222', 3, 1);
      p(x + 2, G - 2, '#111', 3, 2); p(x + 11, G - 2, '#111', 3, 2); p(x - 6, G - 4, 'rgba(255,255,255,.4)', 5, 1);
    },
    ball(s, f) { const { p, W, G } = s, t = (f % 16) / 16, x = W * 0.3 + t * W * 0.4, y = G - 3 - Math.round(Math.sin(t * Math.PI) * 14); p(x, y, '#ffffff', 3, 3); p(x + 1, y + 1, '#222', 1, 1); },
    trophy(s, f) {
      const { p, W, G } = s, x = ((W / 2) | 0) - 4;
      p(x, G - 14, '#f1c40f', 9, 6); p(x + 3, G - 8, '#d4a20b', 3, 4); p(x + 1, G - 4, '#8b5a2b', 7, 4); p(x - 2, G - 13, '#f1c40f', 2, 3); p(x + 9, G - 13, '#f1c40f', 2, 3);
      if (f % 8 < 3) p(x + 6, G - 17, '#ffffff', 1, 3), p(x + 5, G - 16, '#ffffff', 3, 1);
    },
    guitar(s, f) { const { p, W } = s; for (let k = 0; k < 3; k++) { const y = 40 - ((f * 1.2 + k * 8) % 26), x = W * 0.3 + k * 14 + Math.round(Math.sin(f * 0.3 + k) * 2); p(x, y, '#ffd56b', 2, 2); p(x + 2, y - 4, '#ffd56b', 1, 5); } },
    runway(s, f) {
      const { p, W, G } = s;
      p(0, G - 2, '#d9d9d9', W, 2);
      for (let k = 0; k < 2; k++) if ((f + k * 7) % 13 < 2) { const x = 6 + ((f * 17 + k * 31) % (W - 12)); p(x, G - 24, '#ffffff', 3, 3); p(x + 1, G - 26, '#ffffff', 1, 7); p(x - 2, G - 23, '#ffffff', 7, 1); }
    },
    easel(s, f) {
      const { p, W, G } = s, x = W - 30;
      p(x + 2, G - 20, '#8b5a2b', 1, 20); p(x + 15, G - 20, '#8b5a2b', 1, 20);
      p(x, G - 22, '#f5f5f5', 18, 13);
      const n = f % 30;
      for (let k = 0; k < Math.min(n, 12); k++) p(x + 2 + k, G - 18 + Math.round(Math.sin(k * 0.9) * 2), SHIRT[k % SHIRT.length], 1, 2);
    },
    mic(s, f) { const { p, W, G } = s, x = ((W / 2) | 0) + 8; if (f % 12 < 8) { p(x, G - 26, '#ffffff', 11, 6); p(x + 2, G - 20, '#ffffff', 2, 2); for (let k = 0; k < 3; k++) if (f % 12 > k * 2) p(x + 2 + k * 3, G - 24, '#333', 1, 1); } },
  };

  /* ------------------------------------------------------------ mise en scène */
  const DEFAULT_TIME = { space: 'night', night: 'night', stage: 'night', ruins: 'dusk' };
  function build(canvas, spec, seedText, opts = {}) {
    const W = opts.width || 96;
    const H = Math.max(48, Math.round(W * (canvas.clientHeight || 1) / (canvas.clientWidth || 1)) || Math.round(W * 1.6));
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;
    const seed = hash(seedText || 'actu');
    const time = spec.time || DEFAULT_TIME[spec.bg] || 'day';
    const pal = SKIES[time] || SKIES.day;
    const G = Math.round(H * (opts.ground || 0.72));
    const s = { ctx, p: painter(ctx), W, H, G, pal, spec, time, rr: (k) => rng(seed + k * 7919), r: rng(seed) };
    // couche fixe : ciel tramé, astre, décor lointain, sol
    const bgCanvas = document.createElement('canvas');
    bgCanvas.width = W; bgCanvas.height = H;
    const bctx = bgCanvas.getContext('2d');
    const sb = { ...s, ctx: bctx, p: painter(bctx), r: rng(seed) };
    sky(sb.p, W, H, pal, G);
    if (spec.bg !== 'space' && spec.bg !== 'stage') {
      const sunX = Math.round(W * (0.25 + sb.r() * 0.5)), sunY = Math.round(G * (time === 'sunset' || time === 'dusk' ? 0.62 : 0.28)), R = time === 'night' ? 5 : 9;
      disc(sb.p, sunX, sunY, R, pal.sun);
      if (time === 'night') disc(sb.p, sunX + 2, sunY - 1, R - 1, pal.sky[1]); // croissant de lune
    } else if (spec.bg === 'stage') sb.p(0, 0, '#120c18', W, G);
    if (time === 'night' && spec.bg !== 'space' && spec.bg !== 'stage') stars(sb.p, W, G - 20, rng(seed + 3), 0, 18);
    (BACKDROPS[spec.bg] || BACKDROPS.mountains)(sb);
    const ground = GROUND[spec.bg] || pal.ground;
    sb.p(0, G, ground, W, H - G);
    for (let y = G + 2; y < H; y += 3) for (let x = (y * 3) % 5; x < W; x += 5) sb.p(x, y, 'rgba(0,0,0,.12)');
    s.flagTop = sb.flagTop; s.crossAt = sb.crossAt;

    // personnages : alignés au sol, le premier change de costume (tenue de ville → tenue du sujet)
    const cast = (spec.cast && spec.cast.length ? spec.cast : ['citizen']).slice(0, 3);
    const r = rng(seed + 99);
    const people = cast.map((costume, i) => ({
      costume,
      look: { skin: SKIN[(r() * SKIN.length) | 0], hair: HAIR[(r() * HAIR.length) | 0], shirt: SHIRT[(r() * SHIRT.length) | 0], phase: i * 3 + ((r() * 5) | 0) },
      x: Math.round(W * (cast.length === 1 ? 0.36 : 0.18 + i * (0.42 / Math.max(1, cast.length - 1)))),
      walk: ['protester', 'model', 'citizen', 'student'].includes(costume) && cast.length > 1,
    }));
    if (spec.prop === 'handshake' && people.length >= 2) { people[0].x = ((W / 2) | 0) - 9; people[1].x = ((W / 2) | 0) + 2; people[1].face = -1; }
    const labels = (spec.label || []).map(strip).filter(Boolean).slice(0, 2);
    const flags = (spec.flags || []).slice(0, 2);
    const live = LIVE[spec.bg];
    const prop = PROPS[spec.prop];

    function draw(f) {
      ctx.drawImage(bgCanvas, 0, 0);
      if (spec.bg !== 'space' && spec.bg !== 'stage' && time !== 'night') clouds(s.p, W, 6, f, rng(seed + 5), 'rgba(255,255,255,.85)');
      if (live) live(s, f);
      if (spec.bg === 'parliament' && s.flagTop) flag(s, flags[0] || 'eu', s.flagTop[0] - 1, s.flagTop[1] - 1, f);
      flags.forEach((code, i) => { if (!(spec.bg === 'parliament' && i === 0)) flag(s, code, i ? W - 15 : 3, G - 18, f + i * 3); });
      if (prop) prop(s, f);
      const cycle = f % 48; // 6 s : tenue de ville, petit nuage magique, puis costume du sujet
      people.forEach((pp, i) => {
        let costume = pp.costume;
        if (i === 0 && costume !== 'citizen' && cycle < 8) costume = 'citizen';
        let x = pp.x;
        if (pp.walk) x += Math.round(Math.sin((f + pp.look.phase * 4) * 0.12) * 5);
        drawPerson(s.p, x, G - 12, costume, pp.look, f, pp.walk, pp.face || (i % 2 && people.length > 2 ? -1 : 1));
        if (i === 0 && pp.costume !== 'citizen' && cycle >= 7 && cycle < 11) {
          for (let k = 0; k < 7; k++) s.p(x - 2 + ((k * 5 + cycle * 3) % 11), G - 15 + ((k * 7 + cycle) % 15), k % 2 ? '#ffffff' : '#ffe680');
        }
      });
      // étiquette : un petit panneau en haut de la scène
      labels.forEach((t, i) => {
        const tw = textWidth(t), x = Math.round((W - tw) / 2), y = Math.round(H * (opts.labelY || 0.16)) + i * 9;
        s.p(x - 3, y - 2, i ? 'rgba(255,255,255,.88)' : 'rgba(10,10,20,.78)', tw + 6, 9);
        s.p.text(t, x, y, i ? '#14141f' : '#ffffff');
      });
    }
    return { draw };
  }

  /* ------------------------------------------------------------ boucle : seule la scène la plus visible s'anime */
  const scenes = new Map(); // canvas → { scene, ratio }
  let frame = 0, timer = null;
  const io = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
    for (const e of entries) {
      const item = scenes.get(e.target);
      if (!item) continue;
      item.ratio = e.isIntersecting ? e.intersectionRatio : 0;
      if (e.isIntersecting && !item.scene) item.scene = build(e.target, item.spec, item.seed, item.opts);
      if (item.scene && e.isIntersecting) item.scene.draw(frame);
    }
    tick();
  }, { threshold: [0, 0.25, 0.6, 0.95], rootMargin: '100% 0px' }) : null;

  function tick() {
    const visible = [...scenes.values()].some((i) => i.ratio > 0.2);
    if (visible && !timer && !document.hidden) timer = setInterval(step, 1000 / FPS);
    if ((!visible || document.hidden) && timer) { clearInterval(timer); timer = null; }
  }
  function step() {
    frame++;
    let best = null;
    for (const item of scenes.values()) if (item.scene && item.ratio > 0.2 && (!best || item.ratio > best.ratio)) best = item;
    if (best) best.scene.draw(frame);
    // les canevas retirés de la page sont oubliés
    if (frame % 40 === 0) for (const c of scenes.keys()) if (!c.isConnected) { scenes.delete(c); io?.unobserve(c); }
  }
  document.addEventListener('visibilitychange', tick);

  function mount(canvas, spec, seed, opts) {
    if (!spec) return;
    scenes.set(canvas, { spec, seed, opts, scene: null, ratio: 0 });
    if (io) io.observe(canvas);
    else { const sc = build(canvas, spec, seed, opts); scenes.get(canvas).scene = sc; scenes.get(canvas).ratio = 1; sc.draw(0); tick(); }
  }

  /* scène de secours pour les éditions préparées avant l'arrivée des scènes */
  const FROM_THEME = {
    geopolitique: { bg: 'ruins', cast: ['soldier', 'soldier'], prop: 'tank', label: ['MONDE'] },
    politique: { bg: 'parliament', cast: ['politician', 'citizen'], prop: 'podium', label: ['POLITIQUE'] },
    economie: { bg: 'factory', cast: ['business', 'worker'], prop: 'chart', label: ['ECONOMIE'] },
    finance: { bg: 'city', cast: ['business', 'business'], prop: 'coins', label: ['FINANCE'] },
    sport: { bg: 'stadium', cast: ['athlete', 'athlete'], prop: 'ball', label: ['SPORT'] },
    innovation: { bg: 'night', cast: ['scientist'], prop: 'robot', label: ['TECH'] },
    science: { bg: 'field', cast: ['scientist'], prop: 'flask', label: ['SCIENCE'] },
    sante: { bg: 'hospital', cast: ['doctor', 'citizen'], prop: 'cross', label: ['SANTE'] },
    art: { bg: 'city', time: 'sunset', cast: ['artist'], prop: 'easel', label: ['CULTURE'] },
    musique: { bg: 'stage', cast: ['musician', 'musician'], prop: 'guitar', label: ['MUSIQUE'] },
    mode: { bg: 'stage', cast: ['model', 'model'], prop: 'runway', label: ['MODE'] },
  };
  function fallback(article) {
    const t = (article.themes || []).find((x) => FROM_THEME[x]);
    return { ...(FROM_THEME[t] || { bg: 'city', cast: ['journalist', 'citizen'], prop: 'mic', label: ['INFO'] }), flags: [] };
  }

  return { mount, fallback };
})();
