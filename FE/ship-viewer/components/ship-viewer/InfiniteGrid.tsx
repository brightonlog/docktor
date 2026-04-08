'use client';

import { useRef, useMemo } from 'react';
import { extend, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// 무한 그리드 쉐이더
const InfiniteGridShader = {
  vertexShader: `
    varying vec3 worldPosition;
    uniform float uDistance;

    void main() {
      vec3 pos = position.xzy * uDistance;
      pos.xz += cameraPosition.xz;

      worldPosition = pos;

      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying vec3 worldPosition;

    uniform float uSize1;
    uniform float uSize2;
    uniform vec3 uColor;
    uniform float uDistance;

    float getGrid(float size) {
      vec2 r = worldPosition.xz / size;

      vec2 grid = abs(fract(r - 0.5) - 0.5) / fwidth(r);
      float line = min(grid.x, grid.y);

      return 1.0 - min(line, 1.0);
    }

    void main() {
      float d = 1.0 - min(distance(cameraPosition.xz, worldPosition.xz) / uDistance, 1.0);

      float g1 = getGrid(uSize1);
      float g2 = getGrid(uSize2);

      vec3 color = uColor;
      float opacity = mix(g2, g1, g1) * d;

      gl_FragColor = vec4(color, opacity);
      gl_FragColor.a = mix(0.15 * gl_FragColor.a, gl_FragColor.a, g2);

      if (gl_FragColor.a <= 0.0) discard;
    }
  `,
};

interface InfiniteGridProps {
  size1?: number;
  size2?: number;
  color?: THREE.Color | string;
  distance?: number;
  position?: [number, number, number];
}

export default function InfiniteGrid({
  size1 = 1,
  size2 = 10,
  color = new THREE.Color('#00d9ff'),
  distance = 8000,
  position = [0, 0, 0],
}: InfiniteGridProps) {
  const meshRef = useRef<THREE.Mesh>(null);

  const uniforms = useMemo(
    () => ({
      uSize1: { value: size1 },
      uSize2: { value: size2 },
      uColor: { value: typeof color === 'string' ? new THREE.Color(color) : color },
      uDistance: { value: distance },
    }),
    [size1, size2, color, distance]
  );

  return (
    <group position={position}>
      {/* 무한 그리드 - XZ 평면 (바닥) */}
      <mesh ref={meshRef} position={[0, 0, 0]}>
        <planeGeometry args={[2, 2, 1, 1]} />
        <shaderMaterial
          vertexShader={InfiniteGridShader.vertexShader}
          fragmentShader={InfiniteGridShader.fragmentShader}
          uniforms={uniforms}
          transparent
          extensions={{
            derivatives: true,
          }}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>

      {/* X축 (빨강) - 바닥에 표시 */}
      <line position={[0, 0.001, 0]}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([-100, 0, 0, 100, 0, 0])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#ff3653" linewidth={2} />
      </line>

      {/* Z축 (초록) - 바닥에 표시 */}
      <line position={[0, 0.001, 0]}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([0, 0, -100, 0, 0, 100])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#8ccf4d" linewidth={2} />
      </line>
    </group>
  );
}
