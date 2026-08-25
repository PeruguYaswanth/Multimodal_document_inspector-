import React, { useState, useEffect, useCallback } from "react";
import Navbar from "./components/Navbar";
import StatsBanner from "./components/StatsBanner";
import UniversalUploadZone from "./components/UniversalUploadZone";
import DocumentGallery from "./components/DocumentGallery";
import DocumentReviewModal from "./components/DocumentReviewModal";
import CrossDocChatPanel from "./components/CrossDocChatPanel";
import { 
  fetchDocuments, 
  fetchStats, 
  fetchHealth, 
  deleteDocument, 
  reprocessDocument, 
  loadSampleData 
} from "./api";

export default function App() {
  const [activeTab, setActiveTab] = useState("gallery"); // gallery, upload, chat
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [healthInfo, setHealthInfo] = useState(null);
  const [selectedDocForReview, setSelectedDocForReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingSample, setLoadingSample] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [docsData, statsData, healthData] = await Promise.all([
        fetchDocuments(),
        fetchStats(),
        fetchHealth(),
      ]);
      setDocuments(docsData);
      setStats(statsData);
      setHealthInfo(healthData);
    } catch (err) {
      console.error("Error loading app data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleQuickLoadSample = async () => {
    setLoadingSample(true);
    try {
      await loadSampleData();
      await loadData();
      setActiveTab("gallery");
    } catch (err) {
      alert("Failed to load sample dataset: " + err.message);
    } finally {
      setLoadingSample(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    try {
      await deleteDocument(id);
      await loadData();
    } catch (err) {
      alert("Failed to delete document: " + err.message);
    }
  };

  const handleReprocess = async (id) => {
    try {
      await reprocessDocument(id);
      await loadData();
    } catch (err) {
      alert("Reprocessing failed: " + err.message);
    }
  };

  const handleAskChat = (doc) => {
    setActiveTab("chat");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      
      {/* Navigation Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthInfo={healthInfo}
      />

      {/* Main Content Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Top KPI & Quick Load Banner */}
        <StatsBanner
          stats={stats}
          onQuickLoadSample={handleQuickLoadSample}
          loadingSample={loadingSample}
        />

        {/* Tab 1: Collection Gallery & Search */}
        {activeTab === "gallery" && (
          <DocumentGallery
            documents={documents}
            onReview={(doc) => setSelectedDocForReview(doc)}
            onAskChat={handleAskChat}
            onDelete={handleDelete}
            onReprocess={handleReprocess}
            onNavigateUpload={() => setActiveTab("upload")}
            onLoadSample={handleQuickLoadSample}
            loadingSample={loadingSample}
          />
        )}

        {/* Tab 2: Universal Multi-file Upload Zone */}
        {activeTab === "upload" && (
          <UniversalUploadZone
            onUploadComplete={loadData}
            onSelectDocForReview={(doc) => setSelectedDocForReview(doc)}
          />
        )}

        {/* Tab 3: Cross-Document Reasoning & Chat */}
        {activeTab === "chat" && (
          <CrossDocChatPanel
            documents={documents}
            onSelectDocForReview={(doc) => setSelectedDocForReview(doc)}
          />
        )}

      </main>

      {/* Document Review & Dynamic Key-Value Edit Modal */}
      {selectedDocForReview && (
        <DocumentReviewModal
          document={selectedDocForReview}
          onClose={() => setSelectedDocForReview(null)}
          onSaveSuccess={() => {
            loadData();
          }}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        <p>Universal Multimodal Document Analyzer — Generalized 2-Stage Dynamic Vision Pipeline</p>
      </footer>

    </div>
  );
}
