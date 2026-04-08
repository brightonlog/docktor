import React from "react"
import type { Metadata } from 'next'
import localFont from 'next/font/local'
import { Analytics } from '@vercel/analytics/next'
import { TokenManagerProvider } from '@/providers/TokenManagerProvider'
import { AlertProvider } from '@/components/providers/alert-context' // [!code ++] 1. import 추가
import "./globals.css"

const pretendard = localFont({
  src: [
    {
      path: '../public/fonts/Pretendard-Light.otf',
      weight: '300',
      style: 'normal',
    },
    {
      path: '../public/fonts/Pretendard-Medium.otf',
      weight: '500',
      style: 'normal',
    },
  ],
  variable: '--font-pretendard',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'DockTor - AI 선박 결함 탐지 시스템',
  description: 'AI 기반 선박 결함 탐지 로봇 시스템으로 검사 비용 60-70% 절감, 시간 83-92% 단축',
  generator: 'v0.app',
  icons: {
    icon: '/images/docktor_favicon.png',
    apple: '/images/docktor_favicon.png',
  },
}

export default function RootLayout({
                                     children,
                                   }: Readonly<{
  children: React.ReactNode
}>) {
  return (
      <html lang="ko" className={pretendard.variable}>
      <body className="antialiased">
      <TokenManagerProvider>
        {/* [!code ++] 2. AlertProvider로 children 감싸기 */}
        <AlertProvider>
          {children}
        </AlertProvider>
      </TokenManagerProvider>
      <Analytics />
      </body>
      </html>
  )
}