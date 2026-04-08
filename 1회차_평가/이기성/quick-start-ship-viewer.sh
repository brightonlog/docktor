#!/bin/bash

# Quick Start Script for Ship 3D Viewer

echo "================================"
echo "Ship 3D Viewer - Quick Setup"
echo "================================"

# Create React project
echo ""
echo "Creating React project..."
npx create-react-app ship-viewer

cd ship-viewer

# Install dependencies
echo ""
echo "Installing Three.js dependencies..."
npm install three @react-three/fiber @react-three/drei

# Create directories
mkdir -p src/components

# Create ShipModel component
cat > src/components/ShipModel.jsx << 'EOF'
import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Box, Cylinder, Cone } from '@react-three/drei';

function ShipModel({ rotate = true }) {
  const shipRef = useRef();

  useFrame(() => {
    if (rotate && shipRef.current) {
      shipRef.current.rotation.y += 0.005;
    }
  });

  return (
    <group ref={shipRef} position={[0, 0, 0]}>
      {/* Hull */}
      <Box args={[3, 0.8, 1.2]} position={[0, 0, 0]}>
        <meshStandardMaterial color="#4a5568" metalness={0.6} roughness={0.4} />
      </Box>

      {/* Bow */}
      <Cone args={[0.6, 1.5, 4]} position={[2.25, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
        <meshStandardMaterial color="#3a4556" metalness={0.6} roughness={0.4} />
      </Cone>

      {/* Deck */}
      <Box args={[2.8, 0.1, 1.15]} position={[0, 0.45, 0]}>
        <meshStandardMaterial color="#718096" metalness={0.3} roughness={0.7} />
      </Box>

      {/* Bridge */}
      <Box args={[0.8, 0.6, 0.9]} position={[-0.5, 0.85, 0]}>
        <meshStandardMaterial color="#e2e8f0" metalness={0.2} roughness={0.8} />
      </Box>

      {/* Windows */}
      <Box args={[0.82, 0.3, 0.92]} position={[-0.5, 0.95, 0]}>
        <meshStandardMaterial color="#63b3ed" transparent opacity={0.7} />
      </Box>

      {/* Funnel */}
      <Cylinder args={[0.15, 0.15, 0.5, 16]} position={[-0.8, 1.4, 0]}>
        <meshStandardMaterial color="#e53e3e" metalness={0.4} roughness={0.6} />
      </Cylinder>

      {/* Containers */}
      <Box args={[0.7, 0.5, 0.8]} position={[0.6, 0.75, 0]}>
        <meshStandardMaterial color="#f56565" metalness={0.3} roughness={0.7} />
      </Box>
      <Box args={[0.7, 0.5, 0.8]} position={[1.4, 0.75, 0]}>
        <meshStandardMaterial color="#48bb78" metalness={0.3} roughness={0.7} />
      </Box>

      {/* Rails */}
      <Box args={[3, 0.05, 0.05]} position={[0, 0.5, 0.6]}>
        <meshStandardMaterial color="#2d3748" />
      </Box>
      <Box args={[3, 0.05, 0.05]} position={[0, 0.5, -0.6]}>
        <meshStandardMaterial color="#2d3748" />
      </Box>
    </group>
  );
}

export default ShipModel;
EOF

# Create ShipViewer component
cat > src/components/ShipViewer.jsx << 'EOF'
import React, { useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, Grid } from '@react-three/drei';
import ShipModel from './ShipModel';

function ShipViewer() {
  const [autoRotate, setAutoRotate] = useState(true);

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#1a202c' }}>
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

      <Canvas shadows>
        <PerspectiveCamera makeDefault position={[5, 3, 5]} fov={60} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
        <pointLight position={[-10, 10, -10]} intensity={0.5} />

        <ShipModel rotate={autoRotate} />

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

        <Environment preset="sunset" />

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
EOF

# Update App.js
cat > src/App.js << 'EOF'
import React from 'react';
import ShipViewer from './components/ShipViewer';

function App() {
  return (
    <div className="App">
      <ShipViewer />
    </div>
  );
}

export default App;
EOF

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "To start the development server:"
echo "  cd ship-viewer"
echo "  npm start"
echo ""
echo "The ship 3D viewer will open in your browser at http://localhost:3000"
echo ""
