"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Briefcase, LogOut, User, Heart, Bell } from "lucide-react";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export function Header() {
  const { user, loading, logout } = useAuth();

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "?";

  return (
    <header
      data-testid="header"
      className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
    >
      <div className="container mx-auto flex h-14 max-w-screen-2xl items-center px-4">
        <Link
          href="/"
          data-testid="header-logo"
          className="mr-6 flex items-center gap-2 font-semibold"
        >
          <Briefcase className="h-5 w-5" />
          <span>JobScraper</span>
        </Link>

        <nav data-testid="header-nav" className="flex items-center gap-4 text-sm">
          <Link
            href="/jobs"
            data-testid="nav-jobs"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            Jobs
          </Link>
          {user && (
            <>
              <Link
                href="/favorites"
                data-testid="nav-favorites"
                className="text-muted-foreground transition-colors hover:text-foreground inline-flex items-center gap-1"
              >
                <Heart className="h-3.5 w-3.5" />
                Favorites
              </Link>
              <Link
                href="/subscriptions"
                data-testid="nav-subscriptions"
                className="text-muted-foreground transition-colors hover:text-foreground inline-flex items-center gap-1"
              >
                <Bell className="h-3.5 w-3.5" />
                Subscriptions
              </Link>
              <Link
                href="/dashboard"
                data-testid="nav-dashboard"
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                Dashboard
              </Link>
            </>
          )}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />

          <NotificationBell />

          {!loading && !user && (
            <>
              <Button variant="ghost" size="sm" data-testid="login-button" asChild>
                <Link href="/login">Log in</Link>
              </Button>
              <Button size="sm" data-testid="register-button" asChild>
                <Link href="/register">Register</Link>
              </Button>
            </>
          )}

          {!loading && user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative rounded-full"
                  data-testid="user-menu-trigger"
                >
                  <Avatar size="sm">
                    <AvatarFallback>{initials}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5">
                  <p
                    data-testid="user-email"
                    className="truncate text-sm font-medium"
                  >
                    {user.email}
                  </p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/favorites" data-testid="menu-favorites">
                    <Heart className="mr-2 h-4 w-4" />
                    Favorites
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/subscriptions" data-testid="menu-subscriptions">
                    <Bell className="mr-2 h-4 w-4" />
                    Subscriptions
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/dashboard" data-testid="menu-dashboard">
                    <User className="mr-2 h-4 w-4" />
                    Dashboard
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  data-testid="logout-button"
                  onClick={() => logout()}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </header>
  );
}
