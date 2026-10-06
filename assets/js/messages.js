/* The Raider Network v5 — private messages with optional context (tradeId / huntId / itemId).
 * v4 message records (no context) still load. Emails are never shown. */
(function () {
  const TRN = window.TRN, { $, $$, esc } = TRN;

  async function regarding(ctx) {
    if (!ctx) return null;
    if (ctx.trade_id) { const t = (await TRN.store.listTrades()).find(x => x.id === ctx.trade_id); const id = t?.lookingFor[0]?.itemId || ctx.item_id; return { label: `${t ? (t.lookingFor[0]?.name || TRN.data.itemName(id)) : TRN.data.itemName(id)} Trade`, href: `trade.html#${encodeURIComponent(ctx.trade_id)}`, itemId: id }; }
    if (ctx.hunt_id) { const h = (await TRN.store.listHunts()).find(x => x.id === ctx.hunt_id); const id = h?.itemId || ctx.item_id; return { label: `${h ? (h.itemName || TRN.data.itemName(id)) : TRN.data.itemName(id)} Loot Hunt`, href: `hunts.html#${encodeURIComponent(ctx.hunt_id)}`, itemId: id }; }
    if (ctx.item_id) return { label: TRN.data.itemName(ctx.item_id), href: `item.html?id=${encodeURIComponent(ctx.item_id)}`, itemId: ctx.item_id };
    return null;
  }

  async function setupMessages() {
    if (!$('#conversationList')) return;
    const user = await TRN.auth.requireUser('messages.html' + location.search); if (!user) return;
    const uid = user.user_id || user.id;
    const p = new URLSearchParams(location.search);
    const to = p.get('to'), toName = p.get('name') || 'Raider', intent = p.get('intent');
    const startCtx = { trade_id: p.get('tradeId') || null, hunt_id: p.get('huntId') || null, item_id: p.get('itemId') || null };
    const hasCtx = Object.values(startCtx).some(Boolean);
    let msgs = await TRN.store.listMessages(user);
    const counterpart = m => (m.sender_id === uid ? { id: m.recipient_id, name: m.recipient_name || 'Raider' } : { id: m.sender_id, name: m.sender_name || 'Raider' });
    let activeId = null, activeName = '', activeCtx = null;

    async function renderList() {
      msgs = await TRN.store.listMessages(user);
      const conv = new Map();
      [...msgs].reverse().forEach(m => { const c = counterpart(m); if (c.id && !conv.has(c.id)) conv.set(c.id, { ...c, last: m }); });
      if (to && to !== uid && !conv.has(to)) conv.set(to, { id: to, name: toName, last: null, draft: true });
      const rows = await Promise.all([...conv.values()].map(async c => {
        const ctx = c.last && (c.last.trade_id || c.last.hunt_id || c.last.item_id) ? c.last : (c.draft ? startCtx : null);
        const reg = await regarding(ctx); const pu = TRN.store.publicUser(c.id);
        return `<button class="conversation-item ${c.id === activeId ? 'active' : ''}" data-id="${esc(c.id)}" data-name="${esc(c.name)}">
          ${pu?.avatar ? `<img class="avatar-img" src="${TRN.IMG + pu.avatar}" alt="">` : `<span class="avatar">${esc(c.name[0]?.toUpperCase() || 'R')}</span>`}
          <span class="conversation-copy"><strong>${esc(c.name)}</strong><small>${reg ? 'Re: ' + esc(reg.label) : c.last ? esc(c.last.body.slice(0, 42)) : 'New conversation'}</small></span>
          ${c.last ? `<time>${TRN.ageFromIso(c.last.created_at)}</time>` : '<span class="status-chip status-open">NEW</span>'}</button>`;
      }));
      $('#conversationList').innerHTML = rows.join('') || `<div class="empty-note pad">${TRN.icon('message')}<p>No conversations yet. Use <b>Message Raider</b> on a Loot Hunt or Trade request.</p></div>`;
      if (!rows.length) showExample();
      $$('.conversation-item').forEach(i => (i.onclick = () => openConversation(i.dataset.id, i.dataset.name)));
      $('#unreadCount') && ($('#unreadCount').textContent = conv.size);
    }

    async function openConversation(id, name, ctx) {
      activeId = id; activeName = name;
      const thread = (await TRN.store.listMessages(user)).filter(m => (m.sender_id === uid && m.recipient_id === id) || (m.sender_id === id && m.recipient_id === uid));
      const lastCtx = [...thread].reverse().find(m => m.trade_id || m.hunt_id || m.item_id);
      activeCtx = ctx || (lastCtx ? { trade_id: lastCtx.trade_id || null, hunt_id: lastCtx.hunt_id || null, item_id: lastCtx.item_id || null } : null);
      $$('.conversation-item').forEach(x => x.classList.toggle('active', x.dataset.id === id));
      $('#chatEmpty').classList.add('hidden'); $('#chatActive').classList.remove('hidden'); $('.messages-shell').classList.add('chat-open');
      const pu = TRN.store.publicUser(id);
      $('#chatName').textContent = name;
      $('#chatAvatar').innerHTML = pu?.avatar ? `<img class="avatar-img" src="${TRN.IMG + pu.avatar}" alt="">` : `<span class="avatar">${esc(name[0]?.toUpperCase() || 'R')}</span>`;
      $('#chatMeta').textContent = pu ? [pu.platform, pu.region, pu.archetype].filter(Boolean).join(' · ') : 'Raider';
      const reg = await regarding(activeCtx), it = reg?.itemId ? TRN.data.item(reg.itemId) : null;
      $('#chatRegarding').innerHTML = reg ? `${it ? `<img src="${TRN.img(it.image)}" alt="">` : TRN.icon('trade')}<span><small>REGARDING</small><a href="${reg.href}">${esc(reg.label)}</a></span>${it ? `<a class="btn btn-ghost btn-xs" href="item.html?id=${encodeURIComponent(it.id)}">Item Intel</a>` : ''}` : '';
      $('#chatRegarding').classList.toggle('hidden', !reg);
      const ctxTag = m => { if (!(m.trade_id || m.hunt_id || m.item_id)) return ''; return `<em class="ctx-tag">${m.trade_id ? 'Trade' : m.hunt_id ? 'Hunt' : 'Item'}: ${esc(TRN.data.itemName(m.item_id))}</em>`; };
      $('#messageThread').innerHTML = thread.length ? thread.map(m => `<div class="bubble ${m.sender_id === uid ? 'mine' : ''}">${ctxTag(m)}${esc(m.body)}<small>${esc(TRN.ageFromIso(m.created_at))}</small></div>`).join('') : `<div class="empty-note">No messages yet. Agree on time, platform and squad here — share your Raider tag only when you are ready.</div>`;
      $('#messageThread').scrollTop = $('#messageThread').scrollHeight;
      const ta = $('#messageForm textarea');
      if (!thread.length && ta && !ta.value) {
        if (intent === 'join') ta.value = `Hey ${name}, I'd like to join your ${reg ? reg.label : 'loot hunt'}. I'm on ${user.platform || 'Cross-platform'} (${user.region || 'NA East'}).`;
        else if (intent === 'trade') ta.value = `Hey ${name}, I'm responding to your Trade Board post${reg ? ' (' + reg.label + ')' : ''}. Are you still looking?`;
      }
    }

    $('#messageForm').onsubmit = async e => {
      e.preventDefault(); if (!activeId) return;
      const fd = new FormData(e.target), body = String(fd.get('body') || '').trim(), msg = $('#messageFormMsg'); if (!body) return;
      try {
        const rec = { sender_id: uid, recipient_id: activeId, sender_name: user.display_name, recipient_name: activeName, body, ...(activeCtx || {}) };
        await TRN.store.sendMessage(rec); e.target.reset(); msg.textContent = '';
        await openConversation(activeId, activeName, activeCtx); await renderList();
      } catch (err) { msg.textContent = err.message; }
    };
    /* Static, clearly-labelled example so the empty page still explains itself. Not stored, not a real user. */
    function showExample() {
      $('#chatEmpty').innerHTML = `<div class="example-convo"><span class="demo-pill">EXAMPLE · DEMO CONTENT</span>
        <div class="chat-regarding"><span><small>REGARDING</small><b>Rotary Encoder Trade</b></span></div>
        <div class="bubble">Hey — saw your Trade Board post. Still looking for a Rotary Encoder?<small>Example Raider · demo</small></div>
        <div class="bubble mine">Yes! What would you want for it?<small>You · demo</small></div>
        <p class="small-note">This is an illustration of how private messages look — it is not a real conversation. Start one with <b>Message Raider</b> on a Loot Hunt or Trade listing.</p></div>`;
    }
    $('#chatBack').onclick = () => $('.messages-shell').classList.remove('chat-open');
    await renderList();
    if (to && to !== uid) openConversation(to, toName, hasCtx ? startCtx : null);
    else { const first = $('.conversation-item'); if (first && innerWidth > 760) openConversation(first.dataset.id, first.dataset.name); }
  }

  TRN.messages = { setupMessages, regarding };
})();
