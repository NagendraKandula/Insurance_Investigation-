"use client";

import { useEffect, useState } from "react";

interface State<T> {
  key: string;
  data?: T;
  error?: Error;
}

/**
 * Fetch on the client. `key` identifies the request: when it changes the
 * hook fetches again. The previous data stays available while the new
 * request loads, so tables don't flash empty between pages.
 */
export function useApi<T>(key: string, load: () => Promise<T>) {
  const [state, setState] = useState<State<T> | null>(null);

  useEffect(() => {
    let cancelled = false;
    load().then(
      (data) => {
        if (!cancelled) setState({ key, data });
      },
      (error: Error) => {
        if (!cancelled) setState((previous) => ({ key, data: previous?.data, error }));
      },
    );
    return () => {
      cancelled = true;
    };
    // `load` is rebuilt every render; `key` is what identifies the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const current = state?.key === key;
  return {
    data: state?.data,
    error: current ? state?.error : undefined,
    loading: !current,
  };
}
