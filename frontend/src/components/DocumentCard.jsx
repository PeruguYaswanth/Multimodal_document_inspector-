import React from "react";
import { 
  Eye, 
  Trash2, 
  RefreshCw, 
  MessageSquareText, 
  Calendar, 
  AlertTriangle,
  CheckCircle2,
  Table as TableIcon,
  FileText
} from "lucide-react";
import DocumentTypeBadge from "./DocumentTypeBadge";
import ConfidenceBadge from "./ConfidenceBadge";
import { getImageUrl } from "../api";

export default function DocumentCard({ 
  document, 
  onReview, 
  onAskChat, 
  onDelete, 
  onReprocess 
}) {
  const filename = document.original_filename || "Document";
  const imageUrl = getImageUrl(document.image_path);
  
  const extractedKeys = Object.keys(document.extracted_fields || {});
  const hasTables = (document.tables || []).length > 0;
  const isReviewed = document.is_reviewed;
  const needsReview = !isReviewed || document.confidence === "low" || (document.low_confidence_notes || []).length > 0;

  return (
    <div className={`group relative rounded-2xl bg-slate-900/70 border transition-all duration-200 overflow-hidden flex flex-col justify-between hover:shadow-xl hover:shadow-indigo-950/30 ${
      needsReview && !isReviewed
        ? "border-amber-500/40 hover:border-amber-500/70"
        : "border-slate-800 hover:border-slate-700"
    }`}>
      
      {/* Top Image Preview & Badges */}
      <div className="relative h-44 bg-slate-950 overflow-hidden">
        <img
          src={imageUrl}
          alt={filename}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          onError={(e) => { e.target.src = "https://placehold.co/400x300/1e293b/94a3b8?text=Document+Image"; }}
        />
        
        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />

        {/* Top Badges */}
        <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between gap-1">
          <DocumentTypeBadge type={document.document_type} size="sm" />
          <ConfidenceBadge confidence={document.confidence} notesCount={(document.low_confidence_notes || []).length} />
        </div>

        {/* Review Status Banner */}
        {needsReview && !isReviewed ? (
          <div className="absolute bottom-2 left-2.5 flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/90 text-slate-950 text-[10px] font-bold shadow-md">
            <AlertTriangle className="w-3 h-3" />
            <span>NEEDS USER REVIEW</span>
          </div>
        ) : isReviewed ? (
          <div className="absolute bottom-2 left-2.5 flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/90 text-slate-950 text-[10px] font-bold shadow-md">
            <CheckCircle2 className="w-3 h-3" />
            <span>REVIEWED & CONFIRMED</span>
          </div>
        ) : null}

      </div>

      {/* Card Body */}
      <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
        
        <div>
          <h3 className="text-sm font-semibold text-slate-100 truncate" title={document.primary_subject || filename}>
            {document.primary_subject || filename}
          </h3>
          {document.primary_subject && (
            <p className="text-[11px] text-indigo-300 font-mono truncate">{filename}</p>
          )}
          <p className="text-xs text-slate-400 line-clamp-2 mt-1">
            {document.summary || "No summary available."}
          </p>
        </div>

        {/* Dynamic Key-Value Sample Chips */}
        {extractedKeys.length > 0 && (
          <div className="bg-slate-950/50 rounded-xl p-2.5 border border-slate-800/80 space-y-1.5">
            <div className="flex items-center justify-between text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
              <span>Extracted Fields</span>
              <span>{extractedKeys.length} items</span>
            </div>
            <div className="space-y-1">
              {extractedKeys.slice(0, 3).map(key => {
                const val = document.extracted_fields[key];
                const displayVal = typeof val === "object" ? JSON.stringify(val) : String(val);
                return (
                  <div key={key} className="flex items-baseline justify-between text-xs gap-2">
                    <span className="text-slate-400 capitalize truncate max-w-[45%] text-[11px]">
                      {key.replace(/_/g, " ")}:
                    </span>
                    <span className="font-medium text-slate-200 truncate text-[11px] max-w-[55%] text-right font-mono">
                      {displayVal}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Metadata Footer info */}
        <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {document.uploaded_at ? new Date(document.uploaded_at).toLocaleDateString() : "Recent"}
          </span>
          {hasTables && (
            <span className="flex items-center gap-1 text-indigo-400">
              <TableIcon className="w-3 h-3" />
              {document.tables.length} Table(s)
            </span>
          )}
        </div>

      </div>

      {/* Card Action Toolbar */}
      <div className="px-4 py-2.5 bg-slate-950/60 border-t border-slate-800/80 flex items-center justify-between gap-1">
        <button
          onClick={() => onReview(document)}
          className="flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          <Eye className="w-3.5 h-3.5 text-indigo-400" />
          <span>Review / Edit</span>
        </button>

        <button
          onClick={() => onAskChat(document)}
          title="Ask AI about this document"
          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-300 hover:bg-slate-800 transition-colors"
        >
          <MessageSquareText className="w-4 h-4" />
        </button>

        <button
          onClick={() => onReprocess(document.id)}
          title="Re-run 2-Stage Pipeline"
          className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-300 hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        <button
          onClick={() => onDelete(document.id)}
          title="Delete Document"
          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

    </div>
  );
}
