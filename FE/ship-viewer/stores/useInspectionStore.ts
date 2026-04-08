'use client';

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  SelectedArea,
  InspectionState,
  WallDirection,
  WallSection
} from '@/lib/inspection-types';
import { DEFAULT_INSPECTION_STATE } from '@/lib/inspection-types';

interface InspectionStore {
  // 상태
  selectedArea: SelectedArea | null;
  isSelectingCustom: boolean;
  inspectionState: InspectionState;

  // 액션
  setSelectedArea: (area: SelectedArea | null) => void;
  setIsSelectingCustom: (value: boolean) => void;
  updateInspectionState: (partial: Partial<InspectionState>) => void;
  resetInspectionState: () => void;

  // 복합 액션
  startCalibration: () => void;
  startInspection: () => void;
  stopInspection: () => void;
  completeInspection: () => void;
}

export const useInspectionStore = create<InspectionStore>()(
  devtools(
    (set, get) => ({
      // 초기 상태
      selectedArea: null,
      isSelectingCustom: false,
      inspectionState: DEFAULT_INSPECTION_STATE,

      // 기본 액션
      setSelectedArea: (area) => set({ selectedArea: area }),
      setIsSelectingCustom: (value) => set({ isSelectingCustom: value }),
      updateInspectionState: (partial) =>
        set((state) => ({
          inspectionState: { ...state.inspectionState, ...partial }
        })),
      resetInspectionState: () =>
        set({ inspectionState: DEFAULT_INSPECTION_STATE }),

      // 복합 액션
      startCalibration: () =>
        set((state) => ({
          inspectionState: { ...state.inspectionState, isCalibrated: true }
        })),

      startInspection: () => {
        const { selectedArea, inspectionState } = get();
        if (!selectedArea || !inspectionState.isCalibrated) return;

        set((state) => ({
          inspectionState: {
            ...state.inspectionState,
            isInspecting: true,
            progress: 0
          }
        }));
      },

      stopInspection: () =>
        set((state) => ({
          inspectionState: { ...state.inspectionState, isInspecting: false }
        })),

      completeInspection: () =>
        set((state) => ({
          inspectionState: {
            ...state.inspectionState,
            isInspecting: false,
            progress: 100
          }
        })),
    }),
    { name: 'inspection-store' }
  )
);
