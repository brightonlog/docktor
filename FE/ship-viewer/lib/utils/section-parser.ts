/**
 * Section name 파싱 유틸리티
 * Section의 name 필드 (예: "선수 좌현 외판", "선미 우현 외판")에서
 * 벽면 타입(WallType)을 추출하는 함수들
 */

import type { WallType } from '../types/defect-types';

/**
 * Section name에서 벽면 타입 추출
 * @param sectionName - "선수 좌현 외판", "선미 우현 외판" 등
 * @returns WallType ('left' | 'right' | 'front' | 'back') 또는 null
 *
 * @example
 * parseSectionNameToWallType("선수 좌현 외판") → "left"
 * parseSectionNameToWallType("선미 우현 외판") → "right"
 * parseSectionNameToWallType("알 수 없는 구역") → null
 */
export function parseSectionNameToWallType(sectionName: string): WallType | null {
  if (!sectionName) return null;

  const normalized = sectionName.toLowerCase();

  // 좌현/우현 파싱 (좌/우가 선수/선미보다 우선)
  const side = normalized.includes('좌현') || normalized.includes('port') || normalized.includes('좌측')
    ? 'left'
    : normalized.includes('우현') || normalized.includes('starboard') || normalized.includes('우측')
    ? 'right'
    : null;

  // 선수/선미 파싱
  const position = normalized.includes('선수') || normalized.includes('bow')
    ? 'front'
    : normalized.includes('선미') || normalized.includes('stern')
    ? 'back'
    : null;

  // 우선순위: 좌/우현 > 선수/선미
  // 이유: "선수 좌현"처럼 둘 다 포함된 경우 좌/우현이 더 정확한 3D 벽면 정보
  return side || position;
}

/**
 * Section name에서 표시용 위치 설명 텍스트 생성
 * @param sectionName - "선수 좌현 외판", "선미 우현 외판" 등
 * @returns 표시용 텍스트 (예: "좌현 · 선수부", "우현 · 선미부")
 *
 * @example
 * getSectionDescription("선수 좌현 외판") → "좌현 · 선수부"
 * getSectionDescription("선미 우현 외판") → "우현 · 선미부"
 */
export function getSectionDescription(sectionName: string): string {
  if (!sectionName) return '알 수 없는 구역';

  const normalized = sectionName.toLowerCase();

  // 좌현/우현
  const sideText = normalized.includes('좌현') || normalized.includes('port') || normalized.includes('좌측')
    ? '좌현'
    : normalized.includes('우현') || normalized.includes('starboard') || normalized.includes('우측')
    ? '우현'
    : null;

  // 선수/선미
  const positionText = normalized.includes('선수') || normalized.includes('bow')
    ? '선수부'
    : normalized.includes('선미') || normalized.includes('stern')
    ? '선미부'
    : null;

  // 결합
  if (sideText && positionText) {
    return `${sideText} · ${positionText}`;
  } else if (sideText) {
    return sideText;
  } else if (positionText) {
    return positionText;
  } else {
    return sectionName;  // 파싱 실패 시 원본 반환
  }
}

/**
 * 벽면 타입을 한글로 변환
 * @param wallType - 'left' | 'right' | 'front' | 'back'
 * @returns 한글 텍스트 ("좌현", "우현", "선수부", "선미부")
 */
export function wallTypeToKorean(wallType: WallType): string {
  const wallNames: Record<WallType, string> = {
    left: '좌현',
    right: '우현',
    front: '선수부',
    back: '선미부',
  };

  return wallNames[wallType] || wallType;
}
