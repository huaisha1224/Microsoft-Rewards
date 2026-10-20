# -*- coding: utf-8 -*-
"""config.json access plus a small "simple mode" layer on top of it.

The real config.json has ~90 keys. The GUI only exposes the handful that
actually change day-to-day; everything else is loaded, left untouched, and
written back verbatim.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple

# (config key, Chinese label, tooltip shown in the UI)
WORKER_FIELDS: List[Tuple[str, str, str]] = [
    ('doDesktopSearch', '桌面搜索', '用桌面浏览器做 Bing 搜索，积分主力'),
    ('doMobileSearch', '移动搜索', '模拟手机 Edge 搜索，与桌面搜索分开计分'),
    ('doDailyCheckIn', '每日签到', '每日签到积分，关系到连续签到天数'),
    ('doDailySet', '每日任务集', 'Daily Set：首页每日 3 个小任务'),
    ('doClaimBonusPoints', '领取奖励积分', '自动领取已达成的奖励积分'),
    ('doMorePromotions', '更多推广活动', 'More Promotions 区域的卡片任务'),
    ('doPunchCards', '打卡卡片', 'Punch Cards：跨多天的打卡任务'),
    ('doAppPromotions', '应用推广', '手机端 App 推广任务'),
    ('doReadToEarn', '阅读赚积分', 'Read to Earn：点开文章阅读'),
    ('doActivateSearchPerk', '搜索特权激活', 'Activate Search Perk 卡片'),
    ('doBonusSearches', '额外搜索', '超出官方上限的额外搜索，耗时与风险都更高'),
    ('doVisualSearch', '视觉搜索', '以图搜图，速度很慢'),
]

_SAFE = ['doDesktopSearch', 'doMobileSearch', 'doDailyCheckIn', 'doDailySet', 'doClaimBonusPoints']
_STANDARD = _SAFE + [
    'doMorePromotions',
    'doPunchCards',
    'doAppPromotions',
    'doReadToEarn',
    'doActivateSearchPerk',
]

PRESET_ORDER = ['省心', '标准', '全都要']

PRESET_WORKERS: Dict[str, Dict[str, bool]] = {
    name: {key: (key in keys) for key, _label, _tip in WORKER_FIELDS}
    for name, keys in (
        ('省心', _SAFE),
        ('标准', _STANDARD),
        ('全都要', [key for key, _l, _t in WORKER_FIELDS]),
    )
}

PRESET_HINTS: Dict[str, str] = {
    '省心': '只做搜索 + 签到 + 每日任务集。约 10 分钟/账号，风控风险最低。',
    '标准': '覆盖绝大多数积分来源。约 20-30 分钟/账号，日常推荐这一档。',
    '全都要': '额外叠加「额外搜索」和「视觉搜索」。约 40-60 分钟/账号，耗时越长风险越高。',
}

# --- 搜索节奏（间隔）。"官方默认" 等于上游 Validator.ts:330-332 的默认值 -------
# searchDelay = 每个搜索词之后的等待（BrowserSearch.ts:188）
# readDelay   = 每篇阅读文章之后的等待（ReadToEarn.ts:19）
DELAY_PRESETS: Dict[str, Dict[str, Any]] = {
    '很快': {
        'searchDelay': {'min': '15sec', 'max': '40sec'},
        'readDelay': {'min': '15sec', 'max': '40sec'},
        'searchResultVisitTime': '8sec',
    },
    '官方默认': {
        'searchDelay': {'min': '30sec', 'max': '1min'},
        'readDelay': {'min': '30sec', 'max': '1min'},
        'searchResultVisitTime': '10sec',
    },
    '折中': {
        'searchDelay': {'min': '1min', 'max': '2min'},
        'readDelay': {'min': '1min', 'max': '2min'},
        'searchResultVisitTime': '15sec',
    },
    '保守': {
        'searchDelay': {'min': '2min', 'max': '4min'},
        'readDelay': {'min': '2min', 'max': '4min'},
        'searchResultVisitTime': '20sec',
    },
    '极慢': {
        'searchDelay': {'min': '6min', 'max': '12min'},
        'readDelay': {'min': '6min', 'max': '11min'},
        'searchResultVisitTime': '20sec',
    },
}

DELAY_ORDER = ['很快', '官方默认', '折中', '保守', '极慢']

DELAY_HINTS: Dict[str, str] = {
    '很快': '约 20-30 分钟跑完。间隔最短，被判为机器人的风险相对最高。',
    '官方默认': '约 30-40 分钟跑完。上游默认值，使用者最多，均衡之选。',
    '折中': '约 50-60 分钟跑完。比官方更从容一些。',
    '保守': '约 80-90 分钟跑完。',
    '极慢': '约 3 小时，通常跑不完 —— 这是本 fork 示例配置里的原值。',
}


def _norm_visit(value: Any) -> Optional[str]:
    """searchResultVisitTime accepts a number or a duration string."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return '%gsec' % value
    return str(value)


