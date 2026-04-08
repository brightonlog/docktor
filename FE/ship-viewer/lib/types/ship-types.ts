// 🔹 배(Ship) 관련 타입들만 모아놓은 파일

// 배 정보 타입
import {Inspect} from "@/lib/types/inspect-type";

export interface Ship {
    shipId: number;          // 배 ID
    shipName: string;        // 배 이름
    shipType: string;        // 선종 (LNGC, Tanker 등)
    classNo :string
    imo: string;       // IMO 번호
    status: string;          // 상태 (inspecting, completed, waiting)
    lastInspectionDate?: string;  // 최근 검사일
    defectCount: number;     // 결함 수
    imageUrl?: string;       // 배 이미지 URL
    description?: string;    // 설명
    thumbnailUrl: string;
    modelFileUrl: string;
    inspects : Inspect[];
    sections?: Section[];    // 선박 구역 정보 (검사 이력 조회 시 사용)

}
export interface ShipListParams {
    corpId?: number;
    search?: string;
    page?: number;
    limit?: number;
}
// 배 목록 응답 타입
export interface ShipListResponse {
    ships: Ship[];
    totalPages: number;
    totalCount: number;
    currentPage: number;
}


export type InspectionStatus = 'pending' | 'in_progress' | 'completed' | 'failed';
export interface Inspection {
    inspectId: number;
    sectionId: number;
    shipId: number;
    status: InspectionStatus;
    startTime: string | null; // JSON 직렬화 시 Date는 string(ISO 8601)으로 옵니다.
    endTime: string | null;
    createDate: string;
}

export interface Section {
    sectionId: number;
    shipId: number;
    name: string;
    description: string | null;
}