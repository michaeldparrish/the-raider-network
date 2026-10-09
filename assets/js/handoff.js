/* The Raider Network v6.2 — private trade handoff.
 * After an offer is accepted, the two participants (and only they; the server enforces this) see each other's Embark ID,
 * the agreed items, how to connect in ARC Raiders, and confirm the in-game exchange. The trade is COMPLETED only when
 * both have confirmed. Server mode only: there is no demo-mode equivalent. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;
  const API = {
    list: () => TRN.api.get('/handoffs'),
    get: id => TRN.api.get('/handoffs/' + encodeURIComponent(id)),
    open: offerId => TRN.api.post('/offers/' + encodeURIComponent(offerId) + '/handoff'),
    seen: id => TRN.api.post('/handoffs/' + encodeURIComponent(id) + '/seen'),
    confirm: id => TRN.api.post('/handoffs/' + encodeURIComponent(id) + '/confirm'),
    cancel: (id, reason) => TRN.api.post('/handoffs/' + encodeURIComponent(id) + '/cancel', { reason }),
    report: (id, reason, details) => TRN.api.post('/handoffs/' + encodeURIComponent(id) + '/report', { reason, details }),
  };
  const STATUS = {
    AWAITING_EXCHANGE: ['Awaiting exchange', 'status-awaiting'], COMPLETED: ['Completed', 'status-completed'],
    CANCELLED: ['Cancelled', 'status-closed'], HISTORICAL: ['Earlier trade', 'status-historical'], NOT_OPENED: ['Accepted', 'status-awaiting'],
  };
  const chip = s => { const [t, c] = STATUS[s] || [s, 'status-open']; return `<span class="status-chip ${c}">${esc(t.toUpperCase())}</span>`; };
  const CANCEL = { no_show: 'The other Raider didn’t show up', could_not_connect: 'We couldn’t connect in-game', changed_mind: 'Changed my mind', wrong_item: 'Item not as agreed', other: 'Other reason' };
  const REPORT = { no_show: 'No-show', did_not_deliver: 'Didn’t hand over the agreed item', scam_attempt: 'Scam attempt', abusive: 'Abusive behaviour', other: 'Something else' };
  const link = (o) => (o.id ? `handoff.html?id=${encodeURIComponent(o.id)}` : `handoff.html?offer=${encodeURIComponent(o.offer_id)}`);
  const itemTxt = x => x ? `${x.quantity && x.quantity > 1 ? x.quantity + '× ' : ''}${TRN.data.itemLink(x.item_id, x.name)}` : '';

  /* Shared list row: My Profile "Accepted trades" panel and the Messages "Trade handoffs" inbox. */
  function rowHtml(h) {
    const other = h.other || {}, want = h.trade?.wanted;
    const sub = h.status === 'AWAITING_EXCHANGE' ? (h.you?.confirmed_at ? `You confirmed · waiting for ${esc(other.display_name)}` : other.confirmed_at ? `${esc(other.display_name)} confirmed · your turn` : 'Next: add each other in ARC Raiders')
      : h.status === 'NOT_OPENED' ? 'Accepted before trade handoffs existed · open to see details' : h.status === 'CANCELLED' ? 'Cancelled' : 'Done';
    return `<div class="handoff-row" data-handoff-row>
      <div class="handoff-row__main"><span>${h.your_role === 'TRADE_OWNER' ? 'Your trade with' : 'Your offer to'} <b>${esc(other.display_name || 'Raider')}</b>${other.username ? ` <small>@${esc(other.username)}</small>` : ''}</span>
        <strong>LF ${want ? TRN.data.itemLink(want.item_id, want.name) : 'trade'}</strong><small class="muted">${sub}</small></div>
      ${chip(h.status)}<a class="btn btn-primary btn-xs" href="${link(h)}">View Trade Details</a></div>`;
  }
  async function listAll() {
    const d = await API.list();
    const order = { AWAITING_EXCHANGE: 0, NOT_OPENED: 1, COMPLETED: 2, HISTORICAL: 3, CANCELLED: 4 };
    return { rows: [...d.handoffs, ...d.not_opened].sort((a, b) => (order[a.status] - order[b.status]) || String(b.updated_at).localeCompare(String(a.updated_at))), unseen: d.unseen, raw: d };
  }
  function listHtml(rows, empty) {
    return rows.length ? rows.map(rowHtml).join('') : `<p class="empty-note">${empty}</p>`;
  }

  /* One-time "Trade accepted" banner. Shown until the handoff has been opened (or dismissed); the server remembers. */
  function bannerHtml(rows, unseen) {
    const fresh = rows.filter(r => unseen.includes(r.id));
    if (!fresh.length) return '';
    const h = fresh[0];
    return `<div class="handoff-banner" role="status">${TRN.icon('trade')}<div><strong>Trade accepted — view details</strong>
      <span>${esc(h.other.display_name)} ${h.your_role === 'TRADE_OWNER' ? 'is ready to trade with you' : 'accepted your offer'}${fresh.length > 1 ? ` (+${fresh.length - 1} more)` : ''}. Next step: add each other in ARC Raiders.</span></div>
      <a class="btn btn-primary" href="${link(h)}">View Trade Details</a><button class="text-btn" data-dismiss-handoffs="${esc(fresh.map(x => x.id).join(','))}">Dismiss</button></div>`;
  }
  function wireBanner(root) {
    $$('[data-dismiss-handoffs]', root).forEach(b => (b.onclick = async () => {
      b.closest('.handoff-banner')?.remove();
      for (const id of b.dataset.dismissHandoffs.split(',')) { try { await API.seen(id); } catch (e) { console.error(e); } }
    }));
  }

  /* ---------------------------------------------------------------- copy */
  async function copyText(text, btn) {
    let ok = false;
    try { await navigator.clipboard.writeText(text); ok = true; } catch {
      const ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select(); try { ok = document.execCommand('copy'); } catch { ok = false; } ta.remove();
    }
    if (btn) { const t = btn.innerHTML; btn.innerHTML = ok ? 'Copied ✓' : 'Select and copy'; btn.classList.toggle('copied', ok); setTimeout(() => { btn.innerHTML = t; btn.classList.remove('copied'); }, 2200); }
    if (!ok) { const el = $('#otherEmbarkId'); if (el) { const r = document.createRange(); r.selectNodeContents(el); const s = getSelection(); s.removeAllRanges(); s.addRange(r); } }
    return ok;
  }

  /* ---------------------------------------------------------------- page */
  function personCard(p, label, isYou, h) {
    const conf = p.confirmed_at ? `<span class="hp-conf ok">${TRN.svg('check')} Confirmed the exchange</span>` : (h.status === 'AWAITING_EXCHANGE' ? '<span class="hp-conf">Not confirmed yet</span>' : '');
    return `<div class="hp-person ${isYou ? 'is-you' : ''}"><img class="avatar-img" src="${TRN.IMG + esc(p.avatar_url || 'raiders/raider-solo-scout.webp')}" alt="">
      <div><small>${esc(label)}</small><strong>${esc(p.display_name)}</strong><span>@${esc(p.username)} · ${esc(p.platform || 'Platform not set')}${p.region ? ' · ' + esc(p.region) : ''}</span>${conf}</div></div>`;
  }
  function idBlock(h) {
    const o = h.other, you = h.you;
    if (h.status === 'CANCELLED') return `<div class="hp-id hp-id--muted"><small>EMBARK ID</small><p>This trade was cancelled, so ${esc(o.display_name)}'s Embark ID is no longer shown.</p></div>`;
    if (h.status === 'HISTORICAL') {
      const hs = h.historical || {};
      if (!hs.can_share) return `<div class="hp-id hp-id--muted"><small>EMBARK ID</small><p>This offer was accepted before trade handoffs existed and isn't the single, completed trade on this post, so Embark IDs aren't shared here.</p></div>`;
      const share = hs.you_shared ? `<p class="small-note">You've shared your Embark ID${you.embark_id ? ` (<code>${esc(you.embark_id)}</code>)` : ''} with ${esc(o.display_name)} for this trade.</p>`
        : `<div class="hp-share"><p>This trade was completed before trade handoffs existed, so Embark IDs were never exchanged. <b>Each Raider chooses whether to share theirs.</b></p><button class="btn btn-primary" id="shareIdBtn" type="button">Share my Embark ID with ${esc(o.display_name)}</button></div>`;
      const theirsH = o.embark_id ? `<div class="hp-id"><small>${esc(o.display_name.toUpperCase())}'S EMBARK ID</small><div class="hp-id__row"><code id="otherEmbarkId">${esc(o.embark_id)}</code><button class="btn btn-primary" id="copyEmbark" type="button">${TRN.icon('trade')} Copy Embark ID</button></div></div>`
        : `<div class="hp-id hp-id--muted"><small>EMBARK ID</small><p>${esc(o.display_name)} ${hs.other_opened ? "hasn't saved an Embark ID yet." : "hasn't chosen to share their Embark ID for this trade yet."}</p></div>`;
      return theirsH + share + (hs.you_shared && !you.embark_id ? mineBlock(h) : '');
    }
    const theirs = o.embark_id
      ? `<div class="hp-id"><small>${esc(o.display_name.toUpperCase())}'S EMBARK ID</small><div class="hp-id__row"><code id="otherEmbarkId">${esc(o.embark_id)}</code><button class="btn btn-primary" id="copyEmbark" type="button">${TRN.icon('trade')} Copy Embark ID</button></div><span class="small-note">Private: only you and ${esc(o.display_name)} can see this page.</span></div>`
      : `<div class="hp-id hp-id--warn"><small>EMBARK ID</small><p><b>${esc(o.display_name)} hasn't added their Embark ID yet.</b> You need it to find each other in ARC Raiders. It appears here automatically as soon as they save it in My Profile; check back shortly.</p></div>`;
    return theirs + mineBlock(h);
  }
  function mineBlock(h) {
    const o = h.other, you = h.you;
    return you.embark_id ? `<p class="small-note">Your Embark ID shared with ${esc(o.display_name)}: <code>${esc(you.embark_id)}</code> · <a href="profile.html#embark">change</a></p>`
      : `<form class="hp-myid" id="myIdForm"><label><b>Add your Embark ID</b> so ${esc(o.display_name)} can find you<input class="input" name="raider_tag" maxlength="30" placeholder="RaiderName#1234" autocomplete="off" required></label><button class="btn btn-primary">Save</button><span class="form-note" role="status"></span>
          <small class="muted">In ARC Raiders: Main Menu → Social menu (👥) → your profile → <b>Show Discriminator</b>. It looks like <code>DisplayName#1234</code>.</small></form>`;
  }
  function agreedBlock(h) {
    const a = h.agreed, ownerIsYou = h.your_role === 'TRADE_OWNER';
    const owner = ownerIsYou ? 'You' : esc(h.other.display_name), sender = ownerIsYou ? esc(h.other.display_name) : 'You';
    return `<div class="hp-agreed">
      <div><small>TRADE POST BY ${owner.toUpperCase()}</small><p><b>Looking for:</b> ${itemTxt(a.owner_wants)}</p><p><b>Offered:</b> ${a.owner_gives ? itemTxt(a.owner_gives) : '<span class="muted">Not specified in the post</span>'}</p></div>
      <div><small>ACCEPTED OFFER FROM ${sender.toUpperCase()}</small><p><b>Offered:</b> ${a.sender_gives ? itemTxt(a.sender_gives) : '<span class="muted">No item named in the offer</span>'}</p>${h.offer.message ? `<blockquote>${esc(h.offer.message)}</blockquote>` : ''}</div>
      <p class="small-note">Shown exactly as posted. Agree any details that aren't listed here before you meet.</p></div>`;
  }
  const STEPS = (h) => `<ol class="hp-steps">
      <li><b>Copy ${esc(h.other.display_name)}'s Embark ID</b> with the button above.</li>
      <li><b>Add each other in ARC Raiders.</b> From the Main Menu open the Social menu (👥) and send a friend request using the Embark ID. Make sure crossplay is on if you're on different platforms.</li>
      <li><b>Team up and make the exchange</b> as agreed above. Never share account logins or pay real money; the trade is item for item only.</li>
      <li><b>Confirm here.</b> Each of you presses <i>Confirm Trade Completed</i>. The trade is marked completed only when you have both confirmed.</li></ol>`;

  async function setupHandoffPage() {
    const root = $('#handoffRoot'); if (!root) return;
    const p = new URLSearchParams(location.search);
    const user = await TRN.auth.requireUser('handoff.html' + location.search); if (!user) return;
    if (TRN.mode !== 'server') { root.innerHTML = `<div class="notice-bar">${TRN.icon('warning')}<div><strong>Trade handoffs need the live server.</strong> They aren't available in local demo mode.</div></div>`; return; }
    let h;
    try {
      if (p.get('id')) h = (await API.get(p.get('id'))).handoff;
      else if (p.get('offer')) { h = (await API.open(p.get('offer'))).handoff; history.replaceState(null, '', 'handoff.html?id=' + encodeURIComponent(h.id)); }
      else throw new Error('No trade selected.');
    } catch (e) { root.innerHTML = `<div class="notice-bar">${TRN.icon('warning')}<div><strong>${esc(e.message || 'This trade handoff could not be opened.')}</strong> <a href="messages.html">See all your trade handoffs →</a></div></div>`; return; }
    if (h.unseen && h.status !== 'HISTORICAL') API.seen(h.id).catch(() => {});   // historical: sharing is an explicit button
    render(h);

    function render(h) {
      const o = h.other, done = h.status === 'COMPLETED' || h.status === 'HISTORICAL';
      const head = h.status === 'HISTORICAL' ? `<div class="notice-bar">${TRN.svg('info')}<div><strong>${h.historical?.trade_completed ? 'Completed before trade handoffs existed.' : 'Accepted before trade handoffs existed.'}</strong> Shown for reference. Nothing here changes the trade's recorded status.</div></div>`
        : h.status === 'COMPLETED' ? `<div class="notice-bar notice-bar--ok">${TRN.svg('check')}<div><strong>Trade completed.</strong> You both confirmed the exchange on ${esc(new Date(h.completed_at).toLocaleString())}.</div></div>`
        : h.status === 'CANCELLED' ? `<div class="notice-bar">${TRN.icon('warning')}<div><strong>This trade was cancelled${h.cancelled?.by_you ? ' by you' : ` by ${esc(o.display_name)}`}.</strong> Reason: ${esc(CANCEL[h.cancelled?.reason] || 'not given')}. The trade post is back on the board.</div></div>` : '';
      const actions = h.status !== 'AWAITING_EXCHANGE' ? '' : `<section class="panel hp-actions">
        ${h.can_confirm ? `<button class="btn btn-primary btn-lg" id="confirmBtn">${TRN.svg('check')} Confirm Trade Completed</button><p class="small-note">Only press this after the items have changed hands in ARC Raiders.${o.confirmed_at ? ` <b>${esc(o.display_name)} has already confirmed.</b>` : ''}</p>`
          : `<p class="hp-waiting">${TRN.svg('clock')}<span>You confirmed. Waiting for <b>${esc(o.display_name)}</b> to confirm. The trade completes when they do.</span></p>`}
        <details class="hp-more"><summary>Exchange didn't happen?</summary>
          <form id="cancelForm" class="stack-sm"><label>Cancel this trade<select class="input" name="reason" required><option value="">Choose a reason…</option>${Object.entries(CANCEL).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select></label>
            <button class="btn btn-ghost btn-danger">Cancel trade</button><span class="form-note" role="status"></span><small class="muted">The post goes back on the Trade Board and ${esc(o.display_name)} stops seeing your Embark ID.</small></form>
        </details></section>`;
      const report = `<details class="hp-more hp-report"><summary>Report a problem with this trade</summary>
        <form id="reportForm" class="stack-sm"><label>What went wrong?<select class="input" name="reason" required><option value="">Choose…</option>${Object.entries(REPORT).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select></label>
          <label>Details <span class="muted-label">(optional, private to our moderators)</span><textarea class="input" name="details" rows="3" maxlength="500"></textarea></label>
          <button class="btn btn-ghost">Send report</button><span class="form-note" role="status"></span></form></details>`;
      root.innerHTML = `
        <div class="hp-head"><div><span class="eyebrow">${TRN.icon('trade')} PRIVATE TRADE HANDOFF</span><h1>Trade with ${esc(o.display_name)}</h1>
          <p class="muted">LF ${TRN.data.itemLink(h.trade.wanted.item_id, h.trade.wanted.name)} · ${esc(h.trade.platform)} · ${esc(h.trade.region)} · accepted ${TRN.ageFromIso(h.created_at)}</p></div>${chip(h.status)}</div>
        ${head}
        <div class="hp-grid">
          <section class="panel hp-people">${personCard(h.you, 'YOU', true, h)}${personCard(o, h.your_role === 'TRADE_OWNER' ? 'OFFER FROM' : 'TRADE POSTED BY', false, h)}</section>
          <section class="panel hp-idpanel">${idBlock(h)}</section>
          <section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('inventory')} AGREED TRADE</span></header>${agreedBlock(h)}</section>
          ${done || h.status === 'CANCELLED' ? '' : `<section class="panel"><header class="panel-head"><span class="eyebrow">${TRN.icon('route')} HOW TO CONNECT IN ARC RAIDERS</span></header>${STEPS(h)}</section>`}
        </div>
        ${actions}${report}
        <p class="small-note hp-foot"><a href="messages.html">← All trade handoffs</a> · Embark IDs are never shown on public pages, profiles or the Trade Board.</p>`;
      $('#copyEmbark')?.addEventListener('click', e => copyText(o.embark_id, e.currentTarget));
      const sb = $('#shareIdBtn');
      if (sb) sb.onclick = async () => { sb.disabled = true; try { await API.seen(h.id); render((await API.get(h.id)).handoff); TRN.toast('Embark ID shared'); } catch (err) { TRN.toast(err.message); sb.disabled = false; } };
      const my = $('#myIdForm');
      if (my) my.onsubmit = async e => {
        e.preventDefault(); const note = $('.form-note', my), v = String(new FormData(my).get('raider_tag') || '').trim();
        try { await TRN.api.patch('/me', { raider_tag: v }); note.textContent = 'Saved.'; render((await API.get(h.id)).handoff); TRN.toast('Embark ID saved'); }
        catch (err) { note.textContent = err.message; }
      };
      const cb = $('#confirmBtn');
      if (cb) cb.onclick = async () => {
        if (!cb.classList.contains('confirming')) { cb.classList.add('confirming'); cb.innerHTML = `${TRN.svg('check')} Yes — the items have changed hands`; setTimeout(() => { if (cb.isConnected) { cb.classList.remove('confirming'); cb.innerHTML = `${TRN.svg('check')} Confirm Trade Completed`; } }, 6000); return; }
        cb.disabled = true;
        try { const d = await API.confirm(h.id); TRN.toast(d.completed ? 'Trade completed — nice extraction!' : 'Confirmed. Waiting for the other Raider.'); render(d.handoff); }
        catch (err) { TRN.toast(err.message); cb.disabled = false; }
      };
      const cf = $('#cancelForm');
      if (cf) cf.onsubmit = async e => {
        e.preventDefault(); const note = $('.form-note', cf);
        try { const d = await API.cancel(h.id, new FormData(cf).get('reason')); TRN.toast('Trade cancelled'); render(d.handoff); } catch (err) { note.textContent = err.message; }
      };
      const rf = $('#reportForm');
      if (rf) rf.onsubmit = async e => {
        e.preventDefault(); const fd = new FormData(rf), note = $('.form-note', rf);
        try { await API.report(h.id, fd.get('reason'), String(fd.get('details') || '')); rf.innerHTML = '<p class="small-note">Thanks. Your report was sent privately to our moderators.</p>'; }
        catch (err) { note.textContent = err.message; }
      };
    }
  }

  TRN.handoffs = { API, listAll, listHtml, rowHtml, bannerHtml, wireBanner, setupHandoffPage, copyText };
})();
