import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores";
import { loginApi } from "@/lib/api/auth-temp";

export function useLogin() {
    const router = useRouter();
    const [corpCode, setCorpCode] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false)
    const [isLoading, setIsLoading] = useState(false);
    const { login: setLoginUser } = useAuthStore();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const result = await loginApi({
                corpCode: corpCode.trim(),
                password: password.trim(),
            });

            if (result.success && result.data) {
                // 서버 응답의 corpDto를 스토어에 저장
                setLoginUser(
                    result.data.corp,
                    result.data.accessToken,
                    result.data.refreshToken
                );
                router.push("/main");
            } else {
                alert(result.error || "로그인에 실패했습니다.");
            }
        } finally {
            setIsLoading(false);
        }
    };

    return {
        showPassword,
        setShowPassword,
        corpCode,
        setCorpCode,
        password,
        setPassword,
        isLoading,
        handleLogin,
    };
}