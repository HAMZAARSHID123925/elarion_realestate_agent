'use client';

import React from 'react';
import { GitBranch, Cpu } from 'lucide-react';
import { WorkflowStep as WorkflowStepType } from '@/lib/automation-definitions';
import { getAutomationToken } from '@/lib/design-tokens';

interface WorkflowStepProps {
  step: WorkflowStepType;
  index: number;
  isLast: boolean;
  iconType: string;
  isEditMode?: boolean;
}

export default function WorkflowStep({
  step,
  index,
  isLast,
  iconType,
  isEditMode = false,
}: WorkflowStepProps) {
  const tokens = getAutomationToken(iconType);

  return (
    <div className="flex gap-4 group">
      {/* Left column: circle + connector line */}
      <div className="flex flex-col items-center flex-shrink-0">
        <div
          className={`
            relative z-10 w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm
            transition-all duration-200 shadow-sm
            ${step.isCurrent
              ? `${tokens.iconBg} ${tokens.iconColor} ring-2 ring-offset-2 ring-current shadow-md`
              : step.isConditional
              ? 'bg-amber-50 text-amber-600 border-2 border-amber-300 border-dashed'
              : 'bg-slate-100 text-slate-500 border border-slate-200'
            }
          `}
        >
          {step.isConditional ? (
            <GitBranch size={15} />
          ) : (
            <span>{index + 1}</span>
          )}
        </div>
        {/* Vertical connector */}
        {!isLast && (
          <div
            className={`w-0.5 flex-1 mt-1 min-h-[24px] transition-colors duration-300 ${
              step.isCurrent ? tokens.stepColor.replace('text-', 'bg-') : 'bg-slate-200'
            }`}
          />
        )}
      </div>

      {/* Right column: content */}
      <div className={`pb-6 flex-1 ${isLast ? 'pb-0' : ''}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <h4
            className={`font-semibold text-sm transition-colors ${
              step.isCurrent ? 'text-slate-900' : 'text-slate-700'
            }`}
          >
            {step.title}
          </h4>

          {step.isAiTask && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold tracking-wide
                ${tokens.aiTaskBg} ${tokens.aiTaskText}`}
            >
              <Cpu size={10} />
              AI TASK
            </span>
          )}

          {step.isConditional && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
              <GitBranch size={10} />
              CONDITIONAL
            </span>
          )}

          {step.isCurrent && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-600 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              ACTIVE
            </span>
          )}
        </div>

        <p className="text-sm text-slate-500 mt-0.5 leading-relaxed">
          {step.description}
        </p>
      </div>
    </div>
  );
}
