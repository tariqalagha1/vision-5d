/**
 * vision5d_to_pascal.ts — Production Forward Adapter
 *
 * Converts Vision 5D architectural graph into Pascal-native SceneGraph.
 * Uses @pascal-app/core v0.9.2 types. Output: Record<string, AnyNode> + rootNodeIds.
 */

import type { SceneGraph } from '@pascal-app/core/clone-scene-graph'
import { generateId } from '@pascal-app/core/schema'
import { adaptWall } from './wall_adapter'
import { adaptSlab } from './slab_adapter'
import { adaptDoor, adaptWindow } from './opening_adapter'
import { buildProvenance } from './metadata_adapter'
import { IdentityMap, IdentityMapEntry, LifecycleState, createIdentityMap, addIdentityEntry } from '../schemas/identity_map'

export interface Vision5DGraph {
  projectId: string
  jobId: string
  sourceFileSha256: string
  sourceFile: string
  revisionId: string
  unit: string
  nodes: Vision5DNode[]
}

export interface Vision5DNode {
  id: string
  type: string
  name?: string
  parentId?: string | null
  position?: [number, number, number]
  metadata?: Record<string, unknown>
  // Wall-specific
  start?: [number, number]
  end?: [number, number]
  thickness?: number
  height?: number
  // Opening-specific
  wallId?: string
  width?: number
  // Slab-specific
  polygon?: [number, number][]
}

export interface ConvertResult {
  sceneGraph: SceneGraph
  identityMap: IdentityMap
  nodeCounts: Record<string, number>
}

export function convertVision5DToPascal(
  graph: Vision5DGraph,
  pascalSceneId?: string,
): ConvertResult {
  const nodes: Record<string, any> = {}
  const siteId = generateId('site')
  const buildingId = generateId('building')
  const levelId = generateId('level')
  const rootNodeIds = [siteId]

  const provenance = buildProvenance(graph)
  const identityMap = createIdentityMap(
    graph.projectId,
    graph.revisionId,
    pascalSceneId ?? 'pending',
    '0.9.2',
  )

  // Site
  nodes[siteId] = {
    object: 'node', id: siteId, type: 'site',
    name: 'Vision 5D Import Site',
    parentId: null,
    position: [0, 0, 0], rotation: [0, 0, 0],
    visible: true,
    children: [buildingId],
    polygon: { type: 'polygon', points: [[-50, -50], [100, -50], [100, 100], [-50, 100]] },
    metadata: { vision5d: { ...provenance, stable_id: 'site_v5d_001' } },
  }
  addIdentityEntry(identityMap, makeEntry(graph, 'site_v5d_001', siteId, 'site', []))

  // Building
  nodes[buildingId] = {
    object: 'node', id: buildingId, type: 'building',
    name: 'Vision 5D Import',
    parentId: siteId,
    position: [0, 0, 0], rotation: [0, 0, 0],
    visible: true,
    children: [levelId],
    metadata: { vision5d: { ...provenance, stable_id: 'building_v5d_001' } },
  }
  addIdentityEntry(identityMap, makeEntry(graph, 'building_v5d_001', buildingId, 'building', []))

  // Level
  nodes[levelId] = {
    object: 'node', id: levelId, type: 'level',
    name: 'Ground Floor',
    parentId: buildingId,
    position: [0, 0, 0], rotation: [0, 0, 0],
    visible: true,
    level: 0,
    children: [],
    metadata: { vision5d: { ...provenance, stable_id: 'level_v5d_001' } },
  }
  addIdentityEntry(identityMap, makeEntry(graph, 'level_v5d_001', levelId, 'level', []))

  // Process each V5D node
  const nodeCounts: Record<string, number> = {}
  for (const vn of graph.nodes) {
    nodeCounts[vn.type] = (nodeCounts[vn.type] ?? 0) + 1

    if (vn.type === 'wall') {
      const pascalWall = adaptWall(vn, levelId, generateId('wall'))
      nodes[pascalWall.id] = pascalWall
      nodes[levelId].children.push(pascalWall.id)
      addIdentityEntry(identityMap, makeEntry(graph, vn.id, pascalWall.id, 'wall',
        (vn.metadata?.vision5d as any)?.dxf_entity_handles ?? []))
    } else if (vn.type === 'door') {
      const hostPascalId = identityMap.pascalToVision5d
        ? Object.entries(identityMap.pascalToVision5d)
            .find(([_, vid]) => vid === vn.wallId)?.[0] ?? vn.wallId
        : vn.wallId
      const pascalDoor = adaptDoor(vn, levelId, generateId('door'), hostPascalId ?? (vn.wallId ?? ''))
      nodes[pascalDoor.id] = pascalDoor
      nodes[levelId].children.push(pascalDoor.id)
      if (nodes[hostPascalId ?? '']) {
        nodes[hostPascalId ?? ''].children = nodes[hostPascalId ?? ''].children ?? []
        nodes[hostPascalId ?? ''].children.push(pascalDoor.id)
      }
      addIdentityEntry(identityMap, makeEntry(graph, vn.id, pascalDoor.id, 'door', []))
    } else if (vn.type === 'window') {
      const hostPascalId = vn.wallId
      const pascalWindow = adaptWindow(vn, levelId, generateId('window'), hostPascalId ?? '')
      nodes[pascalWindow.id] = pascalWindow
      nodes[levelId].children.push(pascalWindow.id)
      if (nodes[hostPascalId ?? '']) {
        nodes[hostPascalId ?? ''].children = nodes[hostPascalId ?? ''].children ?? []
        nodes[hostPascalId ?? ''].children.push(pascalWindow.id)
      }
      addIdentityEntry(identityMap, makeEntry(graph, vn.id, pascalWindow.id, 'window', []))
    } else if (vn.type === 'slab') {
      const pascalSlab = adaptSlab(vn, levelId, generateId('slab'))
      nodes[pascalSlab.id] = pascalSlab
      nodes[levelId].children.push(pascalSlab.id)
      addIdentityEntry(identityMap, makeEntry(graph, vn.id, pascalSlab.id, 'slab', []))
    }
  }

  return {
    sceneGraph: { nodes, rootNodeIds: rootNodeIds },
    identityMap,
    nodeCounts,
  }
}

function makeEntry(
  graph: Vision5DGraph,
  v5dStableId: string,
  pascalNodeId: string,
  nodeType: string,
  dxfHandles: string[],
): IdentityMapEntry {
  return {
    projectId: graph.projectId,
    vision5dRevisionId: graph.revisionId,
    pascalSceneId: 'pending',
    pascalSchemaVersion: '0.9.2',
    vision5dStableId: v5dStableId,
    pascalNodeId,
    nodeType,
    sourceDxfHandles: dxfHandles,
    createdAt: new Date().toISOString(),
    lastSyncedAt: new Date().toISOString(),
    lifecycleState: LifecycleState.ACTIVE,
  }
}
