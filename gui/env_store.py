# -*- coding: utf-8 -*-
"""Read/write the project .env file, preserving comments and layout.

Design rules (mirrors scripts/api/envEditor.js):
  * Only ``ACCOUNT_<N>_<FIELD>`` lines are understood; everything else is kept
    byte-for-byte.
  * Secrets (PASSWORD / TOTP_SECRET / PROXY_PASSWORD) are never returned by the
    list API - only ``has_*`` booleans.
  * Deleting an account comments out its slot instead of removing the lines, so
    the operation stays reversible.
  * Every write creates ``.env.bak`` first.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional

ACCOUNT_KEY_RE = re.compile(
    r'^(?P<lead>\s*(?:#\s*)?)ACCOUNT_(?P<slot>\d+)_(?P<name>[A-Z0-9_]+)\s*=(?P<value>.*)$'
)

FIELD_ORDER = [
    'EMAIL',
    'PASSWORD',
    'TOTP_SECRET',
    'RECOVERY_EMAIL',
    'GEO_LOCALE',
    'LANG_CODE',
    'PROXY_HTTP',
    'PROXY_URL',
    'PROXY_PORT',
    'PROXY_USERNAME',
    'PROXY_PASSWORD',
    'SAVE_FINGERPRINT_MOBILE',
    'SAVE_FINGERPRINT_DESKTOP',
]

SECRET_FIELDS = {'PASSWORD', 'TOTP_SECRET', 'PROXY_PASSWORD'}

# Values copied straight from env.example are templates, not real accounts.
_PLACEHOLDER_RE = re.compile(r'@(example|test)\.(com|org)$', re.IGNORECASE)


@dataclass
class EnvLine:
    raw: str
    slot: Optional[int] = None
    name: Optional[str] = None
    value: str = ''
    commented: bool = False
    lead: str = ''


def _split_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return value


def load(path: str) -> List[EnvLine]:
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    if text.startswith('\ufeff'):
        text = text[1:]

    lines: List[EnvLine] = []
    for raw in text.splitlines():
        match = ACCOUNT_KEY_RE.match(raw)
        if not match:
            lines.append(EnvLine(raw=raw))
            continue
        lead = match.group('lead')
        lines.append(
            EnvLine(
                raw=raw,
                slot=int(match.group('slot')),
                name=match.group('name'),
                value=_split_value(match.group('value')),
                commented='#' in lead,
                lead=lead,
            )
        )
    return lines


def write(path: str, lines: List[EnvLine]) -> None:
    text = '\n'.join(item.raw for item in lines)
    if not text.endswith('\n'):
        text += '\n'
    try:
        shutil.copy2(path, path + '.bak')
    except (FileNotFoundError, PermissionError):
        pass
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, path)


def all_slots(lines: List[EnvLine]) -> List[int]:
    found = {item.slot for item in lines if item.slot is not None}
    return sorted(found)


def _find(lines: List[EnvLine], slot: int, name: str, prefer_uncommented: bool = True) -> Optional[int]:
    commented_hit: Optional[int] = None
    for index, item in enumerate(lines):
        if item.slot != slot or item.name != name:
            continue
        if not item.commented:
            if prefer_uncommented:
                return index
            commented_hit = commented_hit if commented_hit is not None else index
        elif commented_hit is None:
            commented_hit = index
    return commented_hit


def get_value(lines: List[EnvLine], slot: int, name: str) -> Optional[str]:
    """Effective value, or None when unset / commented out."""
    index = _find(lines, slot, name, prefer_uncommented=True)
    if index is None:
        return None
    item = lines[index]
    if item.commented or not item.value:
        return None
    return item.value


def raw_value(lines: List[EnvLine], slot: int, name: str) -> Optional[str]:
    """Value ignoring the commented flag - used to build child-process env."""
    index = _find(lines, slot, name, prefer_uncommented=True)
    if index is None:
        return None
    return lines[index].value or None


def _render(slot: int, name: str, value: str, commented: bool, lead: str) -> str:
    indent = re.match(r'^\s*', lead).group(0)
    prefix = indent + '#' if commented else ''
    return f'{prefix}ACCOUNT_{slot}_{name}={value}'


def list_accounts(path: str) -> List[Dict]:
    """Safe account summaries - secrets are reduced to ``has_*`` flags."""
    lines = load(path)
    accounts: List[Dict] = []
    for slot in all_slots(lines):
        email = get_value(lines, slot, 'EMAIL')
        if not email or _PLACEHOLDER_RE.search(email):
            continue
        proxy_url = get_value(lines, slot, 'PROXY_URL')
        accounts.append(
            {
                'slot': slot,
                'email': email,
                'geo_locale': get_value(lines, slot, 'GEO_LOCALE') or 'auto',
                'lang_code': get_value(lines, slot, 'LANG_CODE') or 'en',
                'has_password': get_value(lines, slot, 'PASSWORD') is not None,
                'has_totp': get_value(lines, slot, 'TOTP_SECRET') is not None,
                'has_recovery_email': get_value(lines, slot, 'RECOVERY_EMAIL') is not None,
                'proxy_url': proxy_url or '',
                'proxy_port': get_value(lines, slot, 'PROXY_PORT') or '',
                'has_proxy_credentials': get_value(lines, slot, 'PROXY_USERNAME') is not None,
                'save_fingerprint_mobile': (get_value(lines, slot, 'SAVE_FINGERPRINT_MOBILE') or 'false').lower() == 'true',
                'save_fingerprint_desktop': (get_value(lines, slot, 'SAVE_FINGERPRINT_DESKTOP') or 'false').lower() == 'true',
            }
        )
    return accounts


def next_free_slot(path: str) -> int:
    """Lowest positive slot that is not currently in use."""
    used = {item['slot'] for item in list_accounts(path)}
    slot = 1
    while slot in used:
        slot += 1
    return slot


def upsert_account(path: str, slot: int, data: Dict[str, Optional[str]]) -> None:
    """Create or update one account slot.

    ``data`` keys are bare field names (``EMAIL``, ``PASSWORD``, ...).
    ``None`` means "leave the current value alone"; ``''`` means "unset".
    """
    lines = load(path)

    for name in FIELD_ORDER:
        if name not in data:
            continue
        value = data[name]
        if value is None:
            continue

        index = _find(lines, slot, name)
        if value == '':
            if index is not None:
                lines[index].raw = _render(slot, name, lines[index].value, True, lines[index].lead)
                lines[index].commented = True
            continue

        if index is not None:
            lines[index].raw = _render(slot, name, value, False, lines[index].lead)
            lines[index].value = value
            lines[index].commented = False
        else:
            insert_at = len(lines)
            for i, item in enumerate(lines):
                if item.slot == slot:
                    insert_at = i + 1
            lines.insert(
                insert_at,
                EnvLine(raw=_render(slot, name, value, False, ''), slot=slot, name=name, value=value, lead=''),
            )

    write(path, lines)


def delete_account(path: str, slot: int) -> bool:
    """Comment out every line of one slot. Returns True when something changed."""
    lines = load(path)
    changed = False
    for item in lines:
        if item.slot != slot or item.commented:
            continue
        item.raw = _render(slot, item.name, item.value, True, item.lead)
        item.commented = True
        changed = True
    if changed:
        write(path, lines)
    return changed


def child_env_for_slot(path: str, slot: Optional[int]) -> Dict[str, str]:
    """Environment overrides that make the bot run exactly one account.

    ``src/util/Load.ts`` only applies .env values when the key is missing from
    ``process.env``, and treats an empty string as unset. So we blank every
    other slot's EMAIL and remap the chosen slot onto ACCOUNT_1_*.
    """
    lines = load(path)
    env: Dict[str, str] = {}
    for existing in all_slots(lines):
        env[f'ACCOUNT_{existing}_EMAIL'] = ''
    if slot is None:
        return env
    for name in FIELD_ORDER:
        env[f'ACCOUNT_1_{name}'] = raw_value(lines, slot, name) or ''
    return env
