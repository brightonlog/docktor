package com.ssafy.docktor.inspect.controller;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.docktor.defect.dto.DefectDto;
import com.ssafy.docktor.defect.service.DefectService;
import com.ssafy.docktor.inspect.dto.InspectDto;
import com.ssafy.docktor.inspect.dto.InspectRequest;
import com.ssafy.docktor.inspect.dto.RobotStatusDto;
import com.ssafy.docktor.inspect.service.InspectService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/inspect")
@RequiredArgsConstructor
@CrossOrigin("*")
public class InspectController {

    private final InspectService inspectService;
    private final DefectService defectService;

    private final ObjectMapper objectMapper;
    private final MqttClient mqttClient;

    @Value("${mqtt.topic.robot-move}")
    private String moveTopic;

    @Value("${api.callback.url}")
    private String callbackUrl;

    @GetMapping("/list/{shipId}")
    public ResponseEntity<?> getInspectList(@PathVariable("shipId") int shipId) {
        try {
            log.info("배의 {}의 검사 내역 조회", shipId);
            List<InspectDto> list = inspectService.getInspectList(shipId);

            return (list != null)
                    ? new ResponseEntity<>(list, HttpStatus.OK)
                    : new ResponseEntity<>(HttpStatus.NO_CONTENT);
        } catch (Exception e) {
            log.error("서버 에러 발생: ", e);
            return new ResponseEntity<>("서버 에러: " + e.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * 검사별 결함 조회
     * GET /api/inspect/{inspectId}/defects
     */
    @GetMapping("/{inspectId}/defects")
    public ResponseEntity<?> getInspectDefects(@PathVariable("inspectId") Integer inspectId) {
        try {
            List<DefectDto> defects = defectService.getDefectsByInspectId(inspectId);

            return ResponseEntity.ok()
                    .body(Map.of(
                            "success", true,
                            "data", defects
                    ));

        } catch (Exception e) {
            log.error("결함 목록 조회 중 오류 발생", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of(
                            "success", false,
                            "message", "서버 에러: " + e.getMessage()
                    ));
        }
    }

    @PostMapping("/start-inspect")
    public ResponseEntity<?> moveForward(@RequestBody InspectRequest inspectRequest) {
        log.info("🚀 로봇 이동 및 검사 요청 수신: {}", inspectRequest);

        // 서비스에서 Map 받기 (Service 수정 필수!)
        Map<String, Object> serviceResult = inspectService.sendMoveCommand(inspectRequest);

        String status = (String) serviceResult.get("status");

        switch (status) {
            case "started":
                Integer inspectId = (Integer) serviceResult.get("inspectId");
                // ✅ 성공 시 JSON 반환: { "message": "...", "inspectId": 123 }
                return ResponseEntity.ok(Map.of(
                        "message", "검사 명령이 성공적으로 전달되었습니다.",
                        "inspectId", inspectId
                ));

            case "fail_busy":
                return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS)
                        .body(Map.of("message", "로봇이 현재 다른 작업을 수행 중입니다."));

            case "fail_command":
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body(Map.of("message", "검사 응답 수신 실패"));

            case "fail_robot_offline":
                return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                        .body(Map.of("message", "로봇 서버(Flask)가 꺼져 있습니다. 확인 후 다시 시도해주세요."));

            default:
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body(Map.of("message", "알 수 없는 에러"));
        }
    }

    // 검사 완료 시 콜백 함수
    @PostMapping("/callback")
    public ResponseEntity<String> inspectCallback(@RequestBody Map<String, Object> result) {
        inspectService.completeInspect(result);
        return ResponseEntity.ok("Success");
    }

    // 하트비트 수신 (로봇 -> 스프링)
    @PostMapping("/heartbeat")
    public ResponseEntity<Void> receiveHeartbeat(@RequestBody RobotStatusDto status) {
        inspectService.updateRobotHeartbeat(status);
        return ResponseEntity.ok().build();
    }

//    @GetMapping("/test-sync")
//    public ResponseEntity<String> testForceSync() {
//        log.info("🧪 [테스트] 강제 데이터 삽입 및 동기화 테스트 시작");
//
//        try {
//            InspectDto testInspect = InspectDto.builder()
//                    .shipId(38)
//                    .sectionId(5)
//                    .status("in_progress")
//                    .startTime(java.time.LocalDateTime.now())
//                    .build();
//
//            inspectService.sendMoveCommand(38, 5);
//            log.info("✅ 1단계: 강제 인서트 시도 완료 (로그 확인 필요)");
//
//            log.info("🔄 2단계: 스케줄러 동기화 로직 강제 실행");
//            inspectService.syncRobotStatusWithDb();
//
//            return ResponseEntity.ok("테스트 요청 완료! 로그와 DB를 확인하세요.");
//        } catch (Exception e) {
//            log.error("❌ 테스트 중 치명적 에러: ", e);
//            return ResponseEntity.internalServerError().body("에러 발생: " + e.getMessage());
//        }
//    }
    
    // MQTT 테스트 함수
    @PostMapping("/test-mqtt-publish")
    public ResponseEntity<String> testMqttPublish() {
        log.info("📡 MQTT 테스트 발행 시작 - Topic: {}", moveTopic);

        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("inspect_id", 26);
            payload.put("ship_id", 38);
            payload.put("corp_id", 1);
            payload.put("callback_url", callbackUrl); 
            payload.put("duration", 2.0);

            String jsonPayload = objectMapper.writeValueAsString(payload);
            MqttMessage message = new MqttMessage(jsonPayload.getBytes());
            message.setQos(1);

            mqttClient.publish(moveTopic, message);

            log.info("✅ MQTT 메시지 발행 성공");
            return ResponseEntity.ok("전송 성공!");

        } catch (Exception e) {
            log.error("❌ MQTT 에러: ", e);
            return ResponseEntity.internalServerError().body("에러: " + e.getMessage());
        }
    }



}