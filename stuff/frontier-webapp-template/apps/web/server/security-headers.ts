/**
 * Example security headers (tweak per platform):
 * - Strict-Transport-Security
 * - Content-Security-Policy
 * - X-Content-Type-Options
 * - X-Frame-Options or modern 'frame-ancestors' in CSP
 * - Referrer-Policy
 * - Permissions-Policy
 */
export function securityHeaders() {
  return {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer-when-downgrade',
    'Permissions-Policy': 'geolocation=(), microphone=()',
    // CSP: tighten per your needs; consider nonces/hashes.
    'Content-Security-Policy': [
      "default-src 'self'",
      "img-src 'self' data: https:",
      "style-src 'self' 'unsafe-inline'",
      "script-src 'self' 'unsafe-inline'",
      "connect-src 'self'",
      "font-src 'self' data: https:",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; '),
  }
}
