/**
 * 결함(Defect) API
 */

import { authenticatedFetch } from './client';
import type { DefectApiResponse } from '../types/defect-types';

/**
 * 결함 상세 정보 조회
 */
export async function getDefectDetail(
  token: string,
  defectId: number
): Promise<{ success: boolean; data: DefectApiResponse }> {
  return authenticatedFetch<{ success: boolean; data: DefectApiResponse }>(
    `/api/defect/${defectId}`,
    token,
    { method: 'GET' }
  );
}

/**
 * 검사 ID로 결함 목록 조회
 */
export async function getDefectsByInspectId(
  token: string,
  inspectId: number
): Promise<{ success: boolean; data: DefectApiResponse[] }> {
  return authenticatedFetch<{ success: boolean; data: DefectApiResponse[] }>(
    `/api/defect/inspect/${inspectId}`,
    token,
    { method: 'GET' }
  );
}
