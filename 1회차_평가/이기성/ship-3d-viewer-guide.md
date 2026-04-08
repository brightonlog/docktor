# React + Three.js 선박 3D 모형 뷰어 가이드

## 1. 설치

```bash
# React 프로젝트가 이미 있다면
npm install three @react-three/fiber @react-three/drei

# 새 프로젝트 생성부터 시작한다면
npx create-react-app ship-viewer
cd ship-viewer
npm install three @react-three/fiber @react-three/drei
```

## 2. 기본 선박 모형 컴포넌트

### `src/components/ShipModel.jsx`

```jsx
import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Box, Cylinder, Cone } from '@react-three/drei';

function ShipModel({ rotate = true }) {
  const shipRef = useRef();

  // 자동 회전 (옵션)
  useFrame(() => {
    if (rotate && shipRef.current) {
      shipRef.current.rotation.y += 0.005;
    }
  });

  return (
    <group ref={shipRef} position={[0, 0, 0]}>
      {/* 선체 (Hull) - 메인 바디 */}
      <Box args={[3, 0.8, 1.2]} position={[0, 0, 0]}>
        <meshStandardMaterial color="#4a5568" metalness={0.6} roughness={0.4} />
      </Box>

      {/* 선수 (Bow) - 앞쪽 뾰족한 부분 */}
      <Cone
        args={[0.6, 1.5, 4]}
        position={[2.25, 0, 0]}
        rotation={[0, 0, Math.PI / 2]}
      >
        <meshStandardMaterial color="#3a4556" metalness={0.6} roughness={0.4} />
      </Cone>

      {/* 갑판 (Deck) */}
      <Box args={[2.8, 0.1, 1.15]} position={[0, 0.45, 0]}>
        <meshStandardMaterial color="#718096" metalness={0.3} roughness={0.7} />
      </Box>

      {/* 선교 (Bridge/Wheelhouse) */}
      <Box args={[0.8, 0.6, 0.9]} position={[-0.5, 0.85, 0]}>
        <meshStandardMaterial color="#e2e8f0" metalness={0.2} roughness={0.8} />
      </Box>

      {/* 선교 창문 */}
      <Box args={[0.82, 0.3, 0.92]} position={[-0.5, 0.95, 0]}>
        <meshStandardMaterial color="#63b3ed" transparent opacity={0.7} />
      </Box>

      {/* 굴뚝 (Funnel/Smokestack) */}
      <Cylinder args={[0.15, 0.15, 0.5, 16]} position={[-0.8, 1.4, 0]}>
        <meshStandardMaterial color="#e53e3e" metalness={0.4} roughness={0.6} />
      </Cylinder>

      {/* 컨테이너/화물칸 1 */}
      <Box args={[0.7, 0.5, 0.8]} position={[0.6, 0.75, 0]}>
        <meshStandardMaterial color="#f56565" metalness={0.3} roughness={0.7} />
      </Box>

      {/* 컨테이너/화물칸 2 */}
      <Box args={[0.7, 0.5, 0.8]} position={[1.4, 0.75, 0]}>
        <meshStandardMaterial color="#48bb78" metalness={0.3} roughness={0.7} />
      </Box>

      {/* 갑판 레일 (좌측) */}
      <Box args={[3, 0.05, 0.05]} position={[0, 0.5, 0.6]}>
        <meshStandardMaterial color="#2d3748" />
      </Box>

      {/* 갑판 레일 (우측) */}
      <Box args={[3, 0.05, 0.05]} position={[0, 0.5, -0.6]}>
        <meshStandardMaterial color="#2d3748" />
      </Box>
    </group>
  );
}

export default ShipModel;
```

## 3. 메인 3D 뷰어 컴포넌트

### `src/components/ShipViewer.jsx`

```jsx
import React, { useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, Grid } from '@react-three/drei';
import ShipModel from './ShipModel';

function ShipViewer() {
  const [autoRotate, setAutoRotate] = useState(true);

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#1a202c' }}>
      {/* 컨트롤 패널 */}
      <div style={{
        position: 'absolute',
        top: 20,
        left: 20,
        zIndex: 10,
        background: 'rgba(255, 255, 255, 0.9)',
        padding: '15px',
        borderRadius: '8px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>Ship 3D Viewer</h2>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={autoRotate}
            onChange={(e) => setAutoRotate(e.target.checked)}
            style={{ marginRight: '8px' }}
          />
          Auto Rotate
        </label>
      </div>

      {/* 3D Canvas */}
      <Canvas shadows>
        {/* 카메라 */}
        <PerspectiveCamera makeDefault position={[5, 3, 5]} fov={60} />

        {/* 조명 */}
        <ambientLight intensity={0.5} />
        <directionalLight
          position={[10, 10, 5]}
          intensity={1}
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
        />
        <pointLight position={[-10, 10, -10]} intensity={0.5} />

        {/* 선박 모델 */}
        <ShipModel rotate={autoRotate} />

        {/* 바다/그리드 */}
        <Grid
          args={[20, 20]}
          position={[0, -0.5, 0]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#3182ce"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#2b6cb0"
          fadeDistance={25}
          fadeStrength={1}
        />

        {/* 환경 맵 (반사효과) */}
        <Environment preset="sunset" />

        {/* 마우스로 회전/줌 컨트롤 */}
        <OrbitControls
          enablePan={true}
          enableZoom={true}
          enableRotate={true}
          minDistance={3}
          maxDistance={20}
        />
      </Canvas>
    </div>
  );
}

export default ShipViewer;
```

