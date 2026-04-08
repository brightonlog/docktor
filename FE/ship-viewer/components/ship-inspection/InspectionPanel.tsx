'use client';

import { ReactNode, useMemo, useState } from 'react';
import {
    ChevronLeft,
    ChevronRight,
    Settings,
    AlertCircle,
    Calendar,
    MapPin,
    CheckCircle2,
    FileText,
    Download,
    X,
    Square,
    CheckSquare,
    Loader2 // 로딩 아이콘
} from 'lucide-react';
import { format } from "date-fns";
import { toast } from "sonner";
import { useAuthStore } from "@/stores";
import { generateInspectionReport } from "@/lib/api/inspect";

import InspectionAccordion from './InspectionAccordion';
import ShipDetailAccordion from './ShipDetailAccordion';
import InspectionHistoryList from './InspectionHistoryList';

import type { SelectedArea, InspectionState, WallDirection, WallSection } from '@/lib/inspection-types';
import type { Inspect, Defect } from "@/lib/types/inspect-type";
import { Ship } from "@/lib/types/ship-types";

interface InspectionPanelProps {
    isOpen: boolean;
    onToggle: () => void;
    panelMode?: 'default' | 'inspection';
    shipInfo: Ship;
    inspectionHistories?: Inspect[];
    selectedHistoryId?: number | null;
    onSelectHistory?: (id: number) => void;
    selectedInspect?: Inspect | null;
    defects?: Defect[];
    onBackToHistory?: () => void;
    onDefectClick?: (id: number) => void;
    selectedArea: SelectedArea | null;
    selectedAreas?: SelectedArea[];
    onSelectWall: (wall: WallDirection | 'full', section: WallSection) => void;
    isSelectingCustom: boolean;
    inspectionState: InspectionState;
    onStartInspection: () => void;
    onStopInspection: () => void;
    showPositionSettings?: boolean;
    onTogglePositionSettings?: () => void;
    positionSettingsComponent?: ReactNode;
    isFirstLoad?: boolean;

    isCameraOpen: boolean;
    onToggleCamera: () => void;
}

