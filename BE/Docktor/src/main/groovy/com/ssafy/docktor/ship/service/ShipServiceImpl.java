package com.ssafy.docktor.ship.service;

import com.ssafy.docktor.ship.dao.ShipDao;
import com.ssafy.docktor.ship.dto.Ship;
import com.ssafy.docktor.ship.dto.ShipRequestDto;
import com.ssafy.docktor.ship.dto.ShipResponseDto;
import com.ssafy.docktor.common.service.S3Service; // S3 서비스가 있다고 가정
import com.ssafy.docktor.ship.dao.SectionDao;    // 구역 DAO 필요
import com.ssafy.docktor.ship.dao.FileDao;       // 파일 DAO 필요
import com.ssafy.docktor.common.tenant.TenantContext; // 추가

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ShipServiceImpl implements ShipService {

    private final ShipDao shipDao;
    private final SectionDao sectionDao;
    private final FileDao fileDao;
    private final S3Service s3Service;

    @Override
    @Transactional
    public ShipResponseDto createShip(ShipRequestDto requestDto, MultipartFile modelFile, MultipartFile thumbnailFile) {
        // 1. 현재 사용자의 Corp ID 가져오기
        Integer corpId = TenantContext.getCurrentTenant();
        if (corpId == null) {
            throw new IllegalStateException("로그인이 필요합니다.");
        }

        // 2. 선박 정보 빌드 및 저장
        Ship ship = Ship.builder()
                .corpId(corpId)  // requestDto가 아닌 TenantContext에서 가져온 값 사용
                .name(requestDto.getName())
                .classNo(requestDto.getClassNo())
                .imo(requestDto.getImo())
                .classNotation(requestDto.getClassNotation())
                .flagState(requestDto.getFlagState())
                .port(requestDto.getPort())
                .ton(requestDto.getTon())
                .deadWeight(requestDto.getDeadWeight())
                .lbp(requestDto.getLbp())
                .shipbuilder(requestDto.getShipbuilder())
                .hullNumber(requestDto.getHullNumber())
                .deliveryDate(requestDto.getDeliveryDate())
                .buildDate(requestDto.getBuildDate())
                .build();

        shipDao.insertShip(ship);
        Integer shipId = ship.getShipId();

        // 3. 기본 구역(Section) 자동 생성
        createDefaultSections(shipId);

        // 4. 모델링 파일(.glb) S3 업로드 및 File 테이블 저장
        String modelFileUrl = null;

        if (modelFile != null && !modelFile.isEmpty()) {
            try {
                String originalFilename = modelFile.getOriginalFilename();
                String s3Path = String.format("corp_%d/ships/%d/model/%s", corpId, shipId, originalFilename);

                System.out.println("========== 모델 파일 업로드 시작 ==========");
                System.out.println("원본 파일명: " + originalFilename);
                System.out.println("S3 경로: " + s3Path);

                // S3 업로드 실행 및 URL 저장
                modelFileUrl = s3Service.uploadFile(modelFile, s3Path);

                System.out.println("업로드된 모델 파일 URL: " + modelFileUrl);
                System.out.println("URL에 '/model/' 포함 여부: " + (modelFileUrl != null && modelFileUrl.contains("/model/")));

                // DB에 기록 (모델 파일)
                fileDao.insertFile("ship", shipId, modelFileUrl);

                System.out.println("DB 저장 완료 - table: ship, tableId: " + shipId);
                System.out.println("========================================");

            } catch (Exception e) {
                e.printStackTrace();
                throw new RuntimeException("모델 파일 업로드 중 오류 발생");
            }
        } else {
            System.out.println("모델 파일이 제공되지 않음");
        }

        // 5. 썸네일 파일 S3 업로드 및 File 테이블 저장
        String thumbnailUrl = null;

        if (thumbnailFile != null && !thumbnailFile.isEmpty()) {
            try {
                String originalFilename = thumbnailFile.getOriginalFilename();
                // 썸네일은 경로에 'thumbnail' 포함
                String s3Path = String.format("corp_%d/ships/%d/thumbnail/%s", corpId, shipId, originalFilename);

                System.out.println("========== 썸네일 파일 업로드 시작 ==========");
                System.out.println("원본 파일명: " + originalFilename);
                System.out.println("S3 경로: " + s3Path);

                // S3 업로드 실행 및 URL 저장
                thumbnailUrl = s3Service.uploadFile(thumbnailFile, s3Path);

                System.out.println("업로드된 썸네일 URL: " + thumbnailUrl);
                System.out.println("URL에 '/thumbnail/' 포함 여부: " + (thumbnailUrl != null && thumbnailUrl.contains("/thumbnail/")));

                // DB에 기록 (썸네일 파일)
                fileDao.insertFile("ship", shipId, thumbnailUrl);

                System.out.println("DB 저장 완료 - table: ship, tableId: " + shipId);
                System.out.println("========================================");

            } catch (Exception e) {
                e.printStackTrace();
                throw new RuntimeException("썸네일 파일 업로드 중 오류 발생");
            }
        } else {
            System.out.println("썸네일 파일이 제공되지 않음");
        }

        // 6. 응답 반환
        System.out.println("========== 응답 생성 ==========");
        System.out.println("shipId: " + shipId);
        System.out.println("modelFileUrl (반환 예정): " + modelFileUrl);
        System.out.println("thumbnailUrl (반환 예정): " + thumbnailUrl);
        System.out.println("================================");

        return ShipResponseDto.from(ship, modelFileUrl, thumbnailUrl);
    }

    private void createDefaultSections(Integer shipId) {
        sectionDao.insertSection(shipId, "Front", "선수 (Bow)");
        sectionDao.insertSection(shipId, "Back", "선미 (Stern)");
        sectionDao.insertSection(shipId, "Port", "좌현");
        sectionDao.insertSection(shipId, "Starboard", "우현");
    }

    @Override
    public Map<String, Object> getShipList(String search, int page, int limit) {
        // 현재 사용자의 Corp ID 가져오기
        Integer corpId = TenantContext.getCurrentTenant();
        if (corpId == null) {
            throw new IllegalStateException("로그인이 필요합니다.");
        }

        int offset = (page - 1) * limit;

        // DAO 호출 시 corpId 전달
        List<Ship> ships = shipDao.selectShipList(corpId, search, offset, limit);
        int totalCount = shipDao.selectShipCount(corpId, search);

        List<ShipResponseDto> shipDtos = ships.stream()
                .map(ship -> {
                    // 모델 파일 URL 조회
                    String modelFileUrl = fileDao.selectModelPathByTableId("ship", ship.getShipId());
                    // 썸네일 파일 URL 조회
                    String thumbnailUrl = fileDao.selectThumbnailPathByTableId("ship", ship.getShipId());
                    return ShipResponseDto.from(ship, modelFileUrl, thumbnailUrl);
                })
                .collect(Collectors.toList());

        Map<String, Object> result = new HashMap<>();
        result.put("ships", shipDtos);
        result.put("totalCount", totalCount);
        result.put("currentPage", page);
        result.put("totalPages", (int) Math.ceil((double) totalCount / limit));

        return result;
    }

    @Override
    public ShipResponseDto getShipById(Integer id) {
//        // 현재 사용자의 Corp ID 가져오기
//        Integer corpId = TenantContext.getCurrentTenant();
//        Integer corpId = 1;
//        if (corpId == null) {
//            throw new IllegalStateException("로그인이 필요합니다.");
//        }
//
//        // DAO 호출 시 corpId 전달
        Ship ship = shipDao.selectShipById(id, null);
//        if (ship == null) {

//            throw new IllegalArgumentException("해당 ID의 선박이 존재하지 않거나 접근 권한이 없습니다: " + id);
//        }
//
        // 3D 모델 파일 URL 조회 (경로에 'model' 포함)
        String modelFileUrl = fileDao.selectModelPathByTableId("ship", id);
        // 썸네일 파일 URL 조회 (경로에 'thumbnail' 포함)
        String thumbnailUrl = fileDao.selectThumbnailPathByTableId("ship", id);

        // modelFileUrl, thumbnailUrl 포함하여 반환
        return ShipResponseDto.from(ship, modelFileUrl, thumbnailUrl);
    }

    // 사용 X
    @Override
    public ShipResponseDto updateShip(Integer id, ShipRequestDto requestDto, MultipartFile modelFile, MultipartFile thumbnailFile) {
        return null;
    }

    // 선박 삭제
    @Override
    @Transactional
    public void deleteShip(Integer id) {
        // 현재 사용자의 Corp ID 가져오기
        Integer corpId = TenantContext.getCurrentTenant();
        if (corpId == null) {
            throw new IllegalStateException("로그인이 필요합니다.");
        }

        // DAO 호출 시 corpId 전달하여 삭제
        int result = shipDao.deleteShip(id, corpId);

        if (result == 0) {
            throw new IllegalArgumentException("해당 ID의 선박이 존재하지 않거나 접근 권한이 없습니다: " + id);
        }
    }
}