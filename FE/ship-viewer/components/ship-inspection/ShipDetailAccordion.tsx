'use client';

import { useState } from 'react';
import { Ship } from 'lucide-react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import type { ShipInfoData } from '@/lib/inspection-types';

interface ShipDetailAccordionProps {
  shipInfo: ShipInfoData;
}

// [유틸리티] 숫자 포맷 (콤마)
function formatNumber(num: number): string {
  return num.toLocaleString('ko-KR');
}

// [유틸리티] Null 체크
function formatNullable(value: string | null, fallback: string): string {
  return value ?? fallback;
}

// [유틸리티] 날짜 포맷 (YYYY-MM-DD)
function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  } catch (e) {
    return dateStr;
  }
}

export default function ShipDetailAccordion({
                                              shipInfo,
                                            }: ShipDetailAccordionProps) {
  const [openSection, setOpenSection] = useState<string>('ship-detail');

  const styles = {
    textSecondary: 'var(--inspection-text-secondary)',
    textPrimary: 'var(--inspection-text-primary)',
    borderColor: 'var(--inspection-border-color)',
  };

  return (
      <Accordion
          type="single"
          collapsible
          value={openSection}
          onValueChange={(value) => setOpenSection(value)}
          className="inspection-accordion"
      >
        <AccordionItem value="ship-detail" className="accordion-section">
          <AccordionTrigger className="accordion-trigger">
            <div className="accordion-header">
              <div className="step-indicator">
                <Ship size={16} style={{ color: 'var(--inspection-accent-cyan)' }} />
              </div>
              <span className="step-title">선박 상세 정보</span>
            </div>
          </AccordionTrigger>

          <AccordionContent className="accordion-content-inner" style={{ padding: '0px 16px 0px 12px' }}>

            <div className="ship-summary-section pb-2">

              {/* 1. 선박명 섹션 (여백 좁게) */}
              <div style={{ marginBottom: '12px', paddingLeft: '4px' }}>
                <div style={{ fontSize: '12px', color: styles.textSecondary, marginBottom: '2px' }}>
                  선박명
                </div>
                <div style={{ fontSize: '24px', fontWeight: '700', color: styles.textPrimary, letterSpacing: '-0.5px' }}>
                  {shipInfo.name}
                </div>
              </div>

              {/* 2. 상세 스펙 그리드 (중간 타이틀 없음) */}
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', rowGap: '6px', fontSize: '14px', paddingLeft: '4px' }}>

                  {/* IMO */}
                  <span style={{ color: styles.textSecondary }}>IMO</span>
                  <span style={{ fontWeight: 500, color: styles.textPrimary, fontFamily: 'var(--font-pretendard)' }}>
                   {formatNullable(shipInfo.imo, '000000')}
                </span>

                  {/* 톤수 */}
                  <span style={{ color: styles.textSecondary }}>톤수</span>
                  <span style={{ fontWeight: 500, color: styles.textPrimary }}>
                  {formatNumber(shipInfo.ton)} <span style={{fontSize:'12px', color: styles.textSecondary}}>GT</span>
                </span>

                  {/* 재화중량 */}
                  <span style={{ color: styles.textSecondary }}>재화중량</span>
                  <span style={{ fontWeight: 500, color: styles.textPrimary }}>
                  {formatNumber(shipInfo.deadWeight)} <span style={{fontSize:'12px', color: styles.textSecondary}}>DWT</span>
                </span>

                  {/* 제원 */}
                  <span style={{ color: styles.textSecondary }}>제원</span>
                  <span style={{ fontWeight: 500, color: styles.textPrimary }}>
                  {shipInfo.lbp ? `${shipInfo.lbp.toFixed(1)} m` : '-'}
                </span>

                </div>
              </div>
            </div>

            {/* 3. 하단 상세 정보 카드 (기존 유지) */}
            <div className="ship-detail-section" style={{ marginTop: '20px' }}>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '12px'
              }}>
                {/* 등록/분류 정보 */}
                <div className="info-card" style={{ padding: '12px' }}>
                  <div className="wall-label" style={{ marginBottom: '10px', fontSize: '13px' }}>
                    등록/분류 정보
                  </div>
                  <div className="info-list">
                    <div className="info-row">
                      <span className="info-row-label">등록번호</span>
                      <span className="info-row-value info-row-value-code">{shipInfo.classNo}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">선급 표기</span>
                      <span className="info-row-value info-row-value-clamp">
                      {shipInfo.classNotation}
                    </span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">국적</span>
                      <span className="info-row-value info-row-value-code">{shipInfo.flagState}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">등록 항구</span>
                      <span className="info-row-value info-row-value-code">{shipInfo.port}</span>
                    </div>
                  </div>
                </div>

                {/* 건조/일정 정보 */}
                <div className="info-card" style={{ padding: '12px' }}>
                  <div className="wall-label" style={{ marginBottom: '10px', fontSize: '13px' }}>
                    건조/일정 정보
                  </div>
                  <div className="info-list">
                    <div className="info-row">
                      <span className="info-row-label">조선소</span>
                      <span className="info-row-value info-row-value-clamp">
                      {shipInfo.shipbuilder}
                    </span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">Hull No.</span>
                      <span className="info-row-value info-row-value-code">{shipInfo.hullNumber}</span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">건조일</span>
                      <span className="info-row-value info-row-value-code">
                      {formatDate(shipInfo.buildDate)}
                    </span>
                    </div>
                    <div className="info-row">
                      <span className="info-row-label">인도일</span>
                      <span className="info-row-value info-row-value-code">
                      {formatDate(shipInfo.deliveryDate)}
                    </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </AccordionContent>
        </AccordionItem>
      </Accordion>
  );
}