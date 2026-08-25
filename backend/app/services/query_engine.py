import re
import json
import logging
from typing import List, Dict, Any, Optional, Union
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import Document
from app.schemas import QueryRequest, QueryResponse, CitationSource, ComputationDetails
from app.services.vision_client import vision_client

logger = logging.getLogger("query_engine")

def format_indian_number(val: float, preserve_no_decimal: bool = False) -> str:
    """Formats a number according to the Indian numbering system (lakhs/crores: 1,25,000.00)."""
    if preserve_no_decimal and val % 1 == 0:
        s = str(int(val))
        decimals = ""
    else:
        s = f"{val:.2f}"
        parts = s.split(".")
        s = parts[0]
        decimals = f".{parts[1]}" if len(parts) > 1 else ""

    if len(s) <= 3:
        formatted_int = s
    else:
        last_three = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ",".join(groups) + "," + last_three

    return f"₹{formatted_int}{decimals}"

def format_currency_amount(amount: float, curr_symbol: str) -> str:
    """Formats an amount in its document's detected currency convention."""
    if curr_symbol in ("₹", "INR", "Rs", "Rs."):
        return format_indian_number(amount)
    elif curr_symbol in ("$", "USD"):
        return f"${amount:,.2f}" if amount % 1 != 0 else f"${amount:,.0f}"
    elif curr_symbol in ("€", "EUR"):
        return f"€{amount:,.2f}" if amount % 1 != 0 else f"€{amount:,.0f}"
    elif curr_symbol in ("£", "GBP"):
        return f"£{amount:,.2f}" if amount % 1 != 0 else f"£{amount:,.0f}"
    else:
        sym = curr_symbol or "$"
        return f"{sym}{amount:,.2f}" if amount % 1 != 0 else f"{sym}{amount:,.0f}"

