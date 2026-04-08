package com.ssafy.docktor.inspect.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class SseNotificationService {
    private final RedisTemplate<String, Object> redisTemplate;

    public void sendStatusUpdate(Integer inspectId, String status) {
        Map<String, Object> message = new HashMap<>();
        message.put("inspectId", inspectId);
        message.put("status", status);
        redisTemplate.convertAndSend("inspect-channel", message);
    }
}