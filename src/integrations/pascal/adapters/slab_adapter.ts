/**
 * slab_adapter.ts — Vision 5D Slab → Pascal SlabNode
 */

interface Vision5DSlab {
  id: string
  name?: string
  polygon?: [number, number][]
  metadata?: Record<string, unknown>
}

interface PascalSlabNode {
  object: 'node'
  id: string
  type: 'slab'
  name: string
  parentId: string
  position: [number, number, number]
  rotation: [number, number, number]
  visible: boolean
  polygon: [number, number][]
  holes: [number, number][][]
  holeMetadata: unknown[]
  elevation: number
  thickness: number
  autoFromWalls: boolean
  metadata: Record<string, unknown>
}

export function adaptSlab(
  v5dSlab: Vision5DSlab,
  levelId: string,
  pascalId: string,
): PascalSlabNode {
  return {
    object: 'node',
    id: pascalId,
    type: 'slab',
    name: v5dSlab.name ?? 'Slab',
    parentId: levelId,
    position: [0, 0, 0],
    rotation: [0, 0, 0],
    visible: true,
    polygon: v5dSlab.polygon ?? [[0, 0], [10, 0], [10, 10], [0, 10]],
    holes: [],
    holeMetadata: [],
    elevation: 0.0,
    thickness: 0.15,
    autoFromWalls: true,
    metadata: {
      vision5d: {
        ...(v5dSlab.metadata?.vision5d ?? {}),
        stable_id: v5dSlab.id,
      },
    },
  }
}
