package com.ssafy.docktor.defect.controller;

import com.ssafy.docktor.defect.dto.DefectDetailResponseDto;
import com.ssafy.docktor.defect.service.DefectService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/defect")
@RequiredArgsConstructor
@CrossOrigin("*")
public class DefectController {
    
    private final DefectService defectService;
    
    /**
     * 결함 상세 조회
     * GET /api/defect/{defectId}
     */
    @GetMapping("/{defectId}")
    public ResponseEntity<?> getDefectDetail(@PathVariable("defectId") Integer defectId) {
        try {
            log.info("결함 상세 조회 요청: defectId={}", defectId);
            
            DefectDetailResponseDto defect = defectService.getDefectDetail(defectId);
            
            return ResponseEntity.ok()
                    .body(Map.of(
                        "success", true,
                        "data", defect
                    ));
                    
        } catch (IllegalArgumentException e) {
            log.warn("결함을 찾을 수 없음: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of(
                        "success", false,
                        "message", e.getMessage()
                    ));
                    
        } catch (Exception e) {
            log.error("결함 상세 조회 중 오류 발생", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of(
                        "success", false,
                        "message", "서버 에러: " + e.getMessage()
                    ));
        }
    }
}
