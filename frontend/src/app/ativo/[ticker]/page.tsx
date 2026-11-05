import { Suspense } from "react";

import { Loading } from "@/components/ui";

import { AtivoView } from "./AtivoView";

export default function AtivoPage() {
  return (
    <Suspense fallback={<Loading />}>
      <AtivoView />
    </Suspense>
  );
}
