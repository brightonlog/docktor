'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { setTokenManager } from '@/lib/api/client';
import { useAuthStore } from '@/stores/useAuthStore';

export function TokenManagerProvider({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const { accessToken, refreshToken, setAccessToken, logout } = useAuthStore();

    useEffect(() => {
        // 토큰 매니저 설정
        setTokenManager({
            getAccessToken: () => accessToken,
            getRefreshToken: () => refreshToken,
            setAccessToken: setAccessToken,
            logout: logout,
            redirectToLogin: () => router.push('/'),
        });
    }, [accessToken, refreshToken, setAccessToken, logout, router]);

    return <>{children}</>;
}
