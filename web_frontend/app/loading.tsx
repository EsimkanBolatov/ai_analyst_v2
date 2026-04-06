export default function RootLoading() {
  return (
    <div className="shell pt-8 sm:pt-10">
      <div className="panel space-y-6 p-8 sm:p-10">
        <div className="h-4 w-40 animate-pulse rounded-full bg-black/10" />
        <div className="h-14 w-full max-w-3xl animate-pulse rounded-[28px] bg-black/10" />
        <div className="h-24 w-full max-w-2xl animate-pulse rounded-[28px] bg-black/5" />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {[1, 2, 3].map((item) => (
          <div key={item} className="panel h-48 animate-pulse bg-white/50" />
        ))}
      </div>
    </div>
  );
}
