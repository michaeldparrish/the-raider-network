"""v6.3 Loot Trails API tests on Cloudflare's local runtime with a THROW-AWAY local D1 database and local
(simulated, on-disk) R2 bucket. Never touches production.  python3 tools/trails_test.py
Covers creation/reopen, invitations, owner vs contributor permissions, sessions (incl. ending), discoveries + pins,
two screenshots per discovery, 20 MiB limit, duplicates + explicit replacement, progress isolation, review,
explicit publication, public/private visibility, cross-trail access and identity-field exposure."""
import sys, os, io, uuid, json, struct, zlib
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devserver import DevServer

RESULTS = []
PW = 'Trails-Test-Pass-42'


def check(cond, label):
    RESULTS.append((bool(cond), label)); print(('PASS ' if cond else 'FAIL ') + label)


def png_bytes(w=8, h=8, color=(255, 106, 26)):
    raw = b''.join(b'\x00' + bytes(color) * w for _ in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


def jpeg_bytes():
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (16, 16), (25, 211, 197)).save(b, 'JPEG'); return b.getvalue()


class Client:
    def __init__(self, base): self.base = base.rstrip('/') + '/api'; self.s = requests.Session()

    def req(self, method, path, body=None, csrf=True, raw=None, ctype=None):
        h = {'Accept': 'application/json'}
        if csrf and method not in ('GET', 'HEAD'): h['X-TRN-CSRF'] = '1'
        if raw is not None:
            h['Content-Type'] = ctype; r = self.s.request(method, self.base + path, data=raw, headers=h, timeout=60)
        else:
            if body is not None: h['Content-Type'] = 'application/json'
            r = self.s.request(method, self.base + path, json=body, headers=h, timeout=60)
        try: d = r.json()
        except Exception: d = None
        return r.status_code, d, r

    get = lambda self, p: self.req('GET', p)
    post = lambda self, p, b=None, **k: self.req('POST', p, {} if b is None else b, **k)
    delete = lambda self, p: self.req('DELETE', p)
    upload = lambda self, p, data, ctype='image/png', **k: self.req('POST', p, raw=data, ctype=ctype, **k)


def register(base, name, embark=None):
    c = Client(base); u = (name.lower() + uuid.uuid4().hex[:5])[:20]
    body = {'username': u, 'display_name': name, 'email': f'{u}@example.com', 'password': PW, 'confirm_password': PW, 'region': 'NA East', 'platform': 'PC'}
    if embark: body['raider_tag'] = embark
    code, d, _ = c.post('/auth/register', body); assert code == 201, (code, d)
    c.username, c.id, c.name, c.email = u, d['user']['id'], name, f'{u}@example.com'
    return c


