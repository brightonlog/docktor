'use client';

import { create } from 'zustand';
import { devtools,persist } from 'zustand/middleware';
import { Ship } from "@/lib/types/ship-types";
import {Defect, Inspect} from "@/lib/types/inspect-type"; // ✅ 변경된 타입 경로
import type { ShipInfoData } from '@/lib/inspection-types';
import type { ShipType, DefectData } from '@/components/ship-viewer/types';

export type ShipStatus = 'waiting' | 'inspecting' | 'completed';
export interface ShipListItem {
    id: string;
    name: string;
    type: string;
    modelPath: string;
    imo: string;
    status: ShipStatus;
    lastInspection: string;
    defectCount: number;
    image: string;
    description: string;
}
export interface ShipData {
    id: string;
    name: string;
    type: ShipType;
    description: string;
    systems: { id: string; name: string; number: string }[];
    defects: DefectData[];
    inspectionSummary: {
        date: string;
        duration: string;
        inspector: string;
        totalArea: string;
        defectRate: string;
        status: string;
    };
    shipInfo: ShipInfoData;
}

interface ShipStore {
    // 1. 현재 보고 있는 선박 상세 정보 (ship.inspects 안에 점검 목록 포함)
    ship: Ship | null;

    // 2. 목록에서 클릭한 특정 점검 상세 정보 (selectedInspect.defects 안에 결함 목록 포함)
    selectedInspect: Inspect | null;

    // 3. 선택된 결함
    selectedDefect: Defect | null;

    // --- Actions ---
    setShip: (ship: Ship | null) => void;
    setShipInspects: (inspects: Inspect[]) => void;  // ship.inspects 업데이트
    setSelectedInspect: (inspect: Inspect | null) => void;
    setSelectedInspectDefects: (defects: Defect[]) => void;  // selectedInspect.defects 업데이트
    updateInspectDefects: (inspectId: number, defects: Defect[]) => void;  // ship.inspects[].defects 캐싱
    setSelectedDefect: (defect: Defect | null) => void;


    // 변경 예정

    ships: ShipListItem[];

    // 현재 선박 상태
    currentShip: ShipData | null;
    isLoading: boolean;
    error: string | null;

    // 선박 목록 액션
    initializeShips: (ships: ShipListItem[]) => void;
    getShipById: (shipId: string) => ShipListItem | undefined;

    // 현재 선박 액션
    setCurrentShip: (ship: ShipData | null) => void;
    clearShip: () => void;

    // 결함 관련
    addDefect: (defect: DefectData) => void;
    removeDefect: (defectId: string) => void;
    updateDefect: (defectId: string, partial: Partial<DefectData>) => void;
    updateShipInspects: (newInspects: Inspect[]) => void;
}

export const useShipStore = create<ShipStore>()(
    devtools(
        (set,get) => ({
            // 초기값
            ship: null,
            selectedInspect: null,
            selectedDefect: null,

            // Actions 구현
            setShip: (ship) => set({ ship }),

            // ship.inspects 업데이트
            setShipInspects: (inspects) => set((state) => {
                if (!state.ship) return state;
                return {
                    ship: {
                        ...state.ship,
                        inspects: inspects
                    }
                };
            }),

            setSelectedInspect: (inspect) => set({ selectedInspect: inspect }),

            // selectedInspect.defects 업데이트
            setSelectedInspectDefects: (defects) => set((state) => {
                if (!state.selectedInspect) return state;
                return {
                    selectedInspect: {
                        ...state.selectedInspect,
                        defects: defects
                    }
                };
            }),

            // ship.inspects[].defects 캐싱 (특정 inspect의 defects 업데이트)
            updateInspectDefects: (inspectId, defects) => set((state) => {
                if (!state.ship) return state;
                return {
                    ship: {
                        ...state.ship,
                        inspects: state.ship.inspects.map((inspect) =>
                            inspect.inspectId === inspectId
                                ? { ...inspect, defects: defects }
                                : inspect
                        )
                    }
                };
            }),
            updateShipInspects: (newInspects) => set((state) => ({
                // ship이 있을 때만 inspects를 교체하고, 없으면 그대로 둠
                ship: state.ship
                    ? { ...state.ship, inspects: newInspects }
                    : null,

                // (선택사항) 기왕 하는 김에 따로 관리하는 inspects state도 같이 맞추려면:
                // inspects: newInspects
            })),
            setSelectedDefect: (defect) => set({ selectedDefect: defect }),

            ships: [],
            currentShip: null,
            isLoading: false,
            error: null,

            // 여기부턴 고쳐야함
            initializeShips: (ships) => set({ ships }),
            getShipById: (shipId) => {
                const state = get();
                return state.ships.find((ship) => ship.id === shipId);
            },

            // 현재 선박 액션
            setCurrentShip: (ship) => set({ currentShip: ship, error: null }),

            clearShip: () => set({ currentShip: null, error: null }),

            // 결함 관련
            addDefect: (defect) => set((state) => {
                if (!state.currentShip) return state;
                return {
                    currentShip: {
                        ...state.currentShip,
                        defects: [...state.currentShip.defects, defect],
                    },
                };
            }),

            removeDefect: (defectId) => set((state) => {
                if (!state.currentShip) return state;
                return {
                    currentShip: {
                        ...state.currentShip,
                        defects: state.currentShip.defects.filter((d) => d.id !== defectId),
                    },
                };
            }),

            updateDefect: (defectId, partial) => set((state) => {
                if (!state.currentShip) return state;
                return {
                    currentShip: {
                        ...state.currentShip,
                        defects: state.currentShip.defects.map((d) =>
                            d.id === defectId ? { ...d, ...partial } : d
                        ),
                    },
                };
            }),
        }),
        { name: 'ship-store' }
    )
);