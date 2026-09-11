/**
 * pascal_client_errors.ts — Pascal Client Error Types
 */

export class PascalClientError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number,
    public details?: unknown,
  ) {
    super(message)
    this.name = 'PascalClientError'
  }
}

export { PascalValidationError, PascalTimeoutError, PascalConflictError } from './pascal_rest_client'
