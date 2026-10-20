/**
 * .env account editor.
 *
 * Reads and writes ACCOUNT_N_* entries while preserving comments, blank
 * lines and any unrelated variables. Secrets (password / TOTP / proxy
 * password) are never returned to callers: they are reported only as a
 * boolean "set" flag, and omitted from updates when left untouched.
 */

import fs from 'node:fs'
import path from 'node:path'

export const ACCOUNT_FIELDS = [
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
  'SAVE_FINGERPRINT_DESKTOP'
]

const SECRET_FIELDS = new Set(['PASSWORD', 'TOTP_SECRET', 'PROXY_PASSWORD'])

const KEY_RE = /^(\s*)(#\s*)?ACCOUNT_([1-9]\d*)_([A-Z0-9_]+)\s*=\s*(.*)$/
const UTF8 = new TextEncoder()

export function readEnvLines(envPath) {
  if (!fs.existsSync(envPath)) return []
  return fs.readFileSync(envPath, 'utf-8').split(/\r?\n/)
}

function parseLine(line) {
  const m = KEY_RE.exec(line)
  if (!m) return null
  return {
    indent: m[1],
    commented: Boolean(m[2]),
    slot: m[3],
    field: m[4],
    value: m[5].trim()
  }
}

function unquote(value) {
  if (value.length >= 2) {
    const first = value[0]
    const last = value[value.length - 1]
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
      return value.slice(1, -1)
    }
  }
  return value
}

/**
 * Return every account slot found in the file.
 * Secrets are replaced by a boolean flag, never their value.
 */
export function listAccounts(envPath) {
  const lines = readEnvLines(envPath)
  const bySlot = new Map()

  lines.forEach((line, index) => {
    const parsed = parseLine(line)
    if (!parsed) return
    // Commented-out template lines do not define an account
    if (parsed.commented && !bySlot.has(parsed.slot)) return
    if (!bySlot.has(parsed.slot)) {
      bySlot.set(parsed.slot, { slot: Number(parsed.slot), index, values: {}, secrets: {} })
    }
    const acc = bySlot.get(parsed.slot)
    if (SECRET_FIELDS.has(parsed.field)) {
      acc.secrets[parsed.field] = parsed.commented ? false : parsed.value.length > 0
    } else {
      acc.values[parsed.field] = parsed.commented ? '' : unquote(parsed.value)
    }
  })

  return [...bySlot.values()]
    .sort((a, b) => a.slot - b.slot)
    .map((acc) => {
      const v = acc.values
      return {
        slot: acc.slot,
        email: v.EMAIL || '',
        recoveryEmail: v.RECOVERY_EMAIL || '',
        geoLocale: v.GEO_LOCALE || '',
        langCode: v.LANG_CODE || '',
        proxyUrl: v.PROXY_URL || '',
        proxyUsername: v.PROXY_USERNAME || '',
        proxyPort: v.PROXY_PORT || '',
        proxyHttp: String(v.PROXY_HTTP || '').toLowerCase() === 'true',
        saveFingerprintMobile: String(v.SAVE_FINGERPRINT_MOBILE || '').toLowerCase() === 'true',
        saveFingerprintDesktop: String(v.SAVE_FINGERPRINT_DESKTOP || '').toLowerCase() === 'true',
        secrets: acc.secrets
      }
    })
}

function nextFreeSlot(lines) {
  // Reuse the lowest slot that has no active (uncommented) email
  const used = new Set()
  for (const line of lines) {
    const parsed = parseLine(line)
    if (parsed && !parsed.commented && parsed.field === 'EMAIL' && parsed.value) {
      used.add(Number(parsed.slot))
    }
  }
  let slot = 1
  while (used.has(slot)) slot++
  return slot
}

function writeAtomic(envPath, lines) {
  const dir = path.dirname(envPath)
  const tmp = path.join(dir, `.env.tmp-${process.pid}`)
  const bak = path.join(dir, '.env.bak')

  if (fs.existsSync(envPath)) {
    fs.copyFileSync(envPath, bak)
  }
  fs.writeFileSync(tmp, lines.join('\n'))
  fs.renameSync(tmp, envPath)
}

function formatValue(value) {
  const str = String(value ?? '')
  if (str === '') return ''
  // Quote values that would otherwise break parsing
  if (/[\s#'"]/.test(str)) return `"${str.replace(/"/g, '\\"')}"`
  return str
}

/**
 * Create or update one account slot.
 * `fields` uses camelCase keys matching listAccounts output.
 */
export function upsertAccount(envPath, slot, fields) {
  const lines = readEnvLines(envPath)
  const target = slot != null && slot !== '' ? String(slot) : String(nextFreeSlot(lines))

  const wanted = new Map()
  const setField = (field, value) => {
    if (value === undefined || value === null) return
    wanted.set(field, formatValue(value))
  }

  setField('EMAIL', fields.email)
  if (fields.password) setField('PASSWORD', fields.password)
  if (fields.totpSecret) setField('TOTP_SECRET', fields.totpSecret)
  setField('RECOVERY_EMAIL', fields.recoveryEmail)
  setField('GEO_LOCALE', fields.geoLocale)
  setField('LANG_CODE', fields.langCode)
  setField('PROXY_URL', fields.proxyUrl)
  setField('PROXY_PORT', fields.proxyPort)
  setField('PROXY_USERNAME', fields.proxyUsername)
  if (fields.proxyPassword) setField('PROXY_PASSWORD', fields.proxyPassword)
  if (fields.proxyHttp !== undefined) setField('PROXY_HTTP', fields.proxyHttp ? 'true' : 'false')
  if (fields.saveFingerprintMobile !== undefined) {
    setField('SAVE_FINGERPRINT_MOBILE', fields.saveFingerprintMobile ? 'true' : 'false')
  }
  if (fields.saveFingerprintDesktop !== undefined) {
    setField('SAVE_FINGERPRINT_DESKTOP', fields.saveFingerprintDesktop ? 'true' : 'false')
  }

  if (!wanted.size) return { slot: Number(target), changed: false }

  const touched = new Set()
  const out = []

  for (const line of lines) {
    const parsed = parseLine(line)
    if (!parsed || parsed.slot !== target) {
      out.push(line)
      continue
    }
    if (!wanted.has(parsed.field)) {
      out.push(line)
      continue
    }
    const indent = parsed.indent || ''
    out.push(`${indent}ACCOUNT_${target}_${parsed.field}=${wanted.get(parsed.field)}`)
    touched.add(parsed.field)
  }

  const missing = [...wanted.keys()].filter((f) => !touched.has(f))
  if (missing.length) {
    // Drop a trailing blank line so the block stays tidy
    while (out.length && out[out.length - 1].trim() === '') out.pop()
    for (const field of missing) {
      out.push(`ACCOUNT_${target}_${field}=${wanted.get(field)}`)
    }
  }

  writeAtomic(envPath, out)
  return { slot: Number(target), changed: true, added: missing }
}

/** Remove every variable belonging to one slot. */
export function deleteAccount(envPath, slot) {
  const target = String(slot)
  const lines = readEnvLines(envPath)
  const out = lines.filter((line) => {
    const parsed = parseLine(line)
    return !(parsed && parsed.slot === target)
  })
  const removed = lines.length - out.length
  if (removed === 0) return { removed: 0 }
  writeAtomic(envPath, out)
  return { removed }
}

export { UTF8 }
