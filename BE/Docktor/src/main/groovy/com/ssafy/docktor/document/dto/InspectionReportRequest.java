package com.ssafy.docktor.document.dto;

import com.ssafy.docktor.defect.dto.DefectDto;
import com.ssafy.docktor.inspect.dto.InspectDto;
import com.ssafy.docktor.ship.dto.Ship;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 검사 결과 보고서 생성 요청 DTO
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class InspectionReportRequest {
    private Ship ship;              // 배 정보
    private InspectDto inspection;  // 검사 정보
    private List<DefectDto> defects; // 결함 리스트
    private String sectionName;     // 검사 위치명 (예: "선미", "선수" 등)
}
