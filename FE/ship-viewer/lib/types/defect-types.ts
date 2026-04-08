/**
 * 결함(Defect) 관련 타입 정의
 */
import {Defect} from "@/lib/types/inspect-type";

// 백엔드 API 응답 타입
export interface DefectApiResponse extends Defect {
  // 선택적 필드
  category_name?: string;    // 영문명 (crack, blister)
  category_name_kr?: string; // 한글명 (균열, 부풀음)
  cropped_image_url?: string; // S3 URL
  severity?: 'high' | 'medium' | 'low';
  sectionName?: string;      // section_name (e.g., "left_bow", "right_stern")
  wall_type?: string;        // wall_type (e.g., "left", "right")
  xcord?: number;           // x 좌표 (정규화)
  ycord?: number;           // y 좌표 (정규화)
}

// 프론트엔드 DefectData 타입 (기존 확장)
export interface DefectData {
  id: string;
  type: string;
  typeKr?: string;
  position: [number, number, number];  // 3D 좌표 [X, Y, Z]
  confidence: number;                   // 0-100
  severity: 'high' | 'medium' | 'low';
  description: string;
  image?: string;

  // 디버깅용 추가 정보
  wallType?: string;
  pixelPosition?: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
}

// 벽면 타입
export type WallType = 'left' | 'right' | 'front' | 'back';
