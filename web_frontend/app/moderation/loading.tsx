export default function ModerationLoading() {
  return (
    <div className="space-y-6">
      <div className="panel h-48 animate-pulse bg-white/50" />
      <div className="grid gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((item) => (
          <div key={item} className="panel h-32 animate-pulse bg-white/50" />
        ))}
      </div>
      {[1, 2].map((item) => (
        <div key={item} className="panel h-72 animate-pulse bg-white/50" />
      ))}
    </div>
  );
}
