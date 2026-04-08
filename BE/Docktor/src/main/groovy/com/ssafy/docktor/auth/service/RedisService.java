package com.ssafy.docktor.auth.service;

import java.util.concurrent.TimeUnit;

public interface RedisService {

    /**
     * Redis에 데이터 저장
     * @param key 키
     * @param value 값
     * @param timeout 만료 시간
     * @param unit 시간 단위
     */
    void save(String key, String value, long timeout, TimeUnit unit);


    /**
     * Redis에서 데이터 조회
     * @param key 키
     * @return 값 (없으면 null)
     */
    String get(String key);

    /**
     * Redis에서 데이터 삭제
     * @param key 키
     * @return 삭제 성공 여부
     */
    Boolean delete(String key);
}
