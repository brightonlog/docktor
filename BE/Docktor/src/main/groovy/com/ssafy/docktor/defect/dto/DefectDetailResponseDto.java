package com.ssafy.docktor.defect.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 결함 상세 조회 응답 DTO
 * ERD 1.2 기준
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class DefectDetailResponseDto {
    private Integer defectId;
    private Integer inspectId;        // ⚠️ analyzeId 아님!
    private Integer shipId;
    private String shipName;
    
    // 결함 정보
    private String categoryName;      // 영문명 (crack, blister 등)
    private String categoryNameKr;    // 한글명 (균열, 부풀음 등) - 추가!
    private Integer categoryId;
    private BigDecimal confidence;
    
    // 위치 정보
    private Position position;
    
    // 이미지 정보
    private String croppedImageUrl;   // S3 크롭 이미지 경로
    
    // 메타데이터
    private LocalDateTime detectedAt;
    private String severity; // low, medium, high (confidence 기반)
    
    @Data
    @Builder
    @AllArgsConstructor
    @NoArgsConstructor
    public static class Position {
        private Integer x1;
        private Integer y1;
        private Integer x2;
        private Integer y2;
    }
}
