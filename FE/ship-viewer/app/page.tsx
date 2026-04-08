"use client"

import React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Anchor, Shield, Eye, EyeOff, Award as IdCard } from "lucide-react"
import { useLogin } from "@/hooks/use-login" // 훅 불러오기

export default function LoginPage() {
  // 로그인 훅, hooks/use-login.tx
  // 함수 분리
  const { corpCode, setCorpCode, password, setPassword,showPassword, setShowPassword, isLoading, handleLogin } = useLogin()

return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 mb-4">
            <Anchor className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-foreground">Docktor</h1>
          <p className="text-muted-foreground mt-1">AI 기반 선박 결함 탐지 시스템</p>
        </div>

        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl">로그인</CardTitle>
            <CardDescription>
              사번과 비밀번호를 입력하여 선박 검사를 시작하세요
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="employeeId">사번</Label>
                <div className="relative">
                  <Input
                    id="corpCode"
                    type="text"
                    placeholder="EMP-12345"
                    value={corpCode}
                    onChange={(e) => setCorpCode(e.target.value)}
                    className="bg-input/50 pl-10"
                    required
                  />
                  <IdCard className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">비밀번호</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="비밀번호를 입력하세요"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-input/50 pr-10"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" className="rounded border-border" />
                  <span className="text-muted-foreground">로그인 상태 유지</span>
                </label>
                <a href="#" className="text-primary hover:underline">
                  비밀번호 찾기
                </a>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    로그인 중...
                  </div>
                ) : (
                  "로그인"
                )}
              </Button>
            </form>

            {/* Security Notice */}
            <div className="mt-6 pt-4 border-t border-border">
              <div className="flex items-start gap-3 text-xs text-muted-foreground">
                <Shield className="w-4 h-4 mt-0.5 text-accent" />
                <p>
                  이 시스템은 인가된 검사원만 접근할 수 있습니다.
                  
                  모든 활동은 보안 목적으로 기록됩니다.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          SSAFY 2학기 공통 프로젝트 | Docktor
        </p>
      </div>
    </div>
  )
}
