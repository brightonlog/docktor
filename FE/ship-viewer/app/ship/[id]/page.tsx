"use client"

import {Suspense, useCallback, useEffect, useRef, useState} from "react"
import {useParams} from "next/navigation"
import {Canvas, useFrame, useThree} from "@react-three/fiber"
import {Billboard, Environment, OrbitControls, PerspectiveCamera, Sky, useTexture} from "@react-three/drei"
import * as THREE from "three"
import {AlertTriangle, ShipIcon} from "lucide-react"
import {toast} from "sonner"

import {DEFAULT_CAMERA_FOV, DEFAULT_CAMERA_OFFSET, InfiniteGrid, Ocean, ShipModelGLTF} from "@/components/ship-viewer"
import {DefectModal, InspectionHeader, InspectionPanel} from "@/components/ship-inspection"
import type {SelectedArea, WallDirection, WallSection} from "@/lib/inspection-types"
import {DEFAULT_INSPECTION_STATE, getAreaName} from "@/lib/inspection-types"
import {getFullWallBounds, getWallSectionBounds} from "@/lib/wall-detector"
import {useShipStore, useViewerStore} from "@/stores"
import {useShipDetail} from "@/hooks/use-ship-detail"
import {Defect, Inspect} from "@/lib/types/inspect-type"
import {Ship} from "@/lib/types/ship-types"
import { useRobotInspection } from "@/hooks/use-robot-inspect"

// ----------------------------------------------------------------------
// 1. Configuration & Helper Functions
// ----------------------------------------------------------------------

const HULL_FILES: Record<string, Record<string, string>> = {
    '1': {
        'full_ship': '/models/outer_hull_fishing_ship.glb',
        'left_bow': '/models/fishing_ship_saved_front_left.glb',
        'left_stern': '/models/fishing_ship_front_stern.glb',
        'right_bow': '/models/fishing_ship_back_bow.glb',
        'right_stern': '/models/fishing_ship_back_stern.glb',
    }, '2': {
        'left_bow': '/models/container_ship_front_bow.glb',
        'left_stern': '/models/container_ship_front_stern.glb',
        'right_bow': '/models/container_ship_back_bow.glb',
        'right_stern': '/models/container_ship_back_stern.glb',
    }
}

const IMAGE_CONFIG = { width: 180, height: 85 }

function calculateRealMarkerPosition(defect: { xcord: number, ycord: number }, hullModel: THREE.Object3D | null, sectionName: string): [number, number, number] {
    if (!hullModel || !sectionName) return [0, 0, 0];
    const targetPart = hullModel.getObjectByName(sectionName);
    if (!targetPart) return [0, 0, 0];

    const bounds = new THREE.Box3().setFromObject(targetPart);
    const size = bounds.getSize(new THREE.Vector3());
    const min = bounds.min;
    const max = bounds.max;
    const WALL_HEIGHT_RATIO = 0.3;

    const ratioX = defect.xcord / IMAGE_CONFIG.width;
    const ratioY = defect.ycord / IMAGE_CONFIG.height;

    const effectiveHeight = size.y * WALL_HEIGHT_RATIO;
    const targetY = min.y + (effectiveHeight * ratioY);

    let targetZ = 0;
    if (sectionName.includes('bow')) {
        targetZ = max.z - (size.z * ratioX);
    } else {
        targetZ = min.z + (size.z * ratioX);
    }

    const raycaster = new THREE.Raycaster();
    const rayOrigin = new THREE.Vector3();
    const rayDirection = new THREE.Vector3();
    const DISTANCE_OFFSET = 2.0;

    if (sectionName.includes('left')) {
        rayOrigin.set(min.x - DISTANCE_OFFSET, targetY, targetZ);
        rayDirection.set(1, 0, 0);
    } else if (sectionName.includes('right')) {
        rayOrigin.set(max.x + DISTANCE_OFFSET, targetY, targetZ);
        rayDirection.set(-1, 0, 0);
    } else {
        return [bounds.getCenter(new THREE.Vector3()).x, targetY, targetZ];
    }

    raycaster.set(rayOrigin, rayDirection);
    const intersects = raycaster.intersectObject(targetPart, true);

    if (intersects.length > 0) {
        const point = intersects[0].point;
        const OFFSET = 0.05;
        if (sectionName.includes('left')) return [point.x - OFFSET, point.y, point.z];
        else return [point.x + OFFSET, point.y, point.z];
    }
    if (sectionName.includes('left')) return [min.x, targetY, targetZ];
    return [max.x, targetY, targetZ];
}

