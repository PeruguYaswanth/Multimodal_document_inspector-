import React from "react";
import { Layers, CheckCircle2, AlertTriangle, Sparkles, RefreshCw } from "lucide-react";
import { getDocTypeDetails } from "./DocumentTypeBadge";

export default function StatsBanner({ stats, onQuickLoadSample, loadingSample }) {
  if (!stats) return null;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 sm:p-5 backdrop-blur-sm">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        {/* KPI Counter Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 flex-1">
          
          <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-3">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Total Documents</span>
              <Layers className="w-4 h-4 text-indigo-400" />
            </div>
            <p className="text-xl font-bold text-slate-100">{stats.total_documents}</p>
          </div>

          <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-3">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Reviewed / Verified</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-xl font-bold text-emerald-400">{stats.reviewed_count}</p>
          </div>

          <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-3">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Needs Review</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-xl font-bold text-amber-400">{stats.needs_review_count}</p>
          </div>

          <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-3">
            <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
              <span>Low Confidence</span>
              <AlertTriangle className="w-4 h-4 text-rose-400" />
            </div>
            <p className="text-xl font-bold text-rose-400">{stats.low_confidence_count}</p>
          </div>

        </div>

        {/* Action Button & Document Types summary */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 lg:border-l lg:border-slate-800 lg:pl-5">
          
          <div className="flex flex-wrap gap-1.5 max-w-md">
            {Object.entries(stats.type_breakdown || {}).map(([type, count]) => {
              const { label, color } = getDocTypeDetails(type);
              return (
                <span key={type} className={`text-[11px] px-2 py-0.5 rounded-md border ${color}`}>
                  {type}: <strong className="font-semibold">{count}</strong>
                </span>
              );
            })}
          </div>

          <button
            onClick={onQuickLoadSample}
            disabled={loadingSample}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white shadow-lg shadow-indigo-600/20 disabled:opacity-50 transition-all cursor-pointer whitespace-nowrap"
          >
            {loadingSample ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Ingesting Test Suite...
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                Load 4-Type Test Suite
              </>
            )}
          </button>

        </div>

      </div>
    </div>
  );
}
