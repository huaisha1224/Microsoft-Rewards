# -*- coding: utf-8 -*-
"""Self-test for the GUI layer. Runs against throwaway copies - never touches .env.

    python gui/selftest.py

Exit code 0 = all checks passed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import config_store as cs  # noqa: E402
import env_store  # noqa: E402
from runner import BotRunner, classify, detect_node, strip_ansi  # noqa: E402

_failed: list = []


def check(label: str, cond: bool, extra='') -> None:
    print(('  PASS  ' if cond else '  FAIL  ') + label + (('   ' + str(extra)) if extra else ''))
    if not cond:
        _failed.append(label)


def test_env_store(tmp: str) -> str:
    print('\n[env_store] .env account read/write')
    env_path = os.path.join(tmp, '.env')
    shutil.copy2(os.path.join(ROOT, '.env'), env_path)
    original_lines = len(open(env_path, encoding='utf-8').read().splitlines())

    base_accounts = env_store.list_accounts(env_path)
    accs = base_accounts
    check('baseline accounts parsed', len(accs) >= 1, [a['email'] for a in accs])

    slot = env_store.next_free_slot(env_path)
    check('next_free_slot skips used slots', slot not in {a['slot'] for a in accs}, slot)

    env_store.upsert_account(env_path, slot, {
        'EMAIL': 'second@outlook.com',
        'PASSWORD': 'sekret-pass',
        'TOTP_SECRET': 'JBSWY3DPEHPK3PXP',
        'RECOVERY_EMAIL': 'backup@outlook.com',
        'GEO_LOCALE': 'US',
        'LANG_CODE': 'en-US',
        'PROXY_URL': 'http://127.0.0.1',
        'PROXY_PORT': '8080',
        'PROXY_USERNAME': 'puser',
        'PROXY_PASSWORD': 'ppass',
        'SAVE_FINGERPRINT_MOBILE': 'false',
        'SAVE_FINGERPRINT_DESKTOP': 'true',
    })
    accs = env_store.list_accounts(env_path)
    second = next((a for a in accs if a['slot'] == slot), {})
    check('account added', len(accs) == len(base_accounts) + 1, [a['email'] for a in accs])
    check('geo / lang stored', second.get('geo_locale') == 'US' and second.get('lang_code') == 'en-US')
    check('secret flags set', bool(second.get('has_password') and second.get('has_totp') and second.get('has_recovery_email')))
    check('proxy stored', second.get('proxy_url') == 'http://127.0.0.1' and second.get('proxy_port') == '8080')
    check('secret values never leak to summary',
          'sekret-pass' not in json.dumps(accs) and 'JBSWY3DPEHPK3PXP' not in json.dumps(accs))
    check('password really written to file',
          'ACCOUNT_%d_PASSWORD=sekret-pass' % slot in open(env_path, encoding='utf-8').read())

    env_store.upsert_account(env_path, slot,
                             {'EMAIL': 'renamed@outlook.com', 'PASSWORD': None, 'TOTP_SECRET': None})
    second = next((a for a in env_store.list_accounts(env_path) if a['slot'] == slot), {})
    check('email updated', second.get('email') == 'renamed@outlook.com')
    check('None keeps existing secret', second.get('has_password') is True and second.get('has_totp') is True)

    env_store.upsert_account(env_path, slot, {'PROXY_URL': ''})
    second = next((a for a in env_store.list_accounts(env_path) if a['slot'] == slot), {})
    check("empty string unsets a field", second.get('proxy_url') == '')
    check('unset comments out instead of deleting',
          '#ACCOUNT_%d_PROXY_URL=' % slot in open(env_path, encoding='utf-8').read())

    check('delete reports change', env_store.delete_account(env_path, slot) is True)
    check('account deleted', len(env_store.list_accounts(env_path)) == len(base_accounts))
    check('deleted slot becomes reusable', env_store.next_free_slot(env_path) == slot)
    env_store.upsert_account(env_path, slot, {'EMAIL': 'readd@outlook.com', 'GEO_LOCALE': 'CN'})
    check('re-add into the same slot',
          any(a['email'] == 'readd@outlook.com' for a in env_store.list_accounts(env_path)))
    check('comments and layout preserved',
          open(env_path, encoding='utf-8').read().count('#') > 5
          and len(open(env_path, encoding='utf-8').read().splitlines()) >= original_lines)
    check('.env.bak written', os.path.exists(env_path + '.bak'))

    child = env_store.child_env_for_slot(env_path, slot)
    slot_keys = {k: v for k, v in child.items() if re.fullmatch(r'ACCOUNT_\d+_EMAIL', k)}
    check('child env remaps target slot to ACCOUNT_1',
          child.get('ACCOUNT_1_EMAIL') == 'readd@outlook.com', child.get('ACCOUNT_1_EMAIL'))
    check('child env blanks every other slot',
          len([v for v in slot_keys.values() if v]) == 1, slot_keys)
    return env_path


def test_config_store(tmp: str) -> None:
    print('\n[config_store] config.json read/write')
    cfg = cs.load(os.path.join(ROOT, 'config.json'), os.path.join(ROOT, 'config.example.json'))
    check('workers present', 'workers' in cfg and len(cfg['workers']) >= 12)
    check('preset detection', cs.detect_preset(cfg) in cs.PRESET_ORDER + ['自定义'],
          cs.detect_preset(cfg))

    cs.apply_preset(cfg, '省心')
    check("preset '省心' applied", cs.detect_preset(cfg) == '省心')

    check('delay preset detected from real config', cs.detect_delay_preset(cfg) in cs.DELAY_ORDER + ['自定义'],
          cs.detect_delay_preset(cfg))
    cs.apply_delay_preset(cfg, '官方默认')
    check("delay preset '官方默认' applied", cs.detect_delay_preset(cfg) == '官方默认')
    check('delay preset writes upstream defaults',
          cfg['searchSettings']['searchDelay'] == {'min': '30sec', 'max': '1min'}
          and cfg['searchSettings']['readDelay'] == {'min': '30sec', 'max': '1min'}
          and cfg['searchSettings']['searchResultVisitTime'] == '10sec')
    cs.apply_delay_preset(cfg, '自定义')
    check("'自定义' keeps the existing delays (no-op)", cs.detect_delay_preset(cfg) == '官方默认')
    cs.apply_delay_preset(cfg, '极慢')
    check("delay preset '极慢' applied", cs.detect_delay_preset(cfg) == '极慢')
    cs.apply_delay_preset(cfg, '官方默认')

    simple = cs.get_simple(cfg)
    simple['headless'] = True
    simple['delay_preset'] = '官方默认'
    simple['clusters'] = 3
    simple['workers']['doVisualSearch'] = True
    cs.apply_simple(cfg, simple)

    path = os.path.join(tmp, 'config.json')
    cs.save(path, cfg)
    cs.save(path, cfg)
    back = cs.load(path, os.path.join(ROOT, 'config.example.json'))
    check('headless round-trip', back['headless'] is True)
    check('clusters round-trip', back['clusters'] == 3)
    check('worker flag round-trip', back['workers']['doVisualSearch'] is True)
    check('delay preset survives save/load', cs.detect_delay_preset(back) == '官方默认',
          back['searchSettings']['searchDelay'])
    check('untouched sections preserved', 'webhook' in back and 'serverchan' in back['webhook'])
    check('config.json.bak written', os.path.exists(path + '.bak'))


def test_runner() -> None:
    print('\n[runner] subprocess + log parsing')
    lines, exits = [], []
    runner = BotRunner()
    runner.on_line = lines.append
    runner.on_exit = exits.append

    node = detect_node()
    check('node detected', bool(node) and os.path.isfile(node), node)
    check('dist/index.js built', os.path.isfile(os.path.join(ROOT, 'dist', 'index.js')))

    runner.start(node, ROOT, env_overrides={'ACCOUNT_1_EMAIL': 'x@y.com'}, entry='--version')
    deadline = time.time() + 30
    while time.time() < deadline and not exits:
        time.sleep(0.1)
    check('stdout captured', bool(lines), lines)
    check('exit code propagated', exits == [0], exits)

    check('ansi stripped', strip_ansi('\x1b[32mhello\x1b[0m world') == 'hello world')
    check('level classify', (classify('[ERROR] x'), classify('[WARN] x'), classify('collected 1')) == ('error', 'warn', 'ok'))


def test_run_scope() -> None:
    """Builds the real window for a moment - pass --with-ui to include it."""
    print('\n[app] run-scope account picker')
    import app as appmod

    win = appmod.App()
    try:
        for _ in range(4):
            win.update()
            win.update_idletasks()

        check('delay picker reflects config',
              win.delay_var.get() in appmod.cs.DELAY_ORDER + ['自定义'], win.delay_var.get())
        check('delay hint is filled in', bool(win.delay_hint.cget('text')), win.delay_hint.cget('text'))

        opts = list(win.cmb_scope.cget('values'))
        check("picker always offers 'all accounts'", appmod.SCOPE_ALL in opts, opts)

        if not win.accounts:
            check('no accounts -> hint stays sane', bool(win.lbl_scope.cget('text')))
        else:
            acc = win.accounts[0]
            label = '#%d  %s' % (acc['slot'], acc['email'])
            check('picker lists every account', label in opts, opts)

            win.cmb_scope.set(label)
            win.update()
            check('picking an account resolves to its slot',
                  win._selected_scope_slot() == acc['slot'], win._selected_scope_slot())
            check('hint shows the chosen email',
                  acc['email'] in win.lbl_scope.cget('text'), win.lbl_scope.cget('text'))

            win.cmb_scope.set(appmod.SCOPE_ALL)
            win.update()
            check("'all accounts' resolves to None", win._selected_scope_slot() is None)

            win._select(acc['slot'])
            win.update()
            check('account-tab click syncs into the run tab',
                  win._selected_scope_slot() == acc['slot'])

            stale = '#999  ghost@example.com'
            win.cmb_scope.configure(values=list(opts) + [stale])
            win.cmb_scope.set(stale)
            win.update()
            check('stale choice is reported, not crashed on',
                  '不存在' in win.lbl_scope.cget('text'), win.lbl_scope.cget('text'))
    finally:
        win.destroy()


def main() -> int:
    with_ui = '--with-ui' in sys.argv
    print('Microsoft Rewards GUI self-test')
    print('project root: %s' % ROOT)
    if not with_ui:
        print('(window tests skipped - pass --with-ui to include them)')
    tmp = tempfile.mkdtemp(prefix='mrs_gui_selftest_')
    try:
        test_env_store(tmp)
        test_config_store(tmp)
        test_runner()
        if with_ui:
            test_run_scope()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%s' % ('=' * 52))
    if _failed:
        print('FAILED (%d): %s' % (len(_failed), ', '.join(_failed)))
        return 1
    print('ALL CHECKS PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
