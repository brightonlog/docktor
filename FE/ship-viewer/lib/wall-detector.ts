import * as THREE from 'three';
import type { DetectedWall, DetectedWalls, WallDirection, WallSection } from './inspection-types';

interface MeshAnalysis {
  avgNormal: THREE.Vector3;
  position: THREE.Vector3;
  bounds: THREE.Box3;
}

/**
 * 메쉬의 방향과 위치 분석 (로컬 좌표계)
 */
export function analyzeMeshOrientation(mesh: THREE.Mesh, useLocal: boolean = false): MeshAnalysis | null {
  if (!mesh.geometry) return null;

  const geometry = mesh.geometry;

  // 버텍스가 없으면 무시
  if (!geometry.attributes.position) return null;

  // 법선이 없으면 계산
  if (!geometry.attributes.normal) {
    geometry.computeVertexNormals();
  }

  const normalAttribute = geometry.attributes.normal;
  if (!normalAttribute) return null;

  // 평균 법선 벡터 계산
  const avgNormal = new THREE.Vector3(0, 0, 0);

  for (let i = 0; i < normalAttribute.count; i++) {
    const nx = normalAttribute.getX(i);
    const ny = normalAttribute.getY(i);
    const nz = normalAttribute.getZ(i);
    avgNormal.add(new THREE.Vector3(nx, ny, nz));
  }
  avgNormal.divideScalar(normalAttribute.count);
  avgNormal.normalize();

  // 로컬 또는 월드 좌표계로 변환
  const rotationMatrix = useLocal
    ? new THREE.Matrix4().extractRotation(mesh.matrix)
    : new THREE.Matrix4().extractRotation(mesh.matrixWorld);
  const normal = avgNormal.clone().applyMatrix4(rotationMatrix).normalize();

  // 메쉬의 바운딩 박스와 중심점 계산
  let bounds: THREE.Box3;
  if (useLocal) {
    // 로컬 바운딩 박스
    if (!geometry.boundingBox) {
      geometry.computeBoundingBox();
    }
    bounds = geometry.boundingBox ? geometry.boundingBox.clone().applyMatrix4(mesh.matrix) : new THREE.Box3();
  } else {
    // 월드 바운딩 박스
    bounds = new THREE.Box3().setFromObject(mesh);
  }
  const center = bounds.getCenter(new THREE.Vector3());

  return {
    avgNormal: normal,
    position: center,
    bounds: bounds,
  };
}

/**
 * 메쉬가 벽면인지 확인 (컨테이너, 갑판, 바닥, 상부구조물 제외)
 */
export function isWallMesh(mesh: THREE.Mesh, shipModel: THREE.Object3D): boolean {
  if (!mesh || !mesh.geometry) return false;

  const shipBox = getLocalBoundingBox(shipModel);
  const shipSize = shipBox.getSize(new THREE.Vector3());

  // 선체 벽면 높이 (하단 40%만 - 컨테이너 아래)
  const hullMaxY = shipBox.min.y + (shipSize.y * 0.4);

  // 메쉬 이름으로 컨테이너 제외
  if (mesh.name && (
    mesh.name.toLowerCase().includes('container') ||
    mesh.name.toLowerCase().includes('cargo') ||
    mesh.name.toLowerCase().includes('box')
  )) {
    return false;
  }

  // 메쉬 분석 (로컬 좌표계)
  const meshData = analyzeMeshOrientation(mesh, true);
  if (!meshData) return false;

  const { avgNormal, position, bounds } = meshData;

  // 수평면 제외 (갑판, 바닥)
  const horizontalThreshold = 0.7;
  const isHorizontal = Math.abs(avgNormal.y) > horizontalThreshold;
  if (isHorizontal) return false;

  // 측면 벽 확인
  const sideWallThreshold = 0.4;
  const isXWall = Math.abs(avgNormal.x) > sideWallThreshold;
  const isZWall = Math.abs(avgNormal.z) > sideWallThreshold;

  if (!isXWall && !isZWall) return false;

  // 높이 검사 (선체 벽면 범위 내에만, 컨테이너 제외)
  if (position.y > hullMaxY) return false;
  if (bounds.max.y > hullMaxY) return false;

  return true;
}

