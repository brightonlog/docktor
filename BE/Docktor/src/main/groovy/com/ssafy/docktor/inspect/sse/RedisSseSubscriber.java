package com.ssafy.docktor.inspect.sse;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;
@Slf4j
@Service
@RequiredArgsConstructor
public class RedisSseSubscriber implements MessageListener {
    private final ObjectMapper objectMapper;
    private final SseEmitters sseEmitters; // 맵 대신 커스텀 빈 주입
    private static boolean isRobotOnline = false;

    public static boolean getRobotStatus() {
        return isRobotOnline;
    }
    @Override
    public void onMessage(Message message, byte[] pattern) {
        try {
            // 1. Redis 메시지(byte[])를 JsonNode로 읽기
            com.fasterxml.jackson.databind.JsonNode node = objectMapper.readTree(message.getBody());

            if (node.isArray() && node.has(1)) {
                node = node.get(1); // 실제 데이터 객체 선택
            } else if (node.isArray() && node.has(0)) {
                node = node.get(0);
            }

            com.fasterxml.jackson.databind.JsonNode idNode = node.path("inspectId");

            if (idNode.isMissingNode() || idNode.isNull()) {
                log.error("❌ Redis 메시지에 'inspectId'가 없습니다! 데이터: {}", node.toString());
                return;
            }

            int inspectId = idNode.asInt();

            // 4. SSE 전송
            SseEmitter emitter = sseEmitters.get(inspectId);
            if (emitter != null) {
                String jsonPayload = objectMapper.writeValueAsString(node);

                emitter.send(SseEmitter.event().data(jsonPayload));

                log.info("🚀 SSE 전송 성공 (ID: {}): {}", inspectId, jsonPayload);
            } else {
                log.warn("⚠️ 연결된 SSE 에미터를 찾지 못함 (ID: {})", inspectId);
            }
        } catch (Exception e) {
            log.error("❌ Redis message parsing error: {}", e.getMessage());
        }
    }

    public void handleStatusMessage(String message) {
        if ("online".equals(message)) {
            isRobotOnline = true;
            log.info("🤖 로봇이 온라인 상태입니다.");
        } else if ("offline".equals(message)) {
            isRobotOnline = false;
            log.error("💀 로봇이 오프라인(유언 발행) 되었습니다.");
        }
    }
}