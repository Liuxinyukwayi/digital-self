import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-3xl font-bold text-slate-400">
          404
        </div>
        <h2 className="mb-2 text-xl font-bold text-slate-900">页面未找到</h2>
        <p className="mb-6 text-sm text-slate-500">
          您访问的页面不存在
        </p>
        <Link
          href="/"
          className="inline-block rounded-lg bg-indigo-500 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-600"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
