import { Suspense } from "react";
import { EntityView } from "@/components/EntityView";
import { Loading } from "@/components/ui";

export default function EntityPage({ params }: PageProps<"/entities/[type]/[id]">) {
  return (
    <Suspense fallback={<Loading />}>
      {params.then(({ type, id }) => (
        <EntityView type={decodeURIComponent(type)} id={decodeURIComponent(id)} />
      ))}
    </Suspense>
  );
}
