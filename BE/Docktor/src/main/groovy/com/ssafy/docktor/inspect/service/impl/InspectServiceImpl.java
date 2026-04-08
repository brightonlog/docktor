package com.ssafy.docktor.inspect.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.docktor.defect.dao.DefectDao;
import com.ssafy.docktor.defect.dto.DefectDto;
import com.ssafy.docktor.inspect.dao.InspectDao;
import com.ssafy.docktor.inspect.dto.InspectDto;
import com.ssafy.docktor.inspect.dto.InspectRequest;
import com.ssafy.docktor.inspect.dto.RobotStatusDto;
import com.ssafy.docktor.inspect.service.InspectService;
import com.ssafy.docktor.inspect.service.MqttService;
import com.ssafy.docktor.ship.dao.FileDao;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@Slf4j
@RequiredArgsConstructor
public class InspectServiceImpl implements InspectService {

    private final InspectDao inspectDao;
    private final DefectDao defectDao;
    private final FileDao fileDao;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String HEARTBEAT_KEY_PREFIX = "robot:status:";
    private final org.eclipse.paho.client.mqttv3.MqttClient mqttClient;
    private final MqttService mqttService;
    private final ObjectMapper objectMapper;

    @Value("${robot.flask.url}")
    private String flaskUrl;

    @Value("${mqtt.topic.robot-move}")
    private String moveTopic;

    @Value("${api.callback.url}")
    private String callbackUrl;

    @Override
    @Transactional
    public Map<String, Object> sendMoveCommand(InspectRequest inspectRequest) {
        Map<String, Object> resultMap = new HashMap<>();
        if (!mqttService.isConnected()) { // MqttService에 isConnected() 메소드 추가 필요
            log.error("🚨 [MQTT] 브로커와 연결이 끊어져 명령을 보낼 수 없습니다.");
            resultMap.put("status", "fail_command");
            return resultMap;
        }

        String robotId = "orin_01";
        Object robotHeartbeat = redisTemplate.opsForValue().get(HEARTBEAT_KEY_PREFIX + robotId);


        try {
            // 1. DB 인서트 (시작 상태 기록)
            InspectDto inspect = InspectDto.builder()
                    .shipId(inspectRequest.getShipId())
                    .sectionId(inspectRequest.getSectionId())
                    .status("in_progress")
                    .startTime(LocalDateTime.now())
                    .build();
            inspectDao.insertInspect(inspect);
            Integer currentInspectId = inspect.getInspectId();


            // 2. 전송 파라미터 구성 (새 객체 생성으로 중복/간섭 방지)
            Map<String, Object> params = new HashMap<>();
            params.put("inspect_id", currentInspectId);
            params.put("ship_id", inspectRequest.getShipId());
            params.put("corp_id", inspectRequest.getCorpId());
            params.put("direction", inspectRequest.getSectionId());
            params.put("duration", 5.0);
            params.put("callback_url", callbackUrl);

            // 3. 비동기 MQTT 서비스 호출
            mqttService.publishAsync(moveTopic, params);

            log.info("🚀 [Service] 검사 요청 처리 완료 (ID: {})", currentInspectId);

            // 4. 리턴 결과 구성
            resultMap.put("status", "started");
            resultMap.put("inspectId", currentInspectId);
            return resultMap;

        } catch (Exception e) {
            log.error("❌ [Service] 검사 응답 수신 실패: {}", e.getMessage());
            resultMap.put("status", "fail_command");
            return resultMap;
        }
    }

    private void publishMqttCommand(Map<String, Object> payload) {
        try {
            if (!mqttClient.isConnected()) {
                log.warn("⚠️ [MQTT] 연결 끊김 감지, 재연결 시도 중...");
                mqttClient.reconnect();
            }

            String jsonPayload = objectMapper.writeValueAsString(payload);
            MqttMessage message = new MqttMessage(jsonPayload.getBytes());
            message.setQos(1);

            mqttClient.publish(moveTopic, message);
            log.info("▶️ [MQTT] 명령 발행 완료: ID={}", payload.get("inspect_id"));

        } catch (Exception e) {
            log.error("❌ [MQTT] 메시지 발행 중 최종 실패: {}", e.getMessage());
            throw new RuntimeException("MQTT 전송 실패: " + e.getMessage());
        }
    }

