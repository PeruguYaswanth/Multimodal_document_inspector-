import os
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.database import get_db
from app.models import Document
from app.services.pipeline import pipeline
from app.services.image_processor import ImageProcessor

router = APIRouter(prefix="/sample-data", tags=["sample-data"])

def generate_sample_images():
    """Generates 4 distinct test images using Pillow to test Stage 1 generalization."""
    sample_dir = settings.SAMPLE_DIR
    sample_dir.mkdir(parents=True, exist_ok=True)

    # 1. Receipt Image
    receipt_path = sample_dir / "sample_receipt.png"
    if not receipt_path.exists():
        img = Image.new("RGB", (450, 650), color="#FBFBFA")
        d = ImageDraw.Draw(img)
        d.rectangle([20, 20, 430, 630], outline="#D1D5DB", width=2)
        d.text((140, 40), "BLUE BOTTLE COFFEE", fill="#111827")
        d.text((130, 65), "54 Mint Plaza, San Francisco", fill="#4B5563")
        d.text((155, 85), "Date: 08/15/2026 09:23 AM", fill="#4B5563")
        d.line([(40, 115), (410, 115)], fill="#9CA3AF", width=1)
        d.text((45, 135), "1x Bella Donovan Drip Coffee     $4.75", fill="#1F2937")
        d.text((45, 170), "1x Oat Milk Latte               $6.50", fill="#1F2937")
        d.text((45, 205), "1x Almond Croissant             $5.60", fill="#1F2937")
        d.line([(40, 250), (410, 250)], fill="#9CA3AF", width=1)
        d.text((45, 270), "Subtotal:                       $16.85", fill="#1F2937")
        d.text((45, 300), "Tax (9.8%):                      $1.65", fill="#1F2937")
        d.text((45, 340), "TOTAL AMOUNT:                   $18.50", fill="#111827")
        d.text((45, 380), "Payment Method: Visa ending in 4821", fill="#4B5563")
        d.text((120, 520), "Thank you for visiting Blue Bottle!", fill="#6B7280")
        img.save(receipt_path)

    # 2. Handwritten Note Image
    note_path = sample_dir / "sample_handwritten_note.png"
    if not note_path.exists():
        img = Image.new("RGB", (500, 600), color="#FEF3C7")
        d = ImageDraw.Draw(img)
        # Notebook lines
        for y in range(80, 560, 40):
            d.line([(30, y), (470, y)], fill="#FCD34D", width=1)
        d.line([(80, 40), (80, 570)], fill="#F87171", width=2) # Margin
        d.text((100, 50), "Meeting Notes - 8/20/2026", fill="#1E3A8A")
        d.text((100, 90), "Topic: Multimodal Architecture Planning", fill="#1E3A8A")
        d.text((100, 130), "- Two-Stage dynamic extraction pipeline", fill="#1E3A8A")
        d.text((100, 170), "- Classify -> Dynamic fields -> Validation", fill="#1E3A8A")
        d.text((100, 210), "- Python deterministic code-based math", fill="#1E3A8A")
        d.text((100, 250), "Action items:", fill="#B91C1C")
        d.text((100, 290), "1. Build universal backend routers", fill="#1E3A8A")
        d.text((100, 330), "2. Implement dynamic KV review UI", fill="#1E3A8A")
        d.text((100, 370), "3. Verify 4+ doc types generalization", fill="#1E3A8A")
        img.save(note_path)

    # 3. Business Card Image
    card_path = sample_dir / "sample_business_card.png"
    if not card_path.exists():
        img = Image.new("RGB", (600, 350), color="#0F172A")
        d = ImageDraw.Draw(img)
        d.rectangle([20, 20, 580, 330], outline="#38BDF8", width=2)
        d.text((50, 50), "NEURALTECH AI SYSTEMS", fill="#38BDF8")
        d.text((50, 100), "Dr. Evelyn Vance", fill="#F8FAFC")
        d.text((50, 130), "VP of AI Systems & Research", fill="#94A3B8")
        d.line([(50, 170), (550, 170)], fill="#334155", width=1)
        d.text((50, 195), "Email: evelyn.vance@neuraltech.ai", fill="#E2E8F0")
        d.text((50, 225), "Phone: +1 (415) 555-0199", fill="#E2E8F0")
        d.text((50, 255), "Web: https://neuraltech.ai", fill="#38BDF8")
        d.text((50, 285), "HQ: 700 Montgomery St, San Francisco, CA", fill="#94A3B8")
        img.save(card_path)

    # 4. Form / Medical Registration Image
    form_path = sample_dir / "sample_medical_form.png"
    if not form_path.exists():
        img = Image.new("RGB", (550, 700), color="#FFFFFF")
        d = ImageDraw.Draw(img)
        d.rectangle([25, 25, 525, 675], outline="#2563EB", width=2)
        d.rectangle([25, 25, 525, 80], fill="#EFF6FF")
        d.text((130, 45), "PATIENT INTAKE & REGISTRATION FORM", fill="#1E40AF")
        
        # Grid boxes
        d.rectangle([50, 110, 500, 160], outline="#CBD5E1", fill="#F8FAFC")
        d.text((60, 125), "Patient Name: Sarah Connor      DOB: 05/12/1984", fill="#0F172A")
        
        d.rectangle([50, 180, 500, 230], outline="#CBD5E1", fill="#F8FAFC")
        d.text((60, 195), "Patient ID: PT-99824            Intake Date: 08/10/2026", fill="#0F172A")

        d.rectangle([50, 250, 500, 300], outline="#CBD5E1", fill="#F8FAFC")
        d.text((60, 265), "Insurance: BlueCross Shield     Policy No: BC-7729103", fill="#0F172A")

        d.text((50, 330), "Emergency Contact Details:", fill="#1E40AF")
        d.rectangle([50, 360, 500, 420], outline="#CBD5E1")
        d.text((60, 380), "Name: John Connor | Relation: Son | Phone: +1 555-0144", fill="#334155")
        
        d.text((50, 460), "Authorization Status: APPROVED", fill="#059669")
        d.text((50, 500), "Physician Signature: [Dr. K. Silberman, MD]", fill="#334155")
        img.save(form_path)

    # 5. Non-informational scenic image
    photo_path = sample_dir / "sample_scenery_photo.png"
    if not photo_path.exists():
        img = Image.new("RGB", (500, 400), color="#7DD3FC")
        d = ImageDraw.Draw(img)
        d.ellipse([350, 40, 430, 120], fill="#FDE047") # Sun
        d.polygon([(0, 400), (200, 200), (400, 400)], fill="#065F46") # Mountain
        d.polygon([(200, 400), (350, 230), (500, 400)], fill="#047857")
        d.rectangle([0, 360, 500, 400], fill="#15803D") # Grass
        img.save(photo_path)

    return [receipt_path, note_path, card_path, form_path, photo_path]

@router.post("/load-all")
async def load_sample_dataset(db: Session = Depends(get_db)):
    """
    Generates and processes sample images across 4+ distinct document types
    to verify the Stage 1 Generalized Two-Stage Pipeline.
    """
    sample_files = generate_sample_images()
    loaded_docs = []

    for file_path in sample_files:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        dest_name = f"sample_{file_path.name}"
        dest_path = settings.UPLOAD_DIR / dest_name
        meta = ImageProcessor.process_and_save(file_bytes, dest_path)

        doc, is_dup = await pipeline.process_image_two_stage(
            image_path=meta["saved_path"],
            original_filename=file_path.name,
            file_bytes=file_bytes,
            db=db,
            meta_info=meta
        )
        loaded_docs.append(doc.to_dict())

    return {
        "status": "success",
        "message": f"Successfully loaded and verified {len(loaded_docs)} diverse sample documents.",
        "documents": loaded_docs
    }
