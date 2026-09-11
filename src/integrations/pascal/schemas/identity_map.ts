/**
 * identity_map.ts — Bidirectional Vision 5D ↔ Pascal Identity Map
 *
 * Vision 5D stable IDs are AUTHORITATIVE.
 * Pascal node IDs are generated per Pascal conventions.
 * This map maintains the bidirectional link.
 */

export enum LifecycleState {
  ACTIVE = 'ACTIVE',
  CREATED_IN_PASCAL = 'CREATED_IN_PASCAL',
  DELETED_IN_PASCAL = 'DELETED_IN_PASCAL',
  DELETED_IN_VISION5D = 'DELETED_IN_VISION5D',
  SUPERSEDED = 'SUPERSEDED',
}

export interface IdentityMapEntry {
  projectId: string
  vision5dRevisionId: string
  pascalSceneId: string
  pascalSchemaVersion: string
  vision5dStableId: string
  pascalNodeId: string
  nodeType: string
  sourceDxfHandles: string[]
  createdAt: string
  lastSyncedAt: string
  lifecycleState: LifecycleState
}

export interface IdentityMap {
  projectId: string
  vision5dRevisionId: string
  pascalSceneId: string
  pascalSchemaVersion: string
  entries: Record<string, IdentityMapEntry> // keyed by vision5dStableId
  pascalToVision5d: Record<string, string>   // pascalNodeId → vision5dStableId
  createdAt: string
  updatedAt: string
  version: number
}

export function createIdentityMap(
  projectId: string,
  vision5dRevisionId: string,
  pascalSceneId: string,
  pascalSchemaVersion: string,
): IdentityMap {
  return {
    projectId,
    vision5dRevisionId,
    pascalSceneId,
    pascalSchemaVersion,
    entries: {},
    pascalToVision5d: {},
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    version: 1,
  }
}

export function addIdentityEntry(
  map: IdentityMap,
  entry: IdentityMapEntry,
): IdentityMap {
  const updated = { ...map }
  updated.entries[entry.vision5dStableId] = entry
  updated.pascalToVision5d[entry.pascalNodeId] = entry.vision5dStableId
  updated.updatedAt = new Date().toISOString()
  updated.version += 1
  return updated
}

export function resolvePascalId(map: IdentityMap, vision5dStableId: string): string | null {
  return map.entries[vision5dStableId]?.pascalNodeId ?? null
}

export function resolveVision5DId(map: IdentityMap, pascalNodeId: string): string | null {
  return map.pascalToVision5d[pascalNodeId] ?? null
}

export function updateLifecycleState(
  map: IdentityMap,
  vision5dStableId: string,
  state: LifecycleState,
): IdentityMap {
  const updated = { ...map }
  if (updated.entries[vision5dStableId]) {
    updated.entries[vision5dStableId] = {
      ...updated.entries[vision5dStableId],
      lifecycleState: state,
      lastSyncedAt: new Date().toISOString(),
    }
    updated.updatedAt = new Date().toISOString()
    updated.version += 1
  }
  return updated
}
