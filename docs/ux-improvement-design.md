# 선박 검사 뷰어 UX 개선 설계

## 컴포넌트 구조

```tsx
// ===== 새로운 컴포넌트 구조 =====

<InspectionPanel>
  {/* 상단 Breadcrumb 네비게이션 */}
  <Breadcrumb
    items={breadcrumbItems}
    onNavigate={handleBreadcrumbClick}
  />

  {/* 헤더: 뒤로 가기 버튼 */}
  <PanelHeader>
    {panelMode !== 'list' && <BackButton onClick={handleBack} />}
    <Title />
  </PanelHeader>

  {/* 상태 기반 패널 콘텐츠 */}
  <PanelContent>
    {panelMode === 'list' && (
      <InspectionHistoryList
        histories={inspections}
        onSelectInspection={handleSelectInspection}
      />
    )}

    {panelMode === 'inspection' && (
      <InspectionDetailView
        inspection={selectedInspection}
        defects={defects}
        onSelectDefect={handleSelectDefect}
      />
    )}

    {panelMode === 'defect' && (
      <DefectDetailView
        defect={selectedDefect}
        onReportDefect={handleReport}
      />
    )}
  </PanelContent>
</InspectionPanel>
```

---

## 상태 관리 설계

### 1. 타입 정의

```tsx
// lib/types/panel-types.ts

export type PanelMode = 'list' | 'inspection' | 'defect';

export interface BreadcrumbItem {
  label: string;
  mode: PanelMode;
  inspectionId?: number;
  defectId?: string;
}

export interface PanelState {
  mode: PanelMode;
  selectedInspectionId: number | null;
  selectedDefectId: string | null;
  navigationHistory: PanelMode[]; // 뒤로 가기 스택
  breadcrumbs: BreadcrumbItem[]; // Breadcrumb 경로
}

export const INITIAL_PANEL_STATE: PanelState = {
  mode: 'list',
  selectedInspectionId: null,
  selectedDefectId: null,
  navigationHistory: ['list'],
  breadcrumbs: [{ label: '선박 상세 정보', mode: 'list' }],
};
```

### 2. 상태 관리 훅

