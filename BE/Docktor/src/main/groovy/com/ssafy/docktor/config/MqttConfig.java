package com.ssafy.docktor.config;

import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
@Slf4j
@Configuration
public class MqttConfig {

    @Value("${mqtt.broker.url}")
    private String broker;

    @Value("${mqtt.client.id}")
    private String clientId;

    @Value("${mqtt.connection.timeout:10}")
    private int connectionTimeout;

    @Value("${mqtt.keep-alive:20}")
    private int keepAliveInterval;

    @Value("${mqtt.max-inflight:100}")
    private int maxInflight;

    @Value("${mqtt.clean-session:true}")
    private boolean cleanSession;

    @Value("${mqtt.use-unique-id:false}")
    private boolean useUniqueId;

    @Bean
    public MqttClient mqttClient() {
        try {
            // 운영 vs 시연 모드 선택 로직
            String finalClientId = useUniqueId ?
                    clientId + "_" + System.currentTimeMillis() :
                    clientId;

            MqttClient client = new MqttClient(broker, finalClientId, new MemoryPersistence());

            MqttConnectOptions options = new MqttConnectOptions();
            options.setAutomaticReconnect(true);
            options.setCleanSession(cleanSession);
            options.setConnectionTimeout(connectionTimeout);
            options.setKeepAliveInterval(keepAliveInterval);
            options.setMaxInflight(maxInflight);

            log.info("🚀 MQTT 연결 시도 (ID: {}, Mode: {})", finalClientId, useUniqueId ? "시연" : "운영");

            try {
                client.connect(options);
                log.info("✅ MQTT 연결 성공!");
            } catch (Exception e) {
                log.warn("⚠️ MQTT 초기 연결 실패(자동재연결 대기): {}", e.getMessage());
            }

            return client;
        } catch (Exception e) {
            log.error("❌ MQTT 클라이언트 생성 치명적 오류: {}", e.getMessage());
            return null;
        }
    }
}