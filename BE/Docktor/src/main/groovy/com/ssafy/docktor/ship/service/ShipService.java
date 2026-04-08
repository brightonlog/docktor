package com.ssafy.docktor.ship.service;
import com.ssafy.docktor.ship.dto.ShipRequestDto;
import com.ssafy.docktor.ship.dto.ShipResponseDto;
import org.springframework.web.multipart.MultipartFile;
import java.util.Map;

public interface ShipService {

    ShipResponseDto createShip(ShipRequestDto requestDto, MultipartFile modelFile, MultipartFile thumbnailFile);

    Map<String, Object> getShipList(String search, int page, int limit);

    ShipResponseDto getShipById(Integer id);

    ShipResponseDto updateShip(Integer id, ShipRequestDto requestDto, MultipartFile modelFile, MultipartFile thumbnailFile);

    void deleteShip(Integer id);
}