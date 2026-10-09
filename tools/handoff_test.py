"""v6.2 trade-handoff tests: upgrade from v6.1 data, authorisation, privacy of Embark IDs, the full exchange workflow.

Runs Cloudflare's local runtime with a THROW-AWAY local D1 database (never production).

  python3 tools/handoff_test.py --v61 /path/to/v6.1/checkout

Phase A starts the real v6.1 code (from --v61, e.g. `git worktree add /tmp/trn-v61 d5b6bf1`) on a fresh database
and creates v6.1-era data through its own API: a COMPLETED trade with an ACCEPTED offer (the shape of the first real
production trade), an ACCEPTED offer on a still-OPEN trade, and an untouched trade with a PENDING offer.
Phase B applies migration 0002 to that same database, starts v6.2, proves every pre-existing row is byte-identical,
then exercises the handoff API. Requires: pip install requests."""
import sys, os, uuid, json, time, importlib.util
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []
PW = 'Handoff-Test-Pass-9'


def check(cond, label):
    RESULTS.append((bool(cond), label))
    print(('PASS ' if cond else 'FAIL ') + label)


def load_devserver(root):
    spec = importlib.util.spec_from_file_location('devserver_' + uuid.uuid4().hex[:6], os.path.join(root, 'tools', 'devserver.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


class Client:
    def __init__(self, base):
        self.base = base.rstrip('/') + '/api'; self.s = requests.Session()

    def req(self, method, path, body=None, csrf=True):
        h = {'Accept': 'application/json'}
        if csrf and method != 'GET': h['X-TRN-CSRF'] = '1'
        if body is not None: h['Content-Type'] = 'application/json'
        r = self.s.request(method, self.base + path, json=body, headers=h, timeout=30)
        try: d = r.json()
        except Exception: d = None
        return r.status_code, d, r

    get = lambda self, p: self.req('GET', p)
    post = lambda self, p, b=None, **k: self.req('POST', p, {} if b is None else b, **k)
    patch = lambda self, p, b=None: self.req('PATCH', p, {} if b is None else b)
    delete = lambda self, p: self.req('DELETE', p)


def register(base, name, embark=None):
    c = Client(base); u = (name.lower() + uuid.uuid4().hex[:5])[:20]
    body = {'username': u, 'display_name': name, 'email': f'{u}@example.com', 'password': PW, 'confirm_password': PW, 'region': 'NA East', 'platform': 'PlayStation'}
    if embark is not None: body['raider_tag'] = embark
    code, d, _ = c.post('/auth/register', body)
    assert code == 201, (code, d)
    c.username = u; c.id = d['user']['id']; c.name = name
    return c


def legacy_rows(srv):
    return {
        'trade_posts': srv.sql("SELECT * FROM trade_posts ORDER BY id"),
        'trade_offers': srv.sql("SELECT * FROM trade_offers ORDER BY id"),
        'users': srv.sql("SELECT id, username, display_name, email, password_hash, raider_tag, status, created_at, updated_at FROM users ORDER BY id"),
    }


def main():
    v61 = sys.argv[sys.argv.index('--v61') + 1] if '--v61' in sys.argv else '/tmp/trn-v61'
    DS61 = load_devserver(v61); DS62 = load_devserver(os.path.dirname(HERE))
    old = DS61.DevServer(port=8795); old.migrate(); old.start()
    persist = old.persist
    try:
        # ------------------------------------------------------------ Phase A: v6.1 data, created by v6.1 code
        b = old.base
        bailie = register(b, 'Bailie', 'Bailie0811#2468')        # trade owner (shape of the first real trade)
        perish = register(b, 'Perish', None)                      # offer sender without an Embark ID saved
        carol = register(b, 'Carol', 'CarolR#1001'); dave = register(b, 'Dave', 'Dave_Z#7777')
        _, d, _ = bailie.post('/trades', {'wanted_item_name': 'Compensator 3', 'offered_item_id': 'tempest-blueprint', 'region': 'NA East', 'platform': 'PlayStation', 'desired_time': 'Anytime'})
        t_done = d['trade']['id']
        _, d, _ = perish.post(f'/trades/{t_done}/offers', {'message': 'I have Compensator III', 'offered_item_name': 'Compensator III'}); o_done = d['offer']['id']
        bailie.patch(f'/offers/{o_done}', {'action': 'accept'})
        code, _, _ = bailie.patch(f'/trades/{t_done}', {'status': 'COMPLETED'})
        _, d, _ = bailie.post('/trades', {'wanted_item_id': 'anvil-blueprint', 'region': 'NA East', 'platform': 'PlayStation'}); t_open = d['trade']['id']
        _, d, _ = perish.post(f'/trades/{t_open}/offers', {'message': 'Bettina for your Anvil BP?'}); o_open = d['offer']['id']
        bailie.patch(f'/offers/{o_open}', {'action': 'accept'})
        _, d, _ = carol.post('/trades', {'wanted_item_id': 'light-gun-parts', 'region': 'NA East', 'platform': 'PlayStation'}); t_other = d['trade']['id']
        _, d, _ = dave.post(f'/trades/{t_other}/offers', {'message': 'have 3'}); o_other = d['offer']['id']
        _, d, _ = carol.post('/trades', {'wanted_item_id': 'arc-alloy', 'region': 'NA East', 'platform': 'PlayStation'}); t_closed = d['trade']['id']
        _, d, _ = dave.post(f'/trades/{t_closed}/offers', {'message': 'deal?'}); o_closed = d['offer']['id']
        carol.patch(f'/offers/{o_closed}', {'action': 'accept'}); carol.patch(f'/trades/{t_closed}', {'status': 'CLOSED'})
        before = legacy_rows(old)
        check(code == 200 and any(r['status'] == 'COMPLETED' for r in before['trade_posts']) and sum(r['status'] == 'ACCEPTED' for r in before['trade_offers']) == 3,
              'phase A: v6.1 created a COMPLETED trade with an ACCEPTED offer, an ACCEPTED offer on an OPEN trade, and a PENDING offer')
        old.stop()

        # ------------------------------------------------------------ Phase B: migrate the same DB, run v6.2
        srv = DS62.DevServer(port=8796, persist_dir=persist); srv.migrate(); srv.start(); B = srv.base
        try:
            for c in (bailie, perish, carol, dave): c.base = B.rstrip('/') + '/api'
            after = legacy_rows(srv)
            check(after == before, 'migration 0002 + v6.2 start: every pre-existing user, trade and offer row is byte-identical')
            tables = {r['name'] for r in srv.sql("SELECT name FROM sqlite_master WHERE type='table'")}
            check({'trade_handoffs', 'trade_reports'} <= tables and srv.sql('SELECT COUNT(*) AS n FROM trade_handoffs')[0]['n'] == 0, 'migration adds the two tables and creates no rows')
            _, h, _ = Client(B).get('/health'); check(h.get('ok') and h.get('api') == '6.2' and h.get('migrated'), f'health reports v6.2 migrated ({h})')
            _, d, _ = Client(B).get('/trades?status=ALL')
            check({t['id']: t['status'] for t in d['trades']}[t_done] == 'COMPLETED', 'historical completed trade still COMPLETED on the public board')

            # historical accepted offers are listed, not auto-created
            _, d, _ = perish.get('/handoffs')
            check(len(d['not_opened']) == 2 and not d['handoffs'] and not d['unseen'], 'pre-v6.2 accepted offers listed as "not opened"; no banner for old trades')
            code, d, _ = carol.post(f'/offers/{o_done}/handoff'); check(code == 404, 'third party cannot open a historical handoff (404)')
            code, d, _ = perish.post(f'/offers/{o_done}/handoff'); hd = d['handoff']
            check(code == 200 and hd['status'] == 'HISTORICAL' and not hd['can_confirm'] and not hd['can_cancel'], 'completed historical trade opens as read-only HISTORICAL handoff')
            check(hd['other']['embark_id'] is None and hd['historical'] == {'trade_completed': True, 'can_share': True, 'other_opened': False, 'you_shared': False},
                  'historical: pre-v6.2 private IDs stay hidden; opening the page shares nothing')
            check(hd['agreed']['owner_gives']['name'] == 'Tempest Blueprint' and hd['agreed']['sender_gives']['name'] == 'Compensator III', 'agreed items come from the recorded trade and offer')
            code, d2, _ = bailie.post(f'/offers/{o_done}/handoff'); check(code == 200 and d2['handoff']['id'] == hd['id'], 'owner opens the same historical handoff (idempotent)')
            _, d3, _ = perish.get(f"/handoffs/{hd['id']}"); check(d3['handoff']['other']['embark_id'] is None, 'the owner opening it shares nothing either')
            bailie.post(f"/handoffs/{hd['id']}/seen"); _, d3, _ = perish.get(f"/handoffs/{hd['id']}")
            check(d3['handoff']['other']['embark_id'] == 'Bailie0811#2468', 'after the owner presses Share, the sender sees their Embark ID (explicit opt-in)')
            _, d3, _ = bailie.get(f"/handoffs/{hd['id']}"); check(d3['handoff']['other']['embark_id'] is None and not d3['handoff']['historical']['other_opened'], 'the sender has not shared, so the owner sees nothing from them')
            code, d4, _ = dave.post(f'/offers/{o_closed}/handoff'); carol.post(f'/offers/{o_closed}/handoff'); _, d4, _ = dave.get(f"/handoffs/{d4['handoff']['id']}")
            code5, _, _ = carol.post(f"/handoffs/{d4['handoff']['id']}/seen"); _, d4, _ = dave.get(f"/handoffs/{d4['handoff']['id']}")
            check(d4['handoff']['status'] == 'HISTORICAL' and d4['handoff']['other']['embark_id'] is None and code5 == 409 and not d4['handoff']['historical']['can_share'],
                  'historical offer on a CLOSED trade (deal fell through) can never share Embark IDs')
            code, _, _ = perish.post(f"/handoffs/{hd['id']}/confirm"); check(code == 409, 'historical handoff cannot be confirmed (no status change)')
            code, d, _ = perish.post(f'/offers/{o_open}/handoff'); check(code == 409 and 'Bailie' in d['error']['message'], 'offer sender cannot turn an old accepted offer into a live exchange (owner must open it)')
            code, _, _ = bailie.post(f'/offers/{o_open}/handoff'); _, d, _ = bailie.get('/handoffs')
            live_legacy = [x for x in d['handoffs'] if x['offer']['id'] == o_open][0]
            check(live_legacy['status'] == 'AWAITING_EXCHANGE', 'accepted offer on a still-OPEN trade opens as AWAITING_EXCHANGE')
            check(legacy_rows(srv) == before, 'opening historical handoffs changed no trade, offer or user row')

            # ------------------------------------------------------------ new v6.2 flow
            erin = register(B, 'Erin', 'Erin.Trades#5150'); finn = register(B, 'Finn', 'FinnX#0042'); gus = register(B, 'Gus', 'GusOutsider#9999'); hal = register(B, 'Hal', None)
            code, d, _ = Client(B).post('/auth/register', {'username': 'badtag' + uuid.uuid4().hex[:4], 'display_name': 'Bad', 'email': uuid.uuid4().hex[:8] + '@example.com', 'password': PW, 'confirm_password': PW, 'raider_tag': 'not an id'})
            check(code == 400 and d['error']['field'] == 'raider_tag', 'invalid Embark ID rejected at registration')
            code, d, _ = hal.patch('/me', {'raider_tag': 'Hal R # 12'}); check(code == 400, 'malformed Embark ID rejected on profile save')
            code, d, _ = hal.patch('/me', {'raider_tag': 'HalRaider # 3141'}); check(code == 200 and d['user']['raider_tag'] == 'HalRaider#3141', 'Embark ID saved and normalised (spaces around # removed)')
            srv.sql(f"UPDATE users SET raider_tag = 'legacy free text tag' WHERE id = '{gus.id}'")
            code, d, _ = gus.patch('/me', {'display_name': 'Gus Two', 'raider_tag': 'legacy free text tag'})
            check(code == 200 and d['user']['raider_tag'] == 'legacy free text tag', 'an existing non-conforming tag is kept when the profile is saved unchanged')

            _, d, _ = erin.post('/trades', {'wanted_item_id': 'tempest-blueprint', 'offered_item_id': 'anvil-blueprint', 'offered_quantity': 2, 'region': 'NA East', 'platform': 'PlayStation'}); tid = d['trade']['id']
            _, d, _ = finn.post(f'/trades/{tid}/offers', {'message': 'Tempest BP for your 2 Anvil BPs', 'offered_item_id': 'tempest-blueprint'}); ofid = d['offer']['id']
            _, d, _ = hal.post(f'/trades/{tid}/offers', {'message': 'backup offer'}); ohal = d['offer']['id']
            code, d, _ = finn.patch(f'/offers/{ofid}', {'action': 'accept'}); check(code == 403, 'offer sender cannot accept their own offer')
            code, d, _ = erin.patch(f'/offers/{ofid}', {'action': 'accept'})
            hid = (d or {}).get('handoff', {}).get('id')
            check(code == 200 and d['offer']['status'] == 'ACCEPTED' and hid and d['handoff']['status'] == 'AWAITING_EXCHANGE', 'accepting an offer creates an AWAITING_EXCHANGE handoff atomically')
            code, d, _ = erin.patch(f'/offers/{ohal}', {'action': 'accept'}); check(code == 409, 'a second offer cannot be accepted while a handoff is active')

            code, d, _ = finn.get(f'/handoffs/{hid}'); fh = d['handoff']
            check(code == 200 and fh['other']['embark_id'] == 'Erin.Trades#5150' and fh['you']['embark_id'] == 'FinnX#0042' and fh['your_role'] == 'OFFER_SENDER', 'offer sender sees the owner\'s Embark ID')
            code, d, _ = erin.get(f'/handoffs/{hid}'); eh = d['handoff']
            check(code == 200 and eh['other']['embark_id'] == 'FinnX#0042' and eh['other']['display_name'] == 'Finn' and eh['other']['platform'] == 'PlayStation', 'trade owner sees the sender\'s Embark ID, name and platform')
            check(eh['agreed']['owner_gives'] == {'item_id': 'anvil-blueprint', 'name': 'Anvil Blueprint', 'quantity': 2} and eh['agreed']['sender_gives']['name'] == 'Tempest Blueprint', 'handoff shows agreed items and quantities')

            # authorisation: third parties and anonymous
            anon = Client(B)
            for path, m in ((f'/handoffs/{hid}', 'GET'), (f'/handoffs/{hid}/confirm', 'POST'), (f'/handoffs/{hid}/cancel', 'POST'), (f'/handoffs/{hid}/report', 'POST'), (f'/handoffs/{hid}/seen', 'POST'), (f'/offers/{ofid}/handoff', 'POST')):
                code, d, _ = gus.req(m, path, {'reason': 'other'} if m == 'POST' else None)
                code2, _, _ = anon.req(m, path, {'reason': 'other'} if m == 'POST' else None)
                check(code == 404 and code2 == 401 and 'Erin.Trades' not in json.dumps(d), f'{m} {path.split(hid)[-1] or path}: third party 404, anonymous 401')
            _, d, _ = gus.get('/handoffs'); check(not d['handoffs'] and not d['not_opened'], 'third party\'s handoff list does not include other people\'s handoffs')
            code, _, _ = finn.post(f'/handoffs/{hid}/confirm', csrf=False); check(code == 403, 'confirm without the CSRF header is refused')

            # public surfaces never carry Embark IDs
            ids = ['Erin.Trades#5150', 'FinnX#0042', 'Bailie0811#2468', 'HalRaider#3141', 'GusOutsider', 'CarolR#1001']
            blobs = []
            for c in (anon, gus):
                for p in ('/trades?status=ALL', f'/trades/{tid}', f'/trades/{t_done}', f'/users/{erin.username}', f'/users/{finn.username}', '/stats'):
                    blobs.append(json.dumps(c.get(p)[1]))
            blobs.append(json.dumps(gus.get(f'/trades/{tid}/offers')[1])); blobs.append(json.dumps(hal.get('/me/offers')[1])); blobs.append(json.dumps(finn.get('/me/offers')[1]))
            blobs.append(json.dumps(finn.get('/handoffs')[1]))
            leak = [i for i in ids for blob in blobs if i in blob]
            check(not leak, f'no Embark ID in public trades, profiles, stats, offers lists or the handoff list ({leak[:3]})')
            _, d, _ = anon.get(f'/trades/{tid}')
            check(d['trade']['display_status'] == 'AWAITING_EXCHANGE' and d['trade']['status'] == 'OPEN', 'public trade shows "Awaiting exchange" (row stays OPEN), with no participant details')

            # banner: unseen once, then gone
            _, d, _ = finn.get('/handoffs'); check(hid in d['unseen'], 'offer sender gets a one-time "trade accepted" notice')
            _, d, _ = erin.get('/handoffs'); check(hid not in d['unseen'], 'the owner who accepted is not notified about their own action')
            finn.post(f'/handoffs/{hid}/seen'); _, d, _ = finn.get('/handoffs'); check(hid not in d['unseen'], 'notice does not repeat after it has been seen')

            # owner shortcuts blocked during the exchange
            for body, label in (({'status': 'COMPLETED'}, 'mark completed alone'), ({'status': 'CLOSED'}, 'close'), ({'notes': 'changed'}, 'edit')):
                code, _, _ = erin.patch(f'/trades/{tid}', body); check(code == 409, f'owner cannot {label} the trade during an active handoff')
            code, _, _ = erin.delete(f'/trades/{tid}'); check(code == 409, 'owner cannot delete the trade during an active handoff')

            # both-player confirmation
            code, d, _ = finn.post(f'/handoffs/{hid}/confirm')
            check(code == 200 and not d['completed'] and d['handoff']['you']['confirmed_at'] and d['handoff']['status'] == 'AWAITING_EXCHANGE', 'first confirmation is recorded; trade not completed yet')
            _, d, _ = anon.get(f'/trades/{tid}'); check(d['trade']['status'] == 'OPEN', 'one confirmation does not complete the trade')
            code, d, _ = finn.post(f'/handoffs/{hid}/confirm'); check(code == 200 and not d['completed'], 'repeat confirmation by the same Raider changes nothing')
            _, d, _ = erin.get(f'/handoffs/{hid}'); check(d['handoff']['other']['confirmed_at'] and d['handoff']['can_confirm'], 'the other Raider sees the confirmation and can confirm independently')
            code, d, _ = erin.post(f'/handoffs/{hid}/confirm')
            check(code == 200 and d['completed'] and d['handoff']['status'] == 'COMPLETED', 'second confirmation completes the handoff')
            _, d, _ = anon.get(f'/trades/{tid}'); check(d['trade']['status'] == 'COMPLETED' and d['trade']['closed_at'], 'trade is COMPLETED only after both confirmations')
            st = srv.sql(f"SELECT status FROM trade_offers WHERE id = '{ohal}'")[0]['status']; check(st == 'DECLINED', 'remaining pending offers are declined when the trade completes')
            code, _, _ = erin.post(f'/handoffs/{hid}/cancel', {'reason': 'other'}); check(code == 409, 'a completed handoff cannot be cancelled')
            code, _, _ = erin.delete(f'/trades/{tid}'); check(code == 409, 'a trade with a handoff on record cannot be deleted (keeps the record and any report)')
            _, d, _ = erin.post('/trades', {'wanted_item_id': 'arc-circuitry', 'region': 'NA East', 'platform': 'PlayStation'}); tsolo = d['trade']['id']
            code, _, _ = erin.patch(f'/trades/{tsolo}', {'status': 'COMPLETED'}); check(code == 409, 'no Raider can mark a trade completed alone, even with no offer accepted')
            code, _, _ = erin.delete(f'/trades/{tsolo}'); check(code == 200, 'a trade without any handoff can still be deleted')

            # cancellation + reporting
            _, d, _ = erin.post('/trades', {'wanted_item_id': 'bobcat-blueprint', 'region': 'NA East', 'platform': 'PlayStation'}); t2 = d['trade']['id']
            _, d, _ = finn.post(f'/trades/{t2}/offers', {'message': 'one'}); o2 = d['offer']['id']
            _, d, _ = hal.post(f'/trades/{t2}/offers', {'message': 'two'}); o3 = d['offer']['id']
            _, d, _ = erin.patch(f'/offers/{o2}', {'action': 'accept'}); h2 = d['handoff']['id']
            code, _, _ = finn.post(f'/handoffs/{h2}/cancel', {'reason': 'banana'}); check(code == 400, 'cancel needs a valid reason')
            code, d, _ = finn.post(f'/handoffs/{h2}/cancel', {'reason': 'no_show'})
            check(code == 200 and d['handoff']['status'] == 'CANCELLED' and d['handoff']['other']['embark_id'] is None and d['handoff']['cancelled']['by_you'], 'either Raider can cancel; the other\'s Embark ID is hidden afterwards')
            _, d, _ = anon.get(f'/trades/{t2}'); check(d['trade']['status'] == 'OPEN' and d['trade']['display_status'] == 'OPEN', 'cancelled handoff returns the trade to the open board')
            code, d, _ = erin.patch(f'/offers/{o3}', {'action': 'accept'}); h3 = (d or {}).get('handoff', {}).get('id')
            check(code == 200 and h3 and h3 != h2, 'after a cancellation the owner can accept another offer')
            _, d, _ = erin.get(f'/handoffs/{h3}'); check(d['handoff']['you']['embark_id'] and d['handoff']['other']['embark_id'] == 'HalRaider#3141', 'new handoff with the second Raider')
            code, d, _ = gus.post(f'/handoffs/{h2}/report', {'reason': 'no_show'}); check(code == 404, 'third party cannot report a handoff')
            code, d, _ = erin.post(f'/handoffs/{h2}/report', {'reason': 'no_show', 'details': 'Did not show up at the meeting point.'})
            check(code == 201, 'participant can report an unsuccessful exchange')
            code, _, _ = erin.post(f'/handoffs/{h2}/report', {'reason': 'other'}); check(code == 409, 'one report per Raider per handoff')
            rep = srv.sql("SELECT reporter_id, reported_id, reason FROM trade_reports")
            check(len(rep) == 1 and rep[0]['reporter_id'] == erin.id and rep[0]['reported_id'] == finn.id, 'report stored against the other participant (derived server-side)')
            check(all('no_show' not in json.dumps(c.get('/trades?status=ALL')[1]) for c in (anon,)), 'reports never appear on public endpoints')

            # missing Embark ID
            jo = register(B, 'Jo', None); _, d, _ = jo.post('/trades', {'wanted_item_id': 'arc-alloy', 'region': 'NA East', 'platform': 'PlayStation'}); t4 = d['trade']['id']
            _, d, _ = erin.post(f'/trades/{t4}/offers', {'message': 'have alloy'}); o4 = d['offer']['id']
            _, d, _ = jo.patch(f'/offers/{o4}', {'action': 'accept'}); h4 = d['handoff']['id']
            _, d, _ = erin.get(f'/handoffs/{h4}'); check(d['handoff']['other']['embark_id'] is None, 'missing Embark ID is reported as null (the page prompts for it)')
            jo.patch('/me', {'raider_tag': 'JoJo#4242'}); _, d, _ = erin.get(f'/handoffs/{h4}'); check(d['handoff']['other']['embark_id'] == 'JoJo#4242', 'once saved, the Embark ID appears in the existing handoff')

            # historical rows still intact at the end
            end = legacy_rows(srv)
            same_trades = {r['id']: r for r in end['trade_posts']}; same_offers = {r['id']: r for r in end['trade_offers']}
            check(all(same_trades[r['id']] == r for r in before['trade_posts']) and all(same_offers[r['id']] == r for r in before['trade_offers']),
                  'after all tests, every v6.1-era trade and offer row is still byte-identical')
        finally:
            srv.stop()
    finally:
        old.stop(); old.cleanup()
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} handoff checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