## 4. App.js에 적용

### `src/App.js`

```jsx
import React from 'react';
import ShipViewer from './components/ShipViewer';
import './App.css';

function App() {
  return (
    <div className="App">
      <ShipViewer />
    </div>
  );
}

export default App;
```

## 5. 실행

```bash
npm start
```

## 6. 고급 기능 추가

### 6.1 외부 3D 모델 파일 로드 (GLB/GLTF)

실제 선박 3D 모델 파일을 로드하려면:

```jsx
import { useGLTF } from '@react-three/drei';

function ShipModelFromFile() {
  const { scene } = useGLTF('/models/ship.glb');

  return (
    <primitive
      object={scene}
      scale={0.5}
      position={[0, 0, 0]}
    />
  );
}

// 모델 프리로드
useGLTF.preload('/models/ship.glb');
```

### 6.2 애니메이션 추가 (물결 효과)

```jsx
function Ocean() {
  const meshRef = useRef();

  useFrame(({ clock }) => {
    if (meshRef.current) {
      meshRef.current.position.y = Math.sin(clock.getElapsedTime()) * 0.1;
    }
  });

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
      <planeGeometry args={[50, 50, 32, 32]} />
      <meshStandardMaterial
        color="#0077be"
        transparent
        opacity={0.6}
        metalness={0.8}
        roughness={0.2}
      />
    </mesh>
  );
}
```

### 6.3 불량 부위 하이라이트 표시

```jsx
function DefectMarker({ position, type }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.1, 16, 16]} />
      <meshStandardMaterial
        color={type === 'crack' ? 'red' : 'yellow'}
        emissive={type === 'crack' ? 'red' : 'yellow'}
        emissiveIntensity={0.5}
      />
    </mesh>
  );
}

// 사용 예시
<DefectMarker position={[1, 0.5, 0.5]} type="crack" />
<DefectMarker position={[-0.5, 0.8, 0.3]} type="peeling" />
```

## 7. 프로젝트 구조

```
ship-viewer/
├── public/
│   └── models/              # 3D 모델 파일 (옵션)
│       └── ship.glb
├── src/
│   ├── components/
│   │   ├── ShipModel.jsx    # 선박 3D 모델
│   │   ├── ShipViewer.jsx   # 메인 뷰어
│   │   └── DefectMarkers.jsx # 불량 마커 (옵션)
│   ├── App.js
│   └── index.js
└── package.json
```

## 8. 유용한 팁

### 성능 최적화
- `useMemo`로 복잡한 geometry 캐싱
- `instancedMesh`로 동일한 객체 여러개 렌더링
- LOD (Level of Detail) 사용

### 컨트롤
- 마우스 드래그: 회전
- 마우스 휠: 줌인/아웃
- 우클릭 드래그: 이동

### 추천 무료 3D 모델 사이트
- [Sketchfab](https://sketchfab.com/) - 무료 선박 모델
- [Free3D](https://free3d.com/)
- [CGTrader](https://www.cgtrader.com/free-3d-models)

## 9. 데이터와 연동

불량 감지 데이터를 3D 뷰어와 연동:

```jsx
function ShipWithDefects({ defects }) {
  return (
    <group>
      <ShipModel />
      {defects.map((defect, idx) => (
        <DefectMarker
          key={idx}
          position={defect.position}
          type={defect.type}
        />
      ))}
    </group>
  );
}

// 사용
const defectData = [
  { position: [1, 0.5, 0.5], type: 'crack' },
  { position: [-0.5, 0.8, 0.3], type: 'peeling' }
];

<ShipWithDefects defects={defectData} />
```

## 10. 다음 단계

1. 실제 선박 3D 모델 파일 (.glb) 구하기
2. 불량 감지 AI 결과와 3D 좌표 매핑
3. 클릭 시 불량 정보 표시 (Tooltip)
4. 카메라 프리셋 (Top view, Side view, etc.)
5. 스크린샷 캡처 기능
