package com.ssafy.docktor.inspect.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.springframework.scheduling.annotation.Async;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.retry.annotation.Recover;
import org.springframework.stereotype.Service;

import java.util.Map;
@Slf4j
@Service
@RequiredArgsConstructor
public class MqttService {

    private final MqttClient mqttClient;
    private final ObjectMapper objectMapper;

    // ✅ 추가: 현재 브로커와 연결되어 있는지 확인하는 메소드
    public boolean isConnected() {
        return mqttClient != null && mqttClient.isConnected();
    }

    @Async("taskExecutor")
    @Retryable(
            value = { Exception.class },
            maxAttempts = 3,
            backoff = @Backoff(delay = 2000)
    )
    public void publishAsync(String topic, Map<String, Object> payload) {
        try {
            // 발행 직전 한 번 더 체크 및 재연결 시도
            if (!mqttClient.isConnected()) {
                log.warn("⚠️ [MQTT] 발행 시점 연결 끊김 감지, 재연결 시도...");
                mqttClient.reconnect();
            }

            String jsonPayload = objectMapper.writeValueAsString(payload);
            byte[] payloadBytes = jsonPayload.getBytes();

            // 직접 QoS 1로 발행
            mqttClient.publish(topic, payloadBytes, 1, false);
            log.info("▶️ [MQTT] QoS 1 발행 시도 성공 (ID: {})", payload.get("inspect_id"));

        } catch (Exception e) {
            log.error("❌ [MQTT] 발행 중 에러 발생: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }

    @Recover
    public void recover(Exception e, String topic, Map<String, Object> payload) {
        log.error("🚨 [MQTT] 최종 전송 실패 (3회 시도 완료): {}", e.getMessage());
    }
}