interface DefectMarkerProps {
    defect: Defect
    isSelected: boolean
    onClick: () => void
    visible: boolean
    position: [number, number, number]
}

function DefectMarker({defect, isSelected, onClick, visible, position}: DefectMarkerProps) {
    const markerRef = useRef<THREE.Mesh>(null)
    const imageUrl = ((defect as any).category_id === 10 || defect.categoryId === 10) ? '/images/question_mark.png' : '/images/caution_mark.png';
    const texture = useTexture(imageUrl);

    useFrame((state) => {
        if (markerRef.current && visible) {
            const pulse = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.1
            const scaleBase = isSelected ? 1.3 : 0.8
            const scale = scaleBase * pulse
            markerRef.current.scale.setScalar(scale)
        }
    })

    if (!visible) return null
    return (<group position={position}>
        <Billboard follow={true} lockX={false} lockY={false} lockZ={false}>
            <mesh ref={markerRef} onClick={onClick}>
                <planeGeometry args={[1, 1]}/>
                <meshBasicMaterial map={texture} transparent={true} toneMapped={false} side={THREE.DoubleSide} depthTest={false} />
            </mesh>
        </Billboard>
        {isSelected && (<mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
            <ringGeometry args={[0.4, 0.5, 32]}/>
            <meshBasicMaterial color="#ffffff" transparent opacity={0.6} side={THREE.DoubleSide}/>
        </mesh>)}
    </group>)
}

// ----------------------------------------------------------------------
// 2. Ship Scene Component
// ----------------------------------------------------------------------

