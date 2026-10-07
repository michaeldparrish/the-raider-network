"""Start/stop an isolated local copy of the full stack for tests: Cloudflare's own runtime (workerd, via
`wrangler pages dev`) serving the static site + Pages Functions, with a throw-away local D1 database.

Nothing here touches your real Cloudflare account or the production D1 database: `--local` / `--persist-to`
keep everything in a temporary folder on this machine.

Requires Node.js 18+ and wrangler (`npx wrangler` downloads it on first use, or set WRANGLER=/path/to/wrangler)."""
import os, shutil, signal, subprocess, tempfile, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wrangler_cmd():
    w = os.environ.get('WRANGLER')
    if w:
        return [w]
    if shutil.which('wrangler'):
        return ['wrangler']
    return ['npx', '--yes', 'wrangler@4']


class DevServer:
    def __init__(self, port=8799, persist_dir=None):
        self.port = port
        self.base = f'http://127.0.0.1:{port}/'
        self.persist = persist_dir or tempfile.mkdtemp(prefix='trn-d1-')
        self.proc = None

    def migrate(self):
        out = subprocess.run(wrangler_cmd() + ['d1', 'migrations', 'apply', 'raider-network-db', '--local', '--persist-to', self.persist],
                             cwd=ROOT, capture_output=True, text=True, timeout=180, env={**os.environ, 'CI': '1'})
        if out.returncode != 0:
            raise RuntimeError('migration failed:\n' + out.stdout + out.stderr)

    def sql(self, command):
        """Run SQL against the local test database (used to simulate expired sessions and to inspect stored rows)."""
        out = subprocess.run(wrangler_cmd() + ['d1', 'execute', 'raider-network-db', '--local', '--persist-to', self.persist, '--json', '--command', command],
                             cwd=ROOT, capture_output=True, text=True, timeout=120, env={**os.environ, 'CI': '1'})
        if out.returncode != 0:
            raise RuntimeError('d1 execute failed:\n' + out.stdout + out.stderr)
        import json
        txt = out.stdout[out.stdout.index('['):]
        return json.loads(txt)[0]['results']

    def start(self):
        self.log = open(os.path.join(self.persist, 'wrangler.log'), 'a')
        self.proc = subprocess.Popen(wrangler_cmd() + ['pages', 'dev', '.', '--port', str(self.port), '--ip', '127.0.0.1', '--persist-to', self.persist],
                                     cwd=ROOT, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True, env={**os.environ, 'CI': '1'})
        for _ in range(120):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(self.base + 'api/health', timeout=2) as r:
                    if r.status == 200:
                        return self
            except Exception:
                pass
        raise RuntimeError('wrangler pages dev did not start; see ' + self.log.name)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGTERM)
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)
        self.proc = None

    def restart(self):
        self.stop(); time.sleep(1); return self.start()

    def cleanup(self):
        self.stop(); shutil.rmtree(self.persist, ignore_errors=True)
