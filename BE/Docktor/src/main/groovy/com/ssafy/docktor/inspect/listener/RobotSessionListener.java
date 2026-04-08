package com.ssafy.docktor.inspect.listener;

import com.ssafy.docktor.inspect.dao.InspectDao;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.listener.KeyExpirationEventMessageListener;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Component
public class RobotSessionListener extends KeyExpirationEventMessageListener {

    private final InspectDao inspectDao;

    public RobotSessionListener(RedisMessageListenerContainer listenerContainer, InspectDao inspectDao) {
        super(listenerContainer);
        this.inspectDao = inspectDao;
    }

    @Override
    @Transactional // B2B 특성상 데이터 정합성을 위해 트랜잭션 권장
    public void onMessage(Message message, byte[] pattern) {
        String expiredKey = message.toString();

        // 1. 단일 로봇 시스템이므로 고정된 상태 키만 감시
        if ("robot:status:live".equals(expiredKey)) {
            log.error("⚠️ [B2B Alert] 로봇 하트비트 중단 감지. 즉시 상태 복구 로직을 실행합니다.");

            try {
                int affectedRows = inspectDao.updateAllInProgressToDisconnected();

                if (affectedRows > 0) {
                    log.info("✅ 연결 유실 처리 완료: {}건의 검사 상태를 변경했습니다.", affectedRows);
                } else {
                    log.info("ℹ️ 처리할 진행 중인 검사 내역이 없습니다.");
                }
            } catch (Exception e) {
                log.error("❌ [Critical] DB 상태 업데이트 중 에러 발생: {}", e.getMessage());
            }
        }
    }
}