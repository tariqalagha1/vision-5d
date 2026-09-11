/**
 * wall_adapter.ts — Vision 5D Wall → Pascal WallNode
 * Uses native start/end 2D tuples.
 */

interface Vision5DWall {
  id: string
  start?: [number, number]
  end?: [number, number]
  thickness?: number
  height?: number
  metadata?: Record<string, unknown>
  name?: string
}

interface PascalWallNode {
  object: 'node'
  id: string
  type: 'wall'
  name: string
  parentId: string
  position: [number, number, number]
  rotation: [number, number, number]
  visible: boolean
  start: [number, number]
  end: [number, number]
  thickness: number
  height: number
  children: string[]
  frontSide: 'unknown'
  backSide: 'unknown'
  metadata: Record<string, unknown>
}

export function adaptWall(
  v5dWall: Vision5DWall,
  levelId: string,
  pascalId: string,
): PascalWallNode {
  return {
    object: 'node',
    id: pascalId,
    type: 'wall',
    name: v5dWall.name ?? 'Wall',
    parentId: levelId,
    position: [0, 0, 0],
    rotation: [0, 0, 0],
    visible: true,
    start: v5dWall.start ?? [0, 0],
    end: v5dWall.end ?? [0, 0],
    thickness: v5dWall.thickness ?? 0.20,
    height: v5dWall.height ?? 2.70,
    children: [],
    frontSide: 'unknown',
    backSide: 'unknown',
    metadata: {
      vision5d: {
        ...(v5dWall.metadata?.vision5d ?? {}),
        stable_id: v5dWall.id,
      },
    },
  }
}
