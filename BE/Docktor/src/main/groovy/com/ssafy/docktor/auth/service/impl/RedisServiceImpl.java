package com.ssafy.docktor.auth.service.impl;

import com.ssafy.docktor.auth.service.RedisService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class RedisServiceImpl implements RedisService {

    private final RedisTemplate<String, String> redisTemplate;


    @Override
    public void save(String key, String value, long timeout, TimeUnit unit) {
        try{
            redisTemplate.opsForValue().set(key, value,timeout, unit);
            log.debug("Redis 저장 성공 - key: {}",key);
        }catch(Exception e){
            log.error("Redis 저장 실패 - key: {}, error: {}",key,e.getMessage());
        }
    }

    @Override
    public String get(String key) {
        try{
            String value = redisTemplate.opsForValue().get(key);
            log.debug("Redis 조회 성공 - key: {}, found: {}",key, value !=null);
            return value;
        }catch (Exception e){
            log.error("Redis 조회 실패 - key: {}, error: {}",key,e.getMessage());
            return null;
        }
    }

    @Override
    public Boolean delete(String key) {
        try{
            Boolean result = redisTemplate.delete(key);
            log.debug("Redis 삭제 성공 - key: {}, success: {}",key, result);
            return result;
        }catch (Exception e){
            log.error("Redis 삭제 실패 - key: {}, error: {}",key,e.getMessage());
            return false;
        }
    }
}
