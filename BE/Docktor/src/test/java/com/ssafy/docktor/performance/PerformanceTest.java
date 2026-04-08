package com.ssafy.docktor.performance;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.docktor.auth.util.JwtUtil;
import com.ssafy.docktor.ship.dto.ShipRequestDto;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@DisplayName("성능 테스트 - 선박/결함 조회 및 수정")
public class PerformanceTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;
    
    @Autowired
    private JwtUtil jwtUtil;
    
    private String testToken;
    
    @BeforeEach
    public void setUp() {
        // 테스트용 JWT 토큰 생성 (Corp ID = 1)
        testToken = jwtUtil.generateAccessToken(1, "SSAFY", "싸피해운");
        System.out.println("테스트용 JWT 토큰 생성 완료: " + testToken.substring(0, 20) + "...");
    }

    // =================================================================================
    // [NEW] 1. 선박 목록 조회 성능 테스트
    // =================================================================================
    @Test
    @DisplayName("선박 목록 조회 API 성능 테스트")
    public void testShipListPerformance() throws Exception {
        System.out.println("\n========================================");
        System.out.println("선박 목록 조회 API 성능 테스트 시작");
        System.out.println("========================================");

        int iterations = 10;
        long totalTime = 0;

        for (int i = 0; i < iterations; i++) {
            long startTime = System.currentTimeMillis();

            mockMvc.perform(get("/api/ships")
                            .header("Authorization", "Bearer " + testToken)  // ⭐ JWT 추가
                            .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());

            long endTime = System.currentTimeMillis();
            long executionTime = endTime - startTime;
            totalTime += executionTime;

            System.out.printf("실행 %d: %d ms%n", i + 1, executionTime);
        }

        double averageTime = (double) totalTime / iterations;
        System.out.println("----------------------------------------");
        System.out.printf("평균 응답 시간: %.2f ms (%.3f 초)%n", averageTime, averageTime / 1000);
        System.out.println("========================================\n");
    }

    // =================================================================================
    // [NEW] 2. 선박 상세 조회 성능 테스트
    // =================================================================================
    @Test
    @DisplayName("선박 상세 조회 API 성능 테스트")
    public void testShipDetailPerformance() throws Exception {
        Integer shipId = 4; // 테스트할 선박 ID (Corp ID = 4의 선박)

        System.out.println("\n========================================");
        System.out.println("선박 상세 조회 API 성능 테스트 시작");
        System.out.println("========================================");

        int iterations = 10;
        long totalTime = 0;

        for (int i = 0; i < iterations; i++) {
            long startTime = System.currentTimeMillis();

            mockMvc.perform(get("/api/ships/" + shipId)
                            .header("Authorization", "Bearer " + testToken)  // ⭐ JWT 추가
                            .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());

            long endTime = System.currentTimeMillis();
            long executionTime = endTime - startTime;
            totalTime += executionTime;

            System.out.printf("실행 %d: %d ms%n", i + 1, executionTime);
        }

        double averageTime = (double) totalTime / iterations;
        System.out.println("----------------------------------------");
        System.out.printf("평균 응답 시간: %.2f ms (%.3f 초)%n", averageTime, averageTime / 1000);
        System.out.println("========================================\n");
    }

    @Test
    @DisplayName("선박 수정 API 성능 테스트")
    public void testShipUpdatePerformance() throws Exception {
        Integer shipId = 4; // Corp ID = 1의 선박

        ShipRequestDto requestDto = ShipRequestDto.builder()
                .name("성능테스트선박-수정")
                .classNo("TEST-001")
                .imo("IMO9999999")
                .classNotation("Container Ship")
                .flagState("Korea")
                .port("Busan")
                .ton(50000.0)
                .deadWeight(60000.0)
                .lbp(200.0)
                .shipbuilder("현대중공업")
                .hullNumber("HULL-001")
                .build();

        String jsonRequest = objectMapper.writeValueAsString(requestDto);

        MockMultipartFile shipPart = new MockMultipartFile(
                "ship", "", "application/json", jsonRequest.getBytes()
        );

        System.out.println("\n========================================");
        System.out.println("선박 수정 API 성능 테스트 시작");
        System.out.println("========================================");

        int iterations = 10;
        long totalTime = 0;

        for (int i = 0; i < iterations; i++) {
            long startTime = System.currentTimeMillis();

            mockMvc.perform(multipart("/api/ships/" + shipId)
                            .file(shipPart)
                            .header("Authorization", "Bearer " + testToken)  // ⭐ JWT 추가
                            .with(request -> {
                                request.setMethod("PUT");
                                return request;
                            })
                            .contentType(MediaType.MULTIPART_FORM_DATA))
                    .andExpect(status().isOk());

            long endTime = System.currentTimeMillis();
            long executionTime = endTime - startTime;
            totalTime += executionTime;

            System.out.printf("실행 %d: %d ms%n", i + 1, executionTime);
        }

        double averageTime = (double) totalTime / iterations;
        System.out.println("----------------------------------------");
        System.out.printf("평균 응답 시간: %.2f ms (%.3f 초)%n", averageTime, averageTime / 1000);
        System.out.println("========================================\n");
    }

    // =================================================================================
    // [NEW] 3. 결함 목록 조회 성능 테스트
    // =================================================================================
    @Test
    @DisplayName("결함 목록 조회 API 성능 테스트")
    public void testDefectListPerformance() throws Exception {
        Integer shipId = 1; // 특정 선박의 결함 목록을 조회한다고 가정

        System.out.println("\n========================================");
        System.out.println("결함 목록 조회 API 성능 테스트 시작");
        System.out.println("========================================");

        int iterations = 10;
        long totalTime = 0;

        for (int i = 0; i < iterations; i++) {
            long startTime = System.currentTimeMillis();

            mockMvc.perform(get("/api/defect/list/" + shipId)
                            .header("Authorization", "Bearer " + testToken)  // ⭐ JWT 추가
                            .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());

            long endTime = System.currentTimeMillis();
            long executionTime = endTime - startTime;
            totalTime += executionTime;

            System.out.printf("실행 %d: %d ms%n", i + 1, executionTime);
        }

        double averageTime = (double) totalTime / iterations;
        System.out.println("----------------------------------------");
        System.out.printf("평균 응답 시간: %.2f ms (%.3f 초)%n", averageTime, averageTime / 1000);
        System.out.println("========================================\n");
    }

    @Test
    @DisplayName("결함 상세 조회 API 성능 테스트")
    public void testDefectDetailPerformance() throws Exception {
        Integer defectId = 1;

        System.out.println("\n========================================");
        System.out.println("결함 상세 조회 API 성능 테스트 시작");
        System.out.println("========================================");

        int iterations = 10;
        long totalTime = 0;

        for (int i = 0; i < iterations; i++) {
            long startTime = System.currentTimeMillis();

            mockMvc.perform(get("/api/defect/" + defectId)
                            .header("Authorization", "Bearer " + testToken)  // ⭐ JWT 추가
                            .contentType(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk());

            long endTime = System.currentTimeMillis();
            long executionTime = endTime - startTime;
            totalTime += executionTime;

            System.out.printf("실행 %d: %d ms%n", i + 1, executionTime);
        }

        double averageTime = (double) totalTime / iterations;
        System.out.println("----------------------------------------");
        System.out.printf("평균 응답 시간: %.2f ms (%.3f 초)%n", averageTime, averageTime / 1000);
        System.out.println("========================================\n");
    }

    @Test
    @DisplayName("종합 성능 테스트 - 조회 및 수정 시나리오")
    public void testCombinedPerformance() throws Exception {
        Integer shipId = 1;

        System.out.println("\n========================================");
        System.out.println("종합 성능 테스트 (목록 -> 상세 -> 수정)");
        System.out.println("========================================");

        // 1. 선박 목록 조회
        long listStart = System.currentTimeMillis();
        mockMvc.perform(get("/api/ships")
                        .header("Authorization", "Bearer " + testToken))  // ⭐ JWT 추가
                .andExpect(status().isOk());
        long listEnd = System.currentTimeMillis();

        // 2. 선박 상세 조회
        long detailStart = System.currentTimeMillis();
        mockMvc.perform(get("/api/ships/" + shipId)
                        .header("Authorization", "Bearer " + testToken))  // ⭐ JWT 추가
                .andExpect(status().isOk());
        long detailEnd = System.currentTimeMillis();

        // 3. 선박 수정
        ShipRequestDto requestDto = ShipRequestDto.builder()
                .name("종합테스트선박")
                .classNo("COMBINED-001")
                .build();
        String jsonRequest = objectMapper.writeValueAsString(requestDto);
        MockMultipartFile shipPart = new MockMultipartFile("ship", "", "application/json", jsonRequest.getBytes());

        long updateStart = System.currentTimeMillis();
        mockMvc.perform(multipart("/api/ships/" + shipId)
                        .file(shipPart)
                        .header("Authorization", "Bearer " + testToken)  // ⭐ JWT 추가
                        .with(request -> { request.setMethod("PUT"); return request; })
                        .contentType(MediaType.MULTIPART_FORM_DATA))
                .andExpect(status().isOk());
        long updateEnd = System.currentTimeMillis();

        long listTime = listEnd - listStart;
        long detailTime = detailEnd - detailStart;
        long updateTime = updateEnd - updateStart;
        long totalTime = listTime + detailTime + updateTime;

        System.out.printf("선박 목록: %d ms%n", listTime);
        System.out.printf("선박 상세: %d ms%n", detailTime);
        System.out.printf("선박 수정: %d ms%n", updateTime);
        System.out.println("----------------------------------------");
        System.out.printf("총 소요 시간: %d ms (%.3f 초)%n", totalTime, totalTime / 1000.0);
        System.out.println("========================================\n");
    }
}