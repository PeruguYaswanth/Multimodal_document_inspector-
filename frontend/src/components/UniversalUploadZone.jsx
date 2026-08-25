import React, { useState, useRef } from "react";
import { 
  UploadCloud, 
  FileImage, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  RefreshCw, 
  Eye, 
  Layers,
  ArrowRight
} from "lucide-react";
import { uploadImages } from "../api";
import DocumentTypeBadge from "./DocumentTypeBadge";
import ConfidenceBadge from "./ConfidenceBadge";

export default function UniversalUploadZone({ onUploadComplete, onSelectDocForReview }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [processedDocs, setProcessedDocs] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef(null);

  const handleFiles = (files) => {
    setErrorMsg("");
    const validExtensions = [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"];
    const fileList = Array.from(files).filter(f => 
      f.type.startsWith("image/") || validExtensions.some(ext => f.name.toLowerCase().endsWith(ext))
    );
    if (fileList.length === 0) {
      setErrorMsg("Please select valid image files (PNG, JPG, WEBP, TIFF, etc.)");
      return;
    }

    setSelectedFiles(prev => [...prev, ...fileList]);

    // Generate previews
    fileList.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviews(prev => [...prev, { name: file.name, size: file.size, url: reader.result }]);
      };
      reader.readAsDataURL(file);
    });
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleRemove = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    setPreviews(prev => prev.filter((_, i) => i !== index));
  };

  const handleStartIngestion = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setErrorMsg("");
    setProcessedDocs([]);
    setUploadProgress("Starting 2-Stage Multimodal Extraction Pipeline...");

    try {
      setUploadProgress("Running Stage 1A (Classification) & Stage 1B (Dynamic Extraction)...");
      const docs = await uploadImages(selectedFiles);
      setProcessedDocs(docs);
      setUploadProgress(`Successfully processed ${docs.length} document(s)!`);
      if (onUploadComplete) onUploadComplete();
      // Clear file selection after success
      setSelectedFiles([]);
      setPreviews([]);
    } catch (err) {
      setErrorMsg(err.message || "Failed to process images.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Upload Header */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
        <div className="max-w-2xl">
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <UploadCloud className="w-6 h-6 text-indigo-400" />
            Universal Document Ingestion
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Upload any image (receipts, invoices, handwritten notes, ID cards, forms, whiteboards, diagrams).
            The two-stage vision pipeline dynamically classifies document types and extracts key fields without hardcoded schemas.
          </p>
        </div>

        {/* Dropzone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`mt-6 border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
            isDragging 
              ? "border-indigo-500 bg-indigo-500/10 scale-[1.005]" 
              : "border-slate-700/80 bg-slate-950/40 hover:border-slate-600 hover:bg-slate-900/40"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFiles(e.target.files)}
            multiple
            accept="image/*,.png,.jpg,.jpeg,.webp,.tiff,.tif,.bmp"
            className="hidden"
          />

          <div className="flex flex-col items-center justify-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <FileImage className="w-7 h-7" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-200">
                Click or drag & drop documents here
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                Supports PNG, JPG, JPEG, WEBP, TIFF (Multi-file enabled, max 25MB each)
              </p>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-slate-500 bg-slate-900/80 px-3 py-1 rounded-full border border-slate-800">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Auto-rotates via EXIF & checks SHA-256 deduplication</span>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Staged File Previews */}
        {previews.length > 0 && (
          <div className="mt-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Staged Images ({previews.length})
              </h3>
              <button
                onClick={() => { setSelectedFiles([]); setPreviews([]); }}
                className="text-xs text-slate-400 hover:text-slate-200"
              >
                Clear All
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {previews.map((item, idx) => (
                <div key={idx} className="relative group rounded-xl overflow-hidden border border-slate-700/80 bg-slate-900/90 p-1.5">
                  <img
                    src={item.url}
                    alt={item.name}
                    className="w-full h-28 object-cover rounded-lg"
                  />
                  <div className="mt-1.5 px-1">
                    <p className="text-[11px] font-medium text-slate-200 truncate">{item.name}</p>
                    <p className="text-[10px] text-slate-500">{(item.size / 1024).toFixed(0)} KB</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRemove(idx); }}
                    className="absolute top-2.5 right-2.5 w-6 h-6 rounded-full bg-slate-900/90 text-slate-400 hover:text-rose-400 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity border border-slate-700"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Launch Ingestion Button */}
            <div className="pt-2 flex justify-end">
              <button
                onClick={handleStartIngestion}
                disabled={isUploading}
                className="flex items-center gap-2 px-6 py-2.5 text-sm font-semibold rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white shadow-lg shadow-indigo-600/30 disabled:opacity-50 transition-all cursor-pointer"
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>{uploadProgress || "Processing..."}</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Run Two-Stage Extraction ({selectedFiles.length})</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

      </div>

      {/* Newly Processed Documents Results */}
      {processedDocs.length > 0 && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-100">
                Extraction Completed ({processedDocs.length} Documents)
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              Auto-classified & saved to flexible SQLite schema
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {processedDocs.map(doc => (
              <div
                key={doc.id}
                className="flex gap-4 p-4 rounded-xl bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition-all"
              >
                <div className="w-20 h-24 rounded-lg bg-slate-900 overflow-hidden flex-shrink-0 border border-slate-800">
                  <img
                    src={`/uploads/${doc.image_path.split(/[\\/]/).pop()}`}
                    alt={doc.original_filename}
                    className="w-full h-full object-cover"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                </div>

                <div className="flex-1 min-w-0 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1.5">
                      <DocumentTypeBadge type={doc.document_type} size="sm" />
                      <ConfidenceBadge confidence={doc.confidence} notesCount={(doc.low_confidence_notes || []).length} />
                    </div>
                    <p className="text-xs font-semibold text-slate-200 truncate">{doc.original_filename}</p>
                    <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">{doc.summary}</p>
                  </div>

                  <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-800/60">
                    <span className="text-[10px] text-slate-500 font-mono">
                      Hash: {doc.content_hash.substring(0, 8)}...
                    </span>
                    <button
                      onClick={() => onSelectDocForReview(doc)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300"
                    >
                      <span>Review / Edit Fields</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
