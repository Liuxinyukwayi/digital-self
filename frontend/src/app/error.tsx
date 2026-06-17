'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-3xl">
          !
        </div>
        <h2 className="mb-2 text-xl font-bold text-slate-900">出错了</h2>
        <p className="mb-6 text-sm text-slate-500">
          {error.message || '发生了未知错误'}
        </p>
        <button
          onClick={reset}
          className="rounded-lg bg-indigo-500 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-600"
        >
          重试
        </button>
      </div>
    </div>
  );
}
