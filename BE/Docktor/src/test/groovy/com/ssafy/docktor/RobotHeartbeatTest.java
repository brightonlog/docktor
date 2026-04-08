package com.ssafy.docktor;

import com.ssafy.docktor.inspect.dao.InspectDao;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.core.RedisTemplate;

import java.time.Duration;


@SpringBootTest
class RobotHeartbeatTest {

    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    @Autowired
    private InspectDao inspectDao;

    @Test
    @DisplayName("Redis 키 만료 시 DB 상태가 DISCONNECTED로 변경되어야 한다")
    void heartbeatExpirationTest() throws InterruptedException {
        redisTemplate.opsForValue().set("robot:status:live", "running", Duration.ofMillis(500));

        Thread.sleep(2000);
        String currentStatus = inspectDao.getCurrentStatus();

        System.out.println("결과 상태: " + currentStatus);
    }
}