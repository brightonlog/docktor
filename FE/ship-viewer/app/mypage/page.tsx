"use client"

import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  ArrowLeft, 
  User, 
  Mail, 
  Phone, 
  Building2, 
  Calendar,
  FileCheck,
  AlertTriangle,
  Clock,
  Anchor
} from "lucide-react"

export default function MyPage() {
  const router = useRouter()

  const userInfo = {
    name: "김검사",
    employeeId: "EMP-12345",
    email: "inspector.kim@shipyard.com",
    phone: "010-1234-5678",
    department: "품질검사팀",
    joinDate: "2020-03-15",
    role: "선임 검사원"
  }

  const stats = {
    totalInspections: 156,
    thisMonth: 12,
    defectsFound: 47,
    avgInspectionTime: "4시간 23분"
  }

  const recentActivity = [
    { ship: "천연가스 운반선 A호", date: "2025-01-15", defects: 3, status: "completed" },
    { ship: "컨테이너선 B호", date: "2025-01-10", defects: 0, status: "completed" },
    { ship: "벌크선 E호", date: "2025-01-18", defects: 5, status: "inspecting" },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h1 className="font-bold text-lg">마이페이지</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 border border-primary/20">
              <Anchor className="w-5 h-5 text-primary" />
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-4xl">
        {/* Profile Section */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
              <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="w-12 h-12 text-primary" />
              </div>
              <div className="flex-1 text-center sm:text-left">
                <div className="flex flex-col sm:flex-row items-center gap-2 mb-2">
                  <h2 className="text-2xl font-bold text-foreground">{userInfo.name}</h2>
                  <Badge variant="secondary">{userInfo.role}</Badge>
                </div>
                <p className="text-muted-foreground mb-4">{userInfo.employeeId}</p>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center gap-2 justify-center sm:justify-start">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                    <span>{userInfo.email}</span>
                  </div>
                  <div className="flex items-center gap-2 justify-center sm:justify-start">
                    <Phone className="w-4 h-4 text-muted-foreground" />
                    <span>{userInfo.phone}</span>
                  </div>
                  <div className="flex items-center gap-2 justify-center sm:justify-start">
                    <Building2 className="w-4 h-4 text-muted-foreground" />
                    <span>{userInfo.department}</span>
                  </div>
                  <div className="flex items-center gap-2 justify-center sm:justify-start">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span>입사일: {userInfo.joinDate}</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats Section */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="p-4 text-center">
              <FileCheck className="w-8 h-8 mx-auto mb-2 text-primary" />
              <p className="text-2xl font-bold text-foreground">{stats.totalInspections}</p>
              <p className="text-xs text-muted-foreground">총 검사 횟수</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <Calendar className="w-8 h-8 mx-auto mb-2 text-accent" />
              <p className="text-2xl font-bold text-foreground">{stats.thisMonth}</p>
              <p className="text-xs text-muted-foreground">이번 달 검사</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-destructive" />
              <p className="text-2xl font-bold text-foreground">{stats.defectsFound}</p>
              <p className="text-xs text-muted-foreground">발견 결함</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <Clock className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-lg font-bold text-foreground">{stats.avgInspectionTime}</p>
              <p className="text-xs text-muted-foreground">평균 검사 시간</p>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">최근 검사 기록</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.map((activity, index) => (
                <div 
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                >
                  <div>
                    <p className="font-medium text-foreground">{activity.ship}</p>
                    <p className="text-sm text-muted-foreground">{activity.date}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-sm ${activity.defects > 0 ? 'text-destructive' : 'text-success'}`}>
                      결함 {activity.defects}건
                    </span>
                    <Badge 
                      variant={activity.status === "completed" ? "secondary" : "default"}
                    >
                      {activity.status === "completed" ? "완료" : "검사중"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="mt-6 flex flex-col sm:flex-row gap-4">
          <Button variant="outline" className="flex-1 bg-transparent" onClick={() => router.push("/main")}>
            메인으로 돌아가기
          </Button>
          <Button variant="destructive" className="flex-1" onClick={() => router.push("/")}>
            로그아웃
          </Button>
        </div>
      </main>
    </div>
  )
}
