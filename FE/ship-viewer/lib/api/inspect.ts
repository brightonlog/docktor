import { authenticatedFetch } from './client';
import {Inspect, InspectionReportRequest} from '@/lib/types/inspect-type';

// 🟢 특정 선박의 점검 목록 조회
export async function getInspectListApi(token: string, shipId: number) {
    return authenticatedFetch< Inspect[] >(`/api/inspect/list/${shipId}`, token, {
        method: 'GET',
    });
}

export async function getDefectListApi (token: string, inspectId: number){
    return authenticatedFetch<void>(`/api/inspect/${inspectId}/defects`,token,{
        method: 'GET',
    })
}
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

// 보고서 다운로드 요청 API
// blob으로 받아야하기 때문에 json으로 받는 기존 api로직 사용 안함.
export async function generateInspectionReport(token: string, data: InspectionReportRequest) {
    // authenticatedFetch 대신 일반 fetch 사용 (또는 client.ts 구조에 따라 blob 옵션이 있다면 사용)
    const response = await fetch(`${API_BASE_URL}/api/document/inspection-report`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`, // 토큰 직접 헤더에 추가
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        throw new Error('리포트 생성 실패');
    }

    // JSON 대신 파일 데이터(Blob) 반환
    return response.blob();
}

/**
 * 검사 및 로봇 제어 관력 로직
 * */

interface StartInspectionRequest {
    shipId: number;
    sectionId: number;
    startTime: string; // ISO 8601 format (e.g., "2024-02-04T12:00:00.000Z")
}
interface StartInspectionResponse {
    status: string;
    inspectId: string;
    error: string; // ISO 8601 format (e.g., "2024-02-04T12:00:00.000Z")
}

// 🟢 로봇 검사 시작 요청 (POST)
export async function startRobotInspection(token: string, data: StartInspectionRequest) {
    try {
        const response = await fetch(`https://i14e201.p.ssafy.io/api/inspect/start-inspect`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`, // ✅ 토큰 추가
            },
            body: JSON.stringify(data), // ✅ 여기가 핵심: 데이터를 JSON 문자열로 변환해서 body에 넣음
        });

        if (response.status === 401) {
            throw new Error('TOKEN_EXPIRED');
        }

        if (response.status === 403) {
            throw new Error('FORBIDDEN');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || '요청에 실패했습니다.');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}