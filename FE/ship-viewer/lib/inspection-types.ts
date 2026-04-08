import * as THREE from 'three';

// 벽면 방향
export type WallDirection = 'front' | 'back' | 'left' | 'right' | 'full'

// 구역
export type WallSection = 'bow' | 'stern' | 'ship' | 'custom';

// 선택된 영역
export interface SelectedArea {
  wall: WallDirection | 'full' | 'custom';
  section: WallSection;
  bounds?: THREE.Box3;
  center?: THREE.Vector3;
  size?: THREE.Vector3;
  area: number; // m²
}

// 감지된 벽면
export interface DetectedWall {
  meshes: THREE.Mesh[];
  bounds: THREE.Box3;
  center: THREE.Vector3;
  size: THREE.Vector3;
  area: number;
}

// 감지된 모든 벽면
export interface DetectedWalls {
  front: DetectedWall | null;
  back: DetectedWall | null;
  left: DetectedWall | null;
  right: DetectedWall | null;
}

// 검사 상태
export interface InspectionState {
  isInspecting: boolean;
  isCalibrated: boolean;
  progress: number;
  capturedImages: number;
  detectedDefects: number;
  elapsedTime: string;
  robotPosition: { x: number; z: number };
  scaleX: number;
  scaleZ: number;
}

// 선박 정보 (백엔드 API 응답 구조)
export interface ShipInfoData {
  shipId: number;
  corpId: number;
  name: string;
  classNo: string;
  imo: string | null;
  classNotation: string;
  flagState: string;
  port: string;
  ton: number;
  deadWeight: number;
  lbp: number; // length between perpendiculars (m)
  shipbuilder: string;
  hullNumber: string;
  deliveryDate: string; // ISO date string (YYYY-MM-DD)
  buildDate: string; // ISO date string (YYYY-MM-DD)
  createDate: string; // ISO date string (ISO 8601)
}

// 벽면 이름 매핑
export const WALL_NAMES: Record<WallDirection | 'full', string> = {
  full: '전체 벽면',
  front: '전면',
  back: '후면',
  left: '좌측 벽면',
  right: '우측 벽면',
};

// 구역 이름 매핑
export const SECTION_NAMES: Record<WallSection, string> = {
  ship: '전체',
  bow: '선수부',
  stern: '선미부',
  custom: '커스텀',
};

// 영역 이름 생성 헬퍼
export function getAreaName(wall: WallDirection | 'full' | 'custom', section: WallSection): string {
  if (wall === 'custom') return '커스텀 드래그 영역';
  if (wall === 'full') return WALL_NAMES.full;
  return `${WALL_NAMES[wall]} - ${SECTION_NAMES[section]}`;
}

// 기본 검사 상태
export const DEFAULT_INSPECTION_STATE: InspectionState = {
  isInspecting: false,
  isCalibrated: false,
  progress: 0,
  capturedImages: 0,
  detectedDefects: 0,
  elapsedTime: '00:00',
  robotPosition: { x: 0, z: 0 },
  scaleX: 1.0,
  scaleZ: 1.0,
};
