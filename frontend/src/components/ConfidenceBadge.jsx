import React from "react";
import { CheckCircle2, AlertTriangle, AlertCircle } from "lucide-react";

export default function ConfidenceBadge({ confidence = "medium", notesCount = 0 }) {
  const conf = confidence.toLowerCase();
  
  if (conf === "high" && notesCount === 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <CheckCircle2 className="w-3 h-3" />
        High Confidence
      </span>
    );
  }
  
  if (conf === "low" || notesCount > 0) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <AlertTriangle className="w-3 h-3" />
        Needs Review {notesCount > 0 && `(${notesCount} note${notesCount > 1 ? 's' : ''})`}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
      <AlertCircle className="w-3 h-3" />
      Medium Confidence
    </span>
  );
}
