import { createFileRoute, Link, useRouter, redirect } from "@tanstack/react-router";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/brand/Logo";
import { Car, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { storageService } from "@/services/storageService";
import type { UserRole } from "@/types";
import { roleHome } from "@/lib/roles";

const registerSchema = z
  .object({
    fullName: z
      .string()
      .trim()
      .min(2, { message: "Full name must be at least 2 characters" })
      .max(80),
    email: z.string().trim().email({ message: "Enter a valid email address" }),
    phone: z
      .string()
      .trim()
      .regex(/^[+()\-\s\d]{7,20}$/u, { message: "Enter a valid phone number" }),
    password: z.string().min(8, { message: "Password must be at least 8 characters" }),
    confirmPassword: z.string(),
    role: z.enum(["DRIVER", "OWNER"]),
  })
  .refine((v) => v.password === v.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords do not match",
  });

type RegisterValues = z.infer<typeof registerSchema>;

export const Route = createFileRoute("/register")({
  beforeLoad: () => {
    const user = storageService.getUser();
    if (user) {
      throw redirect({ to: roleHome(user.role) });
    }
  },
  component: RegisterPage,
});

function RegisterPage() {
  const { register: registerUser } = useAuth();
  const router = useRouter();

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      phone: "",
      password: "",
      confirmPassword: "",
      role: "DRIVER",
    },
  });

  async function onSubmit(values: RegisterValues) {
    try {
      const user = await registerUser({
        fullName: values.fullName,
        email: values.email,
        phone: values.phone,
        password: values.password,
        role: values.role,
      });
      toast.success("Account created");
      router.navigate({ to: roleHome(user.role) });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      toast.error(message);
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto max-w-md px-6 py-12">
        <Logo />
        <div className="mt-8 rounded-2xl border border-border bg-card p-8 shadow-sm">
          <h1 className="font-display text-2xl font-bold">Create your account</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Join the ParkShare community in a minute.
          </p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            <Controller
              control={control}
              name="role"
              render={({ field }) => (
                <fieldset>
                  <legend className="text-sm font-medium">I want to</legend>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <RoleOption
                      selected={field.value === "DRIVER"}
                      onSelect={() => field.onChange("DRIVER" satisfies UserRole)}
                      icon={Car}
                      title="Find Parking"
                      subtitle="Driver"
                    />
                    <RoleOption
                      selected={field.value === "OWNER"}
                      onSelect={() => field.onChange("OWNER" satisfies UserRole)}
                      icon={Building2}
                      title="List My Space"
                      subtitle="Owner"
                    />
                  </div>
                </fieldset>
              )}
            />

            <div>
              <Label htmlFor="name">Full name</Label>
              <Input
                id="name"
                placeholder="Priya Sharma"
                autoComplete="name"
                aria-invalid={!!errors.fullName}
                className="mt-1.5"
                {...register("fullName")}
              />
              {errors.fullName && (
                <p className="mt-1 text-xs text-destructive">{errors.fullName.message}</p>
              )}
            </div>
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
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="+91 98xxxxxxxx"
                autoComplete="tel"
                aria-invalid={!!errors.phone}
                className="mt-1.5"
                {...register("phone")}
              />
              {errors.phone && (
                <p className="mt-1 text-xs text-destructive">{errors.phone.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="pw">Password</Label>
              <Input
                id="pw"
                type="password"
                placeholder="At least 8 characters"
                autoComplete="new-password"
                aria-invalid={!!errors.password}
                className="mt-1.5"
                {...register("password")}
              />
              {errors.password && (
                <p className="mt-1 text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="pw2">Confirm password</Label>
              <Input
                id="pw2"
                type="password"
                autoComplete="new-password"
                aria-invalid={!!errors.confirmPassword}
                className="mt-1.5"
                {...register("confirmPassword")}
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-xs text-destructive">
                  {errors.confirmPassword.message}
                </p>
              )}
            </div>
            <Button className="w-full" size="lg" disabled={isSubmitting}>
              {isSubmitting ? "Creating account…" : "Create account"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

interface RoleOptionProps {
  selected: boolean;
  onSelect: () => void;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
}

function RoleOption({ selected, onSelect, icon: Icon, title, subtitle }: RoleOptionProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "flex flex-col items-start gap-2 rounded-lg border p-3 text-left transition-colors",
        selected
          ? "border-primary bg-accent"
          : "border-border bg-background hover:border-muted-foreground/30",
      )}
    >
      <Icon className={cn("h-5 w-5", selected ? "text-primary" : "text-muted-foreground")} />
      <div>
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
    </button>
  );
}
