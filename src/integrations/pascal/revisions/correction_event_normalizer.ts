/**
 * correction_event_normalizer.ts — Pascal Edits → Vision 5D Correction Events
 */

import { v4 as uuidv4 } from 'uuid'
import { CorrectionEvent, CorrectionEventType, computeEventChecksum } from '../schemas/correction_event'
import { IdentityMap } from '../schemas/identity_map'

interface PascalEdit {
  operation: CorrectionEventType
  pascalNodeId: string
  oldValue: unknown
  newValue: unknown
  reason?: string
  origin?: 'user_edit' | 'mcp_operation' | 'automated'
}

export class CorrectionEventNormalizer {
  normalizeEdits(
    edits: PascalEdit[],
    projectId: string,
    sourceRevisionId: string,
    pascalSceneId: string,
    identityMap: IdentityMap,
  ): CorrectionEvent[] {
    return edits.map(edit => this.normalizeEdit(edit, projectId, sourceRevisionId, pascalSceneId, identityMap))
  }

  private normalizeEdit(
    edit: PascalEdit,
    projectId: string,
    sourceRevisionId: string,
    pascalSceneId: string,
    identityMap: IdentityMap,
  ): CorrectionEvent {
    const vision5dStableId = edit.pascalNodeId
      ? (identityMap.pascalToVision5d[edit.pascalNodeId] ?? null)
      : null

    const event: Omit<CorrectionEvent, 'checksum'> = {
      eventId: uuidv4(),
      eventType: edit.operation,
      timestamp: new Date().toISOString(),
      projectId,
      sourceRevisionId,
      targetRevisionId: null,
      pascalSceneId,
      pascalNodeId: edit.pascalNodeId,
      vision5dStableId,
      affectedDxfHandles: [],
      oldValue: edit.oldValue,
      newValue: edit.newValue,
      coordinateSystem: 'right-handed X(east) Y(up) Z(north)',
      units: 'meters',
      origin: edit.origin ?? 'user_edit',
      reason: edit.reason ?? null,
      validationStatus: 'pending',
      dependentNodeIds: [],
      appliedAt: null,
    }

    return {
      ...event,
      checksum: computeEventChecksum(event),
    }
  }
}