    @Override
    @Transactional
    public void completeInspect(Map<String, Object> result) {
        log.info("📩 Flask로부터 콜백 수신: {}", result);

        try {
            Integer inspectId = (Integer) result.get("inspect_id");
            String status = (String) result.get("status");
            String originalUrl = (String) result.get("image_url");
            List<Map<String, Object>> defectList = (List<Map<String, Object>>) result.get("defects");

            // 1. 에러 메시지 처리 개선: status가 'failed'일 때만 에러 메시지를 의미 있게 설정
            String errorMessage = (String) result.get("message");

            if (inspectId == null) {
                log.error("❌ 오류: inspect_id가 누락되었습니다.");
                return;
            }

            // 상태값 설정 (기본값 completed)
            String finalStatus = (status != null) ? status : "completed";

            InspectDto updateDto = InspectDto.builder()
                    .inspectId(inspectId)
                    .status(finalStatus)
                    .endTime(LocalDateTime.now())
                    .build();

            int row = inspectDao.updateStatus(updateDto);
            log.info("🔄 Inspect 상태 업데이트 결과: {}건 (ID: {})", row, inspectId);

            // 이미지 및 결함 정보 저장
            if (originalUrl != null) {
                fileDao.insertFile("inspect", inspectId, originalUrl);
            }

            if (defectList != null) {
                for (Map<String, Object> d : defectList) {
                    DefectDto defect = DefectDto.builder()
                            .inspectId(inspectId)
                            .categoryId((Integer) d.get("category_id"))
                            .confidence(BigDecimal.valueOf(Double.valueOf(d.get("confidence").toString())))
                            .x1((Integer) d.get("x1"))
                            .y1((Integer) d.get("y1"))
                            .x2((Integer) d.get("x2"))
                            .y2((Integer) d.get("y2"))
                            .xCord((Integer) d.get("x_cord"))
                            .yCord((Integer) d.get("y_cord"))
                            .build();

                    defectDao.insertDefect(defect);

                    String cropUrl = (String) d.get("cropped_image_url");
                    if (cropUrl != null) {
                        fileDao.insertFile("defect", defect.getDefectId(), cropUrl);
                    }
                }
            }

            log.info("✅ Inspect ID {} 처리 완료", inspectId);
            updateRobotStatus(result.get("robot_id") != null ? (String)result.get("robot_id") : "orin_01", "IDLE");

            // 2. Redis 전송 메시지 구성 (프론트엔드 요구사항에 최적화)
            Map<String, Object> sseMessage = new HashMap<>();
            sseMessage.put("inspectId", inspectId);
            sseMessage.put("status", finalStatus);

            // 실패했을 때만 에러 메시지를 넣거나, 성공 시엔 null/공백 전달
            if ("failed".equals(finalStatus)) {
                sseMessage.put("error", errorMessage != null ? errorMessage : "알 수 없는 에러 발생");
            } else {
                sseMessage.put("error", ""); // 성공 시엔 빈 값
            }

            redisTemplate.convertAndSend("inspect-channel", sseMessage);
            log.info("📢 SSE 알림을 위한 Redis 메시지 발행 완료 (ID: {}, Status: {})", inspectId, finalStatus);

        } catch (Exception e) {
            log.error("❌ 콜백 처리 중 에러: {}", e.getMessage());
            // 에러 발생 시 사용자에게 실패 알림을 보내기 위한 최소한의 장치
            try {
                Map<String, Object> failMessage = new HashMap<>();
                failMessage.put("inspectId", result.get("inspect_id"));
                failMessage.put("status", "failed");
                failMessage.put("error", "서버 내부 처리 중 오류 발생");
                redisTemplate.convertAndSend("inspect-channel", failMessage);
            } catch (Exception ignored) {}

            throw new RuntimeException(e);
        }
    }

    private void updateRobotStatus(String robotId, String status) {
        redisTemplate.opsForValue().set(HEARTBEAT_KEY_PREFIX + robotId, status, Duration.ofSeconds(30));
        log.info("🤖 로봇 [{}] 상태 변경 -> {}", robotId, status);
    }

    @Override
    public void updateRobotHeartbeat(RobotStatusDto status) {
        redisTemplate.opsForValue().set(HEARTBEAT_KEY_PREFIX + status.getRobotId(), "running", Duration.ofSeconds(10));
    }

    @Override
    @Transactional
    public void syncRobotStatusWithDb() {
        List<InspectDto> ongoing = inspectDao.selectOngoingInspects();

        if (ongoing != null) {
            for (InspectDto inspect : ongoing) {
                String status = (String) redisTemplate.opsForValue().get(HEARTBEAT_KEY_PREFIX + "orin_01");

                if (status == null && Duration.between(inspect.getStartTime(), LocalDateTime.now()).toMinutes() > 5) {
                    inspect.setStatus("failed");
                    inspectDao.updateStatus(inspect);
                    log.warn("⚠️ Inspect ID {} - 로봇 응답 없음으로 실패 처리", inspect.getInspectId());

                    Map<String, Object> sseMessage = new HashMap<>();
                    sseMessage.put("inspectId", inspect.getInspectId());
                    sseMessage.put("status", "failed");
                    sseMessage.put("error", "로봇 연결 끊김(타임아웃)");

                    redisTemplate.convertAndSend("inspect-channel", sseMessage);
                }

            }
        }
    }

    @Override public List<InspectDto> getInspectList(Integer corpId) { return inspectDao.selectAllAnalyze(corpId); }
    @Override public RobotStatusDto getRobotStatus(String robotId) { return (RobotStatusDto) redisTemplate.opsForValue().get(HEARTBEAT_KEY_PREFIX + robotId); }
}