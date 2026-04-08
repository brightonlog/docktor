import * as THREE from 'three';

/**
 * 모델의 크기를 기반으로 최적의 카메라 거리를 계산합니다.
 * @param model - 3D 모델 객체
 * @param fov - 카메라 시야각 (기본값: 50)
 * @param aspectRatio - 화면 비율 (기본값: 16/9)
 * @returns 카메라 오프셋 [x, y, z]
 */
export function calculateOptimalCameraDistance(
  model: THREE.Object3D,
  fov: number = 50,
  aspectRatio: number = 16 / 9
): [number, number, number] {
  // 모델의 바운딩 박스 계산
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  // 모델의 최대 치수 (대각선 길이)
  const maxDim = Math.max(size.x, size.y, size.z);
  const diagonal = Math.sqrt(size.x * size.x + size.y * size.y + size.z * size.z);

  // FOV를 라디안으로 변환
  const fovRad = (fov * Math.PI) / 180;

  // 모델이 화면에 꽉 차도록 하는 거리 계산
  // 여유 공간을 위해 3배 거리 사용 (선박 전체가 완전히 화면에 들어오도록)
  const distance = (diagonal / 2) / Math.tan(fovRad / 2) * 3.0;

  // 전면 대각선 뷰: 45도 각도로 배치
  // X와 Z는 같은 거리, Y는 약간 위에서 내려다보도록
  const angle = Math.PI / 4; // 45도
  const horizontalDistance = distance * Math.cos(angle);
  
  const cameraX = horizontalDistance;
  const cameraY = distance * 0.4; // 높이는 거리의 40%
  const cameraZ = horizontalDistance;

  return [cameraX, cameraY, cameraZ];
}

/**
 * 모델의 전면이 카메라를 향하도록 최적의 회전을 계산합니다.
 * @param model - 3D 모델 객체
 * @returns 회전 각도 { x, y, z } (라디안)
 */
export function calculateOptimalRotation(
  model: THREE.Object3D
): { x: number; y: number; z: number } {
  // 모델의 바운딩 박스를 이용해 방향 판단
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());

  // 가장 긴 축을 선박의 길이 방향으로 가정
  let rotationY = 0;

  if (size.x > size.z) {
    // X축이 더 길면, Z축 방향으로 회전 (전면이 대각선을 향하도록)
    rotationY = Math.PI / 4; // 45도
  } else {
    // Z축이 더 길면, 그대로 또는 약간 회전
    rotationY = -Math.PI / 4; // -45도
  }

  return {
    x: Math.PI, // 상하 반전 (일반적인 GLB 모델 관례)
    y: rotationY,
    z: Math.PI, // 앞뒤 반전
  };
}

/**
 * 프리셋을 사용하되, 모델 크기에 맞게 카메라 거리만 조정합니다.
 * @param model - 3D 모델 객체
 * @param baseOffset - 기본 카메라 오프셋
 * @param fov - 카메라 시야각
 * @returns 조정된 카메라 오프셋 [x, y, z]
 */
export function adjustCameraOffsetForModel(
  model: THREE.Object3D,
  baseOffset: [number, number, number],
  fov: number = 50
): [number, number, number] {
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const diagonal = Math.sqrt(size.x * size.x + size.y * size.y + size.z * size.z);

  // 기준 대각선 길이 (컨테이너선 기준)
  const referenceDiagonal = 10;

  // 스케일 팩터 계산
  const scaleFactor = diagonal / referenceDiagonal;

  // 기본 오프셋에 스케일 팩터를 적용하되, 최소/최대 범위 제한
  const minScale = 0.5;
  const maxScale = 3.0;
  const clampedScale = Math.max(minScale, Math.min(maxScale, scaleFactor));

  return [
    baseOffset[0] * clampedScale,
    baseOffset[1] * clampedScale,
    baseOffset[2] * clampedScale,
  ];
}
