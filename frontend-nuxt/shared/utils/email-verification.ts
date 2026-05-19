type UnknownRecord = Record<string, unknown>

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null
}

function hasNonEmptyString(value: unknown) {
  return typeof value === 'string' && value.trim().length > 0
}

function booleanField(value: unknown, key: string): boolean | null {
  if (!isRecord(value) || !(key in value)) return null
  return typeof value[key] === 'boolean' ? value[key] : null
}

function timestampField(value: unknown, key: string): boolean | null {
  if (!isRecord(value) || !(key in value)) return null
  return hasNonEmptyString(value[key])
}

export function getSupabaseEmailVerificationStatus(user: unknown): boolean | null {
  const confirmedAt = timestampField(user, 'email_confirmed_at')
  if (confirmedAt !== null) return confirmedAt

  const confirmed = timestampField(user, 'confirmed_at')
  if (confirmed !== null) return confirmed

  const emailVerified = booleanField(user, 'email_verified')
  if (emailVerified !== null) return emailVerified

  if (!isRecord(user)) return null

  const userMetadata = user.user_metadata
  const metadataEmailVerified = booleanField(userMetadata, 'email_verified')
  if (metadataEmailVerified !== null) return metadataEmailVerified

  const appMetadata = user.app_metadata
  const appEmailVerified = booleanField(appMetadata, 'email_verified')
  if (appEmailVerified !== null) return appEmailVerified

  return null
}

export function isSupabaseEmailVerified(user: unknown) {
  return getSupabaseEmailVerificationStatus(user) === true
}
