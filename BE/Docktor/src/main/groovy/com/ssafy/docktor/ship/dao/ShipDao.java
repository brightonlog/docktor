package com.ssafy.docktor.ship.dao;

import com.ssafy.docktor.ship.dto.Ship;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 선박 DAO (MyBatis Mapper Interface)
 */
@Mapper
public interface ShipDao {

    int insertShip(Ship ship);

    List<Ship> selectShipList(
            @Param("corpId") Integer corpId,
            @Param("search") String search,
            @Param("offset") int offset,
            @Param("limit") int limit
    );

    int selectShipCount(
            @Param("corpId") Integer corpId,
            @Param("search") String search
    );

    Ship selectShipById(
            @Param("shipId") Integer shipId,
            @Param("corpId") Integer corpId
    );

    int updateShip(Ship ship);

    int deleteShip(
            @Param("shipId") Integer shipId,
            @Param("corpId") Integer corpId
    );
}