class QueryEngine:
    @classmethod
    def detect_currency_from_fields(cls, fields: Dict[str, Any], doc_currency: Optional[str] = None) -> str:
        """Detects currency symbol from document model or extracted fields."""
        if doc_currency and doc_currency.strip():
            return doc_currency.strip()
        if "currency" in fields and fields["currency"]:
            return str(fields["currency"]).strip()

        # Inspect formatted strings in fields
        for v in fields.values():
            if isinstance(v, str):
                if "₹" in v or "INR" in v or "Rs" in v:
                    return "₹"
                elif "€" in v or "EUR" in v:
                    return "€"
                elif "£" in v or "GBP" in v:
                    return "£"
                elif "$" in v or "USD" in v:
                    return "$"
        return ""

    @classmethod
    def retrieve_documents(cls, db: Session, request: QueryRequest) -> List[Document]:
        """
        Dynamically retrieves relevant documents from the database.
        When request.document_ids is provided, restricts scope STRICTLY to those IDs.
        """
        if request.document_ids:
            return db.query(Document).filter(Document.id.in_(request.document_ids)).all()

        query = db.query(Document).filter(Document.is_non_informational == False)
        
        q_lower = request.question.lower()
        if any(term in q_lower for term in ["all", "combined", "everything", "total", "across", "summary of documents"]):
            return query.order_by(Document.uploaded_at.desc()).all()

        stop_words = {"what", "is", "the", "are", "from", "selected", "image", "this", "that", "how", "much", "show", "tell", "picture", "photo"}
        q_tokens = [w for w in re.split(r"\W+", q_lower) if len(w) > 2 and w not in stop_words]
        
        if q_tokens:
            conditions = []
            for token in q_tokens:
                pattern = f"%{token}%"
                conditions.append(Document.primary_subject.ilike(pattern))
                conditions.append(Document.document_type.ilike(pattern))
                conditions.append(Document.summary.ilike(pattern))
                conditions.append(Document.full_text.ilike(pattern))
                conditions.append(Document.original_filename.ilike(pattern))
            
            matched = query.filter(or_(*conditions)).all()
            if matched:
                return matched

        return query.order_by(Document.uploaded_at.desc()).limit(15).all()

    @classmethod
    def extract_numeric_aggregation(cls, question: str, docs: List[Document]) -> Optional[ComputationDetails]:
        """
        Dynamically extracts monetary and quantitative numbers across documents for arithmetic questions.
        If all documents share one currency, calculates unified total.
        If currencies are mixed across documents, computes separate per-currency subtotals.
        """
        q_lower = question.lower()
        is_math_question = any(term in q_lower for term in ["total", "sum", "average", "avg", "how much", "how many", "count", "cost", "add up", "combined", "spending"])
        if not is_math_question:
            return None

        # Operation detection
        op = "sum"
        if "avg" in q_lower or "average" in q_lower:
            op = "average"
        elif "how many" in q_lower or "count" in q_lower:
            op = "count"

        ignore_key_patterns = ["id", "number", "phone", "zip", "code", "date", "plate", "ssn", "ref", "version", "year", "serial", "account"]

        found_by_currency: Dict[str, List[float]] = {}
        all_raw_values: List[float] = []
        target_name = "amount"

        for doc in docs:
            fields = doc.extracted_fields or {}
            curr = cls.detect_currency_from_fields(fields, doc.currency) or "None"

            for k, v in fields.items():
                k_lower = k.lower()
                if "formatted" in k_lower:
                    continue
                if any(ign in k_lower for ign in ignore_key_patterns) and not any(m in k_lower for m in ["amount", "price", "cost", "fee", "fine", "total", "subtotal", "tax", "due"]):
                    continue

                val_float = None
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    val_float = float(v)
                    target_name = k
                elif isinstance(v, str):
                    # Check monetary string
                    if re.match(r"^[\$€£₹]?\s*\d[\d,]*(?:\.\d{1,2})?\s*([A-Z]{3})?$", v.strip()):
                        cleaned = re.sub(r"[^\d.]", "", v.replace(",", ""))
                        try:
                            val_float = float(cleaned)
                            target_name = k
                        except ValueError:
                            pass

                if val_float is not None:
                    found_by_currency.setdefault(curr, []).append(val_float)
                    all_raw_values.append(val_float)

        if not all_raw_values:
            if op == "count":
                return ComputationDetails(
                    operation="count",
                    target_field="documents",
                    raw_values=[1.0] * len(docs),
                    result=len(docs),
                    currency="",
                    explanation=f"Counted {len(docs)} matching document(s)."
                )
            return None

        distinct_currencies = [c for c in found_by_currency.keys() if c != "None"]

        # Case A: Single Currency across all documents
        if len(distinct_currencies) <= 1:
            active_curr = distinct_currencies[0] if distinct_currencies else "$"
            values = all_raw_values

            if op == "sum":
                res = round(sum(values), 2)
                formatted_res = format_currency_amount(res, active_curr)
                explanation = f"Summed {len(values)} value(s) in {active_curr}: {formatted_res}"
            elif op == "average":
                res = round(sum(values) / len(values), 2)
                formatted_res = format_currency_amount(res, active_curr)
                explanation = f"Calculated average in {active_curr}: {formatted_res}"
            else:
                res = len(values)
                explanation = f"Counted {len(values)} items."

            return ComputationDetails(
                operation=op,
                target_field=target_name,
                raw_values=values,
                result=res,
                currency=active_curr,
                explanation=explanation
            )

        # Case B: Mixed Currencies across documents (e.g. ₹ and $)
        subtotal_strings = []
        for c, vals in found_by_currency.items():
            c_sum = round(sum(vals), 2)
            c_formatted = format_currency_amount(c_sum, c)
            subtotal_strings.append(f"{c_formatted} ({len(vals)} item{'s' if len(vals) > 1 else ''})")

        mixed_summary = ", ".join(subtotal_strings)
        explanation = (
            f"Currencies are mixed across documents ({', '.join(distinct_currencies)}). "
            f"Separate subtotals: {mixed_summary}. Combined total is not unified across different currencies."
        )

        return ComputationDetails(
            operation=op,
            target_field=target_name,
            raw_values=all_raw_values,
            result=f"Mixed: {mixed_summary}",
            currency="Mixed",
            explanation=explanation
        )

    @classmethod
    async def process_query(cls, db: Session, request: QueryRequest) -> QueryResponse:
        """
        Stage 2 Dynamic Query Pipeline:
        1. Retrieve relevant records matching query tokens / document_ids
        2. Check if direct vision inspection is requested
        3. Perform code calculation if arithmetic requested
        4. Synthesize grounded answer via Gemini
        """
        # Retrieval Stage with strict scoping
        try:
            docs = cls.retrieve_documents(db, request)
        except Exception as e:
            logger.error(f"Retrieval stage failed: {e}")
            raise HTTPException(status_code=500, detail=f"Document retrieval failed: {str(e)}")

        if not docs:
            return QueryResponse(
                question=request.question,
                answer="No documents in your collection matched the query. Please upload relevant images or broaden your search.",
                query_type="general_search",
                sources=[]
            )

        sources = [
            CitationSource(
                document_id=doc.id,
                filename=doc.original_filename,
                document_type=doc.document_type,
                primary_subject=doc.primary_subject,
                currency=doc.currency,
                matched_snippet=doc.summary or doc.full_text[:150],
                matched_fields=doc.extracted_fields
            )
            for doc in docs
        ]

        # Check for direct vision request
        q_lower = request.question.lower()
        wants_visual = request.force_vision or any(
            v_term in q_lower for v_term in ["what color", "what colour", "visual appearance", "visually look like", "visually inspect", "inspect the photo directly"]
        )

        if wants_visual and docs and docs[0].image_path:
            target_doc = docs[0]
            try:
                visual_ans = await vision_client.query_vision_direct(target_doc.image_path, request.question)
                return QueryResponse(
                    question=request.question,
                    answer=visual_ans,
                    query_type="visual_inspection",
                    sources=[sources[0]],
                    visual_inspection_used=True
                )
            except Exception as e:
                logger.warning(f"Direct vision inspection failed, attempting structured synthesis: {e}")

        # Compute deterministic math if applicable
        math_details = cls.extract_numeric_aggregation(request.question, docs)
        math_dict = math_details.model_dump() if math_details else None

        # Synthesize answer using Gemini with strictly scoped context records
        context_data = [d.to_dict() for d in docs]
        
        try:
            answer = await vision_client.generate_chat_answer(
                question=request.question,
                context_data=context_data,
                math_result=math_dict
            )
            q_type = "code_computation" if math_details else "structured_reasoning"
        except Exception as e:
            logger.error(f"Synthesis stage failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Synthesis failed: {str(e)}"
            )

        return QueryResponse(
            question=request.question,
            answer=answer,
            query_type=q_type,
            sources=sources,
            computation=math_details,
            visual_inspection_used=False
        )

query_engine = QueryEngine()
