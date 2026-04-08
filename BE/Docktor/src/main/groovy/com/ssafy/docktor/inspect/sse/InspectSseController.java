package com.ssafy.docktor.inspect.sse;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/sse")
public class InspectSseController {

    private final SseEmitters sseEmitters;

    // 💡 핵심 수정: @PathVariable에 이름을 명시적으로 부여합니다. ("inspectId")
    @GetMapping(value = "/subscribe/{inspectId}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter subscribe(@PathVariable("inspectId") Integer inspectId) {
        SseEmitter emitter = new SseEmitter(120 * 60 * 1000L);

        sseEmitters.add(inspectId, emitter);

        emitter.onCompletion(() -> sseEmitters.remove(inspectId));
        emitter.onTimeout(() -> sseEmitters.remove(inspectId));
        emitter.onError((e) -> sseEmitters.remove(inspectId));

        try {
            emitter.send(SseEmitter.event()
                    .name("connect")
                    .data("SSE Connected for Inspect ID: " + inspectId));
        } catch (IOException e) {
            sseEmitters.remove(inspectId);
            log.error("SSE connection error for ID: {}", inspectId);
        }

        return emitter;
    }
}