function ShipScene({
                       ship,
                       modelPath,
                       defects,
                       selectedDefectId,
                       onDefectClick,
                       showDefects,
                       showGrid,
                       showOcean,
                       showAxes,
                       selectedArea,
                       onShipModelLoaded,
                       isSelectingCustom,
                       onCustomAreaSelected,
                       panelMode,
                       gridYPosition,
                       hullModel,
                       currentSectionName,
                   }: {
    ship: Ship
    shipId: string
    modelPath: string
    defects: Defect[]
    selectedDefectId: number | null
    onDefectClick: (id: number | null) => void
    showDefects: boolean
    showGrid: boolean
    showOcean: boolean
    showAxes: boolean
    selectedArea: SelectedArea | null
    markerArea: SelectedArea | null
    onShipModelLoaded: (model: THREE.Object3D) => void
    isSelectingCustom: boolean
    onCustomAreaSelected: (bounds: THREE.Box3, area: number) => void
    panelMode: 'default' | 'inspection'
    gridYPosition: number
    hullModel: THREE.Object3D | null
    currentSectionName: string | null
}) {
    const [shipModel, setShipModel] = useState<THREE.Object3D | null>(null)

    const handleModelLoaded = useCallback((scene: THREE.Group) => {
        setShipModel(scene)
        onShipModelLoaded(scene)
    }, [onShipModelLoaded])

    const getOverlayModelPath = (): string | null => {
        if (!selectedArea || selectedArea.wall === 'custom') return null;
        const {wall, section} = selectedArea;
        if (ship.modelFileUrl.includes('fishing_ship_saved')) {
            if (wall == 'full') return '/models/outer_hull_fishing_ship.glb';
            else if (wall === 'left') return section === 'bow' ? '/models/fishing_ship_saved_front_left.glb' : '/models/fishing_ship_front_stern.glb';
            else if (wall === 'right') return section === 'bow' ? '/models/fishing_ship_back_bow.glb' : '/models/fishing_ship_back_stern.glb';
        }
        if (ship.modelFileUrl.includes('container_ship')) {
            if (wall == 'full') return '/models/outer_hull_container_ship.glb';
            if ((wall === 'left' || wall === 'right') && (section === 'bow' || section === 'stern')) {
                const fileWall = wall === 'left' ? 'front' : 'back';
                return `/models/container_ship_${fileWall}_${section}.glb`;
            }
        }
        return null;
    };

    const overlayModelPath = getOverlayModelPath();

    const handleOverlayLoaded = useCallback((scene: THREE.Group) => {
        scene.traverse((child) => {
            if (child instanceof THREE.Mesh) {
                const highlightMaterial = new THREE.MeshStandardMaterial({
                    color: '#F86032',
                    transparent: true,
                    opacity: 0.5,
                    emissive: '#F86032',
                    emissiveIntensity: 0.8,
                    side: THREE.DoubleSide,
                });
                child.material = highlightMaterial;
            }
        });
    }, []);

    return (<group>
        {showGrid && (<gridHelper args={[20, 20, 0x00d9ff, 0x1e2739]} position={[0, -0.01, 0]}>
            <meshBasicMaterial attach="material" transparent opacity={0.3}/>
        </gridHelper>)}

        <group position={[0, 0, 0]}>
            <ShipModelGLTF modelPath={modelPath} rotate={false} scale={1} position={[0, 0, 0]} onLoaded={handleModelLoaded} />
            {overlayModelPath && panelMode === 'inspection' && (<ShipModelGLTF modelPath={overlayModelPath} rotate={false} scale={1} onLoaded={handleOverlayLoaded} />)}
            <group>
                {showDefects && defects.map((defect) => {
                    const position = calculateRealMarkerPosition(defect, hullModel, currentSectionName || 'left_bow');
                    return (<DefectMarker
                        key={defect.defectId}
                        defect={defect}
                        isSelected={selectedDefectId === defect.defectId}
                        onClick={() => onDefectClick(selectedDefectId === defect.defectId ? null : defect.defectId)}
                        visible={true}
                        position={position}
                    />)
                })}
            </group>
        </group>
        {showAxes && <axesHelper args={[10]} position={[0, 0, 0]}/>}
        {panelMode === 'inspection' && (
            <InfiniteGrid size1={1} size2={10} color="#404040" distance={100} position={[0, gridYPosition, 0]}/>)}
    </group>)
}

// ----------------------------------------------------------------------
// 3. Camera Controls & Helpers
// ----------------------------------------------------------------------

function CameraController({ resetTrigger, cameraOffset, zoomTarget }: { resetTrigger: number, cameraOffset: [number, number, number], zoomTarget?: [number, number, number] | null }) {
    const {camera} = useThree()
    const targetRef = useRef<[number, number, number] | null>(null)
    const isAnimating = useRef(false)
    useEffect(() => {
        if (!zoomTarget) {
            camera.position.set(cameraOffset[0], cameraOffset[1], cameraOffset[2])
            camera.lookAt(0, 0, 0)
        }
    }, [resetTrigger, camera, cameraOffset, zoomTarget])
    useEffect(() => {
        if (zoomTarget) {
            targetRef.current = zoomTarget
            isAnimating.current = true
        } else {
            targetRef.current = null
            isAnimating.current = false
        }
    }, [zoomTarget])
    useFrame(() => {
        if (isAnimating.current && targetRef.current) {
            const [tx, ty, tz] = targetRef.current
            const targetPos = new THREE.Vector3(tx + 3, ty + 2, tz + 4)
            camera.position.lerp(targetPos, 0.08)
            camera.lookAt(tx, ty, tz)
            if (camera.position.distanceTo(targetPos) < 0.1) isAnimating.current = false
        }
    })
    return null
}

function CameraRefProvider({onCameraReady}: { onCameraReady: (camera: THREE.Camera) => void }) {
    const {camera} = useThree()
    useEffect(() => {
        onCameraReady(camera)
    }, [camera, onCameraReady])
    return null
}

// ----------------------------------------------------------------------
// 4. Main Component
// ----------------------------------------------------------------------

