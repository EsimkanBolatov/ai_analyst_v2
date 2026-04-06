export default function DashboardLoading() {
  return (
    <div className="space-y-8">
      <div className="panel h-48 animate-pulse bg-white/50" />
      <div className="grid gap-4 xl:grid-cols-3">
        {[1, 2, 3].map((item) => (
          <div key={item} className="panel h-80 animate-pulse bg-white/50" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel h-[640px] animate-pulse bg-white/50" />
        <div className="panel h-[640px] animate-pulse bg-white/50" />
      </div>
    </div>
  );
}
