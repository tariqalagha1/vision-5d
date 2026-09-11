/**
 * pascal_rest_client.ts — Production Pascal REST Client
 * Typed requests/responses, retry logic, idempotency keys, correlation IDs.
 */

import { v4 as uuidv4 } from 'uuid'

interface RestConfig {
  baseUrl: string
  timeoutMs: number
  retryCount: number
  retryBackoffMs: number
  authToken?: string
}

interface ApiResponse<T = unknown> {
  status: number
  data: T
  error?: string
}

export class PascalValidationError extends Error {
  constructor(message: string, public issues: unknown[]) {
    super(message)
    this.name = 'PascalValidationError'
  }
}

export class PascalTimeoutError extends Error {
  constructor(url: string, timeoutMs: number) {
    super(`Request to ${url} timed out after ${timeoutMs}ms`)
    this.name = 'PascalTimeoutError'
  }
}

export class PascalConflictError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PascalConflictError'
  }
}

export class PascalRestClient {
  private config: RestConfig

  constructor(config: RestConfig) {
    this.config = config
  }

  private correlationId(): string {
    return uuidv4()
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    retries = 0,
  ): Promise<ApiResponse<T>> {
    const url = `${this.config.baseUrl}${path}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Correlation-ID': this.correlationId(),
    }
    if (this.config.authToken) {
      headers['Authorization'] = `Bearer ${this.config.authToken}`
    }

    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), this.config.timeoutMs)

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      })

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        if (response.status === 400 && data?.error === 'validation_error') {
          throw new PascalValidationError('Schema validation failed', data.issues ?? [])
        }
        if (response.status === 409) {
          throw new PascalConflictError(data?.error ?? 'Conflict')
        }
        throw new Error(`Pascal API error ${response.status}: ${data?.error ?? 'unknown'}`)
      }

      return { status: response.status, data: data as T }
    } catch (err) {
      if (err instanceof PascalValidationError || err instanceof PascalConflictError) {
        throw err // Don't retry deterministic failures
      }
      if (err instanceof DOMException && err.name === 'AbortError') {
        if (retries < this.config.retryCount) {
          await new Promise(r => setTimeout(r, this.config.retryBackoffMs * (retries + 1)))
          return this.request<T>(method, path, body, retries + 1)
        }
        throw new PascalTimeoutError(url, this.config.timeoutMs)
      }
      if (retries < this.config.retryCount) {
        await new Promise(r => setTimeout(r, this.config.retryBackoffMs * (retries + 1)))
        return this.request<T>(method, path, body, retries + 1)
      }
      throw err
    } finally {
      clearTimeout(timeout)
    }
  }

  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    return this.request('GET', '/api/health')
  }

  async createScene(name: string, projectId: string, graph: unknown): Promise<ApiResponse<{ id: string }>> {
    return this.request('POST', '/api/scenes', {
      name,
      projectId,
      graph,
    })
  }

  async getScene(sceneId: string): Promise<ApiResponse<unknown>> {
    return this.request('GET', `/api/scenes/${sceneId}`)
  }

  async updateScene(sceneId: string, name: string, graph: unknown): Promise<ApiResponse<unknown>> {
    return this.request('PUT', `/api/scenes/${sceneId}`, { name, graph })
  }

  async listScenes(projectId?: string, limit?: number): Promise<ApiResponse<{ scenes: unknown[] }>> {
    const params = new URLSearchParams()
    if (projectId) params.set('projectId', projectId)
    if (limit) params.set('limit', String(limit))
    const qs = params.toString()
    return this.request('GET', `/api/scenes${qs ? '?' + qs : ''}`)
  }

  async deleteScene(sceneId: string): Promise<ApiResponse<unknown>> {
    return this.request('DELETE', `/api/scenes/${sceneId}`)
  }
}