export default function InspectionPanel({
                                            isOpen,
                                            onToggle,
                                            panelMode = 'default',
                                            shipInfo,
                                            inspectionHistories = [],
                                            selectedHistoryId = null,
                                            onSelectHistory,
                                            selectedInspect = null,
                                            defects = [],
                                            onBackToHistory = () => {},
                                            onDefectClick = () => {},
                                            selectedArea,
                                            selectedAreas,
                                            onSelectWall,
                                            isSelectingCustom,
                                            inspectionState,
                                            onStartInspection,
                                            onStopInspection,
                                            showPositionSettings,
                                            onTogglePositionSettings,
                                            positionSettingsComponent,
                                            isFirstLoad = true,
                                            isCameraOpen,
                                            onToggleCamera,
                                        }: InspectionPanelProps) {

    // 리포트 모드 상태
    const [isReportMode, setIsReportMode] = useState(false);
    const [selectedReportDefects, setSelectedReportDefects] = useState<Set<number>>(new Set());

    // [상태] 다운로드 로딩 상태
    const [isDownloading, setIsDownloading] = useState(false);

    const { accessToken } = useAuthStore();

    const processedDefects = useMemo(() => {
        const counts: Record<number, number> = {};
        return defects.map(d => {
            const catId = d.categoryId ?? 0;
            const order = (counts[catId] || 0) + 1;
            counts[catId] = order;
            return { ...d, _localOrder: order };
        });
    }, [defects]);

    // ✨ [추가] 전체 선택 여부 확인
    const isAllSelected = processedDefects.length > 0 && selectedReportDefects.size === processedDefects.length;

    // ✨ [추가] 전체 선택 핸들러
    const handleSelectAll = () => {
        if (isAllSelected) {
            // 이미 모두 선택된 상태면 -> 전체 해제
            setSelectedReportDefects(new Set());
        } else {
            // 아니면 -> 전체 선택
            const allIds = processedDefects.map(d => d.defectId);
            setSelectedReportDefects(new Set(allIds));
        }
    };

    const toggleReportMode = () => {
        if (isReportMode) {
            setSelectedReportDefects(new Set());
            setIsReportMode(false);
        } else {
            setIsReportMode(true);
        }
    };

    const handleToggleDefectSelect = (e: React.MouseEvent, defectId: number) => {
        e.stopPropagation();
        const newSet = new Set(selectedReportDefects);
        if (newSet.has(defectId)) {
            newSet.delete(defectId);
        } else {
            newSet.add(defectId);
        }
        setSelectedReportDefects(newSet);
    };

    const handleGenerateReport = async () => {
        if (selectedReportDefects.size === 0) {
            toast.error("리포트에 포함할 결함을 1개 이상 선택해주세요.");
            return;
        }
        if (!selectedInspect || !accessToken) return;

        // 로딩 시작
        setIsDownloading(true);

        try {
            const selectedDefectList = defects.filter(d => selectedReportDefects.has(d.defectId));
            const requestData = {
                ship: shipInfo as any,
                inspection: selectedInspect,
                defects: selectedDefectList
            };

            const blob = await generateInspectionReport(accessToken, requestData);
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Inspection_Report_${selectedInspect.inspectId}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);

            toast.dismiss();
            toast.success("다운로드가 완료되었습니다.");
            toggleReportMode();

        } catch (error) {
            console.error(error);
            toast.dismiss();
            toast.error("리포트 다운로드 실패");
        } finally {
            // 로딩 종료
            setIsDownloading(false);
        }
    };

    const customStyles = {
        textPrimary: { color: 'var(--inspection-text-primary)' },
        textSecondary: { color: 'var(--inspection-text-secondary)' },
        accentNavy: { color: 'var(--inspection-accent-navy)' },
        accentRed: { color: 'var(--inspection-accent-red)' },
        accentAmber: { color: 'var(--inspection-accent-amber)' },
        border: { borderColor: 'var(--inspection-border-color)' },
        bgSecondary: { backgroundColor: 'var(--inspection-bg-secondary)' },
        bgTertiary: { backgroundColor: 'var(--inspection-bg-tertiary)' },
    };

    return (
        <>
            <style>{`
                .custom-scrollbar::-webkit-scrollbar {
                    display: none;
                }
                .custom-scrollbar {
                    -ms-overflow-style: none;
                    scrollbar-width: none;
                }
            `}</style>

            <button
                className={`panel-toggle ${isOpen ? 'open' : ''}`}
                onClick={onToggle}
            >
                {isOpen ? <ChevronLeft size={24} /> : <ChevronRight size={24} />}
            </button>

            <div className={`inspection-panel ${!isOpen ? 'collapsed' : ''}`}>
                <div className="inspection-panel-content h-full flex flex-col p-0">

                    {panelMode === 'default' ? (
                        <>
                            {selectedInspect ? (
                                <div className="flex flex-col h-full animate-in fade-in slide-in-from-right-4 duration-300">
                                    <div
                                        className="sticky top-0 z-10"
                                        style={{
                                            borderBottom: '1px solid var(--inspection-border-color)',
                                            backgroundColor: 'var(--inspection-bg-secondary)'
                                        }}
                                    >
                                        <button
                                            onClick={onBackToHistory}
                                            className="w-full flex items-center justify-start text-sm p-2 rounded transition-all hover:bg-[rgba(48,74,122,0.05)]"
                                            style={{ color: 'var(--inspection-accent-navy)', fontWeight: 500 }}
                                        >
                                            <ChevronLeft className="mr-2 h-4 w-4" />
                                            목록으로 돌아가기
                                        </button>
                                    </div>

                                    <div className="flex-1 overflow-y-auto custom-scrollbar space-y-6">
                                        <div className="p-4 space-y-6">
                                            {/* 요약 카드 */}
                                            <div className="info-card space-y-3 shadow-sm">
                                                <div className="flex items-center" style={customStyles.textPrimary}>
                                                    <Calendar className="w-4 h-4 mr-2" style={customStyles.accentNavy} />
                                                    <span className="text-sm font-medium">
                                                        {format(new Date(selectedInspect.startTime), "yyyy년 MM월 dd일 HH:mm")}
                                                    </span>
                                                </div>
                                                <div className="flex items-center" style={customStyles.textPrimary}>
                                                    <MapPin className="w-4 h-4 mr-2" style={customStyles.accentNavy} />
                                                    <span className="text-sm">
                                                        검사 구역: <span className="font-semibold" style={customStyles.accentNavy}>{selectedInspect.sectionKRName}</span>
                                                    </span>
                                                </div>
                                                <hr style={{ borderTop: '1px solid var(--inspection-border-color)' }} />
                                                <div className="flex justify-between items-center">
                                                    <span className="text-sm" style={customStyles.textSecondary}>발견된 결함</span>
                                                    <span
                                                        className="text-xs px-2.5 py-1 rounded-full font-medium"
                                                        style={{
                                                            backgroundColor: defects.length > 0 ? 'rgba(229, 57, 53, 0.1)' : 'var(--inspection-bg-tertiary)',
                                                            color: defects.length > 0 ? 'var(--inspection-accent-red)' : 'var(--inspection-text-secondary)',
                                                            border: `1px solid ${defects.length > 0 ? 'var(--inspection-accent-red)' : 'var(--inspection-border-color)'}`
                                                        }}
                                                    >
                                                        {defects.length} 건
                                                    </span>
                                                </div>
                                            </div>

                                            {/* 결함 목록 헤더 + 버튼 */}
                                            <div className="space-y-3">
                                                <div className="flex items-center justify-between mb-3">
                                                    <h3 className="section-title" style={{ fontSize: '16px', marginBottom: '0' }}>
                                                        결함 목록
                                                    </h3>
                                                    <div>
                                                        {!isReportMode ? (
                                                            <button
                                                                onClick={toggleReportMode}
                                                                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded border transition-colors hover:bg-slate-100"
                                                                style={{
                                                                    color: 'var(--inspection-text-secondary)',
                                                                    borderColor: 'var(--inspection-border-color)',
                                                                    backgroundColor: 'var(--inspection-bg-primary)'
                                                                }}
                                                            >
                                                                <FileText size={14} />
                                                                <span>문서 다운로드</span>
                                                            </button>
                                                        ) : (
                                                            <div className="flex items-center gap-2">
                                                                {/* ✨ [추가] 전체 선택 버튼 */}
                                                                <button
                                                                    onClick={handleSelectAll}
                                                                    className="flex items-center gap-1 p-1.5 rounded hover:bg-slate-200 transition-colors"
                                                                    style={{ color: 'var(--inspection-text-secondary)' }}
                                                                    title={isAllSelected ? "전체 해제" : "전체 선택"}
                                                                >
                                                                    {isAllSelected ? (
                                                                        <CheckSquare size={18} style={{ color: 'var(--inspection-accent-navy)' }} />
                                                                    ) : (
                                                                        <Square size={18} />
                                                                    )}
                                                                    <span className="text-xs font-medium">전체</span>
                                                                </button>

                                                                {/* 구분선 */}
                                                                <div className="h-4 w-[1px] bg-gray-300 mx-1"></div>

                                                                {/* 취소(X) 버튼 */}
                                                                <button
                                                                    onClick={toggleReportMode}
                                                                    disabled={isDownloading}
                                                                    className="p-1.5 rounded hover:bg-slate-200 transition-colors disabled:opacity-50"
                                                                    style={{ color: 'var(--inspection-text-secondary)' }}
                                                                    title="취소"
                                                                >
                                                                    <X size={18} />
                                                                </button>

                                                                {/* 요청 버튼 */}
                                                                <button
                                                                    onClick={handleGenerateReport}
                                                                    disabled={isDownloading}
                                                                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white rounded shadow-sm transition-transform ${
                                                                        isDownloading ? 'opacity-70 cursor-wait' : 'active:scale-95'
                                                                    }`}
                                                                    style={{ backgroundColor: 'var(--inspection-accent-navy)' }}
                                                                >
                                                                    <Download size={14} />
                                                                    <span>요청 ({selectedReportDefects.size})</span>
                                                                </button>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>

                                                {processedDefects.length === 0 ? (
                                                    <div
                                                        className="text-center py-10 rounded-lg border"
                                                        style={{
                                                            backgroundColor: 'var(--inspection-bg-tertiary)',
                                                            borderColor: 'var(--inspection-border-color)',
                                                            color: 'var(--inspection-text-secondary)'
                                                        }}
                                                    >
                                                        <CheckCircle2 className="w-10 h-10 mx-auto mb-3 opacity-50" style={{ color: 'var(--inspection-accent-green)' }} />
                                                        <p className="text-sm">발견된 결함이 없습니다.</p>
                                                    </div>
                                                ) : (
                                                    <div className="grid gap-3">
                                                        {processedDefects.map((defect) => {
                                                            const isSelected = selectedReportDefects.has(defect.defectId);

                                                            return (
                                                                <div
                                                                    key={defect.defectId}
                                                                    onClick={() => isReportMode ? handleToggleDefectSelect({ stopPropagation: () => {} } as any, defect.defectId) : onDefectClick(defect.defectId)}
                                                                    className={`group relative flex items-center p-3 rounded-lg border cursor-pointer transition-all hover:shadow-sm ${
                                                                        isReportMode && isSelected ? 'ring-1 ring-offset-0' : ''
                                                                    }`}
                                                                    style={{
                                                                        backgroundColor: isReportMode && isSelected ? 'rgba(48, 74, 122, 0.05)' : 'var(--inspection-bg-tertiary)',
                                                                        borderColor: isReportMode && isSelected ? 'var(--inspection-accent-navy)' : 'var(--inspection-border-color)',
                                                                    }}
                                                                >
                                                                    {isReportMode && (
                                                                        <div
                                                                            className="mr-3 cursor-pointer p-1 -ml-1"
                                                                            onClick={(e) => handleToggleDefectSelect(e, defect.defectId)}
                                                                        >
                                                                            {isSelected ? (
                                                                                <CheckSquare size={20} style={{ color: 'var(--inspection-accent-navy)' }} />
                                                                            ) : (
                                                                                <Square size={20} style={{ color: 'var(--inspection-text-secondary)' }} />
                                                                            )}
                                                                        </div>
                                                                    )}

                                                                    <div
                                                                        className="p-2.5 rounded-full mr-3 shrink-0 flex items-center justify-center"
                                                                        style={{
                                                                            backgroundColor: (defect.categoryId === 10) ? 'rgba(255, 167, 38, 0.1)' : 'rgba(229, 57, 53, 0.1)',
                                                                            color: (defect.categoryId === 10) ? 'var(--inspection-accent-amber)' : 'var(--inspection-accent-red)'
                                                                        }}
                                                                    >
                                                                        <AlertCircle className="w-5 h-5" />
                                                                    </div>
                                                                    <div className="flex-1 min-w-0">
                                                                        <div className="flex justify-between items-start">
                                                                            <p className="text-sm font-medium truncate pr-2 transition-colors group-hover:text-[var(--inspection-accent-navy)]" style={customStyles.textPrimary}>
                                                                                {defect.categoryNameKr || defect.categoryName || '결함'} #{defect._localOrder}
                                                                            </p>
                                                                        </div>
                                                                        <div className="flex items-center gap-2 mt-1">
                                                                            {defect.categoryId !== 10 && (
                                                                                <span className="text-xs" style={customStyles.textSecondary}>
                                                                                    신뢰도: {(defect.confidence * 100).toFixed(1)}%
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                    <ChevronRight className="w-4 h-4 transition-colors group-hover:text-[var(--inspection-accent-navy)]" style={customStyles.textSecondary} />
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-4">
                                    <ShipDetailAccordion shipInfo={shipInfo} />
                                    <div className="px-4 pb-4">
                                        <InspectionHistoryList
                                            histories={inspectionHistories}
                                            selectedHistoryId={selectedHistoryId}
                                            onSelectHistory={onSelectHistory || (() => {})}
                                        />
                                    </div>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="flex-1 overflow-y-auto custom-scrollbar">
                            {isFirstLoad && onTogglePositionSettings && (
                                <div className="p-4 pb-0">
                                    <button
                                        className={`w-full flex items-center justify-center gap-2 p-3 rounded-lg border transition-colors ${
                                            showPositionSettings
                                                ? 'bg-[rgba(48,74,122,0.1)] border-[var(--inspection-accent-navy)] text-[var(--inspection-accent-navy)]'
                                                : 'inspection-btn'
                                        }`}
                                        onClick={onTogglePositionSettings}
                                    >
                                        <Settings size={18} />
                                        <span className="text-sm font-medium">선박 위치 설정 {showPositionSettings ? '닫기' : '열기'}</span>
                                    </button>
                                </div>
                            )}

                            {isFirstLoad && positionSettingsComponent}

                            <div className="p-4">
                                <InspectionAccordion
                                    shipInfo={shipInfo}
                                    selectedArea={selectedArea}
                                    selectedAreas={selectedAreas}
                                    onSelectWall={onSelectWall}
                                    isSelectingCustom={isSelectingCustom}
                                    isInspecting={inspectionState.isInspecting}
                                    progress={inspectionState.progress}
                                    onStartInspection={onStartInspection}
                                    onStopInspection={onStopInspection}
                                    isCameraOpen={isCameraOpen}
                                    onToggleCamera={onToggleCamera}
                                />
                            </div>

                            {!isFirstLoad && onTogglePositionSettings && (
                                <div className="mt-auto border-t p-4" style={{ borderColor: 'var(--inspection-border-color)' }}>
                                    {positionSettingsComponent}
                                    <div className="flex justify-end mt-2">
                                        <button
                                            onClick={onTogglePositionSettings}
                                            className="p-2 rounded transition-colors hover:bg-[rgba(48,74,122,0.1)]"
                                            style={{ color: 'var(--inspection-text-secondary)' }}
                                            title="카메라 위치 재설정"
                                        >
                                            <Settings size={20} />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* 전체 화면 로딩 오버레이 */}
            {isDownloading && (
                <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="flex flex-col items-center gap-4 p-8 rounded-2xl bg-[#1e2739] border border-[#304a7a] shadow-2xl">
                        <Loader2 className="w-16 h-16 text-cyan-400 animate-spin" />
                        <div className="flex flex-col items-center gap-1">
                            <div className="text-xl font-bold text-white">리포트 생성 및 다운로드 중...</div>
                            <div className="text-sm text-gray-400">잠시만 기다려주세요. 파일을 준비하고 있습니다.</div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}