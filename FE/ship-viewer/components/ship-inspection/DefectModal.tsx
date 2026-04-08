'use client';

import { useState } from "react";
import { format } from "date-fns";
import {
  X,
  Calendar,
  MapPin,
  Maximize2,
  Crosshair,
  Info,
  AlertTriangle
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTitle as VisuallyHiddenTitle // 접근성용 (화면에 안보이게)
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// 타입 임포트
import { Defect } from "@/lib/types/inspect-type";

interface DefectModalProps {
  open: boolean;
  onClose: () => void;
  defect: Defect | null;
  sectionName?: string;
  inspectTime?: string | null;
}

const customStyles = {
  textPrimary: {
    color: '#1e293b', // slate-800 계열의 진한 색상
  },
  textSecondary: {
    color: '#00509D', // slate-500 계열의 보조 색상
  }
};

export default function DefectModal({
                                      open,
                                      onClose,
                                      defect,
                                      sectionName,
                                      inspectTime
                                    }: DefectModalProps) {

  // 이미지 확대용 상태
  const [isImageExpanded, setIsImageExpanded] = useState(false);

  if (!defect) return null;

  // 신뢰도 색상 헬퍼
  const getConfidenceColor = (conf: number) => {
    if (conf >= 80) return "text-green-500 bg-green-500/10 border-green-200";
    if (conf >= 50) return "text-amber-500 bg-amber-500/10 border-amber-200";
    return "text-red-500 bg-red-500/10 border-red-200";
  };

  const confidenceStyle = getConfidenceColor(defect.confidence);

  return (
      <>
        {/* 1. 메인 결함 상세 모달 */}
        <Dialog open={open} onOpenChange={(val) => !val && onClose()}>
          <DialogContent className="max-w-4xl p-0 overflow-hidden bg-white border-slate-200 shadow-2xl">

            <DialogHeader className="p-6 pb-0 border-b border-slate-100 bg-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <DialogTitle className="text-xl font-bold text-slate-800">
                    결함 상세 정보
                  </DialogTitle>
                </div>
              </div>
              <DialogDescription className="hidden">
                선택된 결함의 상세 정보를 확인합니다.
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-1 md:grid-cols-2 h-full min-h-[450px]">

              {/* [좌측] 이미지 영역 */}
              <div className="relative bg-slate-900 flex items-center justify-center p-4 overflow-hidden group">
                <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px]"></div>

                {defect.croppedImageUrl ? (
                    <div className="relative w-full h-full flex items-center justify-center">
                      <img
                          src={defect.croppedImageUrl}
                          alt="Defect Detail"
                          className="max-w-full max-h-[400px] object-contain rounded shadow-lg border border-slate-700"
                      />

                      <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <button
                            onClick={() => setIsImageExpanded(true)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-black/70 hover:bg-black/90 text-white text-xs rounded-full backdrop-blur-sm transition-all shadow-lg border border-white/10"
                        >
                          <Maximize2 size={12} /> 크게 보기
                        </button>
                      </div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center text-slate-500">
                      <AlertTriangle size={48} className="mb-2 opacity-50" />
                      <p>이미지 정보 없음</p>
                    </div>
                )}
              </div>

              {/* [우측] 정보 영역 */}
              <div className="p-6 flex flex-col gap-6 bg-slate-50/50">

                {defect.categoryId === 10 ? (
                  // categoryId가 10일 때: 중앙 정렬
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center space-y-2">
                      <h4 className="text-sm font-semibold text-slate-500 mb-1 flex items-center justify-center gap-1">
                        <Info size={14} /> 결함 유형
                      </h4>
                      <div className="text-2xl font-bold text-slate-800">
                        {defect.categoryNameKr || defect.categoryName || "미식별 결함"}
                      </div>
                    </div>
                  </div>
                ) : (
                  // categoryId가 10이 아닐 때: 기존 레이아웃
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-500 mb-1 flex items-center gap-1">
                        <Info size={14} /> 결함 유형
                      </h4>
                      <div className="text-2xl font-bold text-slate-800">
                        {defect.categoryNameKr || defect.categoryName || "미식별 결함"}
                      </div>
                    </div>

                    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-slate-600">AI 분석 신뢰도</span>
                        <span className={`text-sm font-bold px-2 py-0.5 rounded border ${confidenceStyle}`}>
                        {Number(defect.confidence * 100).toFixed(1)}%
                      </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                        <div
                            className={`h-2.5 rounded-full transition-all duration-500 ${
                                defect.confidence * 100 >= 80 ? 'bg-green-500' :
                                    defect.confidence * 100 >= 50 ? 'bg-amber-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${Math.min(defect.confidence * 100, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )}

                <Separator className="bg-slate-200" />

                <div className="flex flex-col gap-y-5">
                  {/* 정보 그룹 (시간 & 구역) */}
                  <div className="space-y-4">
                    {/* 검사 시간 */}
                    <div className="flex flex-col gap-y-1.5">
                      <div className="flex items-center gap-1.5 text-slate-500">
                        <Calendar size={14} />
                        <span className="text-xs font-semibold">검사 시간</span>
                      </div>
                      <p className="ml-[20px] text-[15px] font-bold text-slate-900">
                        {inspectTime
                          ? format(new Date(inspectTime), "yyyy.MM.dd HH:mm")
                          : format(new Date(defect.createDate), "yyyy.MM.dd HH:mm")}
                      </p>
                    </div>

                    {/* 발견 구역 */}
                    <div className="flex flex-col gap-y-1.5">
                      <div className="flex items-center gap-1.5 text-slate-500">
                        <MapPin size={14} />
                        <span className="text-xs font-semibold">발견 구역</span>
                      </div>
                      <p className="ml-[20px] text-[15px] font-bold text-slate-900 uppercase">
                        {sectionName || "-"}
                      </p>
                    </div>
                  </div>

                  {/* 좌표 정보 - 구조는 유지하되 폰트와 박스 스타일 복구 */}
                  <div className="flex flex-col gap-y-2.5 pt-3 border-t border-slate-100">
                    <div className="flex items-center gap-1.5 text-slate-500">
                      <Crosshair size={14} />
                      <span className="text-xs font-semibold">좌표 정보</span>
                    </div>

                    <div className="ml-[20px] flex items-center gap-x-2">
                      {/* X 좌표 박스 */}
                      <div className="flex items-center gap-x-2 bg-slate-50 px-2.5 py-1.5 rounded border border-slate-200 text-xs shadow-sm">
                        <span className="font-bold text-slate-400">X</span>
                        <span className="font-bold text-slate-900 text-[14px]">
                          {defect?.xcord != null ? Number(defect.xcord).toFixed(0) : "0"}
                        </span>
                      </div>

                      {/* 구분선 (얇게) */}
                      <div className="w-[1px] h-3 bg-slate-200 mx-1" />

                      {/* Y 좌표 박스 */}
                      <div className="flex items-center gap-x-2 bg-slate-50 px-2.5 py-1.5 rounded border border-slate-200 text-xs shadow-sm">
                        <span className="font-bold text-slate-400">Y</span>
                        <span className="font-bold text-slate-900 text-[14px]">
                          {defect?.ycord != null ? Number(defect.ycord).toFixed(0) : "0"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* 2. [수정] 이미지 전체 화면용 별도 Dialog (중첩 모달) */}
        <Dialog open={isImageExpanded} onOpenChange={setIsImageExpanded}>
          <DialogContent
              className="max-w-[95vw] max-h-[95vh] w-auto h-auto p-0 bg-transparent border-none shadow-none flex items-center justify-center focus:outline-none"
              // 기본 닫기 버튼 숨김 (커스텀 버튼 사용)
              onInteractOutside={() => setIsImageExpanded(false)}
          >
            {/* 접근성 타이틀 (숨김) */}
            <DialogHeader className="sr-only">
              <DialogTitle>확대 이미지</DialogTitle>
              <DialogDescription>결함 이미지 원본 확대 보기</DialogDescription>
            </DialogHeader>

            <div className="relative">
              {/* 닫기 버튼 */}
              <button
                  onClick={() => setIsImageExpanded(false)}
                  className="absolute -top-12 right-0 p-2 bg-white/20 hover:bg-white/40 text-white rounded-full transition-colors z-50 backdrop-blur-md"
              >
                <X size={24} />
              </button>

              {/* 확대 이미지 */}
              {defect.croppedImageUrl && (
                  <img
                      src={defect.croppedImageUrl}
                      alt="Expanded Defect"
                      className="max-w-[90vw] max-h-[85vh] object-contain rounded-md shadow-2xl"
                  />
              )}
            </div>
          </DialogContent>
        </Dialog>
      </>
  );
}