def main():
    srv = DevServer(port=8793); srv.migrate(); srv.start(); B = srv.base
    try:
        anon = Client(B)
        own = register(B, 'Owner', 'TrailBoss#1234'); con = register(B, 'Contrib', 'Helper#5678'); out = register(B, 'Outsider', 'Nosy#0001'); dec = register(B, 'Decliner')

        # ---------------------------------------------------------------- create / list / reopen
        code, d, _ = anon.post('/trails', {'title': 'x', 'mapId': 'spaceport'}); check(code == 401, 'unauthenticated create is refused (401)')
        code, d, _ = own.post('/trails', {'title': 'x', 'mapId': 'spaceport'}, csrf=False); check(code == 403, 'create without the CSRF header is refused')
        code, d, _ = own.post('/trails', {'title': 'Bad map', 'mapId': 'nowhere'}); check(code == 400, 'unsupported map is rejected')
        code, d, _ = own.post('/trails', {'title': 'Stella deep sweep', 'description': 'Squad notes: meet at Seed Vault.', 'mapId': 'stella-montis'})
        T = d['trail']['id']
        check(code == 201 and d['trail']['visibility'] == 'PRIVATE' and d['trail']['myRole'] == 'OWNER', 'trail created PRIVATE by default; creator is OWNER')
        _, d, _ = own.post('/trails', {'title': 'Second trail', 'mapId': 'pendola-pass'}); T2 = d['trail']['id']
        code, d, _ = own.get('/trails'); mine = {t['id']: t for t in d['trails']}
        check(T in mine and mine[T]['stats']['discoveries'] == 0 and mine[T]['myRole'] == 'OWNER', 'dashboard lists my trails with role and stats')
        code, d, _ = anon.get(f'/trails/{T}'); check(code == 404, 'anonymous cannot open a private trail (404)')
        code, d, _ = out.get(f'/trails/{T}'); check(code == 404, 'uninvited Raider cannot open a private trail (404)')
        code, d, _ = anon.get('/trails'); check(code == 401, 'unauthenticated trail list is refused (401)')

        # ---------------------------------------------------------------- invitations
        code, d, _ = con.post(f'/trails/{T}/invitations', {'username': out.username}); check(code == 404, 'non-owner cannot invite')
        code, d, _ = own.post(f'/trails/{T}/invitations', {'username': 'no_such_raider_x'}); check(code == 404, 'inviting an unknown username fails cleanly')
        code, d, _ = own.post(f'/trails/{T}/invitations', {'username': con.username.upper()})
        check(code == 201 and d['invitation']['status'] == 'INVITED', 'owner invites a Raider by username (case-insensitive)')
        code, d, _ = own.post(f'/trails/{T}/invitations', {'username': con.username}); check(code == 409, 'duplicate invitation is refused')
        code, d, _ = con.get('/me/trail-invitations')
        inv = [i for i in d['invitations'] if i['trailId'] == T]
        check(len(inv) == 1 and inv[0]['title'] == 'Stella deep sweep' and inv[0]['owner']['displayName'] == 'Owner', 'invited Raider sees the pending invitation')
        check('description' not in json.dumps(d) and own.id not in json.dumps(d), 'invitation shows title/owner name only (no description, no internal IDs)')
        code, d, _ = con.get(f'/trails/{T}'); check(code == 404, 'invited (not yet accepted) Raider cannot open the trail')
        code, d, _ = out.post(f'/trails/{T}/invitations/respond', {'decision': 'ACCEPT'}); check(code == 404, 'uninvited Raider cannot accept an invitation')
        own.post(f'/trails/{T}/invitations', {'username': dec.username})
        code, d, _ = dec.post(f'/trails/{T}/invitations/respond', {'decision': 'DECLINE'}); check(code == 200 and d['status'] == 'DECLINED', 'invited Raider can decline')
        code, d, _ = dec.get(f'/trails/{T}'); check(code == 404, 'declined Raider has no access')
        code, d, _ = own.post(f'/trails/{T}/invitations', {'username': dec.username}); check(code == 201, 'owner can re-invite a Raider who declined')
        code, d, _ = con.post(f'/trails/{T}/invitations/respond', {'decision': 'ACCEPT'}); check(code == 200 and d['status'] == 'ACCEPTED', 'invited Raider accepts')
        code, d, _ = con.get(f'/trails/{T}')
        check(code == 200 and d['view'] == 'MEMBER' and d['trail']['myRole'] == 'CONTRIBUTOR' and not d['permissions']['canReview'], 'accepted contributor opens the private trail as CONTRIBUTOR')
        squad = {m['username']: m for m in d['squad']}
        check(dec.username not in squad and squad[own.username]['role'] == 'OWNER' and 'completedCount' not in json.dumps(d['squad']),
              'contributor sees owner + accepted members only, with no other Raider\'s progress')
        _, d, _ = own.get(f'/trails/{T}'); squad = {m['username']: m for m in d['squad']}
        check(squad[dec.username]['status'] == 'INVITED' and squad[con.username]['status'] == 'ACCEPTED', 'owner sees every invitation state')

        # ---------------------------------------------------------------- sessions
        code, d, _ = out.post(f'/trails/{T}/sessions', {'title': 'sneaky'}); check(code == 404, 'uninvited Raider cannot start a session')
        code, d, _ = own.post(f'/trails/{T}/sessions', {'title': 'Night 1', 'notes': 'Seed Vault sweep'}); S1 = d['session']['id']
        check(code == 201 and d['session']['startedAt'] and d['session']['endedAt'] is None, 'owner starts a session (title, notes, start time)')
        code, d, _ = con.post(f'/trails/{T}/sessions', {'title': 'Night 2'}); S2 = d['session']['id']; check(code == 201, 'contributor can start a session too')
        code, d, _ = own.post(f'/trails/{T2}/sessions', {'title': 'Other trail'}); S_other = d['session']['id']

        # ---------------------------------------------------------------- discoveries + pins
        disc = lambda c, sid, **k: c.post(f'/trails/{T}/discoveries', {'title': k.get('title', 'Loot'), 'sessionId': sid, 'mapLevel': k.get('level', '2'), 'x': k.get('x', 0.42), 'y': k.get('y', 0.61), 'notes': k.get('notes', ''), **({'itemId': k['item']} if 'item' in k else {})})
        code, d, _ = disc(own, S1, title='Rotary Encoder stash', item='rotary-encoder', x=0.25, y=0.75); D1 = d['discovery']['id']
        check(code == 201 and d['discovery']['reviewStatus'] == 'PENDING' and not d['discovery']['isPublic'] and d['discovery']['x'] == 0.25, 'discovery created PENDING, private, with the pin as given')
        code, d, _ = disc(con, S2, title='Contributor find', level='1', x=0.9, y=0.1); D2 = d['discovery']['id']; check(code == 201, 'contributor records a discovery on level 1')
        code, d, _ = disc(con, S1, title='Bad level', level='all'); check(code == 400, 'map level must be one of the map\'s levels')
        code, d, _ = disc(con, S1, title='Off map', x=1.2); check(code == 400, 'pin outside 0..1 is rejected')
        code, d, _ = disc(con, S_other, title='Cross'); check(code == 400, 'a session from another trail is rejected')
        code, d, _ = disc(out, S1, title='Intruder'); check(code == 404, 'uninvited Raider cannot add discoveries')
        _, d, _ = own.post(f'/trails/{T}/discoveries', {'title': 'Third', 'sessionId': S1, 'mapLevel': '2', 'x': 0.5, 'y': 0.5}); D3 = d['discovery']['id']

        # ---------------------------------------------------------------- screenshots
        img = png_bytes(); jpg = jpeg_bytes()
        up = lambda c, did, typ, data, ctype='image/png', t=T: c.upload(f'/trails/{t}/discoveries/{did}/images/{typ}', data, ctype)
        code, d, _ = up(con, D2, 'MAP_POSITION', img); check(code == 201 and d['image']['contentType'] == 'image/png' and 'r2' not in json.dumps(d).lower() and 'key' not in json.dumps(d), 'contributor uploads MAP_POSITION to own discovery; no storage key in the response')
        code, d, _ = up(con, D2, 'LOOT', jpg, 'image/jpeg'); check(code == 201 and d['image']['contentType'] == 'image/jpeg', 'second, separate LOOT screenshot (JPEG) on the same discovery')
        code, d, _ = up(con, D2, 'LOOT', jpg, 'image/jpeg'); check(code == 409, 'duplicate screenshot of the same type is refused (409)')
        code, d, _ = up(con, D1, 'LOOT', img); check(code == 403, 'contributor cannot upload to the owner\'s discovery')
        code, d, _ = up(own, D2, 'MAP_POSITION', img); check(code == 409, 'owner upload to contributor discovery still respects duplicate protection')
        code, d, _ = up(own, D1, 'MAP_POSITION', img); check(code == 201, 'owner uploads to own discovery')
        code, d, _ = up(own, D1, 'BOGUS', img); check(code == 400, 'unknown screenshot type is rejected')
        code, d, _ = up(own, D3, 'LOOT', img, 'image/jpeg'); check(code == 400, 'file contents must match the declared image type')
        code, d, _ = up(own, D3, 'LOOT', b'GIF89a' + b'0' * 20, 'image/gif'); check(code == 415, 'non PNG/JPEG/WebP upload is refused (415)')
        big = img + b'\0' * (20 * 1024 * 1024 + 1 - len(img))
        code, d, _ = up(own, D3, 'LOOT', big); check(code == 413, '20 MiB + 1 byte is refused (413)')
        okbig = img + b'\0' * (20 * 1024 * 1024 - len(img) - 64)
        code, d, _ = up(own, D3, 'LOOT', okbig); check(code == 201 and d['image']['sizeBytes'] <= 20 * 1024 * 1024, 'a screenshot just under 20 MiB is accepted')
        code, d, _ = up(own, D3, 'MAP_POSITION', jpg + b'TRAILER-AFTER-EOI', 'image/jpeg'); check(code == 201, 'a valid JPEG with data after the end-of-image marker is accepted')
        code, d, r = con.req('GET', f'/trails/{T}/discoveries/{D2}/images/MAP_POSITION')
        check(code == 200 and r.headers.get('Content-Type') == 'image/png' and r.content == img and 'no-store' in r.headers.get('Cache-Control', ''), 'member retrieves the private screenshot (exact bytes, no-store)')
        code, _, r = anon.req('GET', f'/trails/{T}/discoveries/{D2}/images/MAP_POSITION'); check(code == 401, 'anonymous cannot retrieve a private screenshot')
        code, _, r = out.req('GET', f'/trails/{T}/discoveries/{D2}/images/MAP_POSITION'); check(code == 404, 'uninvited Raider cannot retrieve a private screenshot')
        code, _, r = own.req('GET', f'/trails/{T2}/discoveries/{D2}/images/MAP_POSITION'); check(code == 404, 'cross-trail image URL (discovery from another trail) is rejected')

        # replacement workflow
        code, d, _ = out.delete(f'/trails/{T}/discoveries/{D2}/images/LOOT'); check(code == 404, 'outsider cannot remove a screenshot')
        code, d, _ = con.delete(f'/trails/{T}/discoveries/{D1}/images/MAP_POSITION'); check(code == 403, 'contributor cannot remove a screenshot from someone else\'s discovery')
        code, d, _ = con.delete(f'/trails/{T}/discoveries/{D2}/images/LOOT'); check(code == 200 and d['removed'], 'creator explicitly removes a wrong screenshot (pending discovery)')
        code, d, _ = up(con, D2, 'LOOT', png_bytes(color=(0, 200, 0))); check(code == 201, '...and uploads the replacement')

        # ---------------------------------------------------------------- progress isolation
        code, d, _ = own.post(f'/trails/{T}/discoveries/{D1}/progress', {'completed': True}); check(code == 200, 'owner marks a discovery completed')
        con.post(f'/trails/{T}/discoveries/{D2}/progress', {'completed': True}); con.post(f'/trails/{T}/discoveries/{D3}/progress', {'completed': True})
        _, d_o, _ = own.get(f'/trails/{T}'); _, d_c, _ = con.get(f'/trails/{T}')
        check(d_o['myCompletedDiscoveryIds'] == [D1] and sorted(d_c['myCompletedDiscoveryIds']) == sorted([D2, D3]), 'each Raider\'s progress is independent')
        con.post(f'/trails/{T}/discoveries/{D3}/progress', {'completed': False}); _, d_c, _ = con.get(f'/trails/{T}')
        check(d_c['myCompletedDiscoveryIds'] == [D2], 'un-marking affects only my own progress')
        code, d, _ = out.post(f'/trails/{T}/discoveries/{D1}/progress', {'completed': True}); check(code == 404, 'uninvited Raider cannot record progress')
        code, d, _ = own.post(f'/trails/{T2}/discoveries/{D1}/progress', {'completed': True}); check(code == 404, 'cross-trail progress (discovery from another trail) is rejected')
        sq = {m['username']: m for m in d_o['squad']}
        check(sq[own.username]['completedCount'] == 1, 'owner sees squad completion counts (activity)')

        # ---------------------------------------------------------------- review + publication
        code, d, _ = con.post(f'/trails/{T}/discoveries/{D2}/review', {'status': 'APPROVED'}); check(code == 404, 'contributor cannot review')
        code, d, _ = con.post(f'/trails/{T}/discoveries/{D2}/publish', {'publish': True}); check(code == 404, 'contributor cannot publish')
        code, d, _ = con.post(f'/trails/{T}/visibility', {'visibility': 'PUBLIC'}); check(code == 404, 'contributor cannot change visibility')
        code, d, _ = own.post(f'/trails/{T}/discoveries/{D2}/publish', {'publish': True}); check(code == 400, 'a PENDING discovery cannot be published')
        code, d, _ = own.post(f'/trails/{T}/discoveries/{D2}/review', {'status': 'APPROVED'}); check(code == 200 and d['discovery']['reviewStatus'] == 'APPROVED' and not d['discovery']['isPublic'], 'owner approves; approval does not publish')
        code, d, _ = con.delete(f'/trails/{T}/discoveries/{D2}/images/LOOT'); check(code == 409, 'approved discovery screenshots are locked (no change under the owner\'s review)')
        code, d, _ = own.post(f'/trails/{T}/discoveries/{D3}/review', {'status': 'REJECTED'}); check(code == 200, 'owner rejects a discovery')
        code, d, _ = own.post(f'/trails/{T}/discoveries/{D3}/publish', {'publish': True}); check(code == 400, 'a REJECTED discovery cannot be published')
        own.post(f'/trails/{T}/discoveries/{D1}/review', {'status': 'APPROVED'})
        code, d, _ = up(own, D1, 'LOOT', jpg, 'image/jpeg'); check(code == 409, 'no new screenshot can be added to an APPROVED discovery (owner must set it back to pending)')
        code, d, _ = own.post(f'/trails/{T}/discoveries/{D2}/publish', {'publish': True}); check(code == 200 and d['isPublic'], 'owner explicitly publishes one approved discovery')
        code, d, _ = anon.get(f'/trails/{T}'); check(code == 404, 'publishing a discovery does not make a PRIVATE trail visible')
        code, d, _ = own.post(f'/trails/{T}/visibility', {'visibility': 'PUBLIC'}); check(code == 200, 'owner makes the trail PUBLIC')
        code, d, _ = anon.get(f'/trails/{T}')
        ids = [x['id'] for x in d['discoveries']]
        check(code == 200 and d['view'] == 'PUBLIC' and ids == [D2], 'public view shows only the APPROVED + published discovery (not D1 approved-unpublished, not pending/rejected)')
        blob = json.dumps(d)
        check(all(k not in blob for k in ('description', 'Squad notes', 'squad', 'myRole', 'createdBy', 'created_by', 'review', 'is_public', 'sessionId', 'r2', 'status')),
              'public response has no description, squad, roles, creator, review/session fields, storage keys or internal status')
        check(all(x not in blob for x in (own.id, con.id, own.username, con.username, own.email, 'TrailBoss#1234', 'Helper#5678')), 'public response exposes no user IDs, usernames, emails or Embark IDs')
        code, d, _ = out.get(f'/trails/{T}'); check(code == 200 and d['view'] == 'PUBLIC', 'a logged-in non-member also gets only the public view')
        code, _, r = anon.req('GET', f'/trails/{T}/discoveries/{D2}/images/LOOT'); check(code == 401, 'even published discoveries keep screenshots private (anonymous)')
        code, _, r = out.req('GET', f'/trails/{T}/discoveries/{D2}/images/LOOT'); check(code == 404, 'even published discoveries keep screenshots private (non-member)')
        code, d, _ = own.post(f'/trails/{T}/discoveries/{D2}/review', {'status': 'APPROVED'}); _, d, _ = anon.get(f'/trails/{T}')
        check(d['discoveries'] == [], 're-reviewing unpublishes (is_public reset) — privacy-protective behaviour preserved')
        own.post(f'/trails/{T}/discoveries/{D2}/publish', {'publish': True})
        own.post(f'/trails/{T}/visibility', {'visibility': 'PRIVATE'}); code, d, _ = anon.get(f'/trails/{T}'); check(code == 404, 'making the trail PRIVATE again hides it')

        # ---------------------------------------------------------------- member identity exposure
        _, d, _ = con.get(f'/trails/{T}'); blob = json.dumps(d)
        check(all(x not in blob for x in (own.id, own.email, 'TrailBoss#1234', 'Helper#5678', 'password')) and 'r2_key' not in blob,
              'member view shows names/usernames only: no internal user IDs, emails, Embark IDs or storage keys')
        dd = {x['id']: x for x in d['discoveries']}
        check(dd[D2]['images'] == {'MAP_POSITION': True, 'LOOT': True} and dd[D2]['creator']['displayName'] == 'Contrib' and dd[D2]['mine'], 'discovery shows which screenshots exist and who recorded it')

        # ---------------------------------------------------------------- multi-session lifecycle + persistence
        code, d, _ = out.post(f'/trails/{T}/sessions/{S1}/end'); check(code == 404, 'outsider cannot end a session')
        code, d, _ = con.post(f'/trails/{T}/sessions/{S1}/end'); check(code == 404, 'contributor cannot end a session someone else started')
        code, d, _ = own.post(f'/trails/{T}/sessions/{S1}/end'); check(code == 200 and d['session']['endedAt'], 'owner ends a session')
        code, d, _ = own.post(f'/trails/{T}/sessions/{S1}/end'); check(code == 409, 'a session can only end once')
        code, d, _ = disc(own, S1, title='Too late'); check(code == 400, 'no new discoveries in an ended session')
        code, d, _ = own.post(f'/trails/{T}/sessions', {'title': 'Night 3 — days later'}); S3 = d['session']['id']
        code, d, _ = disc(own, S3, title='Day three find'); check(code == 201, 'a new session days later accepts discoveries')
        srv.restart()
        code, d, _ = own.get(f'/trails/{T}')
        ses = {s['id']: s for s in d['sessions']}
        check(code == 200 and len(d['discoveries']) == 4 and ses[S1]['endedAt'] and ses[S1]['discoveryCount'] == 2 and d['myCompletedDiscoveryIds'] == [D1],
              'after a server restart: all sessions, discoveries and my progress persist')

        # ---------------------------------------------------------------- removal
        code, d, _ = con.post(f'/trails/{T}/members/remove', {'username': own.username}); check(code == 404, 'contributor cannot remove members')
        code, d, _ = own.post(f'/trails/{T}/members/remove', {'username': con.username}); check(code == 200, 'owner removes a contributor')
        code, d, _ = con.get(f'/trails/{T}'); check(code == 404, 'removed contributor loses access')
        code, d, _ = disc(con, S3, title='after removal'); check(code == 404, 'removed contributor cannot add discoveries')
        _, d, _ = own.get(f'/trails/{T}'); check(any(x['id'] == D2 for x in d['discoveries']), 'their earlier discoveries stay on the trail')
    finally:
        srv.cleanup()
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} Loot Trails API checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
