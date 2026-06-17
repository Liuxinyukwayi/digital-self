'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiGet } from '@/lib/api';

type StatState = {
  memories: number;
  knowledge: number;
  timeline: number;
  personaReady: boolean;
};

type SetupState = {
  apiConfigured: boolean;
  dataImported: boolean;
  personaReady: boolean;
};

export default function Home() {
  const [stats, setStats] = useState<StatState>({
    memories: 0,
    knowledge: 0,
    timeline: 0,
    personaReady: false,
  });

  const [setup, setSetup] = useState<SetupState>({
    apiConfigured: false,
    dataImported: false,
    personaReady: false,
  });

  useEffect(() => {
    async function load() {
      const [memory, knowledge, timeline, persona, settings] = await Promise.allSettled([
        apiGet<{ items: { id: number }[]; total: number }>('/memory/?limit=1'),
        apiGet<{ items: { id: number }[]; total: number }>('/knowledge/?limit=1'),
        apiGet<{ items: unknown[]; total: number }>('/timeline/?limit=1'),
        apiGet<{ summary: string; traits: unknown[] }>('/persona/'),
        apiGet<{ mimo_configured: boolean; deepseek_configured: boolean; openai_configured: boolean }>('/settings/'),
      ]);

      const memCount = memory.status === 'fulfilled' ? memory.value.total : 0;
      const knowCount = knowledge.status === 'fulfilled' ? knowledge.value.total : 0;
      const pReady =
        persona.status === 'fulfilled' &&
        Boolean(persona.value.summary) &&
        persona.value.traits.length > 0;

      const s = settings.status === 'fulfilled' ? settings.value : null;
      const apiOk = s
        ? s.mimo_configured || s.deepseek_configured || s.openai_configured
        : false;

      setStats({
        memories: memCount,
        knowledge: knowCount,
        timeline: timeline.status === 'fulfilled' ? timeline.value.total : 0,
        personaReady: pReady,
      });

      setSetup({
        apiConfigured: apiOk,
        dataImported: memCount > 0 || knowCount > 0,
        personaReady: pReady,
      });
    }
    load();
  }, []);

  const completedSteps =
    (setup.apiConfigured ? 1 : 0) +
    (setup.dataImported ? 1 : 0) +
    (setup.personaReady ? 1 : 0);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">工作台</h1>
        <p className="page-subtitle">数字分身系统概览</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="记忆" value={stats.memories} hint="条记忆" />
        <StatCard label="知识" value={stats.knowledge} hint="篇文档" />
        <StatCard label="事件" value={stats.timeline} hint="个事件" />
        <StatCard label="画像" value={stats.personaReady ? '已生成' : '待生成'} hint="Persona" />
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-lg font-bold text-slate-900">快速开始</h2>
        <QuickStartPanel setup={setup} completedSteps={completedSteps} />
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-lg font-bold text-slate-900">快速操作</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <QuickAction
            href="/chat"
            title="开始聊天"
            desc="基于记忆和知识库的智能对话"
            accent="bg-teal-500"
          />
          <QuickAction
            href="/memory"
            title="记忆管理"
            desc="查看、搜索、蒸馏你的记忆"
            accent="bg-indigo-500"
          />
          <QuickAction
            href="/sync"
            title="同步数据"
            desc="微信、QQ、飞书、GitHub、邮件"
            accent="bg-violet-500"
          />
          <QuickAction
            href="/persona"
            title="生成 Persona"
            desc="从聊天记录提炼人格特征"
            accent="bg-amber-500"
          />
          <QuickAction
            href="/timeline"
            title="时间线"
            desc="浏览人生事件和经历轨迹"
            accent="bg-rose-500"
          />
          <QuickAction
            href="/settings"
            title="系统设置"
            desc="模型、检索和蒸馏配置"
            accent="bg-slate-500"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, hint }: { label: string; value: number | string; hint: string }) {
  return (
    <div className="stat-card animate-fade-in">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="mt-1 text-xs text-slate-400">{hint}</div>
    </div>
  );
}

function QuickAction({
  href,
  title,
  desc,
  accent,
}: {
  href: string;
  title: string;
  desc: string;
  accent: string;
}) {
  return (
    <Link
      href={href}
      className="panel panel-pad panel-hover group block"
    >
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 h-3 w-3 rounded-full ${accent}`} />
        <div>
          <h3 className="font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
            {title}
          </h3>
          <p className="mt-1 text-sm text-slate-500">{desc}</p>
        </div>
      </div>
    </Link>
  );
}

function QuickStartPanel({ setup, completedSteps }: { setup: SetupState; completedSteps: number }) {
  const steps = [
    {
      num: 1,
      title: '配置 API 密钥',
      desc: '接入 MiMo、DeepSeek 或 ChatGPT 模型',
      href: '/settings',
      done: setup.apiConfigured,
    },
    {
      num: 2,
      title: '导入数据',
      desc: '同步聊天记录、导入文章或笔记',
      href: '/sync',
      done: setup.dataImported,
    },
    {
      num: 3,
      title: '生成 Persona',
      desc: '基于数据提炼你的人格画像',
      href: '/persona',
      done: setup.personaReady,
    },
  ];

  const allDone = completedSteps === 3;

  return (
    <div className="panel panel-pad animate-fade-in">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-base font-bold text-slate-900">
            {allDone ? '所有准备已完成' : `完成 ${completedSteps}/3 步初始化`}
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            {allDone ? '你的数字分身已就绪，开始聊天吧' : '按顺序完成以下步骤，激活你的数字分身'}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className={`h-2 rounded-full transition-all duration-300 ${
                i < completedSteps ? 'w-8 bg-teal-500' : 'w-2 bg-slate-200'
              }`}
            />
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {steps.map((step) => (
          <Link
            key={step.num}
            href={step.href}
            className={`group relative flex items-start gap-3 rounded-xl border p-4 transition-all duration-200 ${
              step.done
                ? 'border-teal-200 bg-teal-50/50 hover:border-teal-300'
                : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
            }`}
          >
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold transition-colors ${
                step.done
                  ? 'bg-teal-500 text-white'
                  : 'bg-slate-100 text-slate-500 group-hover:bg-teal-100 group-hover:text-teal-700'
              }`}
            >
              {step.done ? (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                step.num
              )}
            </div>
            <div className="min-w-0 flex-1">
              <h4 className={`text-sm font-bold ${step.done ? 'text-teal-800' : 'text-slate-900'}`}>
                {step.title}
              </h4>
              <p className={`mt-1 text-xs leading-4 ${step.done ? 'text-teal-600' : 'text-slate-500'}`}>
                {step.desc}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
