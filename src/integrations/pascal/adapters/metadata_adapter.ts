/**
 * metadata_adapter.ts — Provenance metadata builder
 * Every Pascal node from Vision 5D carries metadata.vision5d
 */

import { ADAPTER_VERSION, PASCAL_PINNED_VERSION } from '../index'

export interface Vision5DProvenance {
  stable_id: string
  project_id: string
  source_revision_id: string
  source_file_sha256: string
  source_file: string
  source_entity_handles: string[]
  source_layers: string[]
  extraction_confidence: number
  validation_status: string
  coordinate_system: string
  units: string
  adapter_version: string
  pascal_core_version: string
  pascal_schema_version: string
  created_at: string
  updated_at: string | null
}

export function buildProvenance(graph: {
  projectId: string
  revisionId: string
  sourceFileSha256: string
  sourceFile: string
  unit?: string
}): Omit<Vision5DProvenance, 'stable_id'> {
  const now = new Date().toISOString()
  return {
    project_id: graph.projectId,
    source_revision_id: graph.revisionId,
    source_file_sha256: graph.sourceFileSha256,
    source_file: graph.sourceFile,
    source_entity_handles: [],
    source_layers: [],
    extraction_confidence: 0.95,
    validation_status: 'structural_match',
    coordinate_system: 'right-handed X(east) Y(up) Z(north)',
    units: graph.unit ?? 'meters',
    adapter_version: ADAPTER_VERSION,
    pascal_core_version: PASCAL_PINNED_VERSION,
    pascal_schema_version: PASCAL_PINNED_VERSION,
    created_at: now,
    updated_at: null,
  }
}
