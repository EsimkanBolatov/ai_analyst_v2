import { Suspense } from "react";

import { LegacyProfileViewer } from "@/components/legacy/legacy-profile-viewer";

export default function LegacyProfilePage() {
  return (
    <Suspense fallback={<div className="panel h-96 animate-pulse" />}>
      <LegacyProfileViewer />
    </Suspense>
  );
}
