package com.ssafy.docktor.defect.service;

import com.ssafy.docktor.defect.dao.DefectDao;
import com.ssafy.docktor.defect.dto.DefectDto;
import com.ssafy.docktor.defect.dto.DefectDetailResponseDto;
import com.ssafy.docktor.inspect.dao.InspectDao;
import com.ssafy.docktor.inspect.dto.InspectDto;
import com.ssafy.docktor.ship.dao.ShipDao;
import com.ssafy.docktor.ship.dto.Ship;
import com.ssafy.docktor.common.tenant.TenantContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class DefectService {

    private final DefectDao defectDao;
    private final InspectDao inspectDao;
    private final ShipDao shipDao;

    /**
     * Inspect ID로 결함 목록 조회
     */
    @Transactional(readOnly = true)
    public List<DefectDto> getDefectsByInspectId(Integer inspectId) {
        return defectDao.findByInspectId(inspectId);
    }

    /**
     * 결함 상세 조회
     */
    @Transactional(readOnly = true)
    public DefectDetailResponseDto getDefectDetail(Integer defectId) {
        log.info("결함 ID {} 상세 조회", defectId);

        DefectDto defect = defectDao.findById(defectId);
        if (defect == null) {
            throw new IllegalArgumentException("존재하지 않는 결함입니다.");
        }

        // Inspect 정보 조회
        InspectDto inspect = inspectDao.findById(defect.getInspectId());
        if (inspect == null) {
            throw new IllegalStateException("결함에 연결된 검사 정보를 찾을 수 없습니다.");
        }

//        // 현재 사용자의 Corp ID 가져오기
//        Integer corpId = TenantContext.getCurrentTenant();
//        if (corpId == null) {
//            throw new IllegalStateException("로그인이 필요합니다.");
//        }

        // Ship 정보 조회 (corpId 전달)
        Ship ship = shipDao.selectShipById(inspect.getShipId(), null);
        String shipName = ship != null ? ship.getName() : "Unknown";

        // 심각도 계산 (confidence 기반)
        String severity = calculateSeverity(defect.getConfidence());

        return DefectDetailResponseDto.builder()
                .defectId(defect.getDefectId())
                .inspectId(defect.getInspectId())
                .shipId(inspect.getShipId())
                .shipName(shipName)
                .categoryId(defect.getCategoryId())
                .confidence(defect.getConfidence())
                .position(DefectDetailResponseDto.Position.builder()
                        .x1(defect.getX1())
                        .y1(defect.getY1())
                        .x2(defect.getX2())
                        .y2(defect.getY2())
                        .build())
                .detectedAt(defect.getCreateDate())
                .severity(severity)
                .build();
    }

    /**
     * Confidence 기반 심각도 계산
     */
    private String calculateSeverity(BigDecimal confidence) {
        if (confidence == null) {
            return "low";
        }

        double conf = confidence.doubleValue();
        if (conf >= 0.8) {
            return "high";
        } else if (conf >= 0.5) {
            return "medium";
        } else {
            return "low";
        }
    }
}
