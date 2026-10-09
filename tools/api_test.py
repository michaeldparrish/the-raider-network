"""Authentication, authorization, offers and abuse-control tests for the v6 API.

Runs against Cloudflare's local runtime with a throw-away D1 database (see tools/devserver.py), so it never touches
production. Usage:
    python3 tools/api_test.py                 # starts its own isolated server on port 8799
    python3 tools/api_test.py --base http://127.0.0.1:8788/   # use a server you already started (no DB-level checks)
Requires: pip install requests"""
import sys, uuid, time
import requests
from devserver import DevServer

RESULTS = []


def check(cond, label):
    RESULTS.append((bool(cond), label))
    print(('PASS ' if cond else 'FAIL ') + label)


class Client:
    """One browser-like client: its own cookie jar (= its own session)."""
    def __init__(self, base):
        self.base = base.rstrip('/') + '/api'
        self.s = requests.Session()

    def req(self, method, path, body=None, csrf=True, headers=None):
        h = {'Accept': 'application/json'}
        if csrf and method != 'GET':
            h['X-TRN-CSRF'] = '1'
        if body is not None:
            h['Content-Type'] = 'application/json'
        h.update(headers or {})
        r = self.s.request(method, self.base + path, json=body, headers=h, timeout=20)
        try:
            data = r.json()
        except Exception:
            data = None
        return r.status_code, data, r

    get = lambda self, p, **k: self.req('GET', p, **k)
    post = lambda self, p, b=None, **k: self.req('POST', p, {} if b is None else b, **k)
    patch = lambda self, p, b=None, **k: self.req('PATCH', p, {} if b is None else b, **k)
    delete = lambda self, p, **k: self.req('DELETE', p, **k)


def main():
    base = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else None
    srv = None
    if not base:
        srv = DevServer(port=8799); srv.migrate(); srv.start(); base = srv.base
    try:
        run(base, srv)
    finally:
        if srv:
            srv.cleanup()
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} API checks passed')
    sys.exit(1 if fails else 0)


