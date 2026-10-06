/* The Raider Network v5 — accounts, session and profile page.
 * Demo Mode: accounts live in localStorage (trn_users / trn_session) exactly as in v4.
 * The login email and private Raider tag are never rendered for other users. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;
  const LS = () => TRN.store.LS;
  const getDemoSession = () => LS().get('trn_session', null);
  const setDemoSession = u => (u ? LS().set('trn_session', u) : localStorage.removeItem('trn_session'));

  async function currentUser() {
    if (!TRN.realMode) return getDemoSession();
    const { data: { user } } = await TRN.sb.auth.getUser(); if (!user) return null;
    const [{ data: p }, { data: priv }] = await Promise.all([
      TRN.sb.from('profiles').select('*').eq('id', user.id).maybeSingle(),
      TRN.sb.from('private_profiles').select('raider_tag').eq('id', user.id).maybeSingle()]);
    return { user_id: user.id, email: user.email, ...p, raider_tag: priv?.raider_tag || '' };
  }
  async function requireUser(next) {
    const u = await currentUser();
    if (!u) { location.href = 'auth.html?next=' + encodeURIComponent(next || location.pathname.split('/').pop() + location.search) + '#register'; return null; }
    return u;
  }

  async function register(fd) {
    const email = String(fd.get('email')).trim(), password = fd.get('password');
    const profile = { display_name: String(fd.get('display_name')).trim(), raider_tag: fd.get('raider_tag'), platform: fd.get('platform'), region: fd.get('region'), avatar: fd.get('avatar') || 'raiders/raider-solo-scout.webp' };
    if (!TRN.realMode) {
      const users = LS().get('trn_users', []);
      if (users.some(u => u.email.toLowerCase() === email.toLowerCase())) throw new Error('An account already exists with that email.');
      // Demo-mode account claim: the first local account named "Perisher" owns the seeded Perisher listings/hunts.
      const claim = profile.display_name.toLowerCase() === 'perisher' && !users.some(x => x.id === 'perisher');
      const id = claim ? 'perisher' : 'u' + Date.now(), u = { id, user_id: id, email, password, ...profile, created_at: new Date().toISOString() };
      users.push(u); LS().set('trn_users', users); setDemoSession(u); return;
    }
    const { data, error } = await TRN.sb.auth.signUp({ email, password, options: { data: profile } }); if (error) throw error;
    if (data.user) {
      await TRN.sb.from('profiles').upsert({ id: data.user.id, display_name: profile.display_name, platform: profile.platform, region: profile.region, avatar: profile.avatar });
      await TRN.sb.from('private_profiles').upsert({ id: data.user.id, raider_tag: profile.raider_tag });
    }
    if (!data.session) throw new Error('Account created. Check your email to confirm your account, then log in.');
  }
  async function login(fd) {
    const email = String(fd.get('email')).trim(), password = fd.get('password');
    if (!TRN.realMode) {
      const u = LS().get('trn_users', []).find(x => x.email.toLowerCase() === email.toLowerCase() && x.password === password);
      if (!u) throw new Error('Invalid email or password.'); setDemoSession(u); return;
    }
    const { error } = await TRN.sb.auth.signInWithPassword({ email, password }); if (error) throw error;
  }
  async function logout() { if (TRN.realMode) await TRN.sb.auth.signOut(); else setDemoSession(null); location.href = 'index.html'; }

  const options = (list, sel) => list.map(x => `<option ${x === sel ? 'selected' : ''}>${esc(x)}</option>`).join('');
  const AVATARS = ['solo-scout', 'heavy-looter', 'tech-specialist', 'mountain-runner', 'medic-support', 'stealth-raider', 'veteran-trader', 'expedition-leader', 'engineer', 'comms-operator', 'close-quarters'];
  const avatarPicker = (name, sel) => `<div class="avatar-picker">${AVATARS.map(a => { const v = `raiders/raider-${a}.webp`; return `<label title="${esc(a.replace(/-/g, ' '))}"><input type="radio" name="${name}" value="${v}" ${v === sel ? 'checked' : ''}><img src="${TRN.IMG + v}" alt="${esc(a.replace(/-/g, ' '))}" loading="lazy"></label>`; }).join('')}</div>`;

  function setupAuthPage() {
    if (!$('#loginForm')) return;
    const regions = TRN.db.regions, platforms = TRN.db.platforms;
    $$('select[name=region]').forEach(s => (s.innerHTML = options(regions, 'NA East')));
    $$('select[name=platform]').forEach(s => (s.innerHTML = options(platforms, 'Cross-platform')));
    $('#avatarSlot').innerHTML = avatarPicker('avatar', 'raiders/raider-solo-scout.webp');
    const sw = tab => { const reg = tab === 'register'; $('#registerForm').classList.toggle('hidden', !reg); $('#loginForm').classList.toggle('hidden', reg); $('#registerTab').classList.toggle('active', reg); $('#loginTab').classList.toggle('active', !reg); };
    $('#loginTab').onclick = () => sw('login'); $('#registerTab').onclick = () => sw('register');
    if (location.hash === '#register') sw('register');
    const next = TRN.param('next') || 'profile.html';
    const safeNext = /^[a-z0-9-]+\.html(\?[^#]*)?$/i.test(next) ? next : 'profile.html';
    $('#registerForm').onsubmit = async e => { e.preventDefault(); const m = $('#registerMsg'); m.textContent = 'Creating account…'; try { await register(new FormData(e.target)); m.textContent = TRN.realMode ? 'Account created.' : 'Demo account created.'; setTimeout(() => (location.href = safeNext), 400); } catch (err) { m.textContent = err.message; } };
    $('#loginForm').onsubmit = async e => { e.preventDefault(); const m = $('#loginMsg'); m.textContent = 'Logging in…'; try { await login(new FormData(e.target)); location.href = TRN.param('next') ? safeNext : 'hunts.html'; } catch (err) { m.textContent = err.message; } };
  }

  async function setupProfilePage() {
    const form = $('#profileForm'); if (!form) return;
    const user = await requireUser('profile.html'); if (!user) return;
    const uid = user.user_id || user.id;
    form.elements.region.innerHTML = options(TRN.db.regions, user.region || 'NA East');
    form.elements.platform.innerHTML = options(TRN.db.platforms, user.platform || 'Cross-platform');
    form.elements.display_name.value = user.display_name || ''; form.elements.raider_tag.value = user.raider_tag || '';
    $('#profileAvatarSlot').innerHTML = avatarPicker('avatar', user.avatar || 'raiders/raider-solo-scout.webp');
    const paintHead = u => {
      $('#profileName').textContent = u.display_name || 'My Profile';
      $('#profileMeta').innerHTML = `<span>${TRN.svg('radio')} ${esc(u.platform || 'Cross-platform')}</span><span>${TRN.svg('pin')} ${esc(u.region || 'NA East')}</span><span class="private-tag" title="Only visible to you">${TRN.svg('info')} Tag: ${esc(u.raider_tag || 'not set')} · private</span>`;
      $('#profileAvatar').src = TRN.IMG + (u.avatar || 'raiders/raider-solo-scout.webp');
    };
    paintHead(user);
    form.onsubmit = async e => {
      e.preventDefault(); const fd = new FormData(form), msg = $('#profileMsg');
      const patch = { display_name: fd.get('display_name'), raider_tag: fd.get('raider_tag'), platform: fd.get('platform'), region: fd.get('region'), avatar: fd.get('avatar') || user.avatar };
      try {
        if (!TRN.realMode) { const users = LS().get('trn_users', []); const i = users.findIndex(x => x.id === user.id); if (i > -1) users[i] = { ...users[i], ...patch }; LS().set('trn_users', users); setDemoSession({ ...user, ...patch }); }
        else { let r = await TRN.sb.from('profiles').update({ display_name: patch.display_name, platform: patch.platform, region: patch.region, avatar: patch.avatar }).eq('id', user.user_id); if (r.error) throw r.error; r = await TRN.sb.from('private_profiles').upsert({ id: user.user_id, raider_tag: patch.raider_tag }); if (r.error) throw r.error; }
        Object.assign(user, patch); paintHead(user); msg.textContent = 'Profile saved.'; TRN.toast('Profile saved');
      } catch (err) { msg.textContent = err.message; }
    };
    const [hunts, trades] = await Promise.all([TRN.store.listHunts(), TRN.store.listTrades()]);
    const mine = hunts.filter(h => h.userId === uid), myTrades = trades.filter(t => t.userId === uid);
    const active = mine.filter(h => h.status !== 'completed'), done = mine.filter(h => h.status === 'completed');
    const huntRow = h => `<div class="mini-row"><img src="${TRN.img(TRN.data.item(h.itemId)?.image)}" alt=""><div><strong>${TRN.data.itemLink(h.itemId, h.itemName)}</strong><span>${TRN.data.mapLink(h.mapId)} · ${esc(h.region)} · ${TRN.ageFromIso(h.createdAt)}</span></div>${TRN.statusChip(h.status)}${h.status !== 'completed' ? `<button class="btn btn-ghost btn-xs" data-complete="${esc(h.id)}">Mark complete</button>` : ''}</div>`;
    $('#myHunts').innerHTML = active.length ? active.map(huntRow).join('') : '<p class="empty-note">No active loot hunts. <a href="hunts.html">Start one →</a></p>';
    $('#myCompleted').innerHTML = done.length ? done.map(huntRow).join('') : '<p class="empty-note">Completed hunts will appear here.</p>';
    $('#myTrades').innerHTML = myTrades.filter(t => t.status === 'open').map(t => `<div class="mini-row"><img src="${TRN.img(TRN.data.item(t.lookingFor[0]?.itemId)?.image)}" alt=""><div><strong>LF ${t.lookingFor.map(x => TRN.data.itemLink(x.itemId, x.name)).join(', ')}</strong><span>${esc(t.region)} · ${esc(t.platform)} · ${TRN.ageFromIso(t.createdAt)}</span></div>${TRN.statusChip(t.status)}<button class="btn btn-ghost btn-xs" data-close-trade="${esc(t.id)}">Close</button></div>`).join('') || '<p class="empty-note">No open trade requests. <a href="trade.html">Post one →</a></p>';
    TRN.trades.prep(trades);
    const invHtml = TRN.trades.inventoryPanel(uid);
    $('#myInventoryPanel')?.classList.toggle('hidden', !invHtml); if (invHtml) $('#myInventory').innerHTML = invHtml;
    $('#statActive').textContent = active.length; $('#statDone').textContent = done.length; $('#statTrades').textContent = myTrades.filter(t => t.status === 'open').length;
    $$('[data-complete]').forEach(b => (b.onclick = async () => { await TRN.store.updateHunt(b.dataset.complete, { status: 'completed' }); setupProfilePage(); }));
    $$('[data-close-trade]').forEach(b => (b.onclick = async () => { await TRN.store.updateTrade(b.dataset.closeTrade, { status: 'closed' }); setupProfilePage(); }));
    $('#badgeGrid').innerHTML = (TRN.db.badges || []).map(b => `<div class="badge-slot"><img src="${TRN.IMG}ui/rarity-${{ 'trusted-raider': 'legendary', 'loot-hunter': 'epic', 'route-scout': 'rare', 'project-specialist': 'uncommon' }[b.id]}.png" alt=""><strong>${esc(b.name)}</strong><small>Coming soon</small></div>`).join('');
    $('#logoutBtn').onclick = logout;
  }

  TRN.auth = { currentUser, requireUser, register, login, logout, setupAuthPage, setupProfilePage, avatarPicker, options };
})();
