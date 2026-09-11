/**
 * pascal_to_vision5d.ts — Reverse Adapter
 * Converts Pascal-native SceneGraph back to Vision 5D graph
 */

import { MAX_ROUND_TRIP_DELTA_M, COORDINATE_PRECISION } from '../index'

interface RecoveredGraph {
  nodes: Record<string, unknown>[]
  rootNodeIds: string[]
  revisionId: string
  parentRevisionId: string
  maxDeltaM: number
  deltas: Array<{ nodeId: string; stableId: string; deltaM: number }>
}

export function convertPascalToVision5D(
  pascalNodes: Record<string, any>,
  rootNodeIds: string[],
  identityMap: { pascalToVision5d: Record<string, string> },
  sourceRevisionId: string,
  newRevisionId: string,
): RecoveredGraph {
  const recovered: Record<string, unknown>[] = []
  const deltas: Array<{ nodeId: string; stableId: string; deltaM: number }> = []
  let maxDelta = 0

  for (const [pascalId, node] of Object.entries(pascalNodes)) {
    const stableId = identityMap.pascalToVision5d[pascalId] ?? `recovered_${pascalId}`
    const rn: Record<string, unknown> = {
      id: stableId,
      type: node.type,
      name: node.name,
      parentId: node.parentId,
      metadata: node.metadata ?? {},
    }

    if (node.type === 'wall') {
      rn['start'] = node.start
      rn['end'] = node.end
      rn['thickness'] = node.thickness
      rn['height'] = node.height

      // Compare to original if provenance has global data
      const globalPos = node.metadata?.vision5d?.global_position_for_reverse
      if (globalPos && Array.isArray(globalPos)) {
        const startPt = node.start as [number, number]
        const delta = Math.sqrt(
          (startPt[0] - (globalPos[0] ?? 0)) ** 2 +
          (startPt[1] - (globalPos[1] ?? 0)) ** 2
        )
        maxDelta = Math.max(maxDelta, delta)
        deltas.push({ nodeId: pascalId, stableId, deltaM: Math.round(delta * 1e6) / 1e6 })
      }
    }

    if (node.type === 'door' || node.type === 'window') {
      rn['position'] = node.position
      rn['wallId'] = node.wallId
      rn['width'] = node.width
      rn['height'] = node.height

      // Recover global position from wall-local
      if (node.wallId && pascalNodes[node.wallId]) {
        const wall = pascalNodes[node.wallId]
        const localPos = node.position as [number, number, number]
        const wallStart = wall.start as [number, number]
        const wallEnd = wall.end as [number, number]
        const dx = wallEnd[0] - wallStart[0]
        const dy = wallEnd[1] - wallStart[1]
        const len = Math.sqrt(dx * dx + dy * dy)
        if (len > 1e-9) {
          const ux = dx / len
          const uy = dy / len
          const gx = wallStart[0] + localPos[0] * ux
          const gy = wallStart[1] + localPos[0] * uy
          rn['recovered_global'] = [Math.round(gx * 1e6) / 1e6, Math.round(gy * 1e6) / 1e6, localPos[1]]
        }
      }
    }

    if (node.type === 'slab') {
      rn['polygon'] = node.polygon
    }

    recovered.push(rn)
  }

  return {
    nodes: recovered,
    rootNodeIds,
    revisionId: newRevisionId,
    parentRevisionId: sourceRevisionId,
    maxDeltaM: Math.round(maxDelta * 1e6) / 1e6,
    deltas,
  }
}
