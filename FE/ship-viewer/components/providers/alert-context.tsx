"use client"

import React, { createContext, useContext, useState, useCallback, useRef } from "react"
import { AlertTriangle, CheckCircle, Info, X } from "lucide-react"

// 알림창 옵션 타입
interface AlertOptions {
    title?: string
    message: React.ReactNode
    type?: "info" | "success" | "warning" | "error"
    confirmText?: string
    cancelText?: string
}

interface AlertContextType {
    alert: (message: string, options?: Omit<AlertOptions, "message">) => Promise<boolean>
    confirm: (message: string, options?: Omit<AlertOptions, "message">) => Promise<boolean>
}

const AlertContext = createContext<AlertContextType | undefined>(undefined)

export function AlertProvider({ children }: { children: React.ReactNode }) {
    const [isOpen, setIsOpen] = useState(false)
    const [config, setConfig] = useState<AlertOptions & { isConfirm: boolean }>({
        message: "",
        isConfirm: false,
    })

    // 사용자의 응답(resolve)을 저장할 ref
    const resolveRef = useRef<(value: boolean) => void>(() => {})

    const openDialog = useCallback((isConfirm: boolean, message: string, options?: Omit<AlertOptions, "message">) => {
        setConfig({
            message,
            isConfirm,
            title: options?.title,
            type: options?.type || "info",
            confirmText: options?.confirmText || "확인",
            cancelText: options?.cancelText || "취소",
        })
        setIsOpen(true)

        // Promise 반환: 사용자가 버튼을 누를 때까지 대기
        return new Promise<boolean>((resolve) => {
            resolveRef.current = resolve
        })
    }, [])

    const handleConfirm = () => {
        setIsOpen(false)
        resolveRef.current(true)
    }

    const handleCancel = () => {
        setIsOpen(false)
        resolveRef.current(false)
    }

    // --- UI 렌더링 부분 (CSS Variables 활용) ---
    const getIcon = () => {
        switch (config.type) {
            case "error": return <AlertTriangle className="w-6 h-6 text-[var(--inspection-accent-red)]" />
            case "warning": return <AlertTriangle className="w-6 h-6 text-[var(--inspection-accent-amber)]" />
            case "success": return <CheckCircle className="w-6 h-6 text-[var(--inspection-accent-green)]" />
            default: return <Info className="w-6 h-6 text-[var(--inspection-accent-navy)]" />
        }
    }

    return (
        <AlertContext.Provider
            value={{
                alert: (msg, opts) => openDialog(false, msg, opts),
                confirm: (msg, opts) => openDialog(true, msg, opts),
            }}
        >
            {children}

            {/* 모달 오버레이 및 컨텐츠 */}
            {isOpen && (
                <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-[2px] animate-in fade-in duration-200">
                    <div
                        className="w-[400px] max-w-[90vw] bg-[var(--inspection-bg-primary)] border border-[var(--inspection-border-color)] rounded-2xl shadow-[var(--inspection-shadow)] overflow-hidden animate-in zoom-in-95 duration-200"
                        style={{ fontFamily: "var(--font-pretendard)" }}
                    >
                        {/* 헤더 */}
                        <div className="px-6 py-4 border-b border-[var(--inspection-border-color)] flex items-center gap-3 bg-[var(--inspection-bg-secondary)]">
                            {getIcon()}
                            <span className="font-semibold text-lg text-[var(--inspection-text-primary)]">
                {config.title || (config.type === 'error' ? '오류' : config.type === 'warning' ? '주의' : '알림')}
              </span>
                        </div>

                        {/* 본문 */}
                        <div className="p-6">
                            <p className="text-[15px] text-[var(--inspection-text-secondary)] leading-relaxed whitespace-pre-wrap">
                                {config.message}
                            </p>
                        </div>

                        {/* 푸터 (버튼 영역) */}
                        <div className="flex gap-3 p-4 bg-[var(--inspection-bg-tertiary)] justify-end">
                            {config.isConfirm && (
                                <button
                                    onClick={handleCancel}
                                    className="px-4 py-2 rounded-lg text-sm font-medium transition-all hover:bg-black/5 text-[var(--inspection-text-secondary)]"
                                >
                                    {config.cancelText}
                                </button>
                            )}
                            <button
                                onClick={handleConfirm}
                                className={`px-6 py-2 rounded-lg text-sm font-medium text-white shadow-sm transition-transform active:scale-95 ${
                                    config.type === 'error' ? 'bg-[var(--inspection-accent-red)] hover:bg-red-600' :
                                        config.type === 'success' ? 'bg-[var(--inspection-accent-green)] hover:bg-green-600' :
                                            'bg-[var(--inspection-accent-navy)] hover:opacity-90'
                                }`}
                            >
                                {config.confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </AlertContext.Provider>
    )
}

// Custom Hook
export const useAlert = () => {
    const context = useContext(AlertContext)
    if (!context) {
        throw new Error("useAlert must be used within an AlertProvider")
    }
    return context
}