```tsx
// hooks/use-panel-navigation.ts

import { useState, useCallback } from 'react';
import type { PanelState, PanelMode, BreadcrumbItem } from '@/lib/types/panel-types';

export function usePanelNavigation(
  initialState: PanelState,
  inspections: any[], // 검사 이력 데이터
  defects: any[] // 결함 데이터
) {
  const [state, setState] = useState<PanelState>(initialState);

  // 검사 이력 선택 → INSPECTION 모드
  const selectInspection = useCallback((inspectionId: number) => {
    const inspection = inspections.find(i => i.inspectId === inspectionId);
    const inspectionLabel = inspection?.startTime || `검사 #${inspectionId}`;

    setState(prev => ({
      mode: 'inspection',
      selectedInspectionId: inspectionId,
      selectedDefectId: null,
      navigationHistory: [...prev.navigationHistory, 'inspection'],
      breadcrumbs: [
        { label: '선박 상세 정보', mode: 'list' },
        { label: inspectionLabel, mode: 'inspection', inspectionId },
      ],
    }));
  }, [inspections]);

  // 결함 선택 → DEFECT 모드
  const selectDefect = useCallback((defectId: string) => {
    const defect = defects.find(d => d.id === defectId);
    const defectLabel = defect?.type || `결함 #${defectId}`;
    const inspection = inspections.find(i => i.inspectId === state.selectedInspectionId);
    const inspectionLabel = inspection?.startTime || `검사 #${state.selectedInspectionId}`;

    setState(prev => ({
      ...prev,
      mode: 'defect',
      selectedDefectId: defectId,
      navigationHistory: [...prev.navigationHistory, 'defect'],
      breadcrumbs: [
        { label: '선박 상세 정보', mode: 'list' },
        { label: inspectionLabel, mode: 'inspection', inspectionId: state.selectedInspectionId },
        { label: defectLabel, mode: 'defect', defectId },
      ],
    }));
  }, [defects, inspections, state.selectedInspectionId]);

  // 뒤로 가기
  const goBack = useCallback(() => {
    setState(prev => {
      const history = [...prev.navigationHistory];
      if (history.length <= 1) return prev; // 최소 상태 유지

      history.pop(); // 현재 상태 제거
      const previousMode = history[history.length - 1];

      // Breadcrumb도 함께 업데이트
      const newBreadcrumbs = [...prev.breadcrumbs];
      newBreadcrumbs.pop();

      return {
        ...prev,
        mode: previousMode,
        // 모드에 따라 선택 상태 초기화
        selectedDefectId: previousMode === 'list' ? null : prev.selectedDefectId,
        selectedInspectionId: previousMode === 'list' ? null : prev.selectedInspectionId,
        navigationHistory: history,
        breadcrumbs: newBreadcrumbs,
      };
    });
  }, []);

  // Breadcrumb 클릭으로 특정 모드로 이동
  const navigateTo = useCallback((targetItem: BreadcrumbItem) => {
    setState(prev => {
      // Breadcrumb에서 타겟 위치까지만 유지
      const targetIndex = prev.breadcrumbs.findIndex(
        item => item.mode === targetItem.mode &&
               item.inspectionId === targetItem.inspectionId &&
               item.defectId === targetItem.defectId
      );

      if (targetIndex === -1) return prev;

      const newBreadcrumbs = prev.breadcrumbs.slice(0, targetIndex + 1);
      const newHistory = prev.navigationHistory.slice(0, targetIndex + 1);

      return {
        ...prev,
        mode: targetItem.mode,
        selectedInspectionId: targetItem.inspectionId || null,
        selectedDefectId: targetItem.defectId || null,
        navigationHistory: newHistory,
        breadcrumbs: newBreadcrumbs,
      };
    });
  }, []);

  // 초기화 (리스트로 돌아가기)
  const reset = useCallback(() => {
    setState(initialState);
  }, [initialState]);

  return {
    state,
    selectInspection,
    selectDefect,
    goBack,
    navigateTo,
    reset,
    canGoBack: state.navigationHistory.length > 1,
  };
}
```

---

## 세부 컴포넌트 구현

### 1. Breadcrumb 네비게이션 컴포넌트 (새로운 컴포넌트)

```tsx
// components/ship-inspection/Breadcrumb.tsx

'use client';

import { ChevronRight } from 'lucide-react';
import type { BreadcrumbItem } from '@/lib/types/panel-types';

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  onNavigate: (item: BreadcrumbItem) => void;
}