def _delay_signature(config: Dict[str, Any]) -> Dict[str, Any]:
    ss = config.get('searchSettings', {}) or {}
    return {
        'searchDelay': dict(ss.get('searchDelay', {}) or {}),
        'readDelay': dict(ss.get('readDelay', {}) or {}),
        'searchResultVisitTime': _norm_visit(ss.get('searchResultVisitTime')),
    }


def detect_delay_preset(config: Dict[str, Any]) -> str:
    sig = _delay_signature(config)
    for name in DELAY_ORDER:
        if sig == _delay_signature({'searchSettings': DELAY_PRESETS[name]}):
            return name
    return '自定义'


def apply_delay_preset(config: Dict[str, Any], preset: str) -> Dict[str, Any]:
    """'自定义' is a no-op on purpose - it keeps whatever is already in config."""
    if preset in DELAY_PRESETS:
        ss = config.setdefault('searchSettings', {})
        for key, value in DELAY_PRESETS[preset].items():
            ss[key] = value
    return config


def _bool_map(workers: Dict[str, Any]) -> Dict[str, bool]:
    return {key: bool(workers.get(key, False)) for key, _l, _t in WORKER_FIELDS}


def load(path: str, example_path: str = '') -> Dict[str, Any]:
    """Load config.json, back-filling any missing keys from config.example.json."""
    config: Dict[str, Any] = {}
    if example_path and os.path.exists(example_path):
        config = _read_json(example_path)
    if os.path.exists(path):
        config = _deep_merge(config, _read_json(path))
    config.setdefault('workers', {})
    return config


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def save(path: str, config: Dict[str, Any]) -> None:
    try:
        shutil.copy2(path, path + '.bak')
    except (FileNotFoundError, PermissionError):
        pass
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    os.replace(tmp, path)


def detect_preset(config: Dict[str, Any]) -> str:
    current = _bool_map(config.get('workers', {}))
    for name in PRESET_ORDER:
        if current == PRESET_WORKERS[name]:
            return name
    return '自定义'


def apply_preset(config: Dict[str, Any], preset: str) -> Dict[str, Any]:
    if preset in PRESET_WORKERS:
        config.setdefault('workers', {}).update(PRESET_WORKERS[preset])
    return config


def set_worker(config: Dict[str, Any], key: str, value: bool) -> None:
    config.setdefault('workers', {})[key] = value


# --- simple top-level knobs -------------------------------------------------

def get_simple(config: Dict[str, Any]) -> Dict[str, Any]:
    workers = config.get('workers', {})
    return {
        'headless': bool(config.get('headless', False)),
        'clusters': int(config.get('clusters', 1) or 1),
        'debugLogs': bool(config.get('debugLogs', False)),
        'humanize': bool(config.get('humanize', {}).get('enabled', False)),
        'skipNonPointTasks': bool(config.get('skipNonPointTasks', True)),
        'ensureStreakProtection': bool(config.get('ensureStreakProtection', True)),
        'browserChannel': str(config.get('browserChannel', 'chromium')),
        'workers': {key: bool(workers.get(key, False)) for key, _l, _t in WORKER_FIELDS},
        'delay_preset': detect_delay_preset(config),
    }


def apply_simple(config: Dict[str, Any], simple: Dict[str, Any]) -> Dict[str, Any]:
    config['headless'] = bool(simple.get('headless', False))
    config['clusters'] = max(1, int(simple.get('clusters', 1) or 1))
    config['debugLogs'] = bool(simple.get('debugLogs', False))
    config['skipNonPointTasks'] = bool(simple.get('skipNonPointTasks', True))
    config['ensureStreakProtection'] = bool(simple.get('ensureStreakProtection', True))
    config['browserChannel'] = str(simple.get('browserChannel', 'chromium'))
    config.setdefault('humanize', {})['enabled'] = bool(simple.get('humanize', False))
    config.setdefault('workers', {}).update(simple.get('workers', {}))
    apply_delay_preset(config, simple.get('delay_preset', '自定义'))
    return config