function ShipDetailContent() {
    const params = useParams()
    const shipId = params.id as string

    const {
        ship, inspects, selectedInspect, setSelectedInspect, defects, selectedDefect, setSelectedDefect,
        isLoading, error, accessToken, corp
    } = useShipDetail()

    const setStoreSelectedDefect = useViewerStore((state) => state.setSelectedDefect)

    // Local State
    const [cameraResetTrigger, setCameraResetTrigger] = useState(0)
    const [defectModalOpen, setDefectModalOpen] = useState(false)
    const [zoomTarget, setZoomTarget] = useState<[number, number, number] | null>(null)
    const [isPanelOpen, setIsPanelOpen] = useState(true)
    const [panelMode, setPanelMode] = useState<'default' | 'inspection'>('default')
    const [selectedArea, setSelectedArea] = useState<SelectedArea | null>(null)
    const [isSelectingCustom, setIsSelectingCustom] = useState(false)
    const [showGrid, setShowGrid] = useState(false)
    const [showDefects, setShowDefects] = useState(false)
    const [showOcean, setShowOcean] = useState(true)
    const [showAxes, setShowAxes] = useState(false)

    // [추가] 카메라(Iframe) 표시 상태
    const [isCameraOpen, setIsCameraOpen] = useState(false);

    // Three.js Objects
    const [shipModel, setShipModel] = useState<THREE.Object3D | null>(null)
    const [hullModel, setHullModel] = useState<THREE.Object3D | null>(null)
    const [cameraRef, setCameraRef] = useState<THREE.Camera | null>(null)
    const [gridYPosition, setGridYPosition] = useState(0)

    const currentDefects = defects || []
    const selectedDefectId = selectedDefect?.defectId ?? null
    const currentSectionName = selectedInspect?.sectionName || null;

    // Hook
    const handleInspectionCompleteUI = useCallback((foundInspect: Inspect) => {
        setSelectedInspect(foundInspect);
        setPanelMode('default');
        setShowOcean(true);
        setShowAxes(false);
        if (foundInspect.defects && foundInspect.defects.length > 0) {
            setShowDefects(true);
        }
    }, [setSelectedInspect]);

    const {
        inspectionState,
        setInspectionState,
        startInspection,
        stopInspection
    } = useRobotInspection({
        shipId,
        accessToken,
        corpId: corp?.corpId || 1,
        selectedArea,
        onInspectionComplete: handleInspectionCompleteUI
    });

    // ----------------------------------------------------------------------
    // Side Effects & Handlers
    // ----------------------------------------------------------------------

    // [추가] 검사 종료 시 카메라 자동 끄기
    useEffect(() => {
        if (!inspectionState.isInspecting) {
            setIsCameraOpen(true);
        }
    }, [inspectionState.isInspecting]);

    useEffect(() => {
        console.log("페이지 진입: 상태 초기화");
        setSelectedInspect(null);
        setSelectedDefect(null);
        setStoreSelectedDefect(null);
        setShowDefects(false);
    }, [setSelectedInspect, setSelectedDefect, setStoreSelectedDefect]);

    useEffect(() => {
        if (selectedInspect && selectedInspect.defects.length > 0) {
            setShowDefects(true);
        }
    }, [selectedInspect]);

    useEffect(() => {
        if (inspectionState.isInspecting) {
            setShowAxes(false);
            setShowOcean(true);
        }
    }, [inspectionState.isInspecting]);

    const handleSelectHistory = useCallback(async (inspectId: number) => {
        const targetInspect = inspects.find(i => i.inspectId === inspectId)
        if (!targetInspect) return
        if (!hullModel) console.warn('외판 모델(Hull Model)이 아직 로드되지 않았습니다.')
        setSelectedInspect(targetInspect)
    }, [inspects, setSelectedInspect, hullModel])

    const handleBackToHistory = useCallback(() => {
        setSelectedInspect(null)
        setSelectedDefect(null)
        setStoreSelectedDefect(null)
        setZoomTarget(null)
        setCameraResetTrigger(prev => prev + 1)
        setShowDefects(false)
    }, [setSelectedInspect, setSelectedDefect, setStoreSelectedDefect])

    const handleDefectClick = useCallback((defect: Defect | null) => {
        if (defect) {
            setSelectedDefect(defect)
            const position = calculateRealMarkerPosition(defect, hullModel, currentSectionName || 'left_bow');
            setZoomTarget(position)
            setDefectModalOpen(true)
        } else {
            setSelectedDefect(null)
            setZoomTarget(null)
            setDefectModalOpen(false)
        }
    }, [setSelectedDefect, hullModel, currentSectionName])

    const handleDefectIdClick = useCallback((id: number | null) => {
        if (id !== null) {
            const target = currentDefects.find(d => d.defectId === id)
            handleDefectClick(target || null)
        } else {
            handleDefectClick(null)
        }
    }, [currentDefects, handleDefectClick])

    const handleCloseDefectModal = useCallback(() => {
        setDefectModalOpen(false)
        setSelectedDefect(null)
    }, [setSelectedDefect, setStoreSelectedDefect])

    const handleStartInspectionMode = useCallback(() => {
        setPanelMode('inspection')
        setSelectedInspect(null)
        setSelectedDefect(null)
        setShowDefects(false)
        setZoomTarget(null)
    }, [setSelectedInspect, setSelectedDefect])

    const handleBackToDefault = useCallback(() => {
        setPanelMode('default')
        if (inspectionState.progress === 0) {
            setSelectedArea(null)
            setIsSelectingCustom(false)
            setInspectionState(DEFAULT_INSPECTION_STATE)
            setShowDefects(false)
        }
        setShowOcean(true)
        setShowAxes(false)
    }, [inspectionState.progress, setInspectionState])

    const handleSelectWall = useCallback((wall: WallDirection | 'full', section: WallSection) => {
        if (!shipModel) return;
        let areaData = {bounds: new THREE.Box3(), center: new THREE.Vector3(), size: new THREE.Vector3(), area: 0};
        if (wall === 'full') {
            const res = getFullWallBounds(shipModel);
            if (res) areaData = res;
        } else {
            const res = getWallSectionBounds(shipModel, wall, section);
            if (res) areaData = res;
        }
        setSelectedArea({wall, section, ...areaData})
        setInspectionState(prev => ({...prev, isCalibrated: true}))
        setIsSelectingCustom(false)
        toast.success(`${getAreaName(wall, section)} 영역 선택됨`)
    }, [shipModel, setInspectionState])

    const handleCustomAreaSelected = useCallback((bounds: THREE.Box3, area: number) => {
        const center = bounds.getCenter(new THREE.Vector3())
        const size = bounds.getSize(new THREE.Vector3())
        setSelectedArea({wall: 'custom', section: 'custom', bounds, center, size, area})
        setIsSelectingCustom(false)
        toast.success(`커스텀 영역 선택됨`)
    }, [])


    const handleShipModelLoaded = useCallback((model: THREE.Object3D) => {
        setShipModel(model)
        const box = new THREE.Box3().setFromObject(model)
        setGridYPosition(box.min.y)
    }, [])

    useEffect(() => {
        const loadHullModel = async () => {
            // [수정] ship 데이터가 없으면 로드하지 않음
            if (!ship || !ship.modelFileUrl) return;

            // [수정] ID 대신 URL에 포함된 문자열로 fileMap 결정
            let fileMap: Record<string, string> | null = null;

            if (ship.modelFileUrl.includes('fishing_ship_saved')) {
                // 어선(Fishing Ship)인 경우
                fileMap = {
                    'full_ship': '/models/outer_hull_fishing_ship.glb',
                    'left_bow': '/models/fishing_ship_saved_front_left.glb',
                    'left_stern': '/models/fishing_ship_front_stern.glb',
                    'right_bow': '/models/fishing_ship_back_bow.glb',
                    'right_stern': '/models/fishing_ship_back_stern.glb',
                };
            } else if (ship.modelFileUrl.includes('container_ship')) {
                // 컨테이너선(Container Ship)인 경우
                fileMap = {
                    'full_ship': '/models/outer_hull_container_ship.glb',
                    'left_bow': '/models/container_ship_front_bow.glb',
                    'left_stern': '/models/container_ship_front_stern.glb',
                    'right_bow': '/models/container_ship_back_bow.glb',
                    'right_stern': '/models/container_ship_back_stern.glb',
                };
            }

            if (!fileMap) {
                console.warn(`[HullModel] 지원되지 않는 선박 모델 URL입니다: ${ship.modelFileUrl}`);
                return;
            }

            try {
                const {GLTFLoader} = await import('three/examples/jsm/loaders/GLTFLoader.js');
                const loader = new GLTFLoader();
                const combinedGroup = new THREE.Group();
                combinedGroup.name = "HullGroup";

                const loadPromises = Object.entries(fileMap).map(async ([sectionName, path]) => {
                    return new Promise<void>((resolve) => {
                        loader.load(path, (gltf) => {
                            gltf.scene.name = sectionName;
                            combinedGroup.add(gltf.scene);
                            resolve();
                        }, undefined, (err) => {
                            console.error(`[HullModel] Load Fail: ${sectionName}`, err);
                            resolve();
                        });
                    });
                });

                await Promise.all(loadPromises);

                if (combinedGroup.children.length > 0) {
                    setHullModel(combinedGroup);
                    console.log(`[HullModel] Loaded ${combinedGroup.children.length} sections based on URL check.`);
                }
            } catch (error) {
                console.error('[HullModel] Loader Error:', error);
            }
        }

        loadHullModel();
    }, [ship]); // [수정] 의존성 배열을 shipId에서 ship으로 변경

    if (isLoading) {
        return (<div className="h-screen w-screen flex items-center justify-center bg-gray-900">
            <div className="text-center text-white"><ShipIcon className="w-16 h-16 mx-auto animate-pulse mb-4 text-cyan-400"/><p>Loading Ship Data...</p></div>
        </div>)
    }

    if (error || !ship) {
        return (<div className="h-screen w-screen flex items-center justify-center bg-gray-900">
            <div className="text-center text-white"><AlertTriangle className="w-16 h-16 mx-auto mb-4 text-red-500"/><p>{error || 'Ship not found'}</p></div>
        </div>)
    }

    return (<div className="h-screen w-screen overflow-hidden relative" style={{background: 'var(--inspection-bg-primary)'}}>
        <InspectionHeader panelMode={panelMode} onStartInspection={handleStartInspectionMode} onBackToDefault={handleBackToDefault} />

        <div className="flex h-full" style={{marginTop: '0', height: '100vh', paddingTop: '0'}}>
            {/* Panel */}
            <InspectionPanel
                isOpen={isPanelOpen}
                onToggle={() => setIsPanelOpen(!isPanelOpen)}
                panelMode={panelMode}
                shipInfo={ship}
                inspectionHistories={inspects}
                selectedHistoryId={selectedInspect?.inspectId}
                onSelectHistory={handleSelectHistory}
                selectedArea={selectedArea}
                onSelectWall={handleSelectWall}
                isSelectingCustom={isSelectingCustom}
                inspectionState={inspectionState}
                onStartInspection={startInspection}
                onStopInspection={stopInspection}

                // [중요] 패널로 카메라 Props 전달
                isCameraOpen={isCameraOpen}
                onToggleCamera={() => setIsCameraOpen(prev => !prev)}

                selectedInspect={selectedInspect}
                defects={currentDefects}
                onBackToHistory={handleBackToHistory}
                onDefectClick={handleDefectIdClick}
            />

            {/* 3D Viewer */}
            <div className="flex-1 relative">
                {/* [수정] 로봇 카메라 위치를 오른쪽 상단(right: 20px)으로 변경 */}
                {inspectionState.isInspecting && isCameraOpen && (
                    <div
                        style={{
                            position: 'absolute',
                            top: '20px',
                            right: '20px', // [변경됨] Left -> Right
                            width: '640px',
                            height: '550px',
                            zIndex: 50,
                            backgroundColor: '#000',
                            borderRadius: '12px',
                            overflow: 'hidden',
                            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            display: 'flex',
                            flexDirection: 'column'
                        }}
                    >
                        <div style={{
                            padding: '8px 12px',
                            background: 'rgba(0,0,0,0.8)',
                            color: '#00d9ff',
                            fontSize: '12px',
                            fontWeight: 'bold',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                        }}>
                            <span>🔴 LIVE ROBOT FEED</span>
                            <button onClick={() => setIsCameraOpen(false)} style={{color: '#fff'}}>✕</button>
                        </div>
                        <iframe
                            // src="http://192.168.30.35:5004/"
                            src="http://192.168.0.11:5004/"
                            style={{
                                width: '100%',
                                height: '100%',
                                border: 'none',
                                background: '#1a1a1a'
                            }}
                            title="Robot Camera Feed"
                            allowFullScreen
                        />
                    </div>
                )}

                <div style={{ position: 'absolute', bottom: '20px', right: '20px', zIndex: 10, display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <button onClick={() => setShowOcean(!showOcean)} className={`border border-gray-500 text-white rounded-full hover:bg-black/90 transition-all flex items-center justify-center ${showOcean ? 'bg-black/80' : 'bg-black/40'}`} style={{width: '50px', height: '50px', fontSize: '20px'}}>🌊</button>
                    <button onClick={() => setShowAxes(!showAxes)} className={`border border-gray-500 text-white rounded-full hover:bg-black/90 transition-all flex items-center justify-center ${showAxes ? 'bg-black/80' : 'bg-black/40'}`} style={{width: '50px', height: '50px', fontSize: '20px'}}>📐</button>
                </div>

                <Canvas shadows gl={{antialias: true, alpha: false}}>
                    {panelMode === 'inspection' && <color attach="background" args={['#323232']}/>}
                    <CameraController resetTrigger={cameraResetTrigger} cameraOffset={DEFAULT_CAMERA_OFFSET} zoomTarget={zoomTarget} />
                    <CameraRefProvider onCameraReady={setCameraRef}/>
                    <PerspectiveCamera makeDefault position={DEFAULT_CAMERA_OFFSET} fov={DEFAULT_CAMERA_FOV}/>
                    <fog attach="fog" args={[panelMode === 'inspection' ? '#323232' : '#87CEEB', panelMode === 'inspection' ? 30 : 50, panelMode === 'inspection' ? 100 : 500]}/>
                    <ambientLight intensity={0.4} color="#ffffff"/>
                    <directionalLight position={[10, 15, 5]} intensity={0.8} color="#00d9ff" castShadow/>

                    <ShipScene
                        ship={ship}
                        shipId={String(ship.shipId)}
                        modelPath={ship.modelFileUrl || '/models/fishing_ship_saved.glb'}
                        defects={currentDefects}
                        selectedDefectId={selectedDefectId}
                        onDefectClick={handleDefectIdClick}
                        showDefects={showDefects}
                        showGrid={showGrid}
                        showOcean={showOcean}
                        showAxes={showAxes}
                        selectedArea={selectedArea}
                        markerArea={null}
                        onShipModelLoaded={handleShipModelLoaded}
                        isSelectingCustom={isSelectingCustom}
                        onCustomAreaSelected={handleCustomAreaSelected}
                        panelMode={panelMode}
                        gridYPosition={gridYPosition}
                        hullModel={hullModel}
                        currentSectionName={currentSectionName}
                    />

                    {panelMode === 'default' && showOcean && <Ocean speed={0.3} waveHeight={0.15}/>}
                    {panelMode === 'default' && (<Sky distance={450000} sunPosition={[100, 100, 50]}/>)}
                    <OrbitControls target={[0, 0, 0]} enablePan={!isSelectingCustom} enableZoom={!isSelectingCustom} enableRotate={!isSelectingCustom} minDistance={5} maxDistance={50}/>
                    <Environment preset="city" background={false}/>
                </Canvas>
            </div>
        </div>
        <DefectModal open={defectModalOpen} onClose={handleCloseDefectModal} defect={selectedDefect} sectionName={selectedInspect?.sectionKRName} inspectTime={selectedInspect?.startTime} />
    </div>)
}

export default function ShipDetailPage() {
    return (<Suspense fallback={<div className="text-white text-center p-20">Loading...</div>}>
        <ShipDetailContent/>
    </Suspense>)
}