import { authenticatedFetch } from './client';
import { ShipListParams, ShipListResponse, Ship } from '../types/ship-types';

// 🔹 배 목록 조회
export async function getShipListApi(
    token: string,
    params?: ShipListParams
) {
    const queryParams = new URLSearchParams();

    if (params?.search) queryParams.append('search', params.search);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const query = queryParams.toString();
    const endpoint = query ? `/api/ships?${query}` : '/api/ships';
    return authenticatedFetch<ShipListResponse>(endpoint, token, {
        method: 'GET',
    });
}

// 🔹 배 상세 조회
export async function getShipDetailApi(token: string, shipId: number) {
    return authenticatedFetch<Ship>(`/api/ships/${shipId}`, token, {
        method: 'GET',
    });
}

// 🔹 배 생성
export async function createShipApi(token: string, shipData: Partial<Ship>) {
    return authenticatedFetch<Ship>('/api/ships', token, {
        method: 'POST',
        body: JSON.stringify(shipData),
    });
}

// 🔹 배 수정
export async function updateShipApi(
    token: string,
    shipId: number,
    shipData: Partial<Ship>
) {
    return authenticatedFetch<Ship>(`/api/ships/${shipId}`, token, {
        method: 'PUT',
        body: JSON.stringify(shipData),
    });
}

// 🔹 배 삭제
export async function deleteShipApi(token: string, shipId: number) {
    return authenticatedFetch<void>(`/api/ships/${shipId}`, token, {
        method: 'DELETE',
    });
}