/**
 * 벽면 면적 계산
 */
export function calculateWallArea(direction: WallDirection, size: THREE.Vector3): number {
  switch (direction) {
    case 'front':
    case 'back':
      return size.z * size.y; // Z * Y (측면)
    case 'left':
    case 'right':
      return size.x * size.y; // X * Y (앞뒤)
    default:
      return 0;
  }
}

/**
 * shipModel 기준 상대 좌표계에서 바운딩 박스 계산
 */
function getLocalBoundingBox(shipModel: THREE.Object3D): THREE.Box3 {
  const box = new THREE.Box3();

  // shipModel의 역행렬 (월드 -> shipModel 로컬)
  const shipWorldMatrixInverse = new THREE.Matrix4();
  shipModel.updateMatrixWorld(true);
  shipWorldMatrixInverse.copy(shipModel.matrixWorld).invert();

  shipModel.traverse((child) => {
    if (child instanceof THREE.Mesh && child.geometry) {
      const geometry = child.geometry;

      // geometry의 바운딩 박스 계산
      if (!geometry.boundingBox) {
        geometry.computeBoundingBox();
      }

      if (geometry.boundingBox) {
        const meshBox = geometry.boundingBox.clone();

        // 메쉬의 월드 좌표 변환
        child.updateMatrixWorld(true);
        meshBox.applyMatrix4(child.matrixWorld);

        // shipModel의 로컬 좌표로 변환
        meshBox.applyMatrix4(shipWorldMatrixInverse);

        box.union(meshBox);
      }
    }
  });

  return box;
}

/**
 * 선박 모델에서 벽면 자동 감지
 */
