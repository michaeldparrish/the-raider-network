"""v6.4 Loot Trail amplification plan API tests (migration 0005) on a THROW-AWAY local D1 database.
  python3 tools/plans_test.py
Covers: server-side requirement calculation (quantities never taken from the browser), prerequisites and exclusions,
activation stage per Raider (starting vs already amplified, completing it), installed enhancements per Raider,
had/collected/outstanding without double counting, collection history kept across stage changes, squad privacy
(owner sees everyone, contributors only themselves), outsiders/removed Raiders, public view, plan limits, archive,
and that v6.3 trail data and discoveries are untouched."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devserver import DevServer
from trails_test import Client, register

RESULTS = []


def check(cond, label):
    RESULTS.append((bool(cond), label)); print(('PASS ' if cond else 'FAIL ') + label)


def mat(plan, key): return next((m for m in plan['me']['materials'] if m['itemKey'] == key), None)


def main():
    srv = DevServer(port=8797); srv.migrate(); srv.start(); B = srv.base
    try:
        anon = Client(B)
        own = register(B, 'PlanOwner'); con = register(B, 'PlanHelper'); out = register(B, 'PlanOutsider')
        _, d, _ = own.post('/trails', {'title': 'Burletta build', 'mapId': 'pendola-pass'}); T = d['trail']['id']
        own.post(f'/trails/{T}/invitations', {'username': con.username}); con.post(f'/trails/{T}/invitations/respond', {'decision': 'ACCEPT'})
        _, d, _ = own.post(f'/trails/{T}/sessions', {'title': 'Run', 'notes': ''}); S = d['session']['id']
        _, d, _ = own.post(f'/trails/{T}/discoveries', {'title': 'Old find', 'sessionId': S, 'mapLevel': 'all', 'x': .2, 'y': .3})
        before = srv.sql(f"SELECT id, title, item_id, review_status FROM loot_trail_discoveries WHERE trail_id = '{T}'")

        # ---- validation
        code, d, _ = anon.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': []}); check(code == 401, 'anonymous cannot create a plan')
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': []}, csrf=False); check(code == 403, 'CSRF header required')
        code, d, _ = out.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': []}); check(code == 404, 'outsider cannot create a plan in a private trail')
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'stiletto', 'alreadyAmplified': False, 'enhancements': []}); check(code == 400, 'non-amplifiable weapon is rejected')
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'enhancements': []}); check(code == 400, '"already amplified?" answer is required')
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': ['burst-fire', 'full-auto']})
        check(code == 400 and 'cannot be active together' in d['error']['message'], 'exclusive enhancements are rejected (Burst Fire + Full-Auto)')
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': ['laser-eyes']}); check(code == 400, 'unknown enhancement is rejected')
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': True, 'enhancements': []}); check(code == 400, 'an amplified weapon needs at least one enhancement')
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': ['increased-burst'], 'had': {'tick-pod': 3}})
        check(code == 400, '"had" counts only for materials in the plan')

        # ---- create: Burletta, starting amplification, Increased Burst (pulls in Burst Fire) + Sprint Shooting; client-sent quantities are ignored
        body = {'weaponId': 'burletta', 'alreadyAmplified': False, 'enhancements': ['increased-burst', 'sprint-shooting'],
                'had': {'pressure-regulator': 1, 'queen-reactor': 2}, 'hunting': {'pop-trigger': False}, 'requirements': [{'itemKey': 'queen-reactor', 'requiredQty': 0}]}
        code, d, _ = own.post(f'/trails/{T}/plans', body); P = d['plan']
        check(code == 201 and P['weaponId'] == 'burletta' and P['moduleItemId'] == 'amplification-module-mk-ii' and P['title'].startswith('Burletta amplification'), 'plan created with weapon, module and a descriptive title')
        enh = {e['upgradeId']: e['selection'] for e in P['enhancements']}
        check(enh == {'increased-burst': 'CHOSEN', 'sprint-shooting': 'CHOSEN', 'burst-fire': 'PREREQUISITE'}, 'chosen enhancements and the automatically added prerequisite are stored')
        req = {(r['stage'], r['upgradeId'], r['itemKey']): r['requiredQty'] for r in P['requirements']}
        check(req.get(('ACTIVATION', '', 'amplification-module-mk-ii')) == 1 and req.get(('ENHANCEMENT', 'burst-fire', 'queen-reactor')) == 2
              and req.get(('ENHANCEMENT', 'increased-burst', 'pressure-regulator')) == 2 and req.get(('ENHANCEMENT', 'sprint-shooting', 'fluted-rotor-core')) == 4
              and req.get(('RESEARCH', 'burst-fire', 'pop-trigger')) == 20 and req.get(('RESEARCH', 'increased-burst', 'comet-igniter')) == 10,
              'requirements are calculated by the server from published data (browser quantities ignored)')
        check(any(r['itemKey'].startswith('label:') and r['requiredQty'] is None for r in P['requirements']), 'a research part not in the catalog is kept by label with an unknown quantity')
        check(next(r for r in P['requirements'] if r['itemKey'] == 'fluted-rotor-core')['qtyStatus'] == 'CONFLICT', 'conflicting quantity status is preserved in the plan')
        m = P['me']
        check(m['activation'] == 'REQUIRED' and mat(P, 'amplification-module-mk-ii')['outstanding'] == 1, 'starting amplification: the module is outstanding')
        check(mat(P, 'pressure-regulator')['outstanding'] == 1 and mat(P, 'queen-reactor')['outstanding'] == 0 and mat(P, 'pop-trigger')['hunting'] is False,
              '"had" amounts reduce outstanding; deselected materials are kept but not hunted')
        PID = P['id']

        # ---- progress
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'fluted-rotor-core', 'collectedDelta': 3}]})
        check(code == 200 and mat(d['plan'], 'fluted-rotor-core')['collected'] == 3 and mat(d['plan'], 'fluted-rotor-core')['outstanding'] == 1, 'collecting reduces outstanding')
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'fluted-rotor-core', 'collectedDelta': -9}]})
        check(mat(d['plan'], 'fluted-rotor-core')['collected'] == 0, 'collected count never goes below zero')
        own.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'fluted-rotor-core', 'collected': 4}]})
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'fluted-rotor-core', 'collected': 1000}]}); check(code == 400, 'quantities are bounded (0–999)')
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'tick-pod', 'collected': 2}]}); check(code == 400, 'cannot track a material outside the plan')
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'queen-reactor', 'collected': 1}, {'itemKey': 'queen-reactor', 'collected': 2}]}); check(code == 400, 'a material can appear only once per update')

        # ---- stages
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'install': {'upgradeId': 'burst-fire', 'installed': True}})
        check(code == 409, 'enhancements cannot be marked installed before activation is complete')
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'activation': 'COMPLETED'})
        P = d['plan']; check(code == 200 and P['me']['activation'] == 'COMPLETED' and P['me']['activationCompletedAt'] and mat(P, 'amplification-module-mk-ii')['outstanding'] == 0,
                             'marking activation complete removes the module from outstanding')
        check(mat(P, 'fluted-rotor-core')['collected'] == 4 and mat(P, 'pressure-regulator')['had'] == 1, 'completing a stage keeps the collection history')
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'install': {'upgradeId': 'increased-burst', 'installed': True}}); check(code == 409, 'an enhancement needs its prerequisite installed first')
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'install': {'upgradeId': 'burst-fire', 'installed': True}})
        P = d['plan']; check(code == 200 and mat(P, 'queen-reactor')['stillRequired'] == 0 and mat(P, 'pop-trigger')['stillRequired'] == 0, 'installing Burst Fire stops its install + research materials counting')
        check(mat(P, 'pressure-regulator')['stillRequired'] == 2 and mat(P, 'pressure-regulator')['outstanding'] == 1, 'other enhancements still count, once each (no double counting)')
        own.post(f'/trails/{T}/plans/{PID}/me', {'install': {'upgradeId': 'increased-burst', 'installed': True}})
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'install': {'upgradeId': 'burst-fire', 'installed': False}}); check(code == 409, 'cannot un-install an enhancement another one depends on')
        code, d, _ = own.post(f'/trails/{T}/plans/{PID}/me', {'activation': 'REQUIRED'}); check(code == 409, 'cannot reset activation while enhancements are installed')

        # ---- second Raider joins the same build with an already amplified weapon
        code, d, _ = con.get(f'/trails/{T}/plans'); cp = d['plans'][0]
        check(code == 200 and cp['me'] is None and 'squad' not in cp, 'contributor sees the plan but no one else\'s progress, and has not joined yet')
        code, d, _ = con.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'queen-reactor', 'collected': 1}]}); check(code == 400, 'joining requires saying whether the weapon is already amplified')
        code, d, _ = con.post(f'/trails/{T}/plans/{PID}/me', {'activation': 'NOT_NEEDED'})
        cp = d['plan']; check(code == 200 and mat(cp, 'amplification-module-mk-ii')['outstanding'] == 0 and mat(cp, 'queen-reactor')['outstanding'] == 2,
                              'already amplified: module omitted for that Raider only; their own counts start fresh')
        _, d, _ = own.get(f'/trails/{T}/plans'); op = d['plans'][0]
        check(op['me']['activation'] == 'COMPLETED' and {s['displayName'] for s in op['squad']} == {'PlanOwner', 'PlanHelper'}, 'owner sees every member\'s stage and outstanding totals')
        check(mat(op, 'fluted-rotor-core')['collected'] == 4, 'Raiders\' progress is independent')
        code, d, _ = con.post(f'/trails/{T}/plans/{PID}/status', {'status': 'ARCHIVED'}); check(code == 403, 'a contributor cannot archive someone else\'s plan')

        # ---- privacy
        code, d, _ = out.get(f'/trails/{T}/plans'); check(code == 404, 'outsider cannot list plans')
        own.post(f'/trails/{T}/visibility', {'visibility': 'PUBLIC'})
        code, d, _ = anon.get(f'/trails/{T}'); check(code == 200 and 'plan' not in json.dumps(d).lower(), 'public trail view never includes plans')
        code, d, _ = anon.get(f'/trails/{T}/plans'); check(code == 401, 'plans API requires login even on a public trail')
        code, d, _ = out.get(f'/trails/{T}/plans'); check(code == 404, 'logged-in non-member cannot read plans of a public trail')
        own.post(f'/trails/{T}/members/remove', {'username': con.username})
        code, d, _ = con.post(f'/trails/{T}/plans/{PID}/me', {'progress': [{'itemKey': 'queen-reactor', 'collected': 2}]}); check(code == 404, 'a removed Raider loses access to plans')
        _, d, _ = own.get(f'/trails/{T}/plans'); check({s['displayName'] for s in d['plans'][0]['squad']} == {'PlanOwner'}, 'a removed Raider no longer appears in the owner\'s squad progress')
        own.post(f'/trails/{T}/visibility', {'visibility': 'PRIVATE'})

        # ---- shared material across enhancements: Jupiter Scoped + Ergonomic Bolt both use 3 Fluted Rotor Core
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'jupiter', 'alreadyAmplified': True, 'enhancements': ['scoped', 'ergonomic-bolt']})
        J = d['plan']['id']; check(mat(d['plan'], 'fluted-rotor-core')['stillRequired'] == 6, 'shared material is summed across enhancements (3 + 3)')
        own.post(f'/trails/{T}/plans/{J}/me', {'progress': [{'itemKey': 'fluted-rotor-core', 'collected': 3}]})
        _, d, _ = own.post(f'/trails/{T}/plans/{J}/me', {'install': {'upgradeId': 'scoped', 'installed': True}})
        fr = mat(d['plan'], 'fluted-rotor-core')
        check(fr['stillRequired'] == 3 and fr['spent'] == 3 and fr['outstanding'] == 3 and fr['collected'] == 3,
              'materials spent on an installed enhancement are not counted again for the next one (no double counting)')
        own.post(f'/trails/{T}/plans/{J}/status', {'status': 'ARCHIVED'})

        # ---- already-amplified plan, limit, archive
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'kettle', 'alreadyAmplified': True, 'enhancements': ['anti-shield']})
        k = d['plan']; check(code == 201 and k['me']['activation'] == 'NOT_NEEDED' and mat(k, 'amplification-module-mk-i')['outstanding'] == 0 and mat(k, 'assessor-matrix')['outstanding'] == 3,
                             'plan for an already amplified weapon omits the module from outstanding')
        n = 2
        while n < 10:
            code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'rattler', 'alreadyAmplified': False, 'enhancements': []}); n += 1
        code, d, _ = own.post(f'/trails/{T}/plans', {'weaponId': 'rattler', 'alreadyAmplified': False, 'enhancements': []}); check(code == 409, 'a trail holds at most 10 active plans')
        code, d, _ = own.post(f'/trails/{T}/plans/{k["id"]}/status', {'status': 'ARCHIVED'}); check(code == 200, 'owner can archive a plan')
        _, d, _ = own.get(f'/trails/{T}/plans'); check(all(p['id'] != k['id'] for p in d['plans']) and len(d['plans']) == 9, 'archived plans leave the active list')
        _, d, _ = own.get(f'/trails/{T}'); check(d['view'] == 'MEMBER', 'trail detail still works')
        after = srv.sql(f"SELECT id, title, item_id, review_status FROM loot_trail_discoveries WHERE trail_id = '{T}'")
        check(after == before, 'existing discoveries are untouched by plans')
        srv.restart()
        _, d, _ = own.get(f'/trails/{T}/plans'); p0 = next(p for p in d['plans'] if p['id'] == PID)
        check(p0['me']['activation'] == 'COMPLETED' and len(p0['me']['installed']) == 2 and mat(p0, 'fluted-rotor-core')['collected'] == 4, 'plan state persists across a server restart')
    finally:
        srv.cleanup()
    fails = [l for ok, l in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(fails)}/{len(RESULTS)} plan API checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
