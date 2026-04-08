'use client';

import { useRef, useMemo } from 'react';
import { useFrame, extend, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { Water } from 'three/examples/jsm/objects/Water.js';
import { OceanProps } from './types';

extend({ Water });

declare global {
  namespace JSX {
    interface IntrinsicElements {
      water: React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        ref?: React.Ref<Water>;
        args?: [THREE.BufferGeometry, object];
        'rotation-x'?: number;
        position?: [number, number, number];
      };
    }
  }
}

interface ExtendedOceanProps extends OceanProps {
  waterLevel?: number;
}

export default function Ocean({ speed = 0.3, waveHeight = 0.15, waterLevel = -0.5 }: ExtendedOceanProps) {
  const waterRef = useRef<Water>(null);
  const { gl } = useThree();

  const waterGeometry = useMemo(
    () => new THREE.CircleGeometry(1000, 128),
    []
  );

  const waterNormals = useMemo(() => {
    const loader = new THREE.TextureLoader();
    const texture = loader.load(
      'https://threejs.org/examples/textures/waternormals.jpg',
      (texture) => {
        texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
      }
    );
    return texture;
  }, []);

  const waterOptions = useMemo(
    () => ({
      textureWidth: 512,
      textureHeight: 512,
      waterNormals: waterNormals,
      sunDirection: new THREE.Vector3(100, 100, 50).normalize(),
      sunColor: 0xffffff,
      waterColor: 0x1e5799,
      distortionScale: waveHeight * 15,
      fog: true,
      format:
        gl.outputColorSpace === THREE.SRGBColorSpace
          ? THREE.SRGBColorSpace
          : THREE.LinearSRGBColorSpace,
    }),
    [waterNormals, waveHeight, gl.outputColorSpace]
  );

  useFrame(({ clock }) => {
    if (waterRef.current && waterRef.current.material) {
      (waterRef.current.material as THREE.ShaderMaterial).uniforms.time.value =
        clock.getElapsedTime() * speed;
    }
  });

  return (
    <water
      ref={waterRef}
      args={[waterGeometry, waterOptions]}
      rotation-x={-Math.PI / 2}
      position={[0, waterLevel, 0]}
    />
  );
}
