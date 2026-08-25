import React, { useState } from "react";
import { 
  MessageSquareText, 
  Send, 
  Sparkles, 
  Calculator, 
  Eye, 
  FileText, 
  CheckCircle2, 
  CornerDownLeft,
  Search,
  Filter,
  Layers,
  HelpCircle,
  ExternalLink
} from "lucide-react";
import { askQuery } from "../api";
import DocumentTypeBadge from "./DocumentTypeBadge";

const SUGGESTED_PROMPTS = [
  { text: "How much did I spend total across all receipts?", category: "math" },
  { text: "What is the average amount spent per receipt?", category: "math" },
  { text: "Summarize key action items and topics across all handwritten notes", category: "qa" },
  { text: "Find the contact email and address for Dr. Evelyn Vance", category: "qa" },
  { text: "What color is the header on the receipt?", category: "vision" },
];

export default function CrossDocChatPanel({ documents, onSelectDocForReview }) {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      sender: "assistant",
      text: "Hello! I am your Multimodal Document Intelligence Assistant. You can ask me natural language questions across your entire document archive, compute sums and averages with zero hallucination, or inspect specific visual details in images.",
      query_type: "structured_reasoning",
      sources: []
    }
  ]);
  const [inputText, setInputText] = useState("");
  const [selectedDocId, setSelectedDocId] = useState("all");
  const [forceVision, setForceVision] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (customPrompt = null) => {
    const textToSend = customPrompt || inputText;
    if (!textToSend.trim() || isLoading) return;

    const userMsgId = Date.now().toString();
    const newMsg = {
      id: userMsgId,
      sender: "user",
      text: textToSend,
    };

    setMessages(prev => [...prev, newMsg]);
    setInputText("");
    setIsLoading(true);

    try {
      const docIds = selectedDocId === "all" ? null : [parseInt(selectedDocId, 10)];
      const response = await askQuery({
        question: textToSend,
        documentIds: docIds,
        scope: selectedDocId === "all" ? "all" : "single",
        forceVision,
      });

      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text: response.answer,
        query_type: response.query_type,
        computation: response.computation,
        sources: response.sources || [],
        visual_inspection_used: response.visual_inspection_used,
        suggested_followups: response.suggested_followups || [],
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const errMsg = err.message || "";
      const isBusy = errMsg.includes("503") || errMsg.includes("busy") || errMsg.includes("temporarily");
      const displayText = isBusy 
        ? "AI service is temporarily busy. Please try again in a few seconds." 
        : `Unable to complete query: ${errMsg}`;

      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: displayText,
          query_type: "error",
          failedPrompt: textToSend,
          sources: []
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-3xl h-[80vh] flex flex-col overflow-hidden backdrop-blur-md">
      
      {/* Chat Top Controls & Scope Selection */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/50 flex flex-wrap items-center justify-between gap-3">
        
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <MessageSquareText className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-200">Cross-Document Q&A</h3>
            <p className="text-[11px] text-slate-400">Reasoning & Code-Calculated Aggregation</p>
          </div>
        </div>

        {/* Scope Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-400 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Scope:</span>
          </label>
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="text-xs bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Documents ({documents.length})</option>
            {documents.map(doc => (
              <option key={doc.id} value={doc.id}>
                #{doc.id} - {doc.original_filename} ({doc.document_type})
              </option>
            ))}
          </select>

          <label className="flex items-center gap-1.5 text-xs text-slate-300 ml-2 cursor-pointer bg-slate-900/60 px-2.5 py-1.5 rounded-xl border border-slate-800 hover:border-slate-700">
            <input
              type="checkbox"
              checked={forceVision}
              onChange={(e) => setForceVision(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0 w-3.5 h-3.5"
            />
            <Eye className="w-3.5 h-3.5 text-cyan-400" />
            <span>Direct Vision</span>
          </label>
        </div>

      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
          >
            <div
              className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed ${
                msg.sender === "user"
                  ? "bg-indigo-600 text-white rounded-br-none shadow-lg shadow-indigo-600/20"
                  : "bg-slate-950/80 text-slate-200 border border-slate-800 rounded-bl-none shadow-md"
              }`}
            >
              {/* Assistant Error Alert if applicable */}
              {msg.sender === "assistant" && msg.query_type === "error" && (
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-rose-500/30">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                    <HelpCircle className="w-3 h-3 text-rose-400" />
                    Query Encountered an Error
                  </span>
                </div>
              )}

              {/* Message Text with Line Breaks */}
              <div className="whitespace-pre-line text-slate-200">
                {msg.text}
              </div>

              {msg.query_type === "error" && msg.failedPrompt && (
                <div className="mt-2.5 pt-2 border-t border-rose-500/20">
                  <button
                    onClick={() => handleSendMessage(msg.failedPrompt)}
                    disabled={isLoading}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-semibold border border-rose-500/30 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    <RefreshCw className="w-3 h-3 text-rose-400" />
                    <span>Retry Question</span>
                  </button>
                </div>
              )}

            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start">
            <div className="max-w-md rounded-2xl rounded-bl-none p-4 bg-slate-950/80 border border-slate-800 text-xs text-slate-400 flex items-center gap-3">
              <Sparkles className="w-4 h-4 text-indigo-400 animate-spin" />
              <span>Analyzing cross-document records & computing answer...</span>
            </div>
          </div>
        )}

      </div>

      {/* Suggested Quick Prompts */}
      <div className="px-4 py-2 border-t border-slate-800/60 bg-slate-950/30 flex items-center gap-1.5 overflow-x-auto">
        <span className="text-[10px] font-semibold text-slate-500 uppercase whitespace-nowrap">
          Suggestions:
        </span>
        {SUGGESTED_PROMPTS.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(p.text)}
            className="text-[11px] whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-800/60 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition-colors"
          >
            {p.text}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/70">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask anything (e.g. 'What is the sum of all coffee receipts?', 'Extract action items from my notes')..."
            className="flex-1 text-xs bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isLoading}
            className="p-3 rounded-xl bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white disabled:opacity-50 transition-all cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
}
