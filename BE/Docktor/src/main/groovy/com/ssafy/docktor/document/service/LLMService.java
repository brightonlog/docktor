package com.ssafy.docktor.document.service;

import com.ssafy.docktor.defect.dto.DefectDto;
import com.ssafy.docktor.inspect.dto.InspectDto;
import com.ssafy.docktor.ship.dto.Ship;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.prompt.PromptTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Service
public class LLMService {

    private final ChatClient chatClient;

    @Value("classpath:prompts/ship-analysis.st")
    private Resource promptResource;

    public LLMService(ChatClient.Builder builder) {
        this.chatClient = builder.build();
    }

    /**
     * 선박, 검사 구역, 결함 리스트를 받아 AI 분석 결과를 반환
     * 파라미터에 Ship(선박정보), InspectDto(검사정보) 추가됨
     */
    public String analyzeShipCondition(Ship ship, InspectDto inspect, List<DefectDto> defects) {
        // 1. 데이터 없음 처리
        if (defects == null || defects.isEmpty()) {
            return "특이사항 없음: 해당 구역에서 발견된 결함이 없어 선박 상태가 매우 양호한 것으로 판단됨.";
        }

        // 2. 프롬프트에 주입할 문자열 데이터 생성
        String shipSummary = buildShipSummary(ship);
        String sectionSummary = buildSectionSummary(inspect);
        String defectSummary = buildDefectSummary(defects);

        // 3. 프롬프트 템플릿에 데이터 주입
        PromptTemplate promptTemplate = new PromptTemplate(promptResource);
        Map<String, Object> promptParams = Map.of(
                "shipInfo", shipSummary,
                "sectionInfo", sectionSummary,
                "defectData", defectSummary
        );
        String finalPrompt = promptTemplate.create(promptParams).getContents();

        // 4. AI 호출
        return chatClient.prompt()
                .user(finalPrompt)
                .call()
                .content();
    }

    private String buildShipSummary(Ship ship) {
        if (ship == null) return "선박 정보 없음";
        return String.format("- 선박명: %s (IMO: %s)\n- 선종/Class: %s\n- 건조일: %s",
                ship.getName(), ship.getImo(), ship.getClassNotation(),
                ship.getBuildDate() != null ? ship.getBuildDate().toString() : "정보없음");
    }

    private String buildSectionSummary(InspectDto inspect) {
        if (inspect == null) return "구역 정보 없음";
        return String.format("- 검사 구역: %s (%s)",
                inspect.getSectionKRName() != null ? inspect.getSectionKRName() : "Unknown",
                inspect.getSectionName());
    }

    /**
     * 결함 리스트 요약 (로직 개선 적용됨)
     */
    private String buildDefectSummary(List<DefectDto> defects) {
        StringBuilder sb = new StringBuilder();
        sb.append("총 결함 수: ").append(defects.size()).append("개\n");

        for (int i = 0; i < defects.size(); i++) {
            DefectDto d = defects.get(i);

            // 결함 종류 (한글명 우선)
            String type = d.getCategoryNameKr() != null ? d.getCategoryNameKr() : "미확인 결함";

            // 신뢰도 로직 처리
            String confidenceStr;
            Integer catId = d.getCategoryId();

            // CategoryId가 10(기타 손상)이면 신뢰도 표시 생략
            if (catId != null && catId == 10) {
                confidenceStr = "신뢰도 참고 대상 아님(육안 확인 요망)";
            } else {
                // 그 외: (값 * 100)% 형태로 변환
                BigDecimal conf = d.getConfidence() != null ? d.getConfidence() : BigDecimal.ZERO;
                BigDecimal percent = conf.multiply(new BigDecimal("100"));
                confidenceStr = String.format("AI 신뢰도 %.1f%%", percent);
            }

            sb.append(String.format("- %d. 결함유형: %s | %s\n", i + 1, type, confidenceStr));
        }
        return sb.toString();
    }
}