export function detectShipWalls(shipModel: THREE.Object3D): DetectedWalls {
  // shipModel 기준 상대 좌표계에서 바운딩 박스 계산
  const shipBox = getLocalBoundingBox(shipModel);
  const shipSize = shipBox.getSize(new THREE.Vector3());

  // 벽면 후보 메쉬들을 수집
  const wallCandidates: Record<WallDirection, Array<{ mesh: THREE.Mesh } & MeshAnalysis>> = {
    front: [],
    back: [],
    left: [],
    right: [],
  };

  // 선체 벽면 높이 (하단 40%까지만 선체)
  const hullMinY = shipBox.min.y;
  const deckStartY = shipBox.min.y + (shipSize.y * 0.4);
  const hullMaxY = deckStartY;

  // shipModel의 역행렬 계산
  const shipWorldMatrixInverse = new THREE.Matrix4();
  shipModel.updateMatrixWorld(true);
  shipWorldMatrixInverse.copy(shipModel.matrixWorld).invert();

  // 각 메쉬를 순회하며 법선 벡터로 벽면 분류
  shipModel.traverse((child) => {
    if (!(child instanceof THREE.Mesh) || !child.geometry) return;

    const geometry = child.geometry;

    // 법선 계산
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }

    const normalAttribute = geometry.attributes.normal;
    if (!normalAttribute) return;

    // 평균 법선 벡터 계산
    const avgNormal = new THREE.Vector3(0, 0, 0);
    for (let i = 0; i < normalAttribute.count; i++) {
      const nx = normalAttribute.getX(i);
      const ny = normalAttribute.getY(i);
      const nz = normalAttribute.getZ(i);
      avgNormal.add(new THREE.Vector3(nx, ny, nz));
    }
    avgNormal.divideScalar(normalAttribute.count);
    avgNormal.normalize();

    // 메쉬의 월드 변환을 적용한 후 shipModel 로컬로 변환
    child.updateMatrixWorld(true);

    // 법선을 월드 좌표로 변환
    const worldRotation = new THREE.Matrix4().extractRotation(child.matrixWorld);
    const worldNormal = avgNormal.clone().applyMatrix4(worldRotation).normalize();

    // shipModel 로컬 좌표로 법선 변환
    const shipRotation = new THREE.Matrix4().extractRotation(shipModel.matrixWorld);
    const shipRotationInverse = shipRotation.clone().invert();
    const localNormal = worldNormal.clone().applyMatrix4(shipRotationInverse).normalize();

    // 바운딩 박스를 shipModel 로컬 좌표로 계산
    if (!geometry.boundingBox) {
      geometry.computeBoundingBox();
    }

    const bounds = geometry.boundingBox ? geometry.boundingBox.clone() : new THREE.Box3();
    bounds.applyMatrix4(child.matrixWorld); // 월드 좌표로
    bounds.applyMatrix4(shipWorldMatrixInverse); // shipModel 로컬로

    const position = bounds.getCenter(new THREE.Vector3());

    const meshData: MeshAnalysis = {
      avgNormal: localNormal,
      position: position,
      bounds: bounds,
    };

    const { avgNormal: meshNormal } = meshData;

    // 수평면 완전 제외 (갑판, 바닥 모두 제외)
    const horizontalThreshold = 0.7;
    const isHorizontal = Math.abs(meshNormal.y) > horizontalThreshold;
    if (isHorizontal) return;

    // 측면 벽인지 확인
    const sideWallThreshold = 0.4;
    const isXWall = Math.abs(meshNormal.x) > sideWallThreshold;
    const isZWall = Math.abs(meshNormal.z) > sideWallThreshold;

    // 측면 벽이 아니면 제외
    if (!isXWall && !isZWall) return;

    // 높이 검사: 선체 벽면 범위 내에 있는 것만 포함
    if (position.y < hullMinY || position.y > hullMaxY) return;

    // 메쉬 바운딩 박스가 컨테이너/상부 구조물 영역과 겹치면 제외
    if (bounds.max.y > deckStartY) return;

    // 메쉬 이름으로 컨테이너 제외
    if (child.name && (
      child.name.toLowerCase().includes('container') ||
      child.name.toLowerCase().includes('cargo') ||
      child.name.toLowerCase().includes('box')
    )) {
      return;
    }

    // 벽면 방향별로 분류
    if (isXWall) {
      if (meshNormal.x > 0) {
        wallCandidates.front.push({ mesh: child, ...meshData });
      } else {
        wallCandidates.back.push({ mesh: child, ...meshData });
      }
    } else if (isZWall) {
      if (meshNormal.z > 0) {
        wallCandidates.right.push({ mesh: child, ...meshData });
      } else {
        wallCandidates.left.push({ mesh: child, ...meshData });
      }
    }
  });

  // 각 방향별로 벽면 정보 생성
  const detectedWalls: DetectedWalls = {
    front: null,
    back: null,
    left: null,
    right: null,
  };

  (Object.keys(wallCandidates) as WallDirection[]).forEach((direction) => {
    const candidates = wallCandidates[direction];

    if (candidates.length === 0) {
      detectedWalls[direction] = null;
      return;
    }

    // 모든 후보 메쉬를 하나의 그룹으로 통합하여 바운딩 박스 계산
    const combinedBounds = new THREE.Box3();
    candidates.forEach((candidate) => {
      combinedBounds.union(candidate.bounds);
    });

    const size = combinedBounds.getSize(new THREE.Vector3());
    const center = combinedBounds.getCenter(new THREE.Vector3());

    detectedWalls[direction] = {
      meshes: candidates.map((c) => c.mesh),
      bounds: combinedBounds,
      center: center,
      size: size,
      area: calculateWallArea(direction, size),
    };
  });

  return detectedWalls;
}

/**
 * 벽면 구역별 바운딩 박스 계산
 */
