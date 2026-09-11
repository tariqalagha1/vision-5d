/**
 * correction_event.ts — Vision 5D Correction Event Schema
 *
 * Every Pascal edit becomes an explicit, traceable correction event
 * referencing Vision 5D stable IDs.
 */

export enum CorrectionEventType {
  MOVE_WALL_ENDPOINT = 'MOVE_WALL_ENDPOINT',
  MOVE_WALL = 'MOVE_WALL',
  CHANGE_WALL_THICKNESS = 'CHANGE_WALL_THICKNESS',
  CHANGE_WALL_HEIGHT = 'CHANGE_WALL_HEIGHT',
  ADD_WALL = 'ADD_WALL',
  DELETE_WALL = 'DELETE_WALL',
  ADD_DOOR = 'ADD_DOOR',
  MOVE_DOOR = 'MOVE_DOOR',
  DELETE_DOOR = 'DELETE_DOOR',
  ADD_WINDOW = 'ADD_WINDOW',
  MOVE_WINDOW = 'MOVE_WINDOW',
  DELETE_WINDOW = 'DELETE_WINDOW',
}

export interface CorrectionEvent {
  eventId: string
  eventType: CorrectionEventType
  timestamp: string
  projectId: string
  sourceRevisionId: string
  targetRevisionId: string | null
  pascalSceneId: string
  pascalNodeId: string
  vision5dStableId: string | null  // null for Pascal-created nodes
  affectedDxfHandles: string[]
  oldValue: unknown
  newValue: unknown
  coordinateSystem: 'right-handed X(east) Y(up) Z(north)'
  units: 'meters'
  origin: 'user_edit' | 'mcp_operation' | 'automated'
  reason: string | null
  validationStatus: 'pending' | 'valid' | 'rejected'
  dependentNodeIds: string[]
  checksum: string
  appliedAt: string | null
}

export function computeEventChecksum(event: Omit<CorrectionEvent, 'checksum'>): string {
  const crypto = require('crypto')
  const payload = JSON.stringify(event, Object.keys(event).sort())
  return crypto.createHash('sha256').update(payload).digest('hex')
}
