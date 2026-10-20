# -*- coding: utf-8 -*-
"""update_checker 单元验证（不启动 GUI）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gui'))
import update_checker as uc  # noqa: E402

cases = [
    ('2026.10.18.1', '2026.10.18.1', False),
    ('2026.10.18.1', '2026.10.18', True),
    ('2026.10.18', '2026.10.18.1', False),
    ('2026.10.19', '2026.10.18.1', True),
    ('2026.9.30', '2026.10.1', False),
    ('2026.10.9', '2026.10.10', False),
    ('2027.1', '2026.10.18.1', True),
    ('', '2026.10.18.1', False),
    ('2026.10.18.1', '', True),
]
fails = []
for server, local, expect in cases:
    got = uc.is_newer(server, local)
    flag = 'OK ' if got == expect else 'FAIL'
    if got != expect:
        fails.append((server, local, expect, got))
    print(f'{flag} is_newer({server!r}, {local!r}) = {got} (expect {expect})')

print('parse_version 2026.10.18.1 ->', uc.parse_version('2026.10.18.1'))
print('parse_version 1.0.0-beta ->', uc.parse_version('1.0.0-beta'))

data, err = uc.fetch_latest('MicrosoftRewards')
print('--- live api ---')
print('data :', data)
print('error:', err)
if data:
    v = str(data.get('Version'))
    print('newer than 2026.10.18.1 ?', uc.is_newer(v, '2026.10.18.1'))
    print('DownloadUrl:', data.get('DownloadUrl'))

print('--- bad tool (404) ---')
print(uc.fetch_latest('NoSuchTool_xyz'))
print('--- bad host ---')
print(uc.fetch_latest('MicrosoftRewards', timeout=3, base='https://api.hs2049.invalid/tools/'))

print('RESULT:', 'ALL_OK' if not fails else f'{len(fails)} FAILS')
