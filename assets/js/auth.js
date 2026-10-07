/* The Raider Network v6 — accounts, session and profile page.
 *
 * SERVER mode (production): register / login / logout / session go to /api/auth/* (Cloudflare Pages Functions + D1).
 *   The session lives in an HttpOnly cookie that JavaScript cannot read; nothing about the account is kept in
 *   localStorage. The current user is fetched once per page load from /api/auth/session.
 * DEMO mode (local development without the API): the v5 browser-only demo accounts (trn_users / trn_session).
 * The login email and private Raider tag are never rendered for other users. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;
  const LS = () => TRN.store.LS;
  const getDemoSession = () => LS().get('trn_session', null);
  const setDemoSession = u => (u ? LS().set('trn_session', u) : localStorage.removeItem('trn_session'));

  /* Server users are mapped to the field names the v5 UI already uses (user_id, avatar). */
  const fromServer = u => u && ({ ...u, user_id: u.id, avatar: u.avatar_url });
  let sessionPromise = null;
  async function currentUser() {
    await TRN.api.init();
    if (TRN.mode === 'demo') return getDemoSession();
    if (TRN.mode !== 'server') return null;
    sessionPromise ||= TRN.api.get('/auth/session').then(d => { TRN.sessionTrades = d.trades || null; return fromServer(d.user); }).catch(e => { console.error(e); return null; });
    return sessionPromise;
  }
  const refreshUser = () => { sessionPromise = null; return currentUser(); };

  const safeNext = n => (/^[a-z0-9-]+\.html(\?[^#]*)?(#[\w-]*)?$/i.test(n || '') ? n : null);
  async function requireUser(next) {
    const u = await currentUser();
    if (!u) {
      let page = location.pathname.split('/').pop() || 'index';   // Cloudflare Pages serves /trade for trade.html
      if (!page.endsWith('.html')) page += '.html';
      const target = next || page + location.search;
      location.href = 'auth.html?next=' + encodeURIComponent(target) + '#login';
      return null;
    }
    return u;
  }

  /* ---------------------------------------------------------------- client-side validation (mirrors the server) */
  const RULES = {
    username: v => /^[a-z0-9_]{3,20}$/i.test(v) && /[a-z]/i.test(v) ? '' : 'Username must be 3–20 characters: letters, numbers and underscores, with at least one letter.',
    display_name: v => v.trim().length >= 2 && v.trim().length <= 30 && /^[\p{L}\p{N}][\p{L}\p{N} ._'-]*$/u.test(v.trim()) ? '' : 'Display name must be 2–30 characters (letters, numbers, spaces, . _ \' -).',
    email: v => /^[^\s@<>()",;:]+@[^\s@<>()",;:]+\.[a-z]{2,}$/i.test(v.trim()) && v.length <= 254 ? '' : 'Please enter a valid email address.',
    password: v => v.length >= 10 && v.length <= 128 ? '' : 'Password must be 10–128 characters.',
  };
  function validateRegister(fd) {
    for (const k of ['username', 'display_name', 'email', 'password']) { const m = RULES[k](String(fd.get(k) || '')); if (m) return { field: k, message: m }; }
    if (fd.get('password') !== fd.get('confirm_password')) return { field: 'confirm_password', message: 'Passwords do not match.' };
    return null;
  }
  function showFieldError(form, field, message) {
    $$('.field-error', form).forEach(x => x.remove()); $$('[aria-invalid]', form).forEach(x => x.removeAttribute('aria-invalid'));
    const input = field && form.elements[field];
    if (input && input.insertAdjacentHTML) { input.setAttribute('aria-invalid', 'true'); input.insertAdjacentHTML('afterend', `<small class="field-error">${esc(message)}</small>`); input.focus(); }
  }

  async function register(fd) {
    const bad = validateRegister(fd); if (bad) { const e = new Error(bad.message); e.field = bad.field; throw e; }
    const body = {
      username: String(fd.get('username')).trim(), display_name: String(fd.get('display_name')).trim(), email: String(fd.get('email')).trim(),
      password: fd.get('password'), confirm_password: fd.get('confirm_password'), raider_tag: fd.get('raider_tag') || '',
      platform: fd.get('platform'), region: fd.get('region'), avatar_url: fd.get('avatar') || 'raiders/raider-solo-scout.webp',
    };
    if (TRN.mode === 'server') { const d = await TRN.api.post('/auth/register', body); sessionPromise = Promise.resolve(fromServer(d.user)); return; }
    if (TRN.mode !== 'demo') throw new Error(TRN.backendProblem || 'Registration is unavailable right now.');
    const users = LS().get('trn_users', []);
    if (users.some(u => (u.email || '').toLowerCase() === body.email.toLowerCase())) throw Object.assign(new Error('An account already exists with that email.'), { field: 'email' });
    if (users.some(u => (u.username || '').toLowerCase() === body.username.toLowerCase())) throw Object.assign(new Error('That username is already taken.'), { field: 'username' });
    // Demo-mode account claim (development only): the first local account named "Perisher" owns the seeded Perisher demo listings/hunts.
    const claim = body.display_name.toLowerCase() === 'perisher' && !users.some(x => x.id === 'perisher');
    const id = claim ? 'perisher' : 'u' + Date.now();
    const u = { id, user_id: id, username: body.username.toLowerCase(), email: body.email, password: body.password, display_name: body.display_name, raider_tag: body.raider_tag, platform: body.platform, region: body.region, avatar: body.avatar_url, created_at: new Date().toISOString() };
    users.push(u); LS().set('trn_users', users); setDemoSession(u);
  }
  async function login(fd) {
    const loginName = String(fd.get('login') || '').trim(), password = String(fd.get('password') || '');
    if (!loginName || !password) throw new Error('Enter your username or email and your password.');
    if (TRN.mode === 'server') { const d = await TRN.api.post('/auth/login', { login: loginName, password }); sessionPromise = Promise.resolve(fromServer(d.user)); return; }
    if (TRN.mode !== 'demo') throw new Error(TRN.backendProblem || 'Log in is unavailable right now.');
    const l = loginName.toLowerCase();
    const u = LS().get('trn_users', []).find(x => ((x.email || '').toLowerCase() === l || (x.username || '').toLowerCase() === l) && x.password === password);
    if (!u) throw new Error('Incorrect username/email or password.'); setDemoSession(u);
  }
  async function logout() {
    try { if (TRN.mode === 'server') await TRN.api.post('/auth/logout'); else setDemoSession(null); } catch (e) { console.error(e); }
    sessionPromise = null; location.href = 'index.html';
  }

  const options = (list, sel) => list.map(x => `<option ${x === sel ? 'selected' : ''}>${esc(x)}</option>`).join('');
  const AVATARS = ['solo-scout', 'heavy-looter', 'tech-specialist', 'mountain-runner', 'medic-support', 'stealth-raider', 'veteran-trader', 'expedition-leader', 'engineer', 'comms-operator', 'close-quarters'];
  const avatarPicker = (name, sel) => `<div class="avatar-picker">${AVATARS.map(a => { const v = `raiders/raider-${a}.webp`; return `<label title="${esc(a.replace(/-/g, ' '))}"><input type="radio" name="${name}" value="${v}" ${v === sel ? 'checked' : ''}><img src="${TRN.IMG + v}" alt="${esc(a.replace(/-/g, ' '))}" loading="lazy"></label>`; }).join('')}</div>`;

  async function setupAuthPage() {
    if (!$('#loginForm')) return;
    const regions = TRN.db.regions, platforms = TRN.db.platforms;
    $$('select[name=region]').forEach(s => (s.innerHTML = options(regions, 'NA East')));
    $$('select[name=platform]').forEach(s => (s.innerHTML = options(platforms, 'Cross-platform')));
    $('#avatarSlot').innerHTML = avatarPicker('avatar', 'raiders/raider-solo-scout.webp');
    const sw = tab => { const reg = tab === 'register'; $('#registerForm').classList.toggle('hidden', !reg); $('#loginForm').classList.toggle('hidden', reg); $('#registerTab').classList.toggle('active', reg); $('#loginTab').classList.toggle('active', !reg); $('#registerTab').setAttribute('aria-selected', reg); $('#loginTab').setAttribute('aria-selected', !reg); };
    $('#loginTab').onclick = () => sw('login'); $('#registerTab').onclick = () => sw('register');
    if (location.hash === '#register') sw('register');
    const next = safeNext(TRN.param('next'));
    const note = $('#authModeNote');
    if (note) note.innerHTML = TRN.mode === 'server'
      ? 'Your email is private and never shown to other Raiders. Passwords are stored only as salted hashes, and you stay signed in with a secure cookie for up to 30 days.'
      : TRN.mode === 'demo' ? '<b>Local demo mode:</b> no server is running, so this account is stored only in this browser. Don’t reuse a real password.'
        : esc(TRN.backendProblem || 'Accounts are temporarily unavailable.');
    if (TRN.mode === 'offline') $$('#loginForm button, #registerForm button').forEach(b => (b.disabled = true));
    if (next) $('#authNext').innerHTML = `After you sign in you'll go back to <b>${esc(next.split(/[?#]/)[0].replace('.html', '').replace('trade', 'the Trade Board'))}</b>.`;
    const already = await currentUser();
    if (already && TRN.mode === 'server') $('#authNext').innerHTML = `You're signed in as <b>${esc(already.display_name)}</b>. <a href="${esc(next || 'profile.html')}">Continue →</a>`;
    $('#registerForm').onsubmit = async e => {
      e.preventDefault(); const f = e.target, m = $('#registerMsg'), btn = f.querySelector('button[type=submit]');
      showFieldError(f); m.textContent = 'Creating account…'; btn.disabled = true;
      try { await register(new FormData(f)); m.textContent = TRN.mode === 'server' ? 'Account created. Welcome to the Network!' : 'Demo account created.'; setTimeout(() => (location.href = next || 'profile.html'), 400); }
      catch (err) { m.textContent = err.message; showFieldError(f, err.field, err.message); btn.disabled = false; }
    };
    $('#loginForm').onsubmit = async e => {
      e.preventDefault(); const f = e.target, m = $('#loginMsg'), btn = f.querySelector('button[type=submit]');
      m.textContent = 'Logging in…'; btn.disabled = true;
      try { await login(new FormData(f)); location.href = next || 'profile.html'; }
      catch (err) { m.textContent = err.message; btn.disabled = false; }
    };
  }

  /* ---------------------------------------------------------------- My Profile */
  const fmtDate = iso => { try { return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); } catch { return ''; } };

  async function setupProfilePage() {
    const form = $('#profileForm'); if (!form) return;
    const user = await requireUser('profile.html'); if (!user) return;
    const uid = user.user_id || user.id, srv = TRN.mode === 'server';
    form.elements.region.innerHTML = options(TRN.db.regions, user.region || 'NA East');
    form.elements.platform.innerHTML = options(TRN.db.platforms, user.platform || 'Cross-platform');
    form.elements.display_name.value = user.display_name || ''; form.elements.raider_tag.value = user.raider_tag || '';
    form.elements.raider_tag.required = false;
    $('#profileAvatarSlot').innerHTML = avatarPicker('avatar', user.avatar || 'raiders/raider-solo-scout.webp');
    const paintHead = u => {
      $('#profileName').textContent = u.display_name || 'My Profile';
      $('#profileMeta').innerHTML = `${u.username ? `<span class="handle">@${esc(u.username)}</span>` : ''}${u.joined_at || u.created_at ? `<span>${TRN.svg('clock')} Joined ${esc(fmtDate(u.joined_at || u.created_at))}</span>` : ''}<span>${TRN.svg('radio')} ${esc(u.platform || 'Cross-platform')}</span><span>${TRN.svg('pin')} ${esc(u.region || 'NA East')}</span><span class="private-tag" title="Only visible to you">${TRN.svg('info')} Tag: ${esc(u.raider_tag || 'not set')} · private</span>`;
      $('#profileAvatar').src = TRN.IMG + (u.avatar || 'raiders/raider-solo-scout.webp');
    };
    paintHead(user);
    form.onsubmit = async e => {
      e.preventDefault(); const fd = new FormData(form), msg = $('#profileMsg');
      const patch = { display_name: String(fd.get('display_name') || '').trim(), raider_tag: fd.get('raider_tag'), platform: fd.get('platform'), region: fd.get('region'), avatar: fd.get('avatar') || user.avatar };
      try {
        if (srv) { const d = await TRN.api.patch('/me', { display_name: patch.display_name, raider_tag: patch.raider_tag, platform: patch.platform, region: patch.region, avatar_url: patch.avatar }); Object.assign(user, fromServer(d.user)); }
        else { const users = LS().get('trn_users', []); const i = users.findIndex(x => x.id === user.id); if (i > -1) users[i] = { ...users[i], ...patch }; LS().set('trn_users', users); setDemoSession({ ...user, ...patch }); Object.assign(user, patch); }
        paintHead(user); msg.textContent = 'Profile saved.'; TRN.toast('Profile saved');
      } catch (err) { msg.textContent = err.message; }
    };

    const [hunts, trades] = await Promise.all([TRN.store.listHunts(), TRN.store.listTrades({ fresh: true })]);
    const mine = hunts.filter(h => h.userId === uid), myTrades = trades.filter(t => t.userId === uid);
    const active = mine.filter(h => h.status !== 'completed'), done = mine.filter(h => h.status === 'completed');
    const huntRow = h => `<div class="mini-row"><img src="${TRN.img(TRN.data.item(h.itemId)?.image)}" alt=""><div><strong>${TRN.data.itemLink(h.itemId, h.itemName)}</strong><span>${TRN.data.mapLink(h.mapId)} · ${esc(h.region)} · ${TRN.ageFromIso(h.createdAt)}</span></div>${TRN.statusChip(h.status)}${h.status !== 'completed' ? `<button class="btn btn-ghost btn-xs" data-complete="${esc(h.id)}">Mark complete</button>` : ''}</div>`;
    $('#myHunts').innerHTML = active.length ? active.map(huntRow).join('') : '<p class="empty-note">No active loot hunts. <a href="hunts.html">Start one →</a></p>';
    $('#myCompleted').innerHTML = done.length ? done.map(huntRow).join('') : '<p class="empty-note">Completed hunts will appear here.</p>';
    if (srv) $$('.device-only-note').forEach(n => n.classList.remove('hidden'));
    const openT = myTrades.filter(t => t.status === 'open'), completedT = myTrades.filter(t => t.status === 'completed');
    const tradeLine = t => `<div class="mini-row"><img src="${TRN.img(TRN.data.item(t.lookingFor[0]?.itemId)?.image)}" alt=""><div><strong>LF ${t.lookingFor.map(x => TRN.data.itemLink(x.itemId, x.name)).join(', ')}</strong><span>${esc(t.region)} · ${esc(t.platform)} · ${TRN.ageFromIso(t.createdAt)}${t.pendingOffers ? ` · <b>${t.pendingOffers} offer${t.pendingOffers > 1 ? 's' : ''}</b>` : ''}</span></div>${TRN.statusChip(t.status)}${t.status === 'open' ? `<button class="btn btn-ghost btn-xs" data-close-trade="${esc(t.id)}">Close</button>` : ''}</div>`;
    $('#myTrades').innerHTML = openT.map(tradeLine).join('') || '<p class="empty-note">No open trade requests. <a href="trade.html?new=">Post one →</a></p>';
    TRN.trades.prep(trades);
    const invHtml = TRN.trades.inventoryPanel(uid);
    $('#myInventoryPanel')?.classList.toggle('hidden', !invHtml); if (invHtml) $('#myInventory').innerHTML = invHtml;
    if (srv) {
      $('#statActiveLabel').textContent = 'Active trades'; $('#statActive').textContent = openT.length;
      $('#statTradesLabel').textContent = 'Completed trades'; $('#statTrades').textContent = completedT.length;
      $('#statDoneLabel').textContent = 'Active hunts'; $('#statDone').textContent = active.length;
      await renderOffers(user);
    } else {
      $('#statActive').textContent = active.length; $('#statDone').textContent = done.length; $('#statTrades').textContent = openT.length;
    }
    $$('[data-complete]').forEach(b => (b.onclick = async () => { await TRN.store.updateHunt(b.dataset.complete, { status: 'completed' }); setupProfilePage(); }));
    $$('[data-close-trade]').forEach(b => (b.onclick = async () => { try { await TRN.store.updateTrade(b.dataset.closeTrade, { status: 'closed' }); TRN.toast('Trade closed'); setupProfilePage(); } catch (err) { TRN.toast(err.message); } }));
    $('#badgeGrid').innerHTML = (TRN.db.badges || []).map(b => `<div class="badge-slot"><img src="${TRN.IMG}ui/rarity-${{ 'trusted-raider': 'legendary', 'loot-hunter': 'epic', 'route-scout': 'rare', 'project-specialist': 'uncommon' }[b.id]}.png" alt=""><strong>${esc(b.name)}</strong><small>Coming soon</small></div>`).join('');
    $('#logoutBtn').onclick = logout;
  }

  /* Offers received on my trades (accept / decline) and offers I sent (withdraw). Server mode only. */
  async function renderOffers(user) {
    const panel = $('#myOffersPanel'); if (!panel) return;
    panel.classList.remove('hidden');
    let d; try { d = await TRN.store.offers.mine(); } catch (e) { $('#myOffers').innerHTML = `<p class="empty-note">${esc(e.message)}</p>`; return; }
    const who = o => `<b>${esc(o.from.display_name)}</b> <small>@${esc(o.from.username)}</small>`;
    const recv = d.received.map(o => `<div class="offer-row"><div><span>${who(o)} on <a href="trade.html#${esc(o.trade_id)}">LF ${esc(o.trade?.wanted_name || 'trade')}</a> · ${TRN.ageFromIso(o.created_at)}</span>${o.offered ? `<span class="offer-item">Offers: ${TRN.data.itemLink(o.offered.item_id, o.offered.name)}</span>` : ''}<p>${esc(o.message)}</p></div>${TRN.statusChip(o.status)}${o.status === 'PENDING' ? `<span class="offer-actions"><button class="btn btn-primary btn-xs" data-offer="${esc(o.id)}" data-act="accept">Accept</button><button class="btn btn-ghost btn-xs" data-offer="${esc(o.id)}" data-act="decline">Decline</button></span>` : ''}</div>`).join('');
    const sent = d.sent.map(o => `<div class="offer-row"><div><span>To <b>${esc(o.trade?.owner_display_name || 'Raider')}</b> on <a href="trade.html#${esc(o.trade_id)}">LF ${esc(o.trade?.wanted_name || 'trade')}</a> · ${TRN.ageFromIso(o.created_at)}</span><p>${esc(o.message)}</p></div>${TRN.statusChip(o.status)}${o.status === 'PENDING' ? `<span class="offer-actions"><button class="btn btn-ghost btn-xs" data-offer="${esc(o.id)}" data-act="withdraw">Withdraw</button></span>` : ''}</div>`).join('');
    $('#myOffers').innerHTML = `<h3 class="sub-h">Received</h3>${recv || '<p class="empty-note">No offers on your trades yet.</p>'}<h3 class="sub-h">Sent</h3>${sent || '<p class="empty-note">You haven’t made any offers yet.</p>'}`;
    $$('#myOffers [data-offer]').forEach(b => (b.onclick = async () => { b.disabled = true; try { await TRN.store.offers.act(b.dataset.offer, b.dataset.act); TRN.toast('Offer ' + { accept: 'accepted', decline: 'declined', withdraw: 'withdrawn' }[b.dataset.act]); renderOffers(user); } catch (e) { TRN.toast(e.message); b.disabled = false; } }));
  }

  TRN.auth = { currentUser, refreshUser, requireUser, register, login, logout, setupAuthPage, setupProfilePage, avatarPicker, options, validateRegister };
})();
