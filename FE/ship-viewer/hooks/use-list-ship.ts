import {useRouter} from "next/navigation";
import {useAuthStore} from "@/stores";
import {useShipStore} from "@/stores/useShipStore";
import {useState, useEffect, useCallback} from "react";
// ShipListResponse는 API 응답 타입이므로, 파라미터용 타입이 별도로 필요합니다. (여기선 임의로 정의하거나 any로 처리)
import {Ship} from "@/lib/types/ship-types";
import {getShipListApi} from "@/lib/api/ship"

// API 요청에 사용할 파라미터 타입 정의 (필요에 따라 수정하세요)
interface FetchShipsParams {
    page?: number;
    limit?: number;

    [key: string]: any;
}

export function useShipList() {
    const router = useRouter();
    const {accessToken, refreshToken, setAccessToken, logout} = useAuthStore();

    // state 정의
    const [ships, setShips] = useState<Ship[]>([]);
    const [totalPage, setTotalPage] = useState(0);
    const [totalCount, setTotalCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1); // 초기값 1로 변경 권장
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // 검색 및 필터 state (API 연동 시 params로 넘겨야 함)
    const [searchQuery, setSearchQuery] = useState('');
    const [filterStatus, setFilterStatus] = useState<string | null>(null);

    // 2️⃣ useCallback으로 감싸서 useEffect 의존성 경고 해결 및 최적화
    const fetchShips = useCallback(async (params: FetchShipsParams = {page: 1, limit: 10}) => {
        // 토큰이 아예 없으면 로그인 유도
        // if (!accessToken) {
        // setError('로그인이 필요합니다.'); // 필요시 주석 해제
        // router.push('/'); // 페이지 진입 시점에 튕겨내려면 사용
        // return;
        // }

        setIsLoading(true);
        setError('');

        try {
            const currentToken: string = accessToken || "";
            // 첫 번째 시도
            const result = await getShipListApi(currentToken, params);

            setShips(result.ships);
            setTotalPage(result.totalPages);
            setTotalCount(result.totalCount);
            setCurrentPage(result.currentPage);

        } catch (err) {
            console.error('Fetch ships error:', err);
            setError('예상치 못한 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
        }
    }, [accessToken, refreshToken, logout, router, setAccessToken]);

    // 컴포넌트 마운트 시 자동 조회
    // accessToken이 있을 때만 실행하도록 조건부 처리
    useEffect(() => {
        fetchShips({page: 1, limit: 10});
    }, [fetchShips, accessToken]);

    return {
        ships,
        router,
        totalPage,
        setTotalPage,
        totalCount,
        currentPage,
        setCurrentPage,
        isLoading,
        error,
        // UI에서 필터 조작을 위해 아래 함수들도 반환하는 것이 좋습니다.
        searchQuery,
        setSearchQuery,
        filterStatus,
        setFilterStatus,
        fetchShips
    };
}