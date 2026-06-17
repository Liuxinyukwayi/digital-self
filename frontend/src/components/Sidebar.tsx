'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

type NavChild = { href: string; label: string; icon: string };
type NavItem = { href: string; label: string; icon: string; children?: NavChild[] };

const navItems: NavItem[] = [
  { href: '/', label: '工作台', icon: '⌂' },
  { href: '/chat', label: '聊天', icon: '✦' },
  {
    href: '#',
    label: '记忆管理',
    icon: '◉',
    children: [
      { href: '/memory', label: '记忆', icon: '◈' },
      { href: '/knowledge', label: '知识库', icon: '▤' },
      { href: '/timeline', label: '时间线', icon: '◷' },
    ],
  },
  { href: '/sync', label: '同步', icon: '⟳' },
  { href: '/persona', label: 'Persona', icon: '◉' },
  { href: '/settings', label: '设置', icon: '⚙' },
];

export default function Sidebar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(true);

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          width: 220,
          height: '100vh',
          zIndex: 30,
          display: 'flex',
          flexDirection: 'column',
          background: '#ffffff',
          borderRight: '1px solid #e5e7eb',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '20px 20px',
            borderBottom: '1px solid #f3f4f6',
          }}
        >
          <div
            style={{
              position: 'relative',
              width: 40,
              height: 40,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
            }}
          >
            <span
              style={{
                color: '#fff',
                fontSize: 14,
                fontWeight: 800,
                letterSpacing: '-0.05em',
              }}
            >
              DS
            </span>
            <div
              style={{
                position: 'absolute',
                bottom: -2,
                right: -2,
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: '#10b981',
                border: '2px solid #fff',
              }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: '#111827', letterSpacing: '-0.02em' }}>
              Digital Self
            </span>
            <span style={{ fontSize: 11, color: '#9ca3af', marginTop: 1 }}>
              AI Assistant
            </span>
          </div>
        </div>

        <nav style={{ flex: 1, overflowY: 'auto', padding: '16px 12px' }}>
          {navItems.map((item) =>
            item.children ? (
              <NavGroup
                key={item.label}
                label={item.label}
                icon={item.icon}
                children={item.children}
                expanded={expanded}
                onToggle={() => setExpanded(!expanded)}
                pathname={pathname}
              />
            ) : (
              <NavLink key={item.href} href={item.href} icon={item.icon} label={item.label} active={pathname === item.href} />
            )
          )}
        </nav>

        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid #f3f4f6',
            fontSize: 11,
            color: '#9ca3af',
          }}
        >
          v0.1.0
        </div>
      </aside>

      <main style={{ marginLeft: 220, flex: 1, overflowY: 'auto' }}>{children}</main>
    </div>
  );
}

function NavGroup({
  label,
  icon,
  children,
  expanded,
  onToggle,
  pathname,
}: {
  label: string;
  icon: string;
  children: NavChild[];
  expanded: boolean;
  onToggle: () => void;
  pathname: string;
}) {
  const hasActive = children.some((c) => pathname === c.href);

  return (
    <div style={{ marginBottom: 4 }}>
      <button
        onClick={onToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          width: '100%',
          gap: 12,
          padding: '10px 12px',
          borderRadius: 8,
          fontSize: 14,
          fontWeight: hasActive ? 600 : 500,
          color: hasActive ? '#111827' : '#6b7280',
          background: hasActive ? '#f0fdf4' : 'transparent',
          border: 'none',
          cursor: 'pointer',
          transition: 'background 0.15s, color 0.15s',
        }}
        onMouseEnter={(e) => {
          if (!hasActive) e.currentTarget.style.background = '#f9fafb';
        }}
        onMouseLeave={(e) => {
          if (!hasActive) e.currentTarget.style.background = 'transparent';
        }}
      >
        <span style={{ width: 20, textAlign: 'center', fontSize: 16 }}>{icon}</span>
        <span style={{ flex: 1, textAlign: 'left' }}>{label}</span>
        <span
          style={{
            fontSize: 10,
            color: '#9ca3af',
            transition: 'transform 0.2s ease',
            transform: expanded ? 'rotate(0deg)' : 'rotate(-90deg)',
          }}
        >
          ▾
        </span>
      </button>
      <div
        style={{
          maxHeight: expanded ? `${children.length * 40 + 8}px` : '0px',
          overflow: 'hidden',
          transition: 'max-height 0.25s ease-in-out',
        }}
      >
        <div style={{ paddingTop: 4, paddingBottom: 4 }}>
          {children.map((child) => (
            <NavLink
              key={child.href}
              href={child.href}
              icon={child.icon}
              label={child.label}
              indent
              active={pathname === child.href}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function NavLink({
  href,
  icon,
  label,
  indent,
  active,
}: {
  href: string;
  icon: string;
  label: string;
  indent?: boolean;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '10px 12px',
        paddingLeft: indent ? 44 : 12,
        borderRadius: 8,
        fontSize: indent ? 13 : 14,
        fontWeight: active ? 600 : 500,
        color: active ? '#0d9488' : '#6b7280',
        background: active ? '#f0fdfa' : 'transparent',
        textDecoration: 'none',
        marginBottom: 2,
        transition: 'background 0.15s, color 0.15s',
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.background = '#f9fafb';
          e.currentTarget.style.color = '#111827';
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = '#6b7280';
        }
      }}
    >
      <span style={{ width: 20, textAlign: 'center', fontSize: indent ? 14 : 16 }}>{icon}</span>
      <span>{label}</span>
    </Link>
  );
}