def run(base, srv):
    tag = uuid.uuid4().hex[:6]
    A, B, anon = Client(base), Client(base), Client(base)
    pw = 'Correct-Horse-42'
    ua, ub = f'raider_a_{tag}', f'raider_b_{tag}'

    code, d, _ = anon.get('/health')
    check(code == 200 and d['ok'] and d['migrated'], 'health: D1 connected and migrated')

    # ------------------------------------------------------------- registration + validation
    reg = lambda c, **kw: c.post('/auth/register', {'username': ua, 'display_name': 'Raider A', 'email': f'{ua}@example.com', 'password': pw, 'confirm_password': pw, 'region': 'Europe', 'platform': 'PC', **kw})
    code, d, _ = reg(anon, username='ab')
    check(code == 400 and d['error']['field'] == 'username', 'server rejects a too-short username')
    code, d, _ = reg(anon, password='short', confirm_password='short')
    check(code == 400 and d['error']['field'] == 'password', 'server rejects a short password')
    code, d, _ = reg(anon, password='password123', confirm_password='password123')
    check(code == 400 and d['error']['field'] == 'password', 'server rejects a common password')
    code, d, _ = reg(anon, confirm_password='Different-42!')
    check(code == 400 and d['error']['field'] == 'confirm_password', 'server rejects mismatched confirm password')
    code, d, _ = reg(anon, email='not-an-email')
    check(code == 400 and d['error']['field'] == 'email', 'server rejects an invalid email')
    code, d, _ = reg(anon, username='admin')
    check(code == 400, 'reserved usernames (admin) are rejected')
    code, d, _ = reg(anon, region='Mars')
    check(code == 400 and d['error']['field'] == 'region', 'region must come from the allowed list')
    code, d, _ = reg(anon, avatar_url='https://evil.example/x.png')
    check(code == 400, 'avatar must be one of the site portraits (no external URLs)')
    code, d, _ = anon.req('POST', '/auth/register', {'username': ua}, csrf=False)
    check(code == 403 and d['error']['code'] == 'csrf', 'mutations without the CSRF header are refused')
    code, d, _ = anon.req('POST', '/auth/register', {'username': ua}, headers={'Origin': 'https://evil.example'})
    check(code == 403, 'cross-origin mutations are refused')
    r = anon.s.post(anon.base + '/auth/register', data='username=x', headers={'X-TRN-CSRF': '1', 'Content-Type': 'application/x-www-form-urlencoded'})
    check(r.status_code == 415, 'non-JSON request bodies are refused')

    code, d, r = reg(A)
    check(code == 201 and d['user']['username'] == ua, 'register user A (201)')
    sc = r.headers.get('Set-Cookie', '')
    check('HttpOnly' in sc and 'SameSite=Lax' in sc and 'Path=/' in sc, 'session cookie is HttpOnly + SameSite=Lax')
    check('password' not in str(d).lower() or 'password_hash' not in d['user'], 'register response contains no password data')
    code, d, _ = A.get('/auth/session')
    check(code == 200 and d['user'] and d['user']['username'] == ua, 'session lookup returns user A')

    code, d, _ = reg(anon, email=f'other_{tag}@example.com')
    check(code == 409 and d['error']['field'] == 'username', 'duplicate username rejected (409)')
    code, d, _ = reg(anon, username=f'other_{tag}')
    check(code == 409 and d['error']['field'] == 'email', 'duplicate email rejected (409)')
    code, d, _ = reg(anon, username=ua.upper(), email=f'x{tag}@example.com')
    check(code == 409, 'usernames are case-insensitive (RAIDER_A == raider_a)')
    code, d, _ = reg(anon, username=f'y{tag}', email=f'{ua}@EXAMPLE.com')
    check(code == 409, 'emails are case-insensitive')

    code, d, _ = B.post('/auth/register', {'username': ub, 'display_name': 'Raider B', 'email': f'{ub}@example.com', 'password': pw, 'confirm_password': pw})
    check(code == 201, 'register user B')
    uid_b = d['user']['id']

    if srv:
        rows = srv.sql(f"SELECT password_hash FROM users WHERE username = '{ua}'")
        h = rows[0]['password_hash']
        check(h.startswith('pbkdf2_sha256$100000$') and pw not in h, 'password stored as salted PBKDF2 hash, never plaintext')
        rows = srv.sql(f"SELECT token_hash FROM sessions s JOIN users u ON u.id = s.user_id WHERE u.username = '{ua}'")
        tok = A.s.cookies.get('trn_session')
        check(rows and all(len(x['token_hash']) == 64 and x['token_hash'] != tok for x in rows), 'only SHA-256 hashes of session tokens are stored')

    # ------------------------------------------------------------- login / logout / sessions
    L = Client(base)
    code, d, _ = L.post('/auth/login', {'login': ua, 'password': 'wrong-password-1'})
    check(code == 401 and d['error']['code'] == 'invalid_credentials', 'incorrect password rejected (401)')
    code, d, _ = L.post('/auth/login', {'login': 'nobody_' + tag, 'password': pw})
    check(code == 401 and d['error']['message'] == 'Incorrect username/email or password.', 'unknown account gives the same generic error')
    code, d, _ = L.post('/auth/login', {'login': "' OR 1=1 --", 'password': "' OR '1'='1"})
    check(code == 401, 'SQL-injection style login is just a failed login')
    code, d, _ = L.post('/auth/login', {'login': ua.upper(), 'password': pw})
    check(code == 200 and d['user']['username'] == ua, 'correct login succeeds (username, case-insensitive)')
    code, d, _ = Client(base).post('/auth/login', {'login': f'{ua}@example.com', 'password': pw})
    check(code == 200, 'login with email also works')
    code, d, _ = L.post('/auth/logout')
    check(code == 200, 'logout succeeds')
    code, d, _ = L.get('/auth/session')
    check(code == 200 and d['user'] is None, 'after logout the session is gone')
    code, d, _ = L.post('/trades', {'wanted_item_id': 'rotary-encoder', 'region': 'Europe', 'platform': 'PC'})
    check(code == 401, 'after logout, creating a trade is rejected (401)')

    fake = Client(base); fake.s.cookies.set('trn_session', 'A' * 43)
    code, d, _ = fake.get('/auth/session')
    check(d['user'] is None, 'invalid session token rejected')
    code, d, _ = fake.post('/trades', {'wanted_item_id': 'rotary-encoder', 'region': 'Europe', 'platform': 'PC'})
    check(code == 401, 'invalid session token cannot create trades')

    if srv:
        E = Client(base); E.post('/auth/login', {'login': ua, 'password': pw})
        tok = E.s.cookies.get('trn_session')
        import hashlib
        th = hashlib.sha256(tok.encode()).hexdigest()
        srv.sql(f"UPDATE sessions SET expires_at = '2000-01-01T00:00:00.000Z' WHERE token_hash = '{th}'")
        code, d, _ = E.get('/auth/session')
        check(d['user'] is None, 'expired session rejected')
        code, d, _ = E.post('/trades', {'wanted_item_id': 'rotary-encoder', 'region': 'Europe', 'platform': 'PC'})
        check(code == 401, 'expired session cannot create trades')
        left = srv.sql(f"SELECT COUNT(*) AS n FROM sessions WHERE token_hash = '{th}'")[0]['n']
        check(left == 0, 'expired session row is deleted when presented')

    # ------------------------------------------------------------- trades: create / read / validate
    code, d, _ = A.post('/trades', {'wanted_item_id': 'rotary-encoder', 'wanted_quantity': 2, 'offered_item_name': 'Spare <b>Parts</b>',
                                    'region': 'Europe', 'platform': 'PC', 'desired_time': 'Evenings', 'notes': 'Need it for a project.', 'user_id': uid_b})
    check(code == 201, 'user A creates a trade (201)')
    t = d['trade']; tid = t['id']
    check(t['owner']['username'] == ua, 'trade owner comes from the session, not from a user_id in the body')
    check(t['wanted']['name'] == 'Rotary Encoder' and t['wanted']['quantity'] == 2, 'wanted item name taken from the Loot Intel database')
    check(t['offered']['name'] == 'Spare <b>Parts</b>', 'free text stored as text (escaped by the page when shown)')
    code, d, _ = A.post('/trades', {'wanted_item_id': 'not-a-real-item', 'region': 'Europe', 'platform': 'PC'})
    check(code == 400, 'unknown Loot Intel item id rejected')
    code, d, _ = A.post('/trades', {'wanted_item_name': 'Rotary Encoder', 'wanted_quantity': 500, 'region': 'Europe', 'platform': 'PC'})
    check(code == 400 and d['error']['field'] == 'wanted_quantity', 'quantity limits enforced')
    code, d, _ = A.post('/trades', {'wanted_item_name': 'x' * 300, 'region': 'Europe', 'platform': 'PC'})
    check(code == 400, 'over-long text rejected')
    code, d, _ = anon.get('/trades?status=OPEN')
    check(code == 200 and any(x['id'] == tid for x in d['trades']), 'logged-out visitors can read the Trade Board')
    check('email' not in str(d), 'trade listings never include email addresses')
    code, d, _ = B.get('/trades/' + tid)
    check(code == 200 and d['trade']['is_mine'] is False, 'other users see the trade (not theirs)')
    code, d, _ = anon.get(f'/users/{ua}')
    check(code == 200 and 'email' not in d['user'] and 'raider_tag' not in d['user'], 'public profile hides email and Raider tag')

    # ------------------------------------------------------------- authorization
    code, d, _ = B.patch('/trades/' + tid, {'notes': 'hijacked'})
    check(code == 403, "user B cannot edit A's trade (403)")
    code, d, _ = B.patch('/trades/' + tid, {'status': 'CLOSED'})
    check(code == 403, "user B cannot close A's trade (403)")
    code, d, _ = B.delete('/trades/' + tid)
    check(code == 403, "user B cannot delete A's trade (403)")
    code, d, _ = anon.patch('/trades/' + tid, {'status': 'CLOSED'})
    check(code == 401, 'logged-out visitors cannot modify trades (401)')
    code, d, _ = anon.get('/trades/' + tid)
    check(d['trade']['notes'] == 'Need it for a project.' and d['trade']['status'] == 'OPEN', "A's trade unchanged after B's attempts")

    code, d, _ = A.patch('/trades/' + tid, {'notes': 'Edited by owner', 'wanted_quantity': 3, 'region': 'NA East'})
    check(code == 200 and d['trade']['notes'] == 'Edited by owner' and d['trade']['wanted']['quantity'] == 3 and d['trade']['region'] == 'NA East', 'user A edits own trade')
    code, d, _ = A.patch('/trades/' + tid, {'status': 'CLOSED'})
    check(code == 200 and d['trade']['status'] == 'CLOSED' and d['trade']['closed_at'], 'user A closes own trade')
    code, d, _ = A.patch('/trades/' + tid, {'status': 'OPEN'})
    check(code == 200 and d['trade']['status'] == 'OPEN' and d['trade']['closed_at'] is None, 'user A reopens own trade')
    code, d, _ = A.patch('/trades/' + tid, {'status': 'DELETED'})
    check(code == 400, 'unknown status rejected')

    # ------------------------------------------------------------- offers
    code, d, _ = B.post(f'/trades/{tid}/offers', {'message': 'I have one — evenings EU?', 'offered_item_id': 'snap-hook'})
    check(code == 201 and d['offer']['status'] == 'PENDING', 'user B makes an offer on A\'s trade')
    oid = d['offer']['id']
    code, d, _ = B.post(f'/trades/{tid}/offers', {'message': 'again'})
    check(code == 409, 'only one pending offer per Raider per trade')
    code, d, _ = A.post(f'/trades/{tid}/offers', {'message': 'self offer'})
    check(code == 403, 'owner cannot offer on own trade')
    code, d, _ = A.get(f'/trades/{tid}/offers')
    check(code == 200 and d['is_owner'] and len(d['offers']) == 1, 'owner sees offers on their trade')
    code, d, _ = Client(base).get(f'/trades/{tid}/offers')
    check(code == 401, 'logged-out visitors cannot read offers')
    code, d, _ = B.patch(f'/offers/{oid}', {'action': 'accept'})
    check(code == 403, 'offer sender cannot accept their own offer')
    code, d, _ = A.get('/trades/' + tid)
    check(d['trade']['pending_offers'] == 1, 'pending offer count shown on the trade')
    code, d, _ = A.patch(f'/offers/{oid}', {'action': 'accept'})
    check(code == 200 and d['offer']['status'] == 'ACCEPTED', 'owner accepts the offer')
    hid = (d.get('handoff') or {}).get('id')   # v6.2: accepting opens a private trade handoff
    code, d, _ = B.patch(f'/offers/{oid}', {'action': 'withdraw'})
    check(code == 409, 'an answered offer cannot be withdrawn')
    code, d, _ = B.get('/me/offers')
    check(code == 200 and any(o['id'] == oid for o in d['sent']), 'sender sees the offer in My offers')

    code, d, _ = A.patch('/trades/' + tid, {'status': 'COMPLETED'})
    check(code == 409, 'v6.2: owner cannot mark an accepted trade completed alone')
    A.post(f'/handoffs/{hid}/confirm'); code, d, _ = B.post(f'/handoffs/{hid}/confirm')
    code, d, _ = A.get('/trades/' + tid)
    check(code == 200 and d['trade']['status'] == 'COMPLETED', 'trade completed after both Raiders confirm the exchange')
    code, d, _ = A.patch('/trades/' + tid, {'notes': 'changed after completion'})
    check(code == 409, 'completed trades are locked')
    code, d, _ = B.post(f'/trades/{tid}/offers', {'message': 'late offer'})
    check(code == 409, 'offers on a completed trade are refused')
    code, d, _ = anon.get('/stats')
    check(code == 200 and d['stats']['completed_trades'] >= 1, 'community stats count completed trades')
    code, d, _ = A.get('/auth/session')
    check(d['trades']['completed'] >= 1, 'profile counts include completed trades')

    code, d, _ = A.post('/trades', {'wanted_item_name': 'Patina Blueprint', 'region': 'Europe', 'platform': 'PC'})
    t2 = d['trade']['id']
    check(d['trade']['wanted']['item_id'] is None and d['trade']['wanted']['name'] == 'Patina Blueprint', 'free-text (unlisted) wanted items allowed')
    code, d, _ = B.delete('/trades/' + t2)
    check(code == 403, "user B still cannot delete A's second trade")
    code, d, _ = A.delete('/trades/' + t2)
    check(code == 200, 'user A deletes own trade')
    code, d, _ = anon.get('/trades/' + t2)
    check(code == 404, 'deleted trade is gone (404)')

    # ------------------------------------------------------------- rate limiting
    victim = f'victim_{tag}'
    Client(base).post('/auth/register', {'username': victim, 'display_name': 'Victim', 'email': f'{victim}@example.com', 'password': pw, 'confirm_password': pw})
    X = Client(base); codes = []
    for i in range(10):
        codes.append(X.post('/auth/login', {'login': victim, 'password': f'wrong-guess-{i}'})[0])
    check(codes[:8] == [401] * 8 and codes[8] == 429, f'repeated failed logins are rate limited (got {codes})')
    code, d, r = X.post('/auth/login', {'login': victim, 'password': pw})
    check(code == 429 and r.headers.get('Retry-After'), 'the guessing client is locked out even with the right password (Retry-After sent)')
    code, d, _ = X.post('/auth/login', {'login': f'{victim}@example.com', 'password': 'wrong-again-1'})
    check(code == 429, 'username and email share one per-account counter')
    other_ip = {'CF-Connecting-IP': '198.51.100.23'}   # Cloudflare sets this header from the real client IP in production
    code, d, _ = Client(base).req('POST', '/auth/login', {'login': victim, 'password': pw}, headers=other_ip)
    check(code == 200, "an attacker's failed guesses do not lock the real user out from their own connection")

    import concurrent.futures
    victim2 = f'victim2_{tag}'
    Client(base).post('/auth/register', {'username': victim2, 'display_name': 'Victim Two', 'email': f'{victim2}@example.com', 'password': pw, 'confirm_password': pw})
    par_ip = {'CF-Connecting-IP': '192.0.2.77'}
    def guess(i):
        return Client(base).req('POST', '/auth/login', {'login': victim2, 'password': f'parallel-{i}'}, headers=par_ip)[0]
    with concurrent.futures.ThreadPoolExecutor(14) as ex:
        par = list(ex.map(guess, range(14)))
    check(par.count(401) <= 8 and par.count(429) >= 6, f'parallel guessing cannot exceed the limit ({par.count(401)} checked, {par.count(429)} blocked)')

    bad_cookie = Client(base); bad_cookie.s.headers['Cookie'] = 'analytics=%E0%A4%A'
    code, d, _ = bad_cookie.get('/auth/session')
    check(code == 200 and d['user'] is None, 'a malformed third-party cookie does not break the API')
    code, d, _ = anon.get('/trades?limit=2.5')
    check(code == 200, 'non-integer limit handled')
    for path in ['wrangler.toml', 'functions/_lib/security.js', 'migrations/0001_initial.sql', 'tools/api_test.py', 'docs/BACKEND.md']:
        rr = requests.get(base.rstrip('/') + '/' + path, timeout=10)
        check(rr.status_code == 404, f'repository file /{path} is not served (404)')

    code, d, _ = anon.get('/nope')
    check(code == 404, 'unknown endpoints return JSON 404')
    code, d, _ = anon.req('PUT', '/trades')
    check(code == 405, 'wrong method returns 405')


if __name__ == '__main__':
    main()
