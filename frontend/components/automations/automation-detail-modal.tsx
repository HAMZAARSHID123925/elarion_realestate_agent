'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  X, ChevronRight, Pencil, Play, Building2,
  Zap, HelpCircle, CheckSquare, Package, Clock, Frown, Shield,
  Check, Loader2, Link2, Plus, Trash2, Cpu, GitBranch
} from 'lucide-react';
import {
  AutomationDefinition,
  EscalationRule,
  WorkflowStep as WorkflowStepType,
} from '@/lib/automation-definitions';
import { getAutomationToken } from '@/lib/design-tokens';
import { apiClient } from '@/lib/api-client';
import WorkflowStep from './workflow-step';

// ── Escalation rule icon resolver ─────────────────────────────────────────────
function EscalationRuleIcon({ icon }: { icon: EscalationRule['icon'] }) {
  const cls = 'w-4 h-4';
  switch (icon) {
    case 'emergency':    return <Zap className={`${cls} text-red-500`} />;
    case 'uncertainty':  return <HelpCircle className={`${cls} text-amber-500`} />;
    case 'approval':     return <CheckSquare className={`${cls} text-blue-500`} />;
    case 'resource':     return <Package className={`${cls} text-violet-500`} />;
    case 'time':         return <Clock className={`${cls} text-orange-500`} />;
    case 'sentiment':    return <Frown className={`${cls} text-rose-500`} />;
    case 'policy':       return <Shield className={`${cls} text-slate-500`} />;
    default:             return <Zap className={`${cls} text-slate-400`} />;
  }
}