export function getWallSectionBounds(
  shipModel: THREE.Object3D,
  wall: WallDirection,
  section: WallSection
): { bounds: THREE.Box3; center: THREE.Vector3; size: THREE.Vector3; area: number } | null {
  const shipBox = getLocalBoundingBox(shipModel);
  const shipCenter = shipBox.getCenter(new THREE.Vector3());
  const shipSize = shipBox.getSize(new THREE.Vector3());

  // 선체 벽면 높이 (하단 40%)
  const hullHeight = shipSize.y * 0.4;
  const hullCenterY = shipBox.min.y + hullHeight / 2;

  // X축 구역 범위 계산
  let sectionMinX: number, sectionMaxX: number;
  if (section === 'all') {
    sectionMinX = shipBox.min.x;
    sectionMaxX = shipBox.max.x;
  } else if (section === 'bow') {
    sectionMinX = shipBox.min.x;
    sectionMaxX = shipBox.min.x + shipSize.x / 3;
  } else if (section === 'middle') {
    sectionMinX = shipBox.min.x + shipSize.x / 3;
    sectionMaxX = shipBox.min.x + (2 * shipSize.x) / 3;
  } else {
    // stern
    sectionMinX = shipBox.min.x + (2 * shipSize.x) / 3;
    sectionMaxX = shipBox.max.x;
  }

  const sectionWidth = sectionMaxX - sectionMinX;
  const sectionCenterX = (sectionMinX + sectionMaxX) / 2;

  // 얇은 벽면 두께
  const wallThickness = 0.1;

  let bounds: THREE.Box3;
  let center: THREE.Vector3;
  let size: THREE.Vector3;
  let area: number;

  switch (wall) {
    case 'front':
      // 전면 벽 (Z-)
      size = new THREE.Vector3(sectionWidth, hullHeight, wallThickness);
      center = new THREE.Vector3(sectionCenterX, hullCenterY, shipBox.min.z);
      area = sectionWidth * hullHeight;
      break;
    case 'back':
      // 후면 벽 (Z+)
      size = new THREE.Vector3(sectionWidth, hullHeight, wallThickness);
      center = new THREE.Vector3(sectionCenterX, hullCenterY, shipBox.max.z);
      area = sectionWidth * hullHeight;
      break;
    case 'left':
      // 좌현 벽 (X-)
      size = new THREE.Vector3(wallThickness, hullHeight, sectionWidth);
      center = new THREE.Vector3(shipBox.min.x, hullCenterY, sectionCenterX);
      area = sectionWidth * hullHeight;
      break;
    case 'right':
      // 우현 벽 (X+)
      size = new THREE.Vector3(wallThickness, hullHeight, sectionWidth);
      center = new THREE.Vector3(shipBox.max.x, hullCenterY, sectionCenterX);
      area = sectionWidth * hullHeight;
      break;
    default:
      return null;
  }

  bounds = new THREE.Box3().setFromCenterAndSize(center, size);

  return { bounds, center, size, area };
}

/**
 * 전체 벽면 바운딩 박스 계산
 */
export function getFullWallBounds(
  shipModel: THREE.Object3D
): { bounds: THREE.Box3; center: THREE.Vector3; size: THREE.Vector3; area: number } {
  const shipBox = getLocalBoundingBox(shipModel);
  const shipCenter = shipBox.getCenter(new THREE.Vector3());
  const shipSize = shipBox.getSize(new THREE.Vector3());

  // 선체 벽면 높이 (하단 40%)
  const hullHeight = shipSize.y * 0.4;
  const hullCenterY = shipBox.min.y + hullHeight / 2;

  const size = new THREE.Vector3(shipSize.x, hullHeight, shipSize.z);
  const center = new THREE.Vector3(shipCenter.x, hullCenterY, shipCenter.z);
  const bounds = new THREE.Box3().setFromCenterAndSize(center, size);

  // 4면 면적 합계
  const area = 2 * (shipSize.x * hullHeight) + 2 * (shipSize.z * hullHeight);

  return { bounds, center, size, area };
}
