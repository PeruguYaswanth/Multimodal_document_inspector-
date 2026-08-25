import React from "react";
import { 
  Receipt, 
  FileText, 
  CreditCard, 
  ClipboardList, 
  Image as ImageIcon, 
  FileQuestion,
  PenTool,
  Layout,
  PieChart
} from "lucide-react";

export function getDocTypeDetails(type = "") {
  const t = type.toLowerCase();
  if (t.includes("receipt") || t.includes("invoice")) {
    return { label: "Receipt / Invoice", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30", icon: Receipt };
  }
  if (t.includes("note") || t.includes("handwritten")) {
    return { label: "Handwritten Note", color: "bg-amber-500/10 text-amber-400 border-amber-500/30", icon: PenTool };
  }
  if (t.includes("business") || t.includes("card") || t.includes("id_card")) {
    return { label: "Business / ID Card", color: "bg-sky-500/10 text-sky-400 border-sky-500/30", icon: CreditCard };
  }
  if (t.includes("form") || t.includes("application") || t.includes("medical")) {
    return { label: "Form / Registration", color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30", icon: ClipboardList };
  }
  if (t.includes("whiteboard") || t.includes("diagram")) {
    return { label: "Diagram / Whiteboard", color: "bg-purple-500/10 text-purple-400 border-purple-500/30", icon: PieChart };
  }
  if (t.includes("screenshot")) {
    return { label: "Screenshot", color: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30", icon: Layout };
  }
  if (t.includes("non-informational")) {
    return { label: "Non-Informational", color: "bg-slate-500/10 text-slate-400 border-slate-500/30", icon: ImageIcon };
  }
  return { label: type || "Document", color: "bg-blue-500/10 text-blue-400 border-blue-500/30", icon: FileText };
}

export default function DocumentTypeBadge({ type, size = "md" }) {
  const { label, color, icon: Icon } = getDocTypeDetails(type);
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs gap-1" : "px-2.5 py-1 text-xs gap-1.5";

  return (
    <span className={`inline-flex items-center font-medium rounded-full border ${color} ${sizeClasses}`}>
      <Icon className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
      {label}
    </span>
  );
}
