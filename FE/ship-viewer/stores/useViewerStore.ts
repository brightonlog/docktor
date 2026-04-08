'use client';

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import * as THREE from 'three';

interface ViewerStore {
  // 상태
  isPanelOpen: boolean;
  showGrid: boolean;
  showDefects: boolean;
  selectedDefect: string | null;
  shipModel: THREE.Object3D | null;
  cameraResetTrigger: number;

  // 카메라/위치 설정
  customPosition: { x: number; y: number; z: number } | null;
  customCameraOffset: [number, number, number] | null;
  customCameraFov: number;
  showPositionSettings: boolean;

  // 액션
  setIsPanelOpen: (value: boolean) => void;
  togglePanel: () => void;
  setShowGrid: (value: boolean) => void;
  setShowDefects: (value: boolean) => void;
  setSelectedDefect: (id: string | null) => void;
  setShipModel: (model: THREE.Object3D | null) => void;
  resetCamera: () => void;

  // 위치 설정 액션
  setCustomPosition: (pos: { x: number; y: number; z: number } | null) => void;
  setCustomCameraOffset: (offset: [number, number, number] | null) => void;
  setCustomCameraFov: (fov: number) => void;
  setShowPositionSettings: (value: boolean) => void;
  resetPositionSettings: () => void;
}

export const useViewerStore = create<ViewerStore>()(
  devtools(
    persist(
      (set) => ({
        // 초기 상태
        isPanelOpen: true,
        showGrid: false,
        showDefects: true,
        selectedDefect: null,
        shipModel: null,
        cameraResetTrigger: 0,
        customPosition: null,
        customCameraOffset: null,
        customCameraFov: 50,
        showPositionSettings: false,

        // 액션
        setIsPanelOpen: (value) => set({ isPanelOpen: value }),
        togglePanel: () => set((state) => ({ isPanelOpen: !state.isPanelOpen })),
        setShowGrid: (value) => set({ showGrid: value }),
        setShowDefects: (value) => set({ showDefects: value }),
        setSelectedDefect: (id) => set({ selectedDefect: id }),
        setShipModel: (model) => set({ shipModel: model }),
        resetCamera: () => set((state) => ({
          cameraResetTrigger: state.cameraResetTrigger + 1
        })),

        // 위치 설정 액션
        setCustomPosition: (pos) => set({ customPosition: pos }),
        setCustomCameraOffset: (offset) => set({ customCameraOffset: offset }),
        setCustomCameraFov: (fov) => set({ customCameraFov: fov }),
        setShowPositionSettings: (value) => set({ showPositionSettings: value }),
        resetPositionSettings: () => set({
          customPosition: { x: 0, y: 0, z: 0 },
          customCameraOffset: [25, 18, 50],
          customCameraFov: 50,
        }),
      }),
      {
        name: 'viewer-settings',
        partialize: (state) => ({
          customPosition: state.customPosition,
          customCameraOffset: state.customCameraOffset,
          customCameraFov: state.customCameraFov,
        }),
      }
    ),
    { name: 'viewer-store' }
  )
);
