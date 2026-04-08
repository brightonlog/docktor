package com.ssafy.docktor.auth.service.impl;

import com.ssafy.docktor.auth.dao.AuthDao;
import com.ssafy.docktor.auth.dto.*;
import com.ssafy.docktor.auth.service.AuthService;
import com.ssafy.docktor.auth.service.RedisService;
import com.ssafy.docktor.auth.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.sql.Time;
import java.util.concurrent.TimeUnit;
@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final AuthDao authDao;
    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;
    private final RedisService redisService;

    @Override
    public LoginResponse login(LoginRequest loginRequest) {
        CorpDto corp = authDao.findByCorpCode(loginRequest.getCorpCode());
        
        if (corp == null) {
            return new LoginResponse(false, "아이디 또는 비밀번호가 일치하지 않습니다.");
        }

        // 비밀번호 검증, 암호화 하면..
//        if(!passwordEncoder.matches(loginRequest.getPassword(), corp.getPassword())){
        if(! corp.getPassword().equals(loginRequest.getPassword())){
           return new LoginResponse(false, "아이디 또는 비밀번호가 일치하지 않습니다.");
        }

        // JWT 토큰 생성 (id → corpId로 변경)
        String accessToken = jwtUtil.generateAccessToken(corp.getCorpId(), String.valueOf(corp.getCorpId()), corp.getCorpName());
        String refreshToken = jwtUtil.generateRefreshToken(corp.getCorpId());

        // Redis에 RefreshToken 저장(7일)
        String redisKey = "refresh:"+corp.getCorpId();
        redisService.save(redisKey,refreshToken,300, TimeUnit.SECONDS);

        corp.setPassword(null);

        return new LoginResponse(true, "로그인 성공", accessToken, refreshToken,corp);
    }

    @Override
    public RefreshTokenResponse refresh(RefreshTokenRequest request) {
        String refreshToken = request.getRefreshToken();

        if(!jwtUtil.validateRefreshToken(refreshToken)){
            return new RefreshTokenResponse(false,"유효하지 않는 Refresh Token 입니다.",null);
        }

        Integer corpId = jwtUtil.extractCorpId(refreshToken);

        //Redis에서 저장된 토큰 확인
        String redisKey = "refresh:" + corpId;
        String storedToken = redisService.get(redisKey);

        if(storedToken == null){
            return new RefreshTokenResponse(false, " 로그아웃된 토큰입니다.", null);
        }

        if (!storedToken.equals(refreshToken)) {
            return new RefreshTokenResponse(false,"유효하지 않은 refreshToken 입니다.",null);
        }

        CorpDto corp = authDao.findByCorpId(corpId);

        if(corp == null){
            return new RefreshTokenResponse(false,"존재하지 않는 사용자입니다.",null);
        }

        String newAccessToken = jwtUtil.generateAccessToken(
                corp.getCorpId(),
                corp.getCorpCode(),
                corp.getCorpName()
        );
        return new RefreshTokenResponse(true, "토큰 갱신 성공",newAccessToken);
    }

    @Override
    public void logout(LogoutRequest request) {
         String refreshToken = request.getRefreshToken();
         if(refreshToken == null || refreshToken.isEmpty()){
             return;
         }

         try{
             Integer corpId =jwtUtil.extractCorpId(refreshToken);

             //Redis에서 RefreshToken 삭제
             String redisKey = "refresh:"+corpId;
             redisService.delete(redisKey);
         }catch (Exception e){
             // 토큰이 유효하지 않아도 로그아웃은 성공 처리
         }
    }
}
