'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/overview');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-sm font-medium text-slate-500 animate-pulse">
        Loading TenantFlow Dashboard...
      </div>
    </div>
  );
}
