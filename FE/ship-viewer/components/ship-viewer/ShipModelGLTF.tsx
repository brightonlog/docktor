'use client';

import { useRef, useEffect, Suspense } from 'react';
import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { ShipModelGLTFProps } from './types';

function ShipModelGLTF({
  modelPath = '/models/ship.glb',
  rotate = false,
  scale = 1,
  position = [0, 0, 0],
  rotationX = 0,
  rotationY = 0,
  rotationZ = 0,
  onLoaded,
}: ShipModelGLTFProps) {
  const groupRef = useRef<THREE.Group>(null);
  const { scene } = useGLTF(modelPath);

  useEffect(() => {
    if (scene && groupRef.current) {
      // 기존 children 제거
      while (groupRef.current.children.length > 0) {
        groupRef.current.remove(groupRef.current.children[0]);
      }

      // scene 클론 - Blender에서 설정한 위치 그대로 사용
      const clonedScene = scene.clone();

      // 그룹에 추가 (위치/스케일/회전 보정 없음)
      groupRef.current.add(clonedScene);

      if (onLoaded) {
        onLoaded(clonedScene);
      }
    }
  }, [scene, onLoaded]);

  useFrame(() => {
    if (rotate && groupRef.current) {
      groupRef.current.rotation.y += 0.005;
    }
  });

  if (!scene) return null;

  return (
    <group
      ref={groupRef}
      scale={scale}
      position={position}
      rotation={[rotationX, rotationY, rotationZ]}
    />
  );
}

// 로딩 폴백 컴포넌트
function LoadingBox() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.01;
      meshRef.current.rotation.x += 0.005;
    }
  });

  return (
    <mesh ref={meshRef} position={[0, 0, 0]}>
      <boxGeometry args={[3, 2, 5]} />
      <meshStandardMaterial color="#4a90e2" wireframe />
    </mesh>
  );
}

// Suspense 래퍼
export default function ShipModelWithSuspense(props: ShipModelGLTFProps) {
  return (
    <Suspense fallback={<LoadingBox />}>
      <ShipModelGLTF {...props} />
    </Suspense>
  );
}
