import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <div className="shell flex min-h-[calc(100vh-120px)] items-center justify-center pt-8">
      <AuthForm mode="login" />
    </div>
  );
}
