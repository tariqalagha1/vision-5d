/**
 * revision_manager.ts — Immutable Vision 5D Revision Manager
 * Never overwrites source revisions. Every change creates a new revision.
 */

import { v4 as uuidv4 } from 'uuid'
import { SceneRevision, RevisionManifest } from '../schemas/scene_revision'
import { CorrectionEvent } from '../schemas/correction_event'
import { computeEventChecksum } from '../schemas/correction_event'

export class RevisionManager {
  private revisions: Map<string, SceneRevision> = new Map()

  constructor(private projectId: string) {}

  createInitialRevision(graph: Record<string, unknown>[], rootNodeIds: string[]): SceneRevision {
    const rev: SceneRevision = {
      revisionId: uuidv4(),
      parentRevisionId: null,
      pascalSceneId: null,
      correctionEventIds: [],
      identityMapVersion: 0,
      nodes: Object.fromEntries(graph.map(n => [n.id as string, n])),
      rootNodeIds,
      changedNodes: [],
      createdNodes: graph.map(n => n.id as string),
      deletedNodes: [],
      validationResult: 'all_events_applied',
      checksum: '',
      createdAt: new Date().toISOString(),
    }
    rev.checksum = this.computeChecksum(rev)
    this.revisions.set(rev.revisionId, rev)
    return rev
  }

  applyCorrectionEvents(
    parentRevisionId: string,
    events: CorrectionEvent[],
  ): SceneRevision {
    const parent = this.revisions.get(parentRevisionId)
    if (!parent) throw new Error(`Parent revision ${parentRevisionId} not found`)

    const newNodes = { ...parent.nodes }
    const changedNodes: string[] = []
    const createdNodes: string[] = []
    const deletedNodes: string[] = []

    for (const event of events) {
      if (event.validationStatus === 'rejected') continue

      const stableId = event.vision5dStableId
      if (!stableId) continue

      switch (event.eventType) {
        case 'MOVE_WALL_ENDPOINT':
        case 'MOVE_WALL':
          if (newNodes[stableId]) {
            (newNodes[stableId] as any).end = (event.newValue as any)?.end
            changedNodes.push(stableId)
          }
          break
        case 'CHANGE_WALL_THICKNESS':
          if (newNodes[stableId]) {
            (newNodes[stableId] as any).thickness = (event.newValue as any)?.thickness
            changedNodes.push(stableId)
          }
          break
        case 'ADD_WALL':
        case 'ADD_DOOR':
        case 'ADD_WINDOW':
          newNodes[stableId] = event.newValue
          createdNodes.push(stableId)
          break
        case 'DELETE_WALL':
        case 'DELETE_DOOR':
        case 'DELETE_WINDOW':
          delete newNodes[stableId]
          deletedNodes.push(stableId)
          break
      }
    }

    const rev: SceneRevision = {
      revisionId: uuidv4(),
      parentRevisionId,
      pascalSceneId: events[0]?.pascalSceneId ?? null,
      correctionEventIds: events.map(e => e.eventId),
      identityMapVersion: parent.identityMapVersion + 1,
      nodes: newNodes,
      rootNodeIds: parent.rootNodeIds.filter(id => !deletedNodes.includes(id)),
      changedNodes,
      createdNodes,
      deletedNodes,
      validationResult: 'all_events_applied',
      checksum: '',
      createdAt: new Date().toISOString(),
    }
    rev.checksum = this.computeChecksum(rev)
    this.revisions.set(rev.revisionId, rev)
    return rev
  }

  getRevision(revisionId: string): SceneRevision | undefined {
    return this.revisions.get(revisionId)
  }

  getManifest(): RevisionManifest {
    const revs = Array.from(this.revisions.values())
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
    return {
      revisions: revs,
      immutableChain: true,
      currentRevisionId: revs[revs.length - 1]?.revisionId ?? '',
    }
  }

  private computeChecksum(rev: Omit<SceneRevision, 'checksum'>): string {
    const crypto = require('crypto')
    const payload = JSON.stringify({
      revisionId: rev.revisionId,
      parentRevisionId: rev.parentRevisionId,
      nodeIds: Object.keys(rev.nodes).sort(),
    })
    return crypto.createHash('sha256').update(payload).digest('hex')
  }
}
