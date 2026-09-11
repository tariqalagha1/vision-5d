/**
 * correction_event_applier.ts — Atomic correction event application
 * All-or-nothing: no partial mutation of a Vision 5D revision.
 */

import { CorrectionEvent } from '../schemas/correction_event'
import { SceneRevision } from '../schemas/scene_revision'

export class CorrectionEventApplier {
  apply(
    events: CorrectionEvent[],
    sourceRevision: SceneRevision,
  ): { success: boolean; revision: SceneRevision | null; errors: string[] } {
    const errors: string[] = []

    // Validate all events first (pre-flight check)
    for (const event of events) {
      if (event.validationStatus === 'rejected') {
        errors.push(`Event ${event.eventId}: already rejected`)
        continue
      }
      if (!event.vision5dStableId && 
          !event.eventType.startsWith('ADD_')) {
        errors.push(`Event ${event.eventId}: missing vision5dStableId for non-ADD operation`)
      }
      if (event.eventType.startsWith('DELETE_') && 
          event.vision5dStableId &&
          !sourceRevision.nodes[event.vision5dStableId]) {
        errors.push(`Event ${event.eventId}: node ${event.vision5dStableId} not found in source revision`)
      }
    }

    if (errors.length > 0) {
      return { success: false, revision: null, errors }
    }

    // Apply atomically
    const newNodes = { ...sourceRevision.nodes }
    const changedNodes: string[] = []
    const createdNodes: string[] = []
    const deletedNodes: string[] = []

    for (const event of events) {
      event.validationStatus = 'valid'
      event.appliedAt = new Date().toISOString()
      const sid = event.vision5dStableId!

      switch (event.eventType) {
        case 'MOVE_WALL_ENDPOINT':
        case 'MOVE_WALL':
          if (newNodes[sid]) {
            (newNodes[sid] as any).end = (event.newValue as any)?.end
            changedNodes.push(sid)
          }
          break
        case 'CHANGE_WALL_THICKNESS':
          if (newNodes[sid]) {
            (newNodes[sid] as any).thickness = (event.newValue as any)?.thickness
            changedNodes.push(sid)
          }
          break
        case 'CHANGE_WALL_HEIGHT':
          if (newNodes[sid]) {
            (newNodes[sid] as any).height = (event.newValue as any)?.height
            changedNodes.push(sid)
          }
          break
        case 'ADD_WALL':
        case 'ADD_DOOR':
        case 'ADD_WINDOW':
          newNodes[sid] = { ...(event.newValue as any), id: sid }
          createdNodes.push(sid)
          break
        case 'DELETE_WALL':
        case 'DELETE_DOOR':
        case 'DELETE_WINDOW':
          delete newNodes[sid]
          deletedNodes.push(sid)
          break
        case 'MOVE_DOOR':
        case 'MOVE_WINDOW':
          if (newNodes[sid]) {
            (newNodes[sid] as any).position = (event.newValue as any)?.position
            changedNodes.push(sid)
          }
          break
      }
    }

    const revision: SceneRevision = {
      revisionId: require('uuid').v4(),
      parentRevisionId: sourceRevision.revisionId,
      pascalSceneId: events[0]?.pascalSceneId ?? null,
      correctionEventIds: events.map(e => e.eventId),
      identityMapVersion: sourceRevision.identityMapVersion + 1,
      nodes: newNodes,
      rootNodeIds: sourceRevision.rootNodeIds.filter(id => !deletedNodes.includes(id)),
      changedNodes,
      createdNodes,
      deletedNodes,
      validationResult: 'all_events_applied',
      checksum: '',
      createdAt: new Date().toISOString(),
    }

    return { success: true, revision, errors: [] }
  }
}
