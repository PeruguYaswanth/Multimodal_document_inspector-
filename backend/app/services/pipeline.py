import logging
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models import Document
from app.schemas import ClassificationResult, DynamicExtractionResult
from app.services.vision_client import vision_client
from app.services.image_processor import ImageProcessor

logger = logging.getLogger("document_pipeline")

class DocumentPipeline:
    @staticmethod
    async def process_image_two_stage(
        image_path: str,
        original_filename: str,
        file_bytes: bytes,
        db: Session,
        meta_info: Dict[str, Any]
    ) -> Tuple[Document, bool]:
        """
        Executes the generalized Two-Stage Multimodal Extraction Pipeline:
        1. Check de-duplication by content_hash (SHA-256)
        2. Stage 1A: Classification & Key Fields Detection (temp=0) based on raw image
        3. Check for non-informational images (e.g. blank canvas, abstract noise)
        4. Stage 1B: Dynamic Extraction based on detected key fields (temp=0)
        5. Stage 1C: Pydantic Validation & Retry
        6. Stage 1D: Database Storage
        """
        content_hash = ImageProcessor.compute_hash(file_bytes)

        # Check existing duplicate
        existing_doc = db.query(Document).filter(Document.content_hash == content_hash).first()
        if existing_doc:
            logger.info(f"Duplicate document found for hash {content_hash}, ID: {existing_doc.id}")
            return existing_doc, True

        # --- Stage 1A: Classification ---
        logger.info(f"Stage 1A: Classifying image {original_filename}...")
        raw_classification = await vision_client.classify_image(image_path)
        
        try:
            classification = ClassificationResult(**raw_classification)
        except Exception as e:
            logger.warning(f"Classification validation warning: {e}, adopting flexible fields")
            classification = ClassificationResult(
                document_type=raw_classification.get("document_type", "image_document"),
                primary_subject=raw_classification.get("primary_subject", original_filename),
                key_fields=raw_classification.get("key_fields", ["description", "detected_features"]),
                is_text_heavy=raw_classification.get("is_text_heavy", False),
                is_data_heavy=raw_classification.get("is_data_heavy", False),
                is_non_informational=raw_classification.get("is_non_informational", False)
            )

        # Handle non-informational images
        if classification.is_non_informational:
            doc = Document(
                image_path=image_path,
                original_filename=original_filename,
                document_type="non-informational",
                primary_subject=classification.primary_subject or "Non-Informational Image",
                summary="Image contains no readable text or structured document features.",
                extracted_fields={},
                tables=[],
                full_text="",
                confidence="high",
                low_confidence_notes=["Classified as non-informational / abstract image."],
                content_hash=content_hash,
                is_text_heavy=False,
                is_data_heavy=False,
                is_reviewed=True,
                is_non_informational=True,
                meta_info=meta_info
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return doc, False

        # --- Stage 1B & 1C: Dynamic Extraction & Validation with Retry ---
        logger.info(f"Stage 1B: Extracting fields {classification.key_fields} for '{classification.primary_subject}'...")
        
        extraction_data = None
        for attempt in range(2):
            try:
                raw_extraction = await vision_client.extract_dynamic_fields(
                    image_path=image_path,
                    document_type=classification.document_type,
                    primary_subject=classification.primary_subject,
                    key_fields=classification.key_fields
                )
                extraction_obj = DynamicExtractionResult(**raw_extraction)
                extraction_data = extraction_obj.model_dump()
                break
            except Exception as e:
                logger.error(f"Extraction attempt {attempt + 1} validation error: {e}")
                if attempt == 1:
                    raise RuntimeError(f"Failed to extract structured fields from {original_filename}: {e}")

        # --- Stage 1D: Store in SQLite ---
        confidence_val = extraction_data.get("confidence", "medium")
        low_conf_notes = extraction_data.get("low_confidence_notes", [])
        auto_needs_review = (confidence_val.lower() == "low") or bool(low_conf_notes)

        doc = Document(
            image_path=image_path,
            original_filename=original_filename,
            document_type=classification.document_type,
            primary_subject=extraction_data.get("primary_subject") or classification.primary_subject,
            currency=extraction_data.get("currency"),
            summary=extraction_data.get("summary", ""),
            extracted_fields=extraction_data.get("extracted_fields", {}),
            tables=extraction_data.get("tables", []),
            full_text=extraction_data.get("full_text", ""),
            confidence=confidence_val,
            low_confidence_notes=low_conf_notes,
            content_hash=content_hash,
            is_text_heavy=classification.is_text_heavy,
            is_data_heavy=classification.is_data_heavy,
            is_reviewed=not auto_needs_review,
            is_non_informational=False,
            meta_info=meta_info
        )

        db.add(doc)
        db.commit()
        db.refresh(doc)
        logger.info(f"Document #{doc.id} ({doc.primary_subject}) stored successfully.")
        return doc, False

pipeline = DocumentPipeline()