// ── Channel icon label ────────────────────────────────────────────────────────
function ChannelPill({ channel }: { channel: string }) {
  const map: Record<string, string> = {
    'WhatsApp': 'bg-green-50 text-green-700 border-green-200',
    'Email':    'bg-blue-50 text-blue-700 border-blue-200',
    'Voice':    'bg-violet-50 text-violet-700 border-violet-200',
    'Web':      'bg-sky-50 text-sky-700 border-sky-200',
    'SMS':      'bg-orange-50 text-orange-700 border-orange-200',
    'Web Portal': 'bg-teal-50 text-teal-700 border-teal-200',
  };
  const cls = map[channel] ?? 'bg-slate-50 text-slate-600 border-slate-200';
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-md border text-xs font-medium ${cls}`}>
      {channel}
    </span>
  );
}

import {
  Wrench, BellRing, HeadphonesIcon, FileText, BarChart3, Settings2,
} from 'lucide-react';

function AutomationIconLg({ type }: { type: string }) {
  const cls = 'w-5 h-5';
  switch (type) {
    case 'maintenance': return <Wrench className={cls} />;
    case 'rent':        return <BellRing className={cls} />;
    case 'support':     return <HeadphonesIcon className={cls} />;
    case 'lease':       return <FileText className={cls} />;
    case 'reporting':   return <BarChart3 className={cls} />;
    default:            return <Settings2 className={cls} />;
  }
}

interface AutomationDetailModalProps {
  def: AutomationDefinition | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export default function AutomationDetailModal({
  def,
  isOpen,
  onClose,
  onSaved,
}: AutomationDetailModalProps) {
  const [currentDef, setCurrentDef] = useState<AutomationDefinition | null>(def);
  const [isEditMode, setIsEditMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedOk, setSavedOk] = useState(false);

  // Editable local state
  const [editConditions, setEditConditions] = useState<string[]>([]);
  const [editChannels, setEditChannels] = useState<string[]>([]);
  const [editActive, setEditActive] = useState(true);
  const [editSteps, setEditSteps] = useState<WorkflowStepType[]>([]);

  const modalRef = useRef<HTMLDivElement>(null);

  // Sync local edit state when definition changes or opens
  useEffect(() => {
    if (def) {
      setCurrentDef(def);
      setEditConditions([...def.escalation_conditions]);
      setEditChannels([...def.channels]);
      setEditActive(def.status?.toLowerCase() !== 'inactive');
      setEditSteps(def.steps ? JSON.parse(JSON.stringify(def.steps)) : []);
    }
    setIsEditMode(false);
    setSaveError(null);
    setSavedOk(false);
  }, [def]);

  // Trap focus + Escape close
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  const handleSave = useCallback(async () => {
    if (!currentDef) return;
    setIsSaving(true);
    setSaveError(null);

    const newStatus = editActive ? 'Active' : 'Inactive';

    try {
      const payload = {
        escalation_conditions: editConditions,
        channels: editChannels,
        active: editActive,
        status: newStatus,
        steps: editSteps,
      };

      const res = await apiClient.updateAutomation(currentDef.id, payload);

      // Local state update so header and steps update immediately without reverting
      setCurrentDef((prev) =>
        prev
          ? {
              ...prev,
              status: newStatus,
              channels: editChannels,
              escalation_conditions: editConditions,
              steps: editSteps,
            }
          : null
      );

      setSavedOk(true);
      setTimeout(() => {
        setSavedOk(false);
        setIsEditMode(false);
        setIsSaving(false);
        onSaved?.();
      }, 800);
    } catch (err) {
      console.error('Save error:', err);
      setSaveError('Failed to save to database. Please try again.');
      setIsSaving(false);
    }
  }, [currentDef, editConditions, editChannels, editActive, editSteps, onSaved]);

  const handleCancel = () => {
    if (currentDef) {
      setEditConditions([...currentDef.escalation_conditions]);
      setEditChannels([...currentDef.channels]);
      setEditActive(currentDef.status?.toLowerCase() !== 'inactive');
      setEditSteps(currentDef.steps ? JSON.parse(JSON.stringify(currentDef.steps)) : []);
    }
    setIsEditMode(false);
    setSaveError(null);
  };

  const toggleChannel = (ch: string) => {
    setEditChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  };

  const updateStepField = (index: number, field: keyof WorkflowStepType, value: any) => {
    setEditSteps((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const handleAddStep = () => {
    setEditSteps((prev) => [
      ...prev,
      {
        id: `step_${Date.now()}`,
        title: 'New Execution Step',
        description: 'Describe the operation performed in this step.',
        isAiTask: true,
      },
    ]);
  };

  const handleRemoveStep = (index: number) => {
    setEditSteps((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDeleteModal = async () => {
    if (!currentDef) return;
    if (window.confirm(`Are you sure you want to delete "${currentDef.name}" automation? This will permanently remove it from PostgreSQL database.`)) {
      setIsSaving(true);
      try {
        await apiClient.deleteAutomation(currentDef.id);
        onClose();
        onSaved?.();
      } catch (err) {
        console.error('Delete error:', err);
        setSaveError('Failed to delete automation from database.');
        setIsSaving(false);
      }
    }
  };

  if (!currentDef) return null;

  const tokens = getAutomationToken(currentDef.icon_type);
  const activeStatusText = currentDef.status || 'Active';
  const isInactive = activeStatusText.toLowerCase() === 'inactive';

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        className={`fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Modal panel */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label={`${currentDef.name} Automation Details`}
        className={`
          fixed inset-0 z-50 flex items-center justify-center p-4
          transition-all duration-300
          ${isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'}
        `}
      >
        <div className="w-full max-w-5xl max-h-[90vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">

          {/* ── Modal Header ───────────────────────────────────────────────── */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 flex-shrink-0">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-slate-500 font-medium min-w-0">
              <span className="hover:text-teal-600 cursor-pointer transition-colors" onClick={onClose}>
                Automations
              </span>
              <ChevronRight size={14} className="text-slate-300 flex-shrink-0" />
              <span className="text-slate-900 font-semibold truncate">{currentDef.name}</span>
            </div>

            <button
              id="close-automation-detail-modal"
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-700 transition-colors flex-shrink-0 ml-4"
              aria-label="Close modal"
            >
              <X size={18} />
            </button>
          </div>

          {/* ── Sub-header: Title + badges + actions ───────────────────────── */}
          <div className="px-6 py-5 border-b border-slate-100 flex-shrink-0 bg-slate-50/40">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className={`w-10 h-10 rounded-xl ${tokens.iconBg} flex items-center justify-center shadow-sm`}>
                    <AutomationIconLg type={currentDef.icon_type} />
                  </div>
                  <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                    {currentDef.name} Automation
                  </h2>
                </div>

                <div className="flex items-center gap-3 flex-wrap">
                  {isEditMode ? (
                    <button
                      type="button"
                      onClick={() => setEditActive(!editActive)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold cursor-pointer transition-all border ${
                        editActive
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                          : 'bg-slate-200 text-slate-700 border-slate-300'
                      }`}
                    >
                      <span className={`w-2 h-2 rounded-full ${editActive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                      {editActive ? 'Status: Active (Click to Deactivate)' : 'Status: Inactive (Click to Activate)'}
                    </button>
                  ) : (
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                        isInactive
                          ? 'bg-slate-100 text-slate-600 border border-slate-200'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${isInactive ? 'bg-slate-400' : 'bg-emerald-500 animate-pulse'}`} />
                      {activeStatusText}
                    </span>
                  )}

                  <span className="inline-flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                    <Building2 size={12} className="text-slate-400" />
                    {currentDef.scope}
                  </span>

                  {isEditMode ? (
                    <div className="flex items-center gap-1 flex-wrap">
                      {['WhatsApp', 'Email', 'Voice', 'Web', 'SMS', 'Web Portal'].map((ch) => {
                        const selected = editChannels.includes(ch);
                        return (
                          <button
                            type="button"
                            key={ch}
                            onClick={() => toggleChannel(ch)}
                            className={`px-2 py-0.5 rounded-md border text-xs font-medium transition-all ${
                              selected
                                ? 'bg-teal-600 text-white border-teal-600'
                                : 'bg-slate-50 text-slate-400 border-slate-200 hover:text-slate-700'
                            }`}
                          >
                            {selected ? '✓ ' : '+ '}{ch}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {currentDef.channels.map((ch) => <ChannelPill key={ch} channel={ch} />)}
                    </div>
                  )}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {isEditMode ? (
                  <>
                    <button
                      id="save-automation-edit"
                      onClick={handleSave}
                      disabled={isSaving}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold transition-colors disabled:opacity-60 shadow-sm cursor-pointer"
                    >
                      {isSaving ? <Loader2 size={14} className="animate-spin" /> : savedOk ? <Check size={14} /> : null}
                      {savedOk ? 'Saved to DB!' : isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button
                      id="cancel-automation-edit"
                      onClick={handleCancel}
                      className="px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      id="delete-automation-modal"
                      onClick={handleDeleteModal}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-red-200 hover:bg-red-50 text-red-600 text-sm font-medium transition-colors"
                      title="Delete this automation"
                    >
                      <Trash2 size={14} />
                      Delete
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      id="edit-workflow-btn"
                      onClick={() => setIsEditMode(true)}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors cursor-pointer"
                    >
                      <Pencil size={14} />
                      Edit Workflow
                    </button>
                    <button
                      id="test-run-btn"
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-semibold shadow-sm transition-all bg-teal-600 hover:bg-teal-700"
                    >
                      <Play size={14} />
                      Test Run
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Save error */}
            {saveError && (
              <p className="mt-2 text-xs text-red-600 font-semibold">⚠ {saveError}</p>
            )}
          </div>

          {/* ── Body: two-column layout ────────────────────────────────────── */}
          <div className="flex-1 overflow-y-auto">
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] divide-y lg:divide-y-0 lg:divide-x divide-slate-100">

              {/* ── LEFT: Execution Flow ──────────────────────────────────── */}
              <div className="p-6 overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-2">
                    <Zap size={16} className="text-slate-400" />
                    <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wide">
                      Execution Flow Steps
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400 font-medium">
                      {(isEditMode ? editSteps : currentDef.steps).length} steps
                    </span>
                    {isEditMode && (
                      <button
                        type="button"
                        onClick={handleAddStep}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200 hover:bg-teal-100 transition-colors"
                      >
                        <Plus size={12} />
                        Add Step
                      </button>
                    )}
                  </div>
                </div>

                {isEditMode ? (
                  /* ── Edit Mode: Execution Flow Step Editor ──────────────── */
                  <div className="space-y-4">
                    {editSteps.map((step, idx) => (
                      <div key={step.id || idx} className="p-3.5 rounded-xl border border-teal-200 bg-teal-50/40 relative space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="w-6 h-6 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
                            {idx + 1}
                          </span>
                          <input
                            type="text"
                            value={step.title}
                            onChange={(e) => updateStepField(idx, 'title', e.target.value)}
                            placeholder="Step Title"
                            className="flex-1 text-sm font-semibold text-slate-900 bg-white border border-teal-200 rounded-lg px-2.5 py-1 focus:outline-none focus:ring-2 focus:ring-teal-400"
                          />
                          <button
                            type="button"
                            onClick={() => handleRemoveStep(idx)}
                            className="text-slate-400 hover:text-red-600 transition-colors p-1"
                            title="Remove Step"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>

                        <textarea
                          value={step.description}
                          onChange={(e) => updateStepField(idx, 'description', e.target.value)}
                          placeholder="Step Description"
                          rows={2}
                          className="w-full text-xs text-slate-700 bg-white border border-teal-200 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-teal-400 resize-none"
                        />

                        <div className="flex items-center gap-3 pt-1">
                          <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 font-medium cursor-pointer">
                            <input
                              type="checkbox"
                              checked={!!step.isAiTask}
                              onChange={(e) => updateStepField(idx, 'isAiTask', e.target.checked)}
                              className="rounded border-slate-300 text-teal-600 focus:ring-teal-400"
                            />
                            <Cpu size={12} className="text-teal-600" />
                            AI Task Badge
                          </label>

                          <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 font-medium cursor-pointer">
                            <input
                              type="checkbox"
                              checked={!!step.isConditional}
                              onChange={(e) => updateStepField(idx, 'isConditional', e.target.checked)}
                              className="rounded border-slate-300 text-amber-600 focus:ring-amber-400"
                            />
                            <GitBranch size={12} className="text-amber-600" />
                            Conditional Branch
                          </label>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  /* ── Normal Display: Workflow Step Timeline ─────────────── */
                  <div className="space-y-0">
                    {currentDef.steps.map((step, i) => (
                      <WorkflowStep
                        key={step.id || i}
                        step={step}
                        index={i}
                        isLast={i === currentDef.steps.length - 1}
                        iconType={currentDef.icon_type}
                        isEditMode={false}
                      />
                    ))}
                  </div>
                )}

                {/* Tagline */}
                <div className="mt-6 pt-5 border-t border-slate-100">
                  <p className="text-xs text-slate-400 leading-relaxed italic">{currentDef.tagline}</p>
                </div>
              </div>

              {/* ── RIGHT: Escalation Rules + Integrations ─────────────────── */}
              <div className="p-6 space-y-8 overflow-y-auto">

                {/* Escalation Rules */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <Zap size={16} className="text-red-400" />
                    <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wide">
                      Escalation Rules
                    </h3>
                  </div>

                  <div className="space-y-3">
                    {currentDef.escalation_rules.map((rule) => (
                      <div key={rule.id} className="flex gap-3 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors">
                        <div className="w-8 h-8 rounded-lg bg-white shadow-sm border border-slate-100 flex items-center justify-center flex-shrink-0">
                          <EscalationRuleIcon icon={rule.icon} />
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-800 text-sm leading-tight">{rule.label}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{rule.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Edit mode: editable conditions textarea */}
                  {isEditMode && (
                    <div className="mt-4 p-3 rounded-xl border border-teal-200 bg-teal-50">
                      <label className="block text-xs font-semibold text-teal-700 mb-2">
                        Edit Escalation Conditions (one per line)
                      </label>
                      <textarea
                        id="edit-escalation-conditions"
                        value={editConditions.join('\n')}
                        onChange={(e) => setEditConditions(e.target.value.split('\n').filter(Boolean))}
                        rows={4}
                        className="w-full text-xs text-slate-700 bg-white border border-teal-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400 resize-none"
                      />
                    </div>
                  )}
                </div>

                {/* Active Integrations */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <Link2 size={16} className="text-slate-400" />
                    <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wide">
                      Active Integrations
                    </h3>
                  </div>

                  <div className="space-y-2.5">
                    {currentDef.integrations.map((intg) => (
                      <div
                        key={intg.id}
                        className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg ${intg.color} ${intg.textColor} flex items-center justify-center text-xs font-bold shadow-sm`}>
                            {intg.initials}
                          </div>
                          <span className="text-sm font-semibold text-slate-800">{intg.name}</span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          <Link2 size={14} className="text-slate-400 hover:text-teal-600 cursor-pointer transition-colors" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
