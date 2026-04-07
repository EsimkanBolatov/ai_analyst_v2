export default function MlLabLoading() {
  return (
    <div className="shell pt-8 sm:pt-10">
      <div className="panel h-72 animate-pulse" />
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="h-96 animate-pulse rounded-[28px] border border-line bg-white/40" />
        <div className="h-96 animate-pulse rounded-[28px] border border-line bg-white/40" />
      </div>
    </div>
  );
}