export default function Breadcrumb({ items, onNavigate }: BreadcrumbProps) {
  return (
    <nav className="breadcrumb-nav" aria-label="Breadcrumb">
      <ol className="breadcrumb-list">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li key={`${item.mode}-${item.inspectionId}-${item.defectId}-${index}`} className="breadcrumb-item">
              {!isLast ? (
                <>
                  <button
                    className="breadcrumb-link"
                    onClick={() => onNavigate(item)}
                    type="button"
                  >
                    {item.label}
                  </button>
                  <ChevronRight className="breadcrumb-separator" size={14} />
                </>
              ) : (
                <span className="breadcrumb-current" aria-current="page">
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
```

### 2. InspectionDetailView (새로운 컴포넌트)

```tsx
// components/ship-inspection/InspectionDetailView.tsx

'use client';

import { Clock, MapPin, AlertTriangle } from 'lucide-react';
import type { Inspect } from '@/lib/types/inspect-type';
import type { DefectData } from '@/lib/types/defect-types';

interface InspectionDetailViewProps {
  inspection: Inspect;
  defects: DefectData[];
  onSelectDefect: (defectId: string) => void;
}

export default function InspectionDetailView({
  inspection,
  defects,
  onSelectDefect,
}: InspectionDetailViewProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return '#ff3366';
      case 'medium': return '#ffcc00';
      case 'low': return '#00ff88';
      default: return '#666';
    }
  };

  const severityCounts = defects.reduce((acc, d) => {
    acc[d.severity] = (acc[d.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="inspection-detail-view">
      {/* 검사 메타데이터 */}
      <section className="detail-section">
        <h3>검사 정보</h3>
        <div className="detail-grid">
          <div className="detail-item">
            <Clock size={16} />
            <span>검사 시간</span>
            <strong>{inspection.startTime}</strong>
          </div>
          <div className="detail-item">
            <MapPin size={16} />
            <span>검사 구역</span>
            <strong>Section {inspection.sectionId}</strong>
          </div>
          <div className="detail-item">
            <AlertTriangle size={16} />
            <span>검사 상태</span>
            <strong>{inspection.status}</strong>
          </div>
        </div>
      </section>

      {/* 결함 요약 */}
      <section className="detail-section">
        <h3>결함 요약</h3>
        <div className="severity-summary">
          {(['high', 'medium', 'low'] as const).map(severity => (
            <div
              key={severity}
              className="severity-card"
              style={{ borderColor: getSeverityColor(severity) }}
            >
              <div className="severity-count" style={{ color: getSeverityColor(severity) }}>
                {severityCounts[severity] || 0}
              </div>
              <div className="severity-label">
                {severity === 'high' ? '높음' : severity === 'medium' ? '보통' : '낮음'}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 결함 리스트 */}
      <section className="detail-section">
        <h3>탐지된 결함 ({defects.length})</h3>
        <div className="defect-list">
          {defects.map(defect => (
            <button
              key={defect.id}
              className="defect-card"
              onClick={() => onSelectDefect(defect.id)}
            >
              {defect.image && (
                <div className="defect-thumbnail">
                  <img src={defect.image} alt={defect.type} />
                </div>
              )}
              <div className="defect-info">
                <div className="defect-type">{defect.type}</div>
                <div className="defect-meta">
                  <span className="confidence">{(defect.confidence * 100).toFixed(1)}%</span>
                  <span
                    className="severity-badge"
                    style={{ backgroundColor: getSeverityColor(defect.severity) }}
                  >
                    {defect.severity}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
```

### 2. DefectDetailView (기존 DefectModal 대체)

```tsx
// components/ship-inspection/DefectDetailView.tsx

'use client';

import { MapPin, Percent, AlertCircle, FileText } from 'lucide-react';
import type { DefectData } from '@/lib/types/defect-types';

interface DefectDetailViewProps {
  defect: DefectData;
  onReportDefect?: (defectId: string) => void;
}

export default function DefectDetailView({
  defect,
  onReportDefect,
}: DefectDetailViewProps) {
  return (
    <div className="defect-detail-view">
      {/* 결함 이미지 */}
      {defect.image && (
        <div className="defect-image-container">
          <img src={defect.image} alt={defect.type} />
        </div>
      )}

      {/* 결함 기본 정보 */}
      <section className="detail-section">
        <h3>결함 정보</h3>
        <div className="detail-grid">
          <div className="detail-item">
            <AlertCircle size={16} />
            <span>유형</span>
            <strong>{defect.type}</strong>
          </div>
          <div className="detail-item">
            <Percent size={16} />
            <span>신뢰도</span>
            <strong>{(defect.confidence * 100).toFixed(1)}%</strong>
          </div>
          <div className="detail-item">
            <MapPin size={16} />
            <span>위치</span>
            <strong>
              ({defect.position[0].toFixed(2)}, {defect.position[1].toFixed(2)}, {defect.position[2].toFixed(2)})
            </strong>
          </div>
        </div>
      </section>

      {/* 결함 설명 */}
      {defect.description && (
        <section className="detail-section">
          <h3>상세 설명</h3>
          <p className="defect-description">{defect.description}</p>
        </section>
      )}

      {/* 액션 버튼 */}
      <section className="detail-actions">
        {onReportDefect && (
          <button
            className="inspection-btn inspection-btn-full"
            onClick={() => onReportDefect(defect.id)}
          >
            <FileText size={18} />
            보고서 생성
          </button>
        )}
      </section>
    </div>
  );
}
```

### 3. 통합된 InspectionPanel (수정)

```tsx
// components/ship-inspection/InspectionPanel.tsx

'use client';

import { ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react';
import { usePanelNavigation } from '@/hooks/use-panel-navigation';
import { INITIAL_PANEL_STATE } from '@/lib/types/panel-types';
import Breadcrumb from './Breadcrumb';
import InspectionHistoryList from './InspectionHistoryList';
import InspectionDetailView from './InspectionDetailView';
import DefectDetailView from './DefectDetailView';

export default function InspectionPanel({
  isOpen,
  onToggle,
  inspectionHistories,
  defects,
  onDefectSelect3D, // 3D 뷰 동기화용 콜백
}: InspectionPanelProps) {
  const {
    state,
    selectInspection,
    selectDefect,
    goBack,
    navigateTo,
    reset,
    canGoBack,
  } = usePanelNavigation(INITIAL_PANEL_STATE, inspectionHistories, defects);

  // 검사 선택 시: 3D 뷰에 마커 표시
  const handleSelectInspection = (inspectionId: number) => {
    selectInspection(inspectionId);
    onDefectSelect3D?.(null); // 카메라 리셋
  };

  // 결함 선택 시: 3D 뷰 카메라 이동
  const handleSelectDefect = (defectId: string) => {
    selectDefect(defectId);
    const defect = defects.find(d => d.id === defectId);
    if (defect) {
      onDefectSelect3D?.(defect); // 카메라 줌인
    }
  };

  // Breadcrumb 클릭 핸들러
  const handleBreadcrumbClick = (item: BreadcrumbItem) => {
    navigateTo(item);

    // 3D 뷰 동기화
    if (item.mode === 'list') {
      onDefectSelect3D?.(null); // 카메라 리셋, 마커 숨김
    } else if (item.mode === 'inspection') {
      onDefectSelect3D?.(null); // 카메라 리셋 (마커는 유지)
    }
    // defect 모드는 navigateTo에서 이미 처리됨
  };

  // 선택된 검사/결함 데이터 조회
  const selectedInspection = inspectionHistories.find(
    h => h.inspectId === state.selectedInspectionId
  );
  const selectedDefect = defects.find(d => d.id === state.selectedDefectId);

  return (
    <>
      <button className="panel-toggle" onClick={onToggle}>
        {isOpen ? <ChevronLeft size={24} /> : <ChevronRight size={24} />}
      </button>

      <div className={`inspection-panel ${!isOpen ? 'collapsed' : ''}`}>
        <div className="inspection-panel-content">
          {/* Breadcrumb 네비게이션 */}
          <Breadcrumb
            items={state.breadcrumbs}
            onNavigate={handleBreadcrumbClick}
          />

          {/* 헤더: 뒤로 가기 버튼 + 타이틀 */}
          <div className="panel-header">
            {canGoBack && (
              <button className="back-button" onClick={goBack}>
                <ArrowLeft size={20} />
                뒤로
              </button>
            )}
            <h2 className="panel-title">
              {state.mode === 'list' && '검사 이력'}
              {state.mode === 'inspection' && '검사 상세'}
              {state.mode === 'defect' && '결함 상세'}
            </h2>
          </div>

          {/* 패널 콘텐츠 - 상태 기반 렌더링 */}
          <div className="panel-body">
            {state.mode === 'list' && (
              <InspectionHistoryList
                histories={inspectionHistories}
                onSelectHistory={handleSelectInspection}
              />
            )}

            {state.mode === 'inspection' && selectedInspection && (
              <InspectionDetailView
                inspection={selectedInspection}
                defects={defects}
                onSelectDefect={handleSelectDefect}
              />
            )}

            {state.mode === 'defect' && selectedDefect && (
              <DefectDetailView defect={selectedDefect} />
            )}
          </div>
        </div>
      </div>
    </>
  );
}
```

---

## CSS 스타일 가이드

```css
/* styles/inspection-panel.css */

/* ===== Breadcrumb 네비게이션 ===== */
.breadcrumb-nav {
  padding: 12px 20px;
  background: var(--inspection-bg-secondary);
  border-bottom: 1px solid var(--inspection-border);
}

.breadcrumb-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.breadcrumb-link {
  display: inline-block;
  padding: 4px 8px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--inspection-accent-cyan);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.breadcrumb-link:hover {
  background: var(--inspection-bg-hover);
  text-decoration: underline;
}

.breadcrumb-link:active {
  transform: scale(0.98);
}

.breadcrumb-separator {
  color: var(--inspection-text-secondary);
  opacity: 0.5;
  flex-shrink: 0;
}

.breadcrumb-current {
  display: inline-block;
  padding: 4px 8px;
  color: var(--inspection-text-primary);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

/* ===== 패널 헤더 ===== */
.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--inspection-border);
}

.back-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--inspection-bg-tertiary);
  border: 1px solid var(--inspection-border);
  border-radius: 6px;
  color: var(--inspection-text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.back-button:hover {
  background: var(--inspection-bg-hover);
  border-color: var(--inspection-accent-cyan);
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--inspection-text-primary);
}

/* ===== InspectionDetailView ===== */
.inspection-detail-view {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--inspection-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.detail-grid {
  display: grid;
  gap: 12px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--inspection-bg-tertiary);
  border-radius: 6px;
}

.detail-item svg {
  color: var(--inspection-accent-cyan);
}

.detail-item span {
  flex: 1;
  color: var(--inspection-text-secondary);
  font-size: 13px;
}

.detail-item strong {
  color: var(--inspection-text-primary);
  font-size: 14px;
}

/* ===== 심각도 요약 카드 ===== */
.severity-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.severity-card {
  padding: 16px;
  background: var(--inspection-bg-tertiary);
  border-left: 4px solid;
  border-radius: 6px;
  text-align: center;
}

.severity-count {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 4px;
}

.severity-label {
  font-size: 12px;
  color: var(--inspection-text-secondary);
  text-transform: uppercase;
}

/* ===== 결함 리스트 ===== */
.defect-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.defect-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--inspection-bg-tertiary);
  border: 1px solid var(--inspection-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.defect-card:hover {
  background: var(--inspection-bg-hover);
  border-color: var(--inspection-accent-cyan);
  transform: translateX(4px);
}

.defect-thumbnail {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}

.defect-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.defect-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.defect-type {
  font-size: 14px;
  font-weight: 600;
  color: var(--inspection-text-primary);
}

.defect-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.confidence {
  color: var(--inspection-accent-green);
}

.severity-badge {
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

/* ===== DefectDetailView ===== */
.defect-detail-view {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.defect-image-container {
  width: 100%;
  aspect-ratio: 16/9;
  border-radius: 8px;
  overflow: hidden;
  background: var(--inspection-bg-tertiary);
}

.defect-image-container img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.defect-description {
  padding: 16px;
  background: var(--inspection-bg-tertiary);
  border-left: 3px solid var(--inspection-accent-cyan);
  border-radius: 6px;
  color: var(--inspection-text-primary);
  line-height: 1.6;
}

.detail-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
```

---

## 구현 시 주의할 UX 포인트

### 1. 뒤로 가기 동작

```tsx
// ❌ 잘못된 예: 상태만 초기화
const goBack = () => {
  setMode('list');
  // → 이전에 선택했던 검사/결함 ID를 기억하지 못함
};

// ✅ 올바른 예: 네비게이션 스택 유지
const goBack = () => {
  const history = [...navigationHistory];
  history.pop();
  const previousMode = history[history.length - 1];

  // 모드에 따라 적절한 상태만 유지
  if (previousMode === 'inspection') {
    setSelectedDefectId(null); // 결함 선택 해제
  }
  if (previousMode === 'list') {
    setSelectedInspectionId(null); // 검사 선택 해제
    setSelectedDefectId(null);
  }
};
```

### 2. 3D 뷰 동기화

```tsx
// 패널 상태 변경 시 3D 뷰 자동 업데이트
useEffect(() => {
  switch (state.mode) {
    case 'list':
      // 모든 마커 숨김, 카메라 리셋
      setShowDefects(false);
      setZoomTarget(null);
      break;

    case 'inspection':
      // 선택된 검사의 결함 마커만 표시
      setShowDefects(true);
      setCurrentDefects(/* 해당 검사의 결함 */);
      setZoomTarget(null); // 카메라는 리셋
      break;

    case 'defect':
      // 선택된 결함으로 카메라 줌인
      const defect = findDefect(state.selectedDefectId);
      setZoomTarget(defect.position);
      break;
  }
}, [state.mode, state.selectedInspectionId, state.selectedDefectId]);
```

### 3. 상태 초기화 타이밍

```tsx
// ❌ 잘못된 예: 검사 이력 해제 시 즉시 초기화
const handleClearHistory = () => {
  setMode('list');
  setCurrentDefects([]); // ← 애니메이션 전에 데이터가 사라짐
};

// ✅ 올바른 예: 애니메이션 후 초기화
const handleClearHistory = () => {
  setMode('list');

  // 패널 전환 애니메이션 후 초기화
  setTimeout(() => {
    setCurrentDefects([]);
    setSelectedDefect(null);
  }, 300); // CSS transition 시간과 일치
};
```

### 4. 로딩 상태 처리

```tsx
// 검사 선택 시 결함 데이터 로딩
const handleSelectInspection = async (inspectionId: number) => {
  selectInspection(inspectionId);

  // ❌ 로딩 중 빈 화면 표시
  // setCurrentDefects([]);

  // ✅ 이전 데이터 유지 + 로딩 스피너 표시
  setIsLoadingDefects(true);

  try {
    const defects = await fetchDefects(inspectionId);
    setCurrentDefects(defects);
  } finally {
    setIsLoadingDefects(false);
  }
};
```

### 5. Breadcrumb 네비게이션 동작

```tsx
// Breadcrumb 클릭 시 중간 단계로 이동하는 예시

// ❌ 잘못된 예: 단순 모드만 변경
const handleBreadcrumbClick = (item: BreadcrumbItem) => {
  setMode(item.mode);
  // → 선택된 검사/결함 ID가 유지되지 않음
};

// ✅ 올바른 예: 전체 상태 복원
const handleBreadcrumbClick = (item: BreadcrumbItem) => {
  // Breadcrumb 배열에서 타겟까지만 유지
  const targetIndex = breadcrumbs.findIndex(
    b => b.mode === item.mode &&
         b.inspectionId === item.inspectionId &&
         b.defectId === item.defectId
  );

  const newBreadcrumbs = breadcrumbs.slice(0, targetIndex + 1);

  setState({
    mode: item.mode,
    selectedInspectionId: item.inspectionId || null,
    selectedDefectId: item.defectId || null,
    breadcrumbs: newBreadcrumbs,
    navigationHistory: newBreadcrumbs.map(b => b.mode),
  });

  // 3D 뷰 동기화
  if (item.mode === 'list') {
    setShowDefects(false);
    setZoomTarget(null);
  } else if (item.mode === 'inspection') {
    setShowDefects(true);
    setZoomTarget(null);
  } else if (item.mode === 'defect' && item.defectId) {
    const defect = findDefect(item.defectId);
    setZoomTarget(defect.position);
  }
};
```

### 6. Breadcrumb 레이블 포맷팅

```tsx
// 검사 이력 날짜 포맷 (가독성 향상)
const formatInspectionLabel = (inspection: Inspect): string => {
  // "2025-01-15" → "01/15 검사"
  const date = new Date(inspection.startTime);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${month}/${day} 검사`;
};

// 결함 레이블 (타입 + 심각도)
const formatDefectLabel = (defect: DefectData): string => {
  // "부식" + "HIGH" → "부식 (높음)"
  const severityMap = {
    high: '높음',
    medium: '보통',
    low: '낮음',
  };
  return `${defect.type} (${severityMap[defect.severity]})`;
};

// usePanelNavigation에서 활용
const selectInspection = (inspectionId: number) => {
  const inspection = inspections.find(i => i.inspectId === inspectionId);
  const label = formatInspectionLabel(inspection);

  setState(prev => ({
    ...prev,
    breadcrumbs: [
      { label: '선박 상세 정보', mode: 'list' },
      { label, mode: 'inspection', inspectionId },
    ],
  }));
};
```

### 7. 최소 HUD 수준 우측 패널

우측 패널을 완전히 제거하는 대신, 최소한의 정보만 표시:

```tsx
// 우측 상단에 작은 통계 카드만 표시
{state.mode === 'inspection' && (
  <div className="inspection-hud">
    <div className="hud-stat">
      <AlertTriangle size={16} />
      <span>{defects.length} 결함</span>
    </div>
    <div className="hud-stat">
      <Clock size={16} />
      <span>{duration}</span>
    </div>
  </div>
)}

/* CSS */
.inspection-hud {
  position: absolute;
  top: 80px;
  right: 20px;
  display: flex;
  gap: 12px;
  z-index: 5;
}

.hud-stat {
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.7);
  border: 1px solid rgba(0, 217, 255, 0.3);
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--inspection-text-primary);
}
```

---

## Breadcrumb UX 주의사항

### 1. 긴 레이블 처리
```css
/* 레이블이 너무 길 경우 말줄임표 처리 */
.breadcrumb-link,
.breadcrumb-current {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 호버 시 전체 레이블 표시 (툴팁) */
.breadcrumb-link:hover::after {
  content: attr(title);
  position: absolute;
  top: 100%;
  left: 0;
  padding: 6px 10px;
  background: var(--inspection-bg-primary);
  border: 1px solid var(--inspection-border);
  border-radius: 4px;
  white-space: nowrap;
  z-index: 100;
}
```

### 2. 모바일 대응
```tsx
// 모바일에서는 현재 페이지 + 뒤로 가기만 표시
const isMobile = useMediaQuery('(max-width: 768px)');

{isMobile ? (
  // 간소화된 breadcrumb
  <div className="breadcrumb-mobile">
    {canGoBack && (
      <button onClick={goBack}>
        <ArrowLeft size={16} />
      </button>
    )}
    <span>{state.breadcrumbs[state.breadcrumbs.length - 1].label}</span>
  </div>
) : (
  // 전체 breadcrumb
  <Breadcrumb items={state.breadcrumbs} onNavigate={navigateTo} />
)}
```

### 3. 접근성 (a11y)
```tsx
// ARIA 속성 추가로 스크린 리더 지원
<nav className="breadcrumb-nav" aria-label="Breadcrumb">
  <ol className="breadcrumb-list">
    {items.map((item, index) => (
      <li key={index}>
        {!isLast ? (
          <button
            onClick={() => onNavigate(item)}
            aria-label={`${item.label}로 이동`}
          >
            {item.label}
          </button>
        ) : (
          <span aria-current="page">{item.label}</span>
        )}
      </li>
    ))}
  </ol>
</nav>
```

### 4. 키보드 내비게이션
```tsx
// 키보드 단축키로 breadcrumb 이동
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Alt + ← : 뒤로 가기
    if (e.altKey && e.key === 'ArrowLeft') {
      e.preventDefault();
      goBack();
    }

    // Alt + Home : 최상위로
    if (e.altKey && e.key === 'Home') {
      e.preventDefault();
      navigateTo(state.breadcrumbs[0]);
    }
  };

  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [goBack, navigateTo, state.breadcrumbs]);
```

---

## 마이그레이션 체크리스트

```
□ 새 타입 정의 추가 (panel-types.ts - BreadcrumbItem 포함)
□ usePanelNavigation 훅 구현 (breadcrumbs 상태 관리 포함)
□ Breadcrumb 컴포넌트 생성
□ InspectionDetailView 컴포넌트 생성
□ DefectDetailView 컴포넌트 생성
□ InspectionPanel 리팩토링 (Breadcrumb 통합)
□ Breadcrumb 클릭 핸들러 구현
□ 3D 뷰 동기화 로직 수정 (Breadcrumb 연동)
□ CSS 스타일 추가 (Breadcrumb 포함)
□ 기존 DefectCounter를 최소 HUD로 변경
□ 기존 DefectModal 제거
□ 레이블 포맷팅 유틸 함수 추가
□ 애니메이션 트랜지션 추가
□ 모바일 반응형 대응 (Breadcrumb 간소화)
□ 접근성 개선 (ARIA 속성)
□ 키보드 내비게이션 구현
```

---

## 최종 UX 플로우 예시

```
사용자 시나리오:
1. 검사 이력 리스트에서 "2025-01-15" 검사 선택
   → Breadcrumb: "선박 상세 정보 > 01/15 검사"
   → 3D 뷰: 해당 검사의 결함 마커 표시

2. 검사 상세 화면에서 "부식 (높음)" 결함 선택
   → Breadcrumb: "선박 상세 정보 > 01/15 검사 > 부식 (높음)"
   → 3D 뷰: 해당 결함으로 카메라 줌인

3. Breadcrumb에서 "01/15 검사" 클릭
   → 검사 상세 화면으로 즉시 이동
   → 3D 뷰: 카메라 리셋 (마커는 유지)

4. Breadcrumb에서 "선박 상세 정보" 클릭
   → 검사 이력 리스트로 즉시 이동
   → 3D 뷰: 모든 마커 숨김, 카메라 리셋

5. 뒤로 가기 버튼 또는 Alt+← 사용
   → 이전 화면으로 순차 이동
   → Breadcrumb와 3D 뷰 자동 동기화
```

