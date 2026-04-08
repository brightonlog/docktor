package com.ssafy.docktor.ship.controller;

import com.ssafy.docktor.ship.dto.ShipRequestDto;
import com.ssafy.docktor.ship.dto.ShipResponseDto;
import com.ssafy.docktor.ship.service.ShipService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/ships")
@RequiredArgsConstructor
public class ShipController {

    private final ShipService shipService;

    // 수정: 썸네일과 모델 파일을 별도로 받도록 수정
    @PostMapping
    public ResponseEntity<Map<String, Object>> createShip(
            @RequestPart(value = "ship") ShipRequestDto requestDto,
            @RequestPart(value = "modelFile", required = false) MultipartFile modelFile,
            @RequestPart(value = "thumbnailFile", required = false) MultipartFile thumbnailFile
    ) {
        try {
            // Service에 모델 파일과 썸네일 파일을 모두 전달
            ShipResponseDto ship = shipService.createShip(requestDto, modelFile, thumbnailFile);
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("data", ship);
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (Exception e) {
            e.printStackTrace(); // 에러 로그 확인용
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(response);
        }
    }

    @GetMapping
    public ResponseEntity<Map<String, Object>> getShipList(
            @RequestParam(value = "search", required = false) String search,
            @RequestParam(value = "page", defaultValue = "1") int page,
            @RequestParam(value = "limit", defaultValue = "10") int limit
    ) {
        Map<String, Object> result = shipService.getShipList(search, page, limit);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/{shipId}")
    public ResponseEntity<Map<String, Object>> getShipById(@PathVariable(name = "shipId") Integer shipId) {
        try {
            ShipResponseDto ship = shipService.getShipById(shipId);
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("data", ship);
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
        }
    }

    @PutMapping("/{shipId}")
    public ResponseEntity<Map<String, Object>> updateShip(
            @PathVariable("shipId") Integer shipId,
            @RequestPart(value = "ship") ShipRequestDto requestDto,
            @RequestPart(value = "modelFile", required = false) MultipartFile modelFile,
            @RequestPart(value = "thumbnailFile", required = false) MultipartFile thumbnailFile
    ){
        try {
            ShipResponseDto ship = shipService.updateShip(shipId, requestDto, modelFile, thumbnailFile);
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("data", ship);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(response);
        }
    }

    @DeleteMapping("/{shipId}")
    public ResponseEntity<Map<String, Object>> deleteShip(@PathVariable(name = "shipId") Integer shipId) {
        try {
            shipService.deleteShip(shipId);
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "선박이 삭제되었습니다.");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> response = new HashMap<>();
            response.put("success", false);
            response.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }
}