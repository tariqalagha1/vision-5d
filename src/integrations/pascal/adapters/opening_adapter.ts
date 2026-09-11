/**
 * opening_adapter.ts — Vision 5D Doors/Windows → Pascal DoorNode/WindowNode
 * Uses wall-local positioning [u, v, w].
 */

function wallLocalPosition(
  globalX: number, globalY: number, height: number,
  wallStart: [number, number], wallEnd: [number, number],
): [number, number, number] {
  const dx = wallEnd[0] - wallStart[0]
  const dy = wallEnd[1] - wallStart[1]
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len < 1e-9) return [0, height, 0]
  const ux = dx / len
  const uy = dy / len
  const u = (globalX - wallStart[0]) * ux + (globalY - wallStart[1]) * uy
  return [Math.round(u * 1000) / 1000, height, 0]
}

interface OpeningInput {
  id: string
  name?: string
  position?: [number, number, number]
  wallId?: string
  width?: number
  height?: number
  metadata?: Record<string, unknown>
  doorType?: string
  doorCategory?: string
  windowType?: string
}

export function adaptDoor(
  v5dDoor: OpeningInput,
  levelId: string,
  pascalId: string,
  hostPascalWallId: string,
  // wall geometry needed for local conversion (supplied by caller)
  wallStart?: [number, number],
  wallEnd?: [number, number],
): any {
  const gpos = v5dDoor.position ?? [0, 0, 0]
  const localPos = wallStart && wallEnd
    ? wallLocalPosition(gpos[0], gpos[2] ?? gpos[1], 0, wallStart, wallEnd)
    : [0, 0, 0]

  return {
    object: 'node',
    id: pascalId,
    type: 'door',
    name: v5dDoor.name ?? 'Door',
    parentId: levelId,
    position: localPos,
    rotation: [0, 0, 0],
    wallId: hostPascalWallId,
    side: 'front',
    width: v5dDoor.width ?? 0.9,
    height: v5dDoor.height ?? 2.1,
    doorType: v5dDoor.doorType ?? 'hinged',
    doorCategory: v5dDoor.doorCategory ?? 'interior',
    openingKind: 'door',
    openingShape: 'rectangle',
    visible: true,
    metadata: {
      vision5d: {
        ...(v5dDoor.metadata?.vision5d ?? {}),
        stable_id: v5dDoor.id,
        global_position_for_reverse: gpos,
      },
    },
  }
}

export function adaptWindow(
  v5dWindow: OpeningInput,
  levelId: string,
  pascalId: string,
  hostPascalWallId: string,
  wallStart?: [number, number],
  wallEnd?: [number, number],
): any {
  const gpos = v5dWindow.position ?? [0, 0, 0]
  const sillHeight = gpos[2] ?? gpos[1] ?? 1.0
  const localPos = wallStart && wallEnd
    ? wallLocalPosition(gpos[0], gpos[2] ?? gpos[1], sillHeight, wallStart, wallEnd)
    : [0, sillHeight, 0]

  return {
    object: 'node',
    id: pascalId,
    type: 'window',
    name: v5dWindow.name ?? 'Window',
    parentId: levelId,
    position: localPos,
    rotation: [0, 0, 0],
    wallId: hostPascalWallId,
    side: 'front',
    width: v5dWindow.width ?? 1.5,
    height: v5dWindow.height ?? 1.2,
    windowType: v5dWindow.windowType ?? 'fixed',
    openingKind: 'window',
    openingShape: 'rectangle',
    visible: true,
    metadata: {
      vision5d: {
        ...(v5dWindow.metadata?.vision5d ?? {}),
        stable_id: v5dWindow.id,
        global_position_for_reverse: gpos,
      },
    },
  }
}
