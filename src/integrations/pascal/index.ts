/**
 * index.ts — Production Pascal Integration Layer
 * V5D-PASCAL-PRODUCTION-ADAPTER-001
 *
 * Pascal integration surface: types/adapters → REST API → MCP → revisions
 * Uses @pascal-app/core v0.9.2, pinned to commit 42ac4be1
 */

// Clients
export { PascalRestClient } from './client/pascal_rest_client'
export { PascalMcpClient } from './client/pascal_mcp_client'
export { PascalClientError, PascalValidationError, PascalTimeoutError, PascalConflictError } from './client/pascal_client_errors'

// Adapters
export { convertVision5DToPascal } from './adapters/vision5d_to_pascal'
export { convertPascalToVision5D } from './adapters/pascal_to_vision5d'
export { adaptWall } from './adapters/wall_adapter'
export { adaptSlab } from './adapters/slab_adapter'
export { adaptOpening } from './adapters/opening_adapter'
export { buildProvenance } from './adapters/metadata_adapter'

// Schemas
export { IntegrationConfig, loadConfig } from './schemas/integration_config'
export { IdentityMap, IdentityMapEntry, LifecycleState } from './schemas/identity_map'
export { CorrectionEvent, CorrectionEventSchema, CorrectionEventType } from './schemas/correction_event'
export { SceneRevision, RevisionManifest } from './schemas/scene_revision'

// Validation
export { validatePascalNode } from './validation/pascal_node_validator'
export { validatePascalGraph } from './validation/pascal_graph_validator'
export { validateHierarchy } from './validation/hierarchy_validator'
export { validateGeometry } from './validation/geometry_validator'
export { validateProvenance } from './validation/provenance_validator'

// Revisions
export { RevisionManager } from './revisions/revision_manager'
export { CorrectionEventNormalizer } from './revisions/correction_event_normalizer'
export { CorrectionEventApplier } from './revisions/correction_event_applier'

// Migration
export { migrateProofPascalScene } from './migration/migrate_proof_pascal_scene'

// Observability
export { PascalMetrics } from './observability/pascal_metrics'
export { pascalLogger } from './observability/pascal_logging'
export { PascalTraceContext } from './observability/pascal_trace_context'

// Version
export const PASCAL_PINNED_COMMIT = '42ac4be1ce5f3fee74806aa093267b6fee77d47d'
export const PASCAL_PINNED_VERSION = '0.9.2'
export const ADAPTER_VERSION = '3.0.0-production'
export const MAX_ROUND_TRIP_DELTA_M = 0.0005
export const COORDINATE_PRECISION = 6
