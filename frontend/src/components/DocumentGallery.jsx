import React, { useState, useMemo } from "react";
import { 
  Search, 
  Filter, 
  Grid, 
  List as ListIcon, 
  AlertTriangle, 
  Layers, 
  UploadCloud, 
  Sparkles,
  Calendar
} from "lucide-react";
import DocumentCard from "./DocumentCard";
import DocumentTypeBadge from "./DocumentTypeBadge";
import ConfidenceBadge from "./ConfidenceBadge";
import { getImageUrl } from "../api";

export default function DocumentGallery({
  documents,
  onReview,
  onAskChat,
  onDelete,
  onReprocess,
  onNavigateUpload,
  onLoadSample,
  loadingSample
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedType, setSelectedType] = useState("all");
  const [selectedConfidence, setSelectedConfidence] = useState("all");
  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false);
  const [viewMode, setViewMode] = useState("grid"); // grid or table

  // Unique document types present in collection
  const availableTypes = useMemo(() => {
    const set = new Set(documents.map(d => d.document_type || "other"));
    return Array.from(set);
  }, [documents]);

  // Filtering logic
  const filteredDocs = useMemo(() => {
    return documents.filter(doc => {
      // Search term matching
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const fname = (doc.original_filename || "").toLowerCase();
        const summary = (doc.summary || "").toLowerCase();
        const text = (doc.full_text || "").toLowerCase();
        const fieldsStr = JSON.stringify(doc.extracted_fields || {}).toLowerCase();
        if (!fname.includes(term) && !summary.includes(term) && !text.includes(term) && !fieldsStr.includes(term)) {
          return false;
        }
      }

      // Type filter
      if (selectedType !== "all" && doc.document_type !== selectedType) {
        return false;
      }

      // Confidence filter
      if (selectedConfidence !== "all" && doc.confidence !== selectedConfidence) {
        return false;
      }

      // Needs review flag filter
      if (onlyNeedsReview) {
        const needsRev = !doc.is_reviewed || doc.confidence === "low" || (doc.low_confidence_notes || []).length > 0;
        if (!needsRev) return false;
      }

      return true;
    });
  }, [documents, searchTerm, selectedType, selectedConfidence, onlyNeedsReview]);

  return (
    <div className="space-y-6">
      
      {/* Search and Filters Toolbar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 sm:p-5 backdrop-blur-sm space-y-4">
        
        <div className="flex flex-col sm:flex-row items-center gap-3 justify-between">
          
          {/* Search Box */}
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search text, items, merchant, notes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full text-xs bg-slate-950 border border-slate-700/80 rounded-xl pl-9 pr-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-200"
              >
                Clear
              </button>
            )}
          </div>

          {/* Quick Filter Controls */}
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
            
            {/* Needs Review Filter Toggle */}
            <button
              onClick={() => setOnlyNeedsReview(prev => !prev)}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                onlyNeedsReview
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/50 shadow-md shadow-amber-500/10"
                  : "bg-slate-950/50 text-slate-400 border border-slate-800 hover:border-slate-700"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Needs Review Only</span>
            </button>

            {/* View Mode (Grid / Table) */}
            <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setViewMode("grid")}
                className={`p-1.5 rounded-lg transition-colors ${
                  viewMode === "grid" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
                title="Grid View"
              >
                <Grid className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`p-1.5 rounded-lg transition-colors ${
                  viewMode === "table" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
                title="Table View"
              >
                <ListIcon className="w-3.5 h-3.5" />
              </button>
            </div>

          </div>

        </div>

        {/* Filter Pills (Categories & Confidence) */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80">
          
          <span className="text-[11px] text-slate-500 uppercase font-semibold mr-1">Type:</span>
          <button
            onClick={() => setSelectedType("all")}
            className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
              selectedType === "all"
                ? "bg-indigo-600 text-white"
                : "bg-slate-950/50 text-slate-400 border border-slate-800 hover:border-slate-700"
            }`}
          >
            All Types ({documents.length})
          </button>

          {availableTypes.map(t => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-2.5 py-1 text-xs rounded-lg font-medium capitalize transition-all ${
                selectedType === t
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-950/50 text-slate-400 border border-slate-800 hover:border-slate-700"
              }`}
            >
              {t.replace(/_/g, " ")} ({documents.filter(d => d.document_type === t).length})
            </button>
          ))}

          <div className="h-4 w-[1px] bg-slate-800 mx-2 hidden sm:block" />

          <span className="text-[11px] text-slate-500 uppercase font-semibold mr-1">Confidence:</span>
          {["all", "high", "medium", "low"].map(c => (
            <button
              key={c}
              onClick={() => setSelectedConfidence(c)}
              className={`px-2 py-0.5 text-xs rounded-lg capitalize transition-all ${
                selectedConfidence === c
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {c}
            </button>
          ))}

        </div>

      </div>

      {/* Gallery Content Area */}
      {filteredDocs.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-12 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mx-auto">
            <Layers className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-200">No Documents Found</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
              {documents.length === 0
                ? "Your collection is empty. Upload image documents or load the 4-type sample test dataset to get started immediately."
                : "No documents matched your current search filters. Try clearing your search or filters."}
            </p>
          </div>

          {documents.length === 0 && (
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={onNavigateUpload}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30"
              >
                <UploadCloud className="w-4 h-4" />
                <span>Upload Documents</span>
              </button>

              <button
                onClick={onLoadSample}
                disabled={loadingSample}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
              >
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span>Load Sample Dataset</span>
              </button>
            </div>
          )}
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredDocs.map(doc => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onReview={onReview}
              onAskChat={onAskChat}
              onDelete={onDelete}
              onReprocess={onReprocess}
            />
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-3.5 font-semibold">Image & Filename</th>
                  <th className="p-3.5 font-semibold">Type</th>
                  <th className="p-3.5 font-semibold">Summary</th>
                  <th className="p-3.5 font-semibold">Confidence</th>
                  <th className="p-3.5 font-semibold">Date</th>
                  <th className="p-3.5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredDocs.map(doc => {
                  const imageFileName = (doc.image_path || "").split(/[\\/]/).pop();
                  return (
                    <tr key={doc.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="p-3.5 flex items-center gap-3">
                        <img
                          src={getImageUrl(doc.image_path)}
                          alt={doc.original_filename}
                          className="w-10 h-10 object-cover rounded-lg bg-slate-950 border border-slate-800 flex-shrink-0"
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                        <span className="font-semibold text-slate-200 truncate max-w-xs">{doc.original_filename}</span>
                      </td>
                      <td className="p-3.5">
                        <DocumentTypeBadge type={doc.document_type} size="sm" />
                      </td>
                      <td className="p-3.5 max-w-xs text-slate-400 truncate">
                        {doc.summary || "-"}
                      </td>
                      <td className="p-3.5">
                        <ConfidenceBadge confidence={doc.confidence} notesCount={(doc.low_confidence_notes || []).length} />
                      </td>
                      <td className="p-3.5 text-slate-400 whitespace-nowrap">
                        {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : "-"}
                      </td>
                      <td className="p-3.5 text-right space-x-2">
                        <button
                          onClick={() => onReview(doc)}
                          className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          Review
                        </button>
                        <button
                          onClick={() => onAskChat(doc)}
                          className="text-xs text-slate-400 hover:text-slate-200 font-medium"
                        >
                          Chat
                        </button>
                        <button
                          onClick={() => onDelete(doc.id)}
                          className="text-xs text-rose-400 hover:text-rose-300 font-medium"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
