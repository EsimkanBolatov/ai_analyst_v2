import Link from "next/link";

export default function NotFound() {
  return (
    <div className="shell flex min-h-[calc(100vh-160px)] items-center justify-center pt-8">
      <section className="panel max-w-2xl p-8 text-center sm:p-10">
        <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.35em] text-smoke">
          404
        </p>
        <h1 className="mt-4 text-4xl font-semibold text-ink sm:text-5xl">
          Страница не найдена
        </h1>
        <p className="mt-4 text-sm leading-7 text-smoke sm:text-base">
          Запрошенный маршрут отсутствует в текущем release-контуре AI-Analyst Platform.
        </p>
        <div className="mt-8 flex justify-center">
          <Link href="/" className="button-primary">
            Вернуться на главную
          </Link>
        </div>
      </section>
    </div>
  );
}
