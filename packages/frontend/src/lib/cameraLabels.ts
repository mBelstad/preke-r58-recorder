/**
 * Camera Labels - Single source of truth for camera display names
 * 
 * This file provides consistent labeling across all components.
 * Update here to change labels everywhere.
 */

export const CAMERA_LABELS: Record<string, string> = {
  'cam0': 'HDMI 1',
  'cam1': 'HDMI 2',
  'cam2': 'HDMI 3',
  'cam3': 'HDMI 4',
}

/**
 * Get a human-readable label for a camera ID
 */
export function getCameraLabel(camId: string): string {
  return CAMERA_LABELS[camId] || camId.toUpperCase()
}

/**
 * Get camera label with additional info (for detailed views)
 */
export function getCameraLabelWithInfo(camId: string): { name: string; subtitle: string } {
  const name = CAMERA_LABELS[camId] || camId.toUpperCase()
  return {
    name,
    subtitle: 'HDMI Input'
  }
}
