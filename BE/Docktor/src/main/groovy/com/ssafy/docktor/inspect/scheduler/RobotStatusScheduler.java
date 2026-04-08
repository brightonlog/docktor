package com.ssafy.docktor.inspect.scheduler;

import com.ssafy.docktor.inspect.service.InspectService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class RobotStatusScheduler {

    private final InspectService inspectService;

    @Scheduled(fixedRate = 300000)
    public void syncRobotStatus() {
        log.info("🕒 로봇 상태 DB 동기화 스케줄러 시작");
        try {
            inspectService.syncRobotStatusWithDb();
            log.info("🕒 로봇 상태 DB 동기화 완료");
        } catch (Exception e) {
            log.error("🕒 스케줄러 작업 중 에러 발생: ", e);
        }
    }
}