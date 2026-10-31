import { Suspense } from "react";
import { QueueTable } from "@/components/QueueTable";
import { Loading } from "@/components/ui";

const first = (value: string | string[] | undefined) =>
  Array.isArray(value) ? value[0] : (value ?? "");

export default function QueuePage({ searchParams }: PageProps<"/queue">) {
  return (
    <Suspense fallback={<Loading />}>
      {searchParams.then((params) => (
        <QueueTable
          initialRisk={first(params.risk).toUpperCase()}
          initialType={first(params.type).toLowerCase()}
          initialIndicator={first(params.indicator)}
        />
      ))}
    </Suspense>
  );
}
