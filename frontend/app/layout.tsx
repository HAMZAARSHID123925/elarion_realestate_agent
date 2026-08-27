import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/layout/sidebar';
import TopBar from '@/components/layout/top-bar';

export const metadata: Metadata = {
  title: 'TenantFlow.ai — AI Operations Layer Dashboard',
  description: 'AI-driven real estate operations, maintenance triage, and tenant communication dashboard.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-[#F8FAFC]">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar />
          <main className="flex-1 p-8 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
