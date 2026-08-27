'use client';

import React, { useState } from 'react';
import { AlertTriangle, Trash2, X, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  propertyId: string | null;
  propertyTitle: string;
  onClose: () => void;
  onDeleted: () => void;
}

export default function DeleteConfirmModal({
  isOpen,
  propertyId,
  propertyTitle,
  onClose,
  onDeleted,
}: DeleteConfirmModalProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!propertyId) return;
    setDeleting(true);
    setError(null);
    try {
      await apiClient.deleteProperty(propertyId);
      onDeleted();
      onClose();
    } catch (err: any) {
      console.error('Failed to delete property:', err);
      setError(err.message || 'Failed to delete property. Please try again.');
    } finally {
      setDeleting(false);
    }
  };

  if (!isOpen || !propertyId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md mx-4 bg-white rounded-2xl shadow-2xl border border-slate-200/50 animate-in fade-in zoom-in-95 duration-200">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <X size={16} />
        </button>

        {/* Content */}
        <div className="p-6 text-center">
          {/* Warning Icon */}
          <div className="w-14 h-14 mx-auto rounded-2xl bg-red-50 flex items-center justify-center mb-4">
            <AlertTriangle size={28} className="text-red-500" />
          </div>

          <h3 className="text-lg font-bold text-slate-900 mb-2">Delete Property?</h3>
          <p className="text-sm text-slate-500 mb-1">
            This will permanently remove <strong className="text-slate-700">{propertyTitle}</strong> from the database.
          </p>
          <p className="text-xs text-slate-400 mb-6">
            Conversation history linked to this property will be preserved.
          </p>

          {/* Error */}
          {error && (
            <div className="mb-4 px-4 py-2 rounded-xl bg-red-50 border border-red-200 text-sm text-red-600 font-medium">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex-1 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-all shadow-md shadow-red-900/15 active:scale-[0.98] disabled:opacity-60"
            >
              {deleting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 size={14} />
                  Delete Property
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
