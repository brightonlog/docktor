import * as THREE from 'three';

export interface ShipModelGLTFProps {
  modelPath: string;
  rotate?: boolean;
  scale?: number;
  position?: [number, number, number];
  rotationX?: number;
  rotationY?: number;
  rotationZ?: number;
  onLoaded?: (scene: THREE.Group) => void;
}

export interface OceanProps {
  speed?: number;
  waveHeight?: number;
}

export interface DefectData {
  id: string;
  type: string;
  position: [number, number, number];
  confidence: number;
  severity: 'high' | 'medium' | 'low';
  description: string;
  image?: string;
}

export type ShipType = 'LNGC' | 'Container' | 'VLCC' | 'LPGC' | 'Bulk Carrier';
