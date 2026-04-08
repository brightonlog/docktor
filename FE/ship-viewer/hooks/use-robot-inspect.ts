"use client"

import { useState, useEffect, useCallback } from "react"
import { toast } from "sonner"
import { useAlert } from "@/components/providers/alert-context"
import { startRobotInspection, getInspectListApi, getDefectListApi } from "@/lib/api/inspect"
import { useShipStore } from "@/stores"
import { DEFAULT_INSPECTION_STATE } from "@/lib/inspection-types"
import type { InspectionState, SelectedArea } from "@/lib/inspection-types"
import type { Inspect } from "@/lib/types/inspect-type"

interface UseRobotInspectionProps {
    shipId: string
    accessToken: string | null
    corpId: number
    selectedArea: SelectedArea | null
    onInspectionComplete?: (foundInspect: Inspect) => void
}

export function useRobotInspection({
                                       shipId,
                                       accessToken,
                                       corpId,
                                       selectedArea,
                                       onInspectionComplete
                                   }: UseRobotInspectionProps) {
    const { alert, confirm } = useAlert()
    // 1. Store 액션 가져오기
    const { updateShipInspects } = useShipStore()

    const [inspectionState, setInspectionState] = useState<InspectionState>(DEFAULT_INSPECTION_STATE)
    const [currentInspectId, setCurrentInspectId] = useState<number | null>(null)

    // SSE 연결 로직 (이전과 동일)
    useEffect(() => {
        if (!currentInspectId) return

        const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL
        const sseUrl = `${API_URL}/api/sse/subscribe/${currentInspectId}`

        console.log(`📡 SSE 연결 시도: ${sseUrl}`)
        const eventSource = new EventSource(sseUrl)

        eventSource.onmessage = (event) => {
            try {
                if (event.data.includes("connect")) return

                const data = JSON.parse(event.data)

                if (data.status === 'completed' && Number(data.inspectId) === currentInspectId) {
                    handleInspectionFinish(currentInspectId)
                    eventSource.close()
                } else if (data.status === 'failed') {
                    toast.error(`검사 실패: ${data.error}`)
                    setInspectionState(prev => ({ ...prev, isInspecting: false }))
                    setCurrentInspectId(null)
                    eventSource.close()
                }
            } catch (e) {
                console.warn("SSE 파싱 경고:", event.data)
            }
        }

        eventSource.onerror = (e) => {
            eventSource.close()
        }

        return () => {
            eventSource.close()
        }
    }, [currentInspectId])

    // ----------------------------------------------------------------------
    // 검사 완료 후 데이터 처리 (핵심 수정 부분)
    // ----------------------------------------------------------------------
    const handleInspectionFinish = useCallback(async (completedInspectId: number) => {
        const token = accessToken || ""

        // 상태 초기화
        setInspectionState(prev => ({ ...prev, isInspecting: false, progress: 100 }))
        setCurrentInspectId(null)

        try {
            // 1. 최신 검사 목록 조회
            const inspectResponse = await getInspectListApi(token, Number(shipId))

            if (inspectResponse && inspectResponse.length > 0) {
                // 2. 각 검사의 결함 정보까지 모두 조회 (비동기 병렬 처리)
                const inspectsWithDefects = await Promise.all(inspectResponse.map(async (inspect: Inspect) => {
                    try {
                        const defectsResponse: any = await getDefectListApi(token, inspect.inspectId)
                        return { ...inspect, defects: defectsResponse?.data || [] }
                    } catch (err) {
                        return { ...inspect, defects: [] }
                    }
                }))

                // [요청 1 반영] Store의 ship.inspects를 최신 리스트로 갱신
                updateShipInspects(inspectsWithDefects)

                // 방금 완료된 검사 찾기
                const foundInspect = inspectsWithDefects.find(i => Number(i.inspectId) === Number(completedInspectId))

                if (foundInspect) {
                    // [요청 2 반영] Alert 대신 Confirm 사용
                    const shouldMove = await confirm(
                        '검사가 완료되었습니다.\n해당 검사 결과로 이동하시겠습니까?',
                        {
                            title: '검사 완료',
                            type: 'success',
                            confirmText: '결과 보기',
                            cancelText: '닫기'
                        }
                    )

                    if (shouldMove && onInspectionComplete) {
                        // '예'를 누르면 콜백 실행 -> Page에서 화면 전환 및 마커 표시
                        onInspectionComplete(foundInspect)
                    } else {
                        toast.success('검사 이력이 저장되었습니다.')
                    }
                } else {
                    toast.error("검사 결과 동기화 중 문제가 발생했습니다.")
                }
            } else {
                updateShipInspects([])
            }

        } catch (e) {
            console.error("목록 갱신 실패", e)
            toast.error("데이터 갱신 실패")
        }
    }, [shipId, accessToken, updateShipInspects, onInspectionComplete, confirm])

    // 검사 시작 로직 (이전과 동일)
    const startInspection = useCallback(async () => {
        if (!selectedArea) {
            await alert('영역을 먼저 선택하세요', { type: 'warning' })
            return
        }

        let sectionId = 0
        const { wall, section } = selectedArea
        if (wall === 'full') sectionId = 5
        else if (wall === 'left') {
            if (section === 'bow') sectionId = 1; else if (section === 'stern') sectionId = 2;
        } else if (wall === 'right') {
            if (section === 'bow') sectionId = 3; else if (section === 'stern') sectionId = 4;
        }

        if (sectionId === 0) {
            await alert('올바른 구역이 아닙니다.', { type: 'warning' })
            return
        }

        const isConfirmed = await confirm('검사를 시작하시겠습니까?', {
            title: '검사 시작 확인', type: 'info', confirmText: '시작하기', cancelText: '취소'
        })
        if (!isConfirmed) return

        try {
            if (!accessToken) {
                await alert('로그인이 필요합니다.', { type: 'warning' })
                return
            }

            const requestData = {
                shipId: Number(shipId),
                sectionId: sectionId,
                startTime: new Date().toISOString(),
                corpId: corpId
            }

            const response = await startRobotInspection(accessToken, requestData)

            if (response.inspectId) {
                await alert('검사를 시작합니다.', { type: 'success' })
                setCurrentInspectId(response.inspectId)
                setInspectionState(prev => ({ ...prev, isInspecting: true, progress: 0 }))
            }
        } catch (error: any) {
            await alert('검사 요청 실패: ' + (error.message || '서버 응답 없음'), { type: 'error' })
        }
    }, [selectedArea, shipId, accessToken, corpId, alert, confirm])

    const stopInspection = useCallback(() => {
        setInspectionState(prev => ({ ...prev, isInspecting: false }))
        toast.info('검사 중지')
    }, [])

    return {
        inspectionState,
        setInspectionState,
        startInspection,
        stopInspection,
        isInspecting: inspectionState.isInspecting
    }
}