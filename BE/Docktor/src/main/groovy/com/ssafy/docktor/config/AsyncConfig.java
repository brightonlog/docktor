package com.ssafy.docktor.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

@Configuration
public class AsyncConfig {
    @Bean(name = "taskExecutor")
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);   // 기본 쓰레드 수
        executor.setMaxPoolSize(10);  // 최대 쓰레드 수
        executor.setQueueCapacity(100); // 대기 큐
        executor.setThreadNamePrefix("MqttAsync-");
        executor.initialize();
        return executor;
    }
}