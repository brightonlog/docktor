package com.ssafy.docktor.auth.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

@Component
public class JwtUtil {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration}")
    private Long accessTokenExpiration;

    @Value("${jwt.refresh-token-expiration}")
    private long refreshTokenExpiration;

    private SecretKey getSigningKey() {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        return Keys.hmacShaKeyFor(keyBytes);
    }

    // AccessToken 생성
    public String generateAccessToken(Integer corpId, String corpCode, String corpName) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("corpId", corpId);
        claims.put("corpCode", corpCode);
        claims.put("corpName", corpName);
        claims.put("tokenType","access");

        return Jwts.builder()
                .claims(claims)
                .subject(corpCode)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + accessTokenExpiration))
                .signWith(getSigningKey())
                .compact();
    }

    public String generateRefreshToken(Integer corpId){
        Map<String,Object> claims = new HashMap<>();
        claims.put("corpId",corpId);  // 오타 수정: cordId → corpId
        claims.put("tokenType","refresh");

        return Jwts.builder()
                .setClaims(claims)
                .setSubject(corpId.toString())
                .setIssuedAt(new Date())
                .setExpiration(new Date(System.currentTimeMillis() +refreshTokenExpiration))
                .signWith(getSigningKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    // 토큰에서 사용자 정보 추출
    public Claims extractClaims(String token) {
        return Jwts.parser()
                .verifyWith(getSigningKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    // 토큰에서 corpCode 추출
    public String extractCorpCode(String token) {
        return extractClaims(token).getSubject();
    }

    // 토큰에서 corpId 추출
    public Integer extractCorpId(String token) {
        return extractClaims(token).get("corpId", Integer.class);
    }

    // 토큰 타입 추출
    public String extractTokenType(String token){
        return extractClaims(token).get("tokenType",String.class);
    }

    // AccessToken 검증
    public Boolean validateAccessToken(String token){
        try{
            Claims claims = extractClaims(token);
            String tokenType = claims.get("tokenType",String.class);
            return "access".equals(tokenType) && !isTokenExpired(token);
        }catch (Exception e){
            return false;
        }
    }

    // RefreshToken 검증
    public Boolean validateRefreshToken(String token){
        try{
            Claims claims = extractClaims(token);
            String tokenType = claims.get("tokenType",String.class);
            return "refresh".equals(tokenType) && !isTokenExpired(token);
        }catch (Exception e){
            return false;
        }
    }

    // 토큰 만료 여부 확인
    private boolean isTokenExpired(String token) {
        return extractClaims(token).getExpiration().before(new Date());
    }
}
