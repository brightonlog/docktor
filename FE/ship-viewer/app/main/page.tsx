"use client"
import Link from 'next/link';
import { useRouter } from "next/navigation"
import Image from "next/image"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Search,
  Ship,
  User,
  Anchor,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useSearchParams } from "next/navigation"
import {useShipList} from "@/hooks/use-list-ship";
import {useAuthStore} from "@/stores";




export default function MainPage() {
  const router = useRouter();
  const {
    ships,
    totalCount,
    isLoading,
    currentPage,
    setCurrentPage,

  } = useShipList()

  const {corp} = useAuthStore()


  const handleShipClick = (shipId: string) => {
    router.push(`/ship/${shipId}`)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/main" className="cursor-pointer">
            <Image
              src="/images/docktor_logo.png"
              alt="Docktor Logo"
              width={360}
              height={80}
              priority
              className="h-20 w-auto"
            />
          </Link>

          {/* My Page Button */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="w-4 h-4 text-primary" />
                </div>
                <span className="hidden sm:inline">김검사</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1.5">
                <p className="text-sm font-medium">김검사</p>
                <p className="text-xs text-muted-foreground">EMP-12345</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/mypage")}>
                <User className="w-4 h-4 mr-2" />
                마이페이지
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/")}>
                로그아웃
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-6">
          {/* Search & Filter Section */}
          <div className="mb-6 space-y-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <Input
                    placeholder="선박명, 선종, IMO 번호로 검색..."
                    // value={searchQuery}
                    // onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 bg-card border-border h-12 text-base"
                />
              </div>
            </div>

            {/* Stats */}
            <div className="flex gap-4 text-sm">
              <span>전체 {ships.length}척</span>
            </div>
          </div>

          {/* Ship List */}
          <div className="grid gap-4">
            {ships.map((ship) => {
              return (
                  <div
                      key={ship.shipId}
                      onClick={() => handleShipClick(String(ship.shipId))}
                      className="group relative bg-card border border-border rounded-xl overflow-hidden cursor-pointer hover:border-primary/50 transition-all duration-300"
                  >
                    <div className="flex flex-col sm:flex-row">
                      {/* Ship Image */}
                      <div className="relative w-full sm:w-64 h-48 sm:h-auto bg-muted flex-shrink-0">
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Ship className="w-16 h-16 text-muted-foreground/30" />
                        </div>
                        <Image
                            src={ship.thumbnailUrl || "/placeholder.svg"}
                            fill
                            className="object-cover"
                            onError={(e) => {
                              e.currentTarget.style.display = 'none'
                            }} alt={""}                                        />
                        <div className="absolute top-3 left-3">
                        </div>
                      </div>

                      {/* Ship Info */}
                      <div className="flex-1 p-4 sm:p-5">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">{ship.name}
                            </h3>
                          </div>
                          <Badge variant="secondary" className="ml-2">
                            {ship.shipbuilder}
                          </Badge>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4 text-sm">
                          <div>
                            <p className="text-muted-foreground">Class No.</p>
                            <p className="font-medium text-foreground">{ship.classNo}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">IMO</p>
                            <p className="font-medium text-foreground">{ship.imo}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Hull No.</p>
                            <p className="font-medium text-foreground"> {ship.hullNumber}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Arrow indicator */}
                      <div className="hidden sm:flex items-center pr-4">
                        <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                          <svg className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </div>
              )
            })}
          </div>

          {ships.length === 0 && (
              <div className="text-center py-16">
                <Ship className="w-16 h-16 mx-auto text-muted-foreground/30 mb-4" />
                <p className="text-muted-foreground">검색 결과가 없습니다</p>
              </div>
          )}
        </main>
      </div>
  )
}
