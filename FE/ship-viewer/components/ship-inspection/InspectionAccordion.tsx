'use client';

import { Camera, EyeOff, CheckCircle, CheckCircle2  } from 'lucide-react'; // [수정] 아이콘 추가
import type { SelectedArea, WallDirection, WallSection, ShipInfoData } from '@/lib/inspection-types';

interface InspectionAccordionProps {
    shipInfo: ShipInfoData;
    selectedArea: SelectedArea | null;
    selectedAreas?: SelectedArea[];
    onSelectWall: (wall: WallDirection | 'full', section: WallSection) => void;
    isSelectingCustom: boolean;
    isInspecting: boolean;
    progress: number;
    onStartInspection: () => void;
    onStopInspection: () => void;

    // [추가] 카메라 제어용 Props
    isCameraOpen: boolean;
    onToggleCamera: () => void;
}

export default function InspectionAccordion({
                                                shipInfo,
                                                selectedArea,
                                                onSelectWall,
                                                isInspecting,
                                                isSelectingCustom,
                                                progress,
                                                onStartInspection,
                                                onStopInspection,
                                                // [추가] Props 구조 분해
                                                isCameraOpen,
                                                onToggleCamera,
                                            }: InspectionAccordionProps) {


    const isActive = (wall: WallDirection | 'full', section: WallSection) => {
        if (!selectedArea) return false;
        return selectedArea.wall === wall && selectedArea.section === section;
    };

    return (
        <div className="inspection-accordion" style={{ padding: 0, background: 'transparent', height: '100%', display: 'flex', flexDirection: 'column' }}>

            {/* 1. 선박명 영역 (고정) */}
            <div style={{ textAlign: 'center', margin: '24px 0 20px', paddingTop: '20px', paddingBottom: '0px' }}>
                <div style={{ fontSize: '12px', color: 'var(--inspection-text-secondary)', marginBottom: '6px' }}>
                    선박명
                </div>
                <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--inspection-text-primary)' }}>
                    {shipInfo.name}
                </div>
            </div>

            {/* 2. 검사 벽면 선택 영역 (가변 높이 - 남은 공간 차지) */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '0 10px' }}>

                {/* 섹션 헤더 */}
                <div className="accordion-header" style={{ marginBottom: '16px', paddingLeft: '4px', paddingTop: '70px' }}>
                    <div className="step-indicator">
                        {selectedArea ? (
                            <CheckCircle2 size={18} className="step-complete" style={{ color: 'var(--inspection-accent-green)' }} />
                        ) : (
                            <CheckCircle size={18} style={{ color: 'var(--inspection-text-secondary)' }} />
                        )}
                    </div>
                    <span className="step-title">검사 벽면 선택</span>
                </div>

                {/* 버튼 그룹들 */}
                <div className="accordion-content-inner" style={{ padding: 0 }}>
                    <div className="btn-group">
                        <button
                            className={`inspection-btn inspection-btn-full ${isActive('full', 'ship') ? 'active' : ''}`}
                            onClick={() => onSelectWall('full', 'ship')}
                        >
                            전체 벽면
                        </button>
                    </div>

                    <div className="wall-label" style={{ marginTop: '24px' }}>좌측 벽면 (Left)</div>
                    <div className="btn-group btn-group-2">
                        <button
                            className={`inspection-btn inspection-btn-small ${isActive('left', 'bow') ? 'active' : ''}`}
                            onClick={() => onSelectWall('left', 'bow')}
                        >
                            선수 (Bow)
                        </button>
                        <button
                            className={`inspection-btn inspection-btn-small ${isActive('left', 'stern') ? 'active' : ''}`}
                            onClick={() => onSelectWall('left', 'stern')}
                        >
                            선미 (Stern)
                        </button>
                    </div>

                    <div className="wall-label" style={{ marginTop: '24px' }}>우측 벽면 (Right)</div>
                    <div className="btn-group btn-group-2">
                        <button
                            className={`inspection-btn inspection-btn-small ${isActive('right', 'bow') ? 'active' : ''}`}
                            onClick={() => onSelectWall('right', 'bow')}
                        >
                            선수 (Bow)
                        </button>
                        <button
                            className={`inspection-btn inspection-btn-small ${isActive('right', 'stern') ? 'active' : ''}`}
                            onClick={() => onSelectWall('right', 'stern')}
                        >
                            선미 (Stern)
                        </button>
                    </div>
                </div>
            </div>

            {/* 3. 하단 버튼 영역 (고정) */}
            <div style={{
                padding: '20px 10px 20px',
                background: 'var(--inspection-bg-secondary)',
                marginTop: 'auto',
                display: 'flex',        // [수정] 버튼 세로 배치를 위해 flex 추가
                flexDirection: 'column', // [수정] 세로 방향
                gap: '10px'             // [수정] 버튼 사이 간격
            }}>
                {!isInspecting ? (
                    <button
                        className="inspection-btn inspection-btn-full inspection-btn-start"
                        onClick={onStartInspection}
                        style={{
                            height: '64px',
                            fontSize: '18px',
                            fontWeight: '700',
                            borderRadius: '12px',
                            width: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 4px 14px rgba(48, 74, 122, 0.4)', // 그림자 강조 (파란색)
                            marginTop: 0,
                        }}
                    >
                        검사 시작
                    </button>
                ) : (
                    <>
                        <button
                            className="inspection-btn inspection-btn-full inspection-btn-danger"
                            onClick={onStopInspection}
                            style={{
                                height: '64px',
                                fontSize: '18px',
                                fontWeight: '700',
                                borderRadius: '12px',
                                width: '100%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                marginTop: 0,
                            }}
                        >
                            검사 중지 ({progress}%)
                        </button>

                        {/* [추가] 검사 화면 보기 토글 버튼 */}
                        <button
                            className="inspection-btn"
                            onClick={onToggleCamera}
                            style={{
                                height: '48px',
                                fontSize: '15px',
                                fontWeight: '600',
                                borderRadius: '10px',
                                width: '100%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                background: isCameraOpen ? '#3b82f6' : '#334155', // 켜짐: 파랑, 꺼짐: 회색
                                color: 'white',
                                border: '1px solid rgba(255,255,255,0.1)',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            {isCameraOpen ? <EyeOff size={18} /> : <Camera size={18} />}
                            {isCameraOpen ? '검사 화면 닫기' : '검사 화면 보기'}
                        </button>
                    </>
                )}
            </div>

        </div>
    );
}