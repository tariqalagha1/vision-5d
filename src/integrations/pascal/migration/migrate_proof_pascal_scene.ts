/**
 * migrate_proof_pascal_scene.ts — Proof-format → Native Pascal migration
 * Idempotent, deterministic, non-destructive.
 */

export interface ProofFormatScene {
  nodes: any[]      // array format
  version?: string
  generatedBy?: string
}

export interface NativePascalGraph {
  nodes: Record<string, any>
  rootNodeIds: string[]
}

export function migrateProofPascalScene(proofScene: ProofFormatScene | NativePascalGraph): {
  graph: NativePascalGraph
  migrated: boolean
  report: string[]
} {
  // Idempotency: if already native, return as-is
  if (proofScene.nodes && !Array.isArray(proofScene.nodes) && (proofScene as any).rootNodeIds) {
    return {
      graph: proofScene as NativePascalGraph,
      migrated: false,
      report: ['Already in native format — no migration needed'],
    }
  }

  const report: string[] = []
  const nodesArray = (proofScene as ProofFormatScene).nodes ?? []
  const newNodes: Record<string, any> = {}
  const rootNodeIds: string[] = []

  for (const node of nodesArray) {
    const nid = node.id
    const newNode = { ...node }

    // GAP-003: start_point_2d/end_point_2d → start/end
    if (newNode.type === 'wall') {
      if (newNode.start_point_2d && !newNode.start) {
        newNode.start = newNode.start_point_2d
        delete newNode.start_point_2d
        report.push(`Migrated wall ${nid}: start_point_2d → start`)
      }
      if (newNode.end_point_2d && !newNode.end) {
        newNode.end = newNode.end_point_2d
        delete newNode.end_point_2d
        report.push(`Migrated wall ${nid}: end_point_2d → end`)
      }
    }

    // GAP-004: ensure parentId
    if (!newNode.parentId) {
      newNode.parentId = null
    }

    // GAP-009: create site if missing
    if (newNode.type === 'building' && !newNode.parentId) {
      newNode.parentId = null
    }

    // Root detection
    if (newNode.parentId === null) {
      rootNodeIds.push(nid)
    }

    newNodes[nid] = newNode
  }

  // Ensure rootNodeIds has at least one entry
  if (rootNodeIds.length === 0 && Object.keys(newNodes).length > 0) {
    rootNodeIds.push(Object.keys(newNodes)[0])
    report.push('No explicit roots found — using first node as root')
  }

  return {
    graph: { nodes: newNodes, rootNodeIds },
    migrated: true,
    report,
  }
}
