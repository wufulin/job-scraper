"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const registerSchema = z
  .object({
    email: z.string().email("Please enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerUser } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setError(null);
    try {
      await registerUser(data.email, data.password);
      router.push("/jobs");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Registration failed"
      );
    }
  };

  return (
    <div
      data-testid="register-page"
      className="flex min-h-[60vh] items-center justify-center px-4"
    >
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Create account</CardTitle>
          <CardDescription>
            Sign up to save job searches and get notifications.
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="flex flex-col gap-4">
            {error && (
              <div
                data-testid="register-error"
                className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                data-testid="register-email"
                aria-invalid={!!errors.email}
                {...register("email")}
              />
              {errors.email && (
                <p
                  data-testid="register-email-error"
                  className="text-xs text-destructive"
                >
                  {errors.email.message}
                </p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                autoComplete="new-password"
                data-testid="register-password"
                aria-invalid={!!errors.password}
                {...register("password")}
              />
              {errors.password && (
                <p
                  data-testid="register-password-error"
                  className="text-xs text-destructive"
                >
                  {errors.password.message}
                </p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                autoComplete="new-password"
                data-testid="register-confirm-password"
                aria-invalid={!!errors.confirmPassword}
                {...register("confirmPassword")}
              />
              {errors.confirmPassword && (
                <p
                  data-testid="register-confirm-password-error"
                  className="text-xs text-destructive"
                >
                  {errors.confirmPassword.message}
                </p>
              )}
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-3">
            <Button
              type="submit"
              className="w-full"
              disabled={isSubmitting}
              data-testid="register-submit"
            >
              {isSubmitting ? "Creating account…" : "Create account"}
            </Button>

            <p className="text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                href="/login"
                data-testid="register-login-link"
                className="text-primary underline-offset-4 hover:underline"
              >
                Log in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
