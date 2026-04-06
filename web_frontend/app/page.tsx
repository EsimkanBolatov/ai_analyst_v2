import { LandingHero } from "@/components/landing-hero";

const sprintItems = [
  {
    title: "Этап 1",
    text: "JWT-авторизация, роли и новый frontend-контур на Next.js.",
  },
  {
    title: "Этап 2",
    text: "ИИ-бухгалтер с памятью, бюджетами и голосовым интерфейсом.",
  },
  {
    title: "Этап 3",
    text: "Краудсорсинг репортов и двухэтапная модерация мошеннических кейсов.",
  },
];

export default function HomePage() {
  return (
    <div className="shell pt-8 sm:pt-10">
      <LandingHero />
      <section className="mt-8 grid gap-4 lg:grid-cols-3">
        {sprintItems.map((item) => (
          <article key={item.title} className="panel p-6">
            <p className="font-[family-name:var(--font-mono)] text-xs uppercase tracking-[0.3em] text-smoke">
              {item.title}
            </p>
            <h2 className="mt-4 text-2xl font-semibold text-ink">{item.title}: фундамент продукта</h2>
            <p className="mt-3 text-sm leading-7 text-smoke">{item.text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
