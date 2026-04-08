'use client';

import { ArrowLeft, Search } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

interface InspectionHeaderProps {
  panelMode?: 'default' | 'inspection';
  onStartInspection?: () => void;
  onBackToDefault?: () => void;
}

export default function InspectionHeader({
  panelMode = 'default',
  onStartInspection,
  onBackToDefault,
}: InspectionHeaderProps) {
  return (
    <div className="inspection-header">
      <div className="logo">
        <Link href="/main" style={{ cursor: 'pointer' }}>
          <Image
            src={panelMode === 'inspection' ? '/images/white_docktor_logo.png' : '/images/docktor_logo.png'}
            alt="DockTor Logo"
            width={360}
            height={80}
            priority
            style={{ height: '80px', width: 'auto' }}
          />
        </Link>
      </div>

      {/* 헤더 액션 버튼 */}
      <div className="header-actions">
        {panelMode === 'default' && onStartInspection && (
          <button
            className="inspection-btn inspection-btn-primary"
            onClick={onStartInspection}
          >
            <Search size={16} style={{ marginRight: '8px' }} />
            선박 검사
          </button>
        )}
        {panelMode === 'inspection' && onBackToDefault && (
          <button
            className="inspection-btn"
            onClick={onBackToDefault}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '12px 24px',
              fontSize: '19px',
              borderRadius: '10px',
            }}
          >
            <ArrowLeft size={16} />
            돌아가기
          </button>
        )}
      </div>
    </div>
  );
}
