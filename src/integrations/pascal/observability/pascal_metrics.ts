/**
 * observability modules — Structured logging, metrics, trace context
 */

export interface PascalMetrics {
  scenesExported: number
  scenesImported: number
  nodeCount: number
  validationFailures: number
  restLatencyMs: number[]
  mcpLatencyMs: number[]
  retries: number
  correctionEventCount: number
  roundTripDeltaM: number
  conflicts: number
  failedSyncs: number
}

export class PascalMetricsCollector {
  private metrics: PascalMetrics = {
    scenesExported: 0,
    scenesImported: 0,
    nodeCount: 0,
    validationFailures: 0,
    restLatencyMs: [],
    mcpLatencyMs: [],
    retries: 0,
    correctionEventCount: 0,
    roundTripDeltaM: 0,
    conflicts: 0,
    failedSyncs: 0,
  }

  recordExport(nodeCount: number) { this.metrics.scenesExported++; this.metrics.nodeCount = nodeCount }
  recordImport() { this.metrics.scenesImported++ }
  recordValidationFailure() { this.metrics.validationFailures++ }
  recordRestLatency(ms: number) { this.metrics.restLatencyMs.push(ms) }
  recordMcpLatency(ms: number) { this.metrics.mcpLatencyMs.push(ms) }
  recordRetry() { this.metrics.retries++ }
  recordCorrectionEvent() { this.metrics.correctionEventCount++ }
  recordRoundTripDelta(deltaM: number) { this.metrics.roundTripDeltaM = deltaM }
  recordConflict() { this.metrics.conflicts++ }
  recordFailedSync() { this.metrics.failedSyncs++ }

  snapshot(): PascalMetrics {
    return { ...this.metrics }
  }

  reset() {
    this.metrics = {
      scenesExported: 0, scenesImported: 0, nodeCount: 0,
      validationFailures: 0, restLatencyMs: [], mcpLatencyMs: [],
      retries: 0, correctionEventCount: 0, roundTripDeltaM: 0,
      conflicts: 0, failedSyncs: 0,
    }
  }
}

export const pascalMetrics = new PascalMetricsCollector()

export const pascalLogger = {
  info: (msg: string, ctx?: Record<string, unknown>) =>
    console.log(JSON.stringify({ level: 'info', message: msg, ...ctx, timestamp: new Date().toISOString() })),
  warn: (msg: string, ctx?: Record<string, unknown>) =>
    console.warn(JSON.stringify({ level: 'warn', message: msg, ...ctx, timestamp: new Date().toISOString() })),
  error: (msg: string, ctx?: Record<string, unknown>) =>
    console.error(JSON.stringify({ level: 'error', message: msg, ...ctx, timestamp: new Date().toISOString() })),
}

export class PascalTraceContext {
  private correlationId: string

  constructor() {
    this.correlationId = require('uuid').v4()
  }

  getCorrelationId(): string { return this.correlationId }

  child(operation: string): PascalTraceContext {
    const child = new PascalTraceContext()
    child.correlationId = `${this.correlationId}.${operation}`
    return child
  }
}
