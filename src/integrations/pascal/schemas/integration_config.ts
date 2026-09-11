/**
 * integration_config.ts — Pascal Integration Configuration
 * Validated via Zod. Never hard-code environment-specific URLs.
 */

import { z } from 'zod'

export const IntegrationConfigSchema = z.object({
  pascalRestBaseUrl: z.string().url(),
  pascalMcpEndpoint: z.string().optional(),
  requestTimeoutMs: z.number().int().positive().default(30000),
  retryCount: z.number().int().min(0).max(5).default(3),
  retryBackoffMs: z.number().int().positive().default(1000),
  maxSceneSizeBytes: z.number().int().positive().default(10 * 1024 * 1024),
  expectedPascalCoreVersion: z.string().default('0.9.2'),
  expectedPascalSchemaVersion: z.string().default('0.9.2'),
  maxRoundTripDeltaM: z.number().positive().default(0.0005),
  coordinatePrecision: z.number().int().min(1).max(12).default(6),
  enableRestAuth: z.boolean().default(false),
  enableMcpAuth: z.boolean().default(false),
  restAuthToken: z.string().optional(),
  mcpAuthToken: z.string().optional(),
  featureFlags: z.object({
    enableAutoSync: z.boolean().default(false),
    enableMcpAutomation: z.boolean().default(false),
    enableConflictAutoResolve: z.boolean().default(false),
  }).default({}),
})

export type IntegrationConfig = z.infer<typeof IntegrationConfigSchema>

const DEFAULT_CONFIG: IntegrationConfig = {
  pascalRestBaseUrl: 'http://localhost:3131',
  requestTimeoutMs: 30000,
  retryCount: 3,
  retryBackoffMs: 1000,
  maxSceneSizeBytes: 10 * 1024 * 1024,
  expectedPascalCoreVersion: '0.9.2',
  expectedPascalSchemaVersion: '0.9.2',
  maxRoundTripDeltaM: 0.0005,
  coordinatePrecision: 6,
  enableRestAuth: false,
  enableMcpAuth: false,
  featureFlags: {
    enableAutoSync: false,
    enableMcpAutomation: false,
    enableConflictAutoResolve: false,
  },
}

export function loadConfig(overrides?: Partial<IntegrationConfig>): IntegrationConfig {
  const merged = { ...DEFAULT_CONFIG, ...overrides }
  return IntegrationConfigSchema.parse(merged)
}
