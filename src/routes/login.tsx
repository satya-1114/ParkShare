import { createFileRoute, Link, useRouter, useSearch, redirect } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Logo } from "@/components/brand/Logo";
import { useAuth } from "@/contexts/AuthContext";
import { storageService } from "@/services/storageService";
import { roleHome } from "@/lib/roles";

const searchSchema = z.object({
  redirect: z.string().optional(),
});

const loginSchema = z.object({
  email: z.string().trim().email({ message: "Enter a valid email address" }),
  password: z.string().min(8, { message: "Password must be at least 8 characters" }),
  remember: z.boolean().optional(),
});

type LoginValues = z.infer<typeof loginSchema>;

export const Route = createFileRoute("/login")({
  validateSearch: searchSchema,
  beforeLoad: () => {
    const user = storageService.getUser();
    if (user) {
      throw redirect({ to: roleHome(user.role) });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const search = useSearch({ from: Route.id });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", remember: false },
  });

  async function onSubmit(values: LoginValues) {
    try {
      const user = await login({ email: values.email, password: values.password });
      toast.success("Signed in successfully");
      const target = search.redirect ?? roleHome(user.role);
      router.navigate({ to: target });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign-in failed";
      toast.error(message);
    }
  }

  return (
    <div className="grid min-h-screen bg-surface lg:grid-cols-2">
      <aside className="hidden bg-navy p-10 text-navy-foreground lg:flex lg:flex-col lg:justify-between">
        <Logo variant="light" />
        <div>
          <h2 className="font-display text-3xl font-bold">
            Trusted community parking, one login away.
          </h2>
          <p className="mt-4 max-w-md text-navy-foreground/70">
            Manage bookings, list your parking space, and keep track of your
            earnings — all in one place.
          </p>
        </div>
        <p className="text-xs text-navy-foreground/60">
          © {new Date().getFullYear()} ParkShare
        </p>
      </aside>

      <div className="flex flex-col justify-center px-6 py-12 sm:px-12">
        <div className="mx-auto w-full max-w-sm">
          <div className="lg:hidden">
            <Logo />
          </div>
          <h1 className="mt-6 font-display text-2xl font-bold lg:mt-0">Welcome back</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in to continue to your ParkShare account.
          </p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                aria-invalid={!!errors.email}
                className="mt-1.5"
                {...register("email")}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <span className="text-xs text-muted-foreground">Forgot password?</span>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                aria-invalid={!!errors.password}
                className="mt-1.5"
                {...register("password")}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox id="remember" {...register("remember")} />
              <Label htmlFor="remember" className="font-normal">Remember me</Label>
            </label>
            <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
              {isSubmitting ? "Signing in…" : "Sign In"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            New to ParkShare?{" "}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
