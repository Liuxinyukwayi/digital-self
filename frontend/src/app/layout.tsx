import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'Digital Self - 数字分身',
  description: '创建你的数字分身，具有长期记忆和人格风格',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <Sidebar>{children}</Sidebar>
      </body>
    </html>
  );
}
