'use client';

import React, { useState } from 'react';
import { X, Plus, Sparkles, Loader2, Check, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { AutomationCard } from '@/lib/types';

interface AddAutomationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (newCard: AutomationCard) => void;
}

const AVAILABLE_CHANNELS = ['WhatsApp', 'Email', 'Voice', 'Web', 'SMS', 'Web Portal'];
const ICON_TYPES = [
  { id: 'maintenance', label: 'Maintenance (Wrench)' },
  { id: 'rent', label: 'Rent Collection (Bell)' },
  { id: 'support', label: 'Resident Support (Headphones)' },
  { id: 'lease', label: 'Leasing / Renewal (File)' },
  { id: 'reporting', label: 'Owner Reporting (Chart)' },
];

export default function AddAutomationModal({
  isOpen,
  onClose,
  onCreated,
}: AddAutomationModalProps) {
  const [name, setName] = useState('');
  const [tagline, setTagline] = useState('');
  const [description, setDescription] = useState('');
  const [iconType, setIconType] = useState('maintenance');
  const [selectedChannels, setSelectedChannels] = useState<string[]>(['WhatsApp', 'Email']);
  const [escalationText, setEscalationText] = useState('AI confidence < 85%\nManual approval requested');
  const [scope, setScope] = useState('All Properties (42)');

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const toggleChannel = (ch: string) => {
    setSelectedChannels((prev) => {
      const updated = prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch];
      if (updated.length > 0 && fieldErrors.channels) {
        setFieldErrors((errs) => {
          const cp = { ...errs };
          delete cp.channels;
          return cp;
        });
      }
      return updated;
    });
    setError(null);
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!name.trim()) {
      errors.name = 'Automation name is required.';
    } else if (name.trim().length < 3) {
      errors.name = 'Automation name must be at least 3 characters.';
    }

    if (selectedChannels.length === 0) {
      errors.channels = 'Select at least one active communication channel.';
    }

    const conditions = escalationText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    if (conditions.length === 0) {
      errors.escalation = 'At least one escalation condition is required.';
    }

    if (!scope.trim()) {
      errors.scope = 'Property scope is required.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      setError('Please resolve the highlighted validation errors.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    const conditions = escalationText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    const autoId = name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '_');

    try {
      const payload: Partial<AutomationCard> & { tagline?: string } = {
        id: autoId,
        name: name.trim(),
        status: 'Active',
        description: description.trim() || `Handles: ${name.trim()} operations.`,
        tagline: tagline.trim() || `Automated operational workflow for ${name.trim()}.`,
        channels: selectedChannels,
        escalation_conditions: conditions,
        scope: scope.trim() || 'All Properties (42)',
        properties_count: 42,
        icon_type: iconType,
        handles: [name.trim(), 'Automated workflow'],
      };

      const res = await apiClient.createAutomation(payload);
      setSuccess(true);

      const createdCard: AutomationCard = res.data ?? {
        id: autoId,
        name: name.trim(),
        status: 'Active',
        description: description.trim() || `Handles: ${name.trim()} operations.`,
        channels: selectedChannels,
        escalation_conditions: conditions,
        scope: scope.trim(),
        properties_count: 42,
        icon_type: iconType,
        handles: [name.trim()],
      };

      setTimeout(() => {
        setSuccess(false);
        setIsSubmitting(false);
        onCreated(createdCard);
        onClose();
      }, 800);
    } catch (err: unknown) {
      console.error('Error creating automation:', err);
      const msg = err instanceof Error ? err.message : 'Failed to save automation to database.';
      setError(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200">
          
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center font-bold">
                <Sparkles size={18} />
              </div>
              <h2 className="font-extrabold text-slate-900 text-lg">Add New Automation</h2>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-slate-200/60 text-slate-400 hover:text-slate-700 flex items-center justify-center transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium flex items-center gap-2">
                <AlertCircle size={15} />
                <span>{error}</span>
              </div>
            )}

            {/* Automation Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Automation Name *
              </label>
              <input
                type="text"
                placeholder="e.g., Security Inspection, Late Fee Waiver"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (fieldErrors.name) {
                    setFieldErrors((prev) => {
                      const cp = { ...prev };
                      delete cp.name;
                      return cp;
                    });
                  }
                }}
                className={`w-full text-sm rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 transition-all ${
                  fieldErrors.name
                    ? 'bg-red-50/30 border border-red-300 focus:ring-red-400 focus:border-red-400'
                    : 'bg-slate-50 border border-slate-200 focus:ring-teal-400 focus:bg-white'
                }`}
              />
              {fieldErrors.name && (
                <p className="text-xs text-red-500 mt-1 font-medium">{fieldErrors.name}</p>
              )}
            </div>

            {/* Workflow Category */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Category & Icon Type
              </label>
              <select
                value={iconType}
                onChange={(e) => setIconType(e.target.value)}
                className="w-full text-sm bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:bg-white transition-all appearance-none cursor-pointer"
              >
                {ICON_TYPES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Tagline / Description */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Workflow Description
              </label>
              <input
                type="text"
                placeholder="e.g., Handles: Routine inspections, vendor dispatch."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full text-sm bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:bg-white transition-all"
              />
            </div>

            {/* Channels */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Active Communication Channels *
              </label>
              <div className="flex items-center gap-2 flex-wrap">
                {AVAILABLE_CHANNELS.map((ch) => {
                  const selected = selectedChannels.includes(ch);
                  return (
                    <button
                      type="button"
                      key={ch}
                      onClick={() => toggleChannel(ch)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                        selected
                          ? 'bg-teal-600 text-white border-teal-600 shadow-xs'
                          : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      {selected ? '✓ ' : '+ '}{ch}
                    </button>
                  );
                })}
              </div>
              {fieldErrors.channels && (
                <p className="text-xs text-red-500 mt-1 font-medium">{fieldErrors.channels}</p>
              )}
            </div>

            {/* Escalation Conditions */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Escalation Conditions (one per line) *
              </label>
              <textarea
                rows={3}
                value={escalationText}
                onChange={(e) => {
                  setEscalationText(e.target.value);
                  if (fieldErrors.escalation) {
                    setFieldErrors((prev) => {
                      const cp = { ...prev };
                      delete cp.escalation;
                      return cp;
                    });
                  }
                }}
                placeholder="e.g., Emergency detected&#10;AI confidence < 85%"
                className={`w-full text-xs text-slate-700 rounded-xl p-3 focus:outline-none focus:ring-2 resize-none transition-all ${
                  fieldErrors.escalation
                    ? 'bg-red-50/30 border border-red-300 focus:ring-red-400 focus:border-red-400'
                    : 'bg-slate-50 border border-slate-200 focus:ring-teal-400 focus:bg-white'
                }`}
              />
              {fieldErrors.escalation && (
                <p className="text-xs text-red-500 mt-1 font-medium">{fieldErrors.escalation}</p>
              )}
            </div>

            {/* Scope */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Property Scope *
              </label>
              <input
                type="text"
                placeholder="e.g., All Properties (42) or 5 Selected Properties"
                value={scope}
                onChange={(e) => {
                  setScope(e.target.value);
                  if (fieldErrors.scope) {
                    setFieldErrors((prev) => {
                      const cp = { ...prev };
                      delete cp.scope;
                      return cp;
                    });
                  }
                }}
                className={`w-full text-sm rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 transition-all ${
                  fieldErrors.scope
                    ? 'bg-red-50/30 border border-red-300 focus:ring-red-400 focus:border-red-400'
                    : 'bg-slate-50 border border-slate-200 focus:ring-teal-400 focus:bg-white'
                }`}
              />
              {fieldErrors.scope && (
                <p className="text-xs text-red-500 mt-1 font-medium">{fieldErrors.scope}</p>
              )}
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 text-sm font-semibold hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold shadow-md shadow-teal-900/10 transition-colors disabled:opacity-60"
              >
                {isSubmitting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : success ? (
                  <Check size={16} />
                ) : (
                  <Plus size={16} />
                )}
                {success ? 'Saved to DB!' : isSubmitting ? 'Saving to DB...' : 'Create Automation'}
              </button>
            </div>
          </form>

        </div>
      </div>
    </>
  );
}
