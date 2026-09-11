/**
 * scene_revision.ts — Immutable Vision 5D Scene Revision
 */

export interface SceneRevision {
  revisionId: string
  parentRevisionId: string | null
  pascalSceneId: string | null
  correctionEventIds: string[]
  identityMapVersion: number
  nodes: Record<string, unknown>
  rootNodeIds: string[]
  changedNodes: string[]
  createdNodes: string[]
  deletedNodes: string[]
  validationResult: 'all_events_applied' | 'partial_application' | 'rejected'
  checksum: string
  createdAt: string
}

export interface RevisionManifest {
  revisions: SceneRevision[]
  immutableChain: boolean
  currentRevisionId: string
}
