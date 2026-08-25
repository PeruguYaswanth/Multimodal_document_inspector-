import React, { useState, useEffect } from "react";
import { 
  X, 
  Check, 
  Plus, 
  Trash2, 
  Save, 
  RefreshCw, 
  ZoomIn, 
  ZoomOut, 
  RotateCw,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Table as TableIcon,
  Sparkles,
  ExternalLink
} from "lucide-react";
import DocumentTypeBadge from "./DocumentTypeBadge";
import ConfidenceBadge from "./ConfidenceBadge";
import { updateDocument, reprocessDocument } from "../api";

export default function DocumentReviewModal({ document: initialDoc, onClose, onSaveSuccess }) {
  const [doc, setDoc] = useState(initialDoc);
  const [activeTab, setActiveTab] = useState("fields"); // fields, tables, text, meta
  const [primarySubject, setPrimarySubject] = useState("");
  const [fields, setFields] = useState({});
  const [tables, setTables] = useState([]);
  const [summary, setSummary] = useState("");
  const [fullText, setFullText] = useState("");
  const [confidence, setConfidence] = useState("medium");
  const [isReviewed, setIsReviewed] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newVal, setNewVal] = useState("");
  
  const [zoomLevel, setZoomLevel] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    if (initialDoc) {
      setDoc(initialDoc);
      setPrimarySubject(initialDoc.primary_subject || "");
      setFields(initialDoc.extracted_fields || {});
      setTables(initialDoc.tables || []);
      setSummary(initialDoc.summary || "");
      setFullText(initialDoc.full_text || "");
      setConfidence(initialDoc.confidence || "medium");
      setIsReviewed(Boolean(initialDoc.is_reviewed));
    }
  }, [initialDoc]);

  if (!doc) return null;

  const imageFileName = (doc.image_path || "").split(/[\\/]/).pop();
  const imageUrl = `/uploads/${imageFileName}`;

  const handleFieldChange = (key, value) => {
    setFields(prev => ({ ...prev, [key]: value }));
  };

  const handleAddField = () => {
    if (!newKey.trim()) return;
    setFields(prev => ({ ...prev, [newKey.trim()]: newVal }));
    setNewKey("");
    setNewVal("");
  };

  const handleDeleteField = (key) => {
    setFields(prev => {
      const copy = { ...prev };
      delete copy[key];
      return copy;
    });
  };

  const handleSave = async (markReviewed = true) => {
    setIsSaving(true);
    setSaveMessage("");
    try {
      const updated = await updateDocument(doc.id, {
        primary_subject: primarySubject,
        summary,
        extracted_fields: fields,
        tables,
        full_text: fullText,
        confidence,
        is_reviewed: markReviewed ? true : isReviewed,
      });
      setDoc(updated);
      setPrimarySubject(updated.primary_subject || "");
      setIsReviewed(updated.is_reviewed);
      setSaveMessage(markReviewed ? "Saved & Marked as Confirmed!" : "Changes Saved!");
      if (onSaveSuccess) onSaveSuccess(updated);
      setTimeout(() => setSaveMessage(""), 3000);
    } catch (err) {
      alert("Failed to save changes: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReprocess = async () => {
    setIsReprocessing(true);
    try {
      const reprocessed = await reprocessDocument(doc.id);
      setDoc(reprocessed);
      setPrimarySubject(reprocessed.primary_subject || "");
      setFields(reprocessed.extracted_fields || {});
      setTables(reprocessed.tables || []);
      setSummary(reprocessed.summary || "");
      setFullText(reprocessed.full_text || "");
      setConfidence(reprocessed.confidence || "medium");
      setIsReviewed(Boolean(reprocessed.is_reviewed));
      if (onSaveSuccess) onSaveSuccess(reprocessed);
    } catch (err) {
      alert("Reprocessing failed: " + err.message);
    } finally {
      setIsReprocessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      
      <div className="relative w-full max-w-6xl h-[90vh] bg-slate-900 border border-slate-700/80 rounded-3xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div className="flex items-center gap-3">
            <DocumentTypeBadge type={doc.document_type} />
            <span className="text-slate-400">/</span>
            <h2 className="text-base font-bold text-slate-100 truncate max-w-md">
              {doc.original_filename}
            </h2>
            <ConfidenceBadge confidence={confidence} notesCount={(doc.low_confidence_notes || []).length} />
          </div>

          <div className="flex items-center gap-2">
            {saveMessage && (
              <span className="text-xs font-semibold text-emerald-400 animate-pulse flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {saveMessage}
              </span>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body: Split Screen */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
          
          {/* Left Column: Image Viewer with Zoom & Pan */}
          <div className="lg:col-span-6 bg-slate-950 p-4 border-b lg:border-b-0 lg:border-r border-slate-800 flex flex-col justify-between overflow-hidden">
            
            {/* Image Viewer Toolbar */}
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs text-slate-400">
              <span className="font-mono">Dimensions: {doc.meta_info?.width}x{doc.meta_info?.height}</span>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setZoomLevel(z => Math.max(0.5, z - 0.25))}
                  className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <span className="px-1 text-[11px] font-mono">{Math.round(zoomLevel * 100)}%</span>
                <button
                  onClick={() => setZoomLevel(z => Math.min(3, z + 0.25))}
                  className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setRotation(r => (r + 90) % 360)}
                  className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                  title="Rotate"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Zoomable Image Container */}
            <div className="flex-1 overflow-auto flex items-center justify-center p-4 my-2 rounded-xl bg-slate-900/50 border border-slate-800/60">
              <img
                src={imageUrl}
                alt={doc.original_filename}
                style={{
                  transform: `scale(${zoomLevel}) rotate(${rotation}deg)`,
                  transition: "transform 0.2s ease-out"
                }}
                className="max-h-full max-w-full object-contain rounded-lg shadow-lg"
                onError={(e) => { e.target.src = "https://placehold.co/600x800/1e293b/94a3b8?text=Image+Preview"; }}
              />
            </div>

            {/* Low Confidence Warnings if any */}
            {(doc.low_confidence_notes || []).length > 0 && (
              <div className="mt-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Extraction Flag Notes:</p>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-200 mt-1">
                    {doc.low_confidence_notes.map((note, idx) => (
                      <li key={idx}>{note}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

          </div>

          {/* Right Column: Dynamic Key-Value & Structured Data Editor */}
          <div className="lg:col-span-6 flex flex-col justify-between bg-slate-900 overflow-hidden">
            
            {/* Tabs */}
            <div className="flex items-center gap-2 px-6 pt-4 border-b border-slate-800">
              <button
                onClick={() => setActiveTab("fields")}
                className={`pb-3 text-xs font-semibold border-b-2 transition-all ${
                  activeTab === "fields"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Dynamic Fields ({Object.keys(fields).length})
              </button>

              <button
                onClick={() => setActiveTab("tables")}
                className={`pb-3 text-xs font-semibold border-b-2 transition-all ${
                  activeTab === "tables"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Tables ({tables.length})
              </button>

              <button
                onClick={() => setActiveTab("text")}
                className={`pb-3 text-xs font-semibold border-b-2 transition-all ${
                  activeTab === "text"
                    ? "border-indigo-500 text-indigo-400"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                Full Text OCR
              </button>
            </div>

            {/* Tab Contents Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              
              {/* Primary Subject */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Primary Subject / Title
                </label>
                <input
                  type="text"
                  value={primarySubject}
                  onChange={(e) => setPrimarySubject(e.target.value)}
                  placeholder="e.g. South Indian Curd Rice Dish, Metro Parking Ticket..."
                  className="w-full text-xs bg-slate-950 border border-slate-700/80 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Summary Editor */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Document Summary
                </label>
                <textarea
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  rows={2}
                  className="w-full text-xs bg-slate-950 border border-slate-700/80 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Dynamic Fields Tab */}
              {activeTab === "fields" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Extracted Key-Value Pairs
                    </label>
                    <span className="text-[11px] text-slate-500">Universal Schema</span>
                  </div>

                  <div className="space-y-2.5">
                    {Object.entries(fields).map(([k, v]) => {
                      const displayVal = typeof v === "object" ? JSON.stringify(v) : String(v ?? "");
                      return (
                        <div key={k} className="flex items-center gap-2 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                          <span className="w-1/3 text-xs font-medium text-slate-400 capitalize truncate font-mono">
                            {k.replace(/_/g, " ")}:
                          </span>
                          <input
                            type="text"
                            value={displayVal}
                            onChange={(e) => handleFieldChange(k, e.target.value)}
                            className="flex-1 text-xs bg-slate-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
                          />
                          <button
                            onClick={() => handleDeleteField(k)}
                            className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                            title="Delete field"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      );
                    })}
                  </div>

                  {/* Add New Key-Value Pair */}
                  <div className="pt-3 border-t border-slate-800/80 flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="New key name (e.g. tax_rate)"
                      value={newKey}
                      onChange={(e) => setNewKey(e.target.value)}
                      className="w-1/3 text-xs bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200"
                    />
                    <input
                      type="text"
                      placeholder="Value"
                      value={newVal}
                      onChange={(e) => setNewVal(e.target.value)}
                      className="flex-1 text-xs bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200"
                    />
                    <button
                      onClick={handleAddField}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Tables Tab */}
              {activeTab === "tables" && (
                <div className="space-y-4">
                  {tables.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No structured tables detected in this document.</p>
                  ) : (
                    tables.map((tbl, tIdx) => (
                      <div key={tIdx} className="bg-slate-950/60 rounded-xl border border-slate-800 p-3 space-y-2">
                        <h4 className="text-xs font-bold text-slate-300">{tbl.title || `Table #${tIdx + 1}`}</h4>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs">
                            <thead className="bg-slate-900/90 text-slate-400">
                              <tr>
                                {Object.keys(tbl.rows[0] || {}).map(header => (
                                  <th key={header} className="p-2 font-medium capitalize">{header}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/60">
                              {tbl.rows.map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-slate-900/40">
                                  {Object.entries(row).map(([k, cell], cIdx) => (
                                    <td key={cIdx} className="p-2 font-mono text-slate-300">
                                      {String(cell)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Full Text OCR Tab */}
              {activeTab === "text" && (
                <div>
                  <textarea
                    value={fullText}
                    onChange={(e) => setFullText(e.target.value)}
                    rows={12}
                    placeholder="Full readable transcription..."
                    className="w-full text-xs font-mono bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-300 focus:outline-none focus:border-indigo-500 leading-relaxed"
                  />
                </div>
              )}

            </div>

            {/* Modal Footer Controls */}
            <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between gap-3">
              <button
                onClick={handleReprocess}
                disabled={isReprocessing}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 bg-slate-800/80 rounded-xl"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isReprocessing ? 'animate-spin' : ''}`} />
                <span>Re-run Extraction</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSave(false)}
                  disabled={isSaving}
                  className="px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 border border-slate-700 rounded-xl transition-all"
                >
                  Save Draft
                </button>

                <button
                  onClick={() => handleSave(true)}
                  disabled={isSaving}
                  className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
                >
                  <Check className="w-4 h-4" />
                  <span>Confirm & Mark Reviewed</span>
                </button>
              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
