// 🔹 InspectType 상태 타입 (DB Enum)
import {Ship} from "@/lib/types/ship-types";

export type InspectStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

// 🔹 InspectType (점검) 인터페이스
export interface Inspect {
    inspectId: number;      // inspect_id
    sectionId: number;      // section_id
    sectionName: string;    // section_name (e.g., "left_bow", "right_stern")
    sectionKRName: string;
    shipId: number;         // ship_id
    status: InspectStatus;  // status
    startTime: string | null; // start_time (Date string)
    endTime: string | null;   // end_time (Date string)
    createDate: string;       // create_date (Date string)
    defects: Defect[];
}

export interface Defect {
    defectId: number;
    inspectId: number;
    categoryId: number;
    categoryName: string | null;
    categoryNameKr: string | null;
    confidence: number;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    xcord: number;
    ycord: number;
    croppedImageUrl: string | null;
    createDate: string;
}

export interface DefectListResponse {
    success: boolean;
    data: Defect[];
    error?: string;
}

// 보고서 다운로드 요청 데이터
export interface InspectionReportRequest {
    ship: Ship;              // 배 정보
    inspection: Inspect;     // 검사 정보
    defects: Defect[];       // 선택된 결함 리스트
}