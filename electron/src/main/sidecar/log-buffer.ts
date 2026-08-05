import { LOG_BUFFER_MAX_LINES } from './constants'

/** Bounded ring buffer of recent sidecar log lines with runtime-secret redaction, used to render a diagnosable (but safe) failure UI. */
export class RedactingLogBuffer {
  private readonly lines: string[] = []

  append(line: string, ...secretsToRedact: readonly string[]): void {
    const redacted = secretsToRedact.reduce<string>(
      (text, secret) => (secret.length > 0 ? text.split(secret).join('***REDACTED***') : text),
      line
    )
    this.lines.push(redacted)
    if (this.lines.length > LOG_BUFFER_MAX_LINES) {
      this.lines.shift()
    }
  }

  getLines(): string[] {
    return [...this.lines]
  }

  clear(): void {
    this.lines.length = 0
  }
}
