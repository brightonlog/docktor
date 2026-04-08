package com.ssafy.docktor.inspect.sse;


import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class SseEmitters {
    // 멀티쓰레드 환경을 위해 ConcurrentHashMap 사용 필수!
    private final Map<Integer, SseEmitter> emitters = new ConcurrentHashMap<>();

    public void add(Integer id, SseEmitter emitter) {
        this.emitters.put(id, emitter);
    }

    public void remove(Integer id) {
        this.emitters.remove(id);
    }

    public SseEmitter get(Integer id) {
        return this.emitters.get(id);
    }
}