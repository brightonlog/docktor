'use client';

import { ClipboardList, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { format } from 'date-fns';
import {Inspect} from "@/lib/types/inspect-type";



interface InspectionHistoryListProps {
  histories: Inspect[];
  selectedHistoryId: number | null;
  onSelectHistory: (id: number) => void;
}

export default function InspectionHistoryList({
  histories,
  selectedHistoryId,
  onSelectHistory,
}: InspectionHistoryListProps) {
  const getStatusColor = (status: string) => {
    if (status === 'completed') return 'var(--inspection-accent-green)';
    if (status === 'in_progress') return 'var(--inspection-accent-yellow)';
    if (status === 'failed') return '#ff3366';
    return 'var(--inspection-text-secondary)';
  };

  return (
    <div className="inspection-history-list">
      {/* 섹션 헤더 */}
      <div className="history-list-header">
        <ClipboardList size={18} style={{ color: 'var(--inspection-accent-cyan)' }} />
        <span>검사 이력</span>
      </div>

      {/* 리스트 */}
      <div className="history-list-container">
        {histories.length === 0 ? (
          <div className="history-empty">검사 이력이 없습니다</div>
        ) : (
          histories.map((history) => (
            <button
              key={history.inspectId}
              className={`history-list-item ${selectedHistoryId === history.inspectId ? 'selected' : ''}`}
              onClick={() => onSelectHistory(history.inspectId)}
            >
              <div className="history-item-left">
                <div className="history-date">
                  {history.startTime ? format(new Date(history.startTime), 'yyyy-MM-dd') : '-'}
                </div>
                <div className="flex items-center gap-2">
                  {/* 상태 배지 구역 */}
                  <div
                      className={`px-2 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1 border
                        ${history.status === 'completed' ? 'bg-green-50 border-green-200 text-green-600' :
                                            history.status === 'failed' ? 'bg-red-50 border-red-200 text-red-600' :
                                                'bg-blue-50 border-blue-200 text-blue-600'}`}
                                    >
                                      {history.status === 'completed' && <CheckCircle2 size={12} />}
                                      {history.status === 'completed' ? '성공' :
                                          history.status === 'failed' ? '실패' : '진행중'}
                                    </div>

                                    {/* 섹션 이름 구역 */}
                                    <span className="text-sm font-medium text-slate-700">
                      {history.sectionKRName}
                    </span>
                </div>
              </div>
              <div className="history-item-right">
                <div
                  className="history-defect-count"
                  style={{
                    color: history.defects.length > 0
                      ? 'var(--inspection-accent-red)'
                      : 'var(--inspection-accent-green)'
                  }}
                >
                  <AlertTriangle size={14} />
                  <span>결함 {history.defects.length}건</span>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
