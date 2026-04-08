import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuthStore } from "@/stores";
import { useShipStore } from "@/stores/useShipStore";
import { getShipDetailApi } from "@/lib/api/ship";
import { getDefectListApi, getInspectListApi } from "@/lib/api/inspect";
import { Inspect } from "@/lib/types/inspect-type";

export function useShipDetail() {
    const params = useParams();
    const { accessToken,corp } = useAuthStore();

    const {
        ship,
        selectedInspect,
        selectedDefect,
        setShip,
        setShipInspects,
        setSelectedInspect,
        setSelectedDefect,
    } = useShipStore();

    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const idParam = params?.id;
        if (!idParam) return;

        const shipId = Number(Array.isArray(idParam) ? idParam[0] : idParam);

        if (isNaN(shipId)) {
            setError("유효하지 않은 선박 ID입니다.");
            setIsLoading(false);
            return;
        }

        const fetchData = async () => {
            setIsLoading(true);
            setError(null);

            try {
                const token = accessToken || "";

                // 1. Ship 데이터 가져오기
                const shipResponse = await getShipDetailApi(token, shipId);
                setShip(shipResponse.data);

                // 2. Inspect 목록 가져오기
                const inspectResponse = await getInspectListApi(token, shipId);

                if (inspectResponse && inspectResponse.length > 0) {
                    // 3. ✅ 모든 inspect의 defects를 한번에 가져오기
                    const inspectsWithDefects = await Promise.all(
                        inspectResponse.map(async (inspect: Inspect) => {
                            try {
                                const defectsResponse: any = await getDefectListApi(token, inspect.inspectId);
                                return {
                                    ...inspect,
                                    defects: defectsResponse?.data || []
                                };
                            } catch (err) {
                                console.error(`Inspect ${inspect.inspectId} 결함 조회 실패:`, err);
                                return {
                                    ...inspect,
                                    defects: []
                                };
                            }
                        })
                    );

                    // 4. ship.inspects에 defects 포함해서 저장
                    setShipInspects(inspectsWithDefects);

                    // 5. 첫번째 점검 선택
                    // setSelectedInspect(inspectsWithDefects[0]);
                }
            } catch (err) {
                console.error("데이터 조회 실패:", err);
                setError("데이터를 불러오는 중 오류가 발생했습니다.");
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();

        return () => {
            setShip(null);
            setSelectedInspect(null);
            setSelectedDefect(null);
        };

    }, [params?.id, accessToken, setShip, setShipInspects, setSelectedInspect, setSelectedDefect]);

    // ✅ 점검 선택 핸들러 (이미 defects가 있으므로 API 호출 필요 없음)
    const handleSelectInspect = useCallback((inspect: Inspect) => {
        setSelectedInspect(inspect);
        setSelectedDefect(null);
    }, [setSelectedInspect, setSelectedDefect]);

    // ship.inspects에서 inspects, selectedInspect.defects에서 defects 파생
    const inspects = ship?.inspects ?? [];
    const defects = selectedInspect?.defects ?? [];

    return {
        ship,
        corp,
        inspects,
        selectedInspect,
        setSelectedInspect,
        handleSelectInspect,
        defects,
        selectedDefect,
        setSelectedDefect,
        accessToken,
        isLoading,
        error,
        shipId: params?.id
    };
}