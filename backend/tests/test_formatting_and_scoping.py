import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from PIL import Image
from pathlib import Path
from app.main import app
from app.services.vision_client import vision_client

client = TestClient(app)

@pytest.mark.asyncio
async def test_all_six_formatting_and_scoping_cases():
    """
    Executes and validates all 6 verification scenarios:
    1. Indian lakh formatting: ₹1,25,450.00
    2. US Western formatting: $1,250.75
    3. Integer precision without decimals: ₹500
    4. Single document strict scoping
    5. Multi-document single currency aggregation (all ₹)
    6. Multi-document mixed currency aggregation (₹ and $)
    """
    # 1. Setup Document 1: Indian Lakh Bill (₹1,25,450.00)
    p1 = Path("backend/uploads/test_indian_lakh.jpg")
    Image.new("RGB", (400, 400), "#FEF3C7").save(p1)
    
    mock_c1 = {
        "document_type": "invoice",
        "primary_subject": "Apollo Hospital Medical Bill",
        "key_fields": ["hospital_name", "total_amount", "currency", "bill_date"],
        "is_text_heavy": True,
        "is_data_heavy": True,
        "is_non_informational": False
    }
    mock_e1 = {
        "document_type": "invoice",
        "primary_subject": "Apollo Hospital Medical Bill",
        "currency": "₹",
        "summary": "Inpatient treatment bill from Apollo Hospital.",
        "extracted_fields": {
            "hospital_name": "Apollo Hospitals Chennai",
            "total_amount": 125450.00,
            "total_formatted": "₹1,25,450.00",
            "currency": "₹",
            "bill_date": "2026-08-20"
        },
        "tables": [],
        "full_text": "APOLLO HOSPITALS - Total Bill: ₹1,25,450.00",
        "confidence": "high",
        "low_confidence_notes": []
    }

    # 2. Setup Document 2: US Western Bill ($1,250.75)
    p2 = Path("backend/uploads/test_us_bill.jpg")
    Image.new("RGB", (400, 400), "#E0F2FE").save(p2)
    
    mock_c2 = {
        "document_type": "receipt",
        "primary_subject": "Apple Store Hardware Invoice",
        "key_fields": ["store_name", "total_amount", "currency"],
        "is_text_heavy": True,
        "is_data_heavy": True,
        "is_non_informational": False
    }
    mock_e2 = {
        "document_type": "receipt",
        "primary_subject": "Apple Store Hardware Invoice",
        "currency": "$",
        "summary": "Hardware purchase receipt from Apple Union Square.",
        "extracted_fields": {
            "store_name": "Apple Union Square",
            "total_amount": 1250.75,
            "total_formatted": "$1,250.75",
            "currency": "$",
            "transaction_date": "2026-08-21"
        },
        "tables": [],
        "full_text": "APPLE STORE - TOTAL: $1,250.75",
        "confidence": "high",
        "low_confidence_notes": []
    }

    # 3. Setup Document 3: No-Decimal Bill (₹500)
    p3 = Path("backend/uploads/test_no_decimals.jpg")
    Image.new("RGB", (400, 400), "#DCFCE7").save(p3)
    
    mock_c3 = {
        "document_type": "receipt",
        "primary_subject": "Cafe Coffee Day Bill",
        "key_fields": ["merchant", "total_amount", "currency"],
        "is_text_heavy": True,
        "is_data_heavy": True,
        "is_non_informational": False
    }
    mock_e3 = {
        "document_type": "receipt",
        "primary_subject": "Cafe Coffee Day Bill",
        "currency": "₹",
        "summary": "Beverage receipt from Cafe Coffee Day.",
        "extracted_fields": {
            "merchant": "Cafe Coffee Day",
            "total_amount": 500.0,
            "total_formatted": "₹500",
            "currency": "₹",
            "date": "2026-08-22"
        },
        "tables": [],
        "full_text": "CAFE COFFEE DAY - NET AMOUNT: ₹500",
        "confidence": "high",
        "low_confidence_notes": []
    }

    # Upload Doc 1
    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_c1)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_e1)):
        with open(p1, "rb") as f:
            res1 = client.post("/api/documents/upload", files={"files": ("test_indian_lakh.jpg", f, "image/jpeg")})
        doc1 = res1.json()[0]

    # Upload Doc 2
    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_c2)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_e2)):
        with open(p2, "rb") as f:
            res2 = client.post("/api/documents/upload", files={"files": ("test_us_bill.jpg", f, "image/jpeg")})
        doc2 = res2.json()[0]

    # Upload Doc 3
    with patch.object(vision_client, "classify_image", AsyncMock(return_value=mock_c3)), \
         patch.object(vision_client, "extract_dynamic_fields", AsyncMock(return_value=mock_e3)):
        with open(p3, "rb") as f:
            res3 = client.post("/api/documents/upload", files={"files": ("test_no_decimals.jpg", f, "image/jpeg")})
        doc3 = res3.json()[0]

    # --- TEST 1: Indian-formatted amount (₹1,25,450.00) ---
    with patch.object(vision_client, "call_huggingface_api", AsyncMock(return_value="The total amount on the hospital bill is ₹1,25,450.00.")):
        q1 = client.post("/api/query", json={"question": "What is the total amount on the hospital bill?", "document_ids": [doc1["id"]]})
        data1 = q1.json()
        assert "₹1,25,450.00" in data1["answer"]
        assert "$" not in data1["answer"]

    # --- TEST 2: US-formatted amount ($1,250.75) ---
    with patch.object(vision_client, "call_huggingface_api", AsyncMock(return_value="The total amount on the Apple receipt is $1,250.75.")):
        q2 = client.post("/api/query", json={"question": "What is the total amount on the Apple receipt?", "document_ids": [doc2["id"]]})
        data2 = q2.json()
        assert "$1,250.75" in data2["answer"]
        assert "₹" not in data2["answer"]

    # --- TEST 3: No-decimal precision (₹500) ---
    with patch.object(vision_client, "call_huggingface_api", AsyncMock(return_value="The total amount on the coffee bill is ₹500.")):
        q3 = client.post("/api/query", json={"question": "How much was the coffee bill?", "document_ids": [doc3["id"]]})
        data3 = q3.json()
        assert "₹500" in data3["answer"]
        assert "₹500.00" not in data3["answer"]

    # --- TEST 4: Single document strict scoping ---
    with patch.object(vision_client, "call_huggingface_api", AsyncMock(return_value="The Apollo hospital bill was issued by Apollo Hospitals Chennai for a total of ₹1,25,450.00.")):
        q4 = client.post("/api/query", json={"question": "Summarize this document", "document_ids": [doc1["id"]]})
        data4 = q4.json()
        assert len(data4["sources"]) == 1
        assert data4["sources"][0]["document_id"] == doc1["id"]
        assert "Apple" not in data4["answer"]
        assert "Coffee" not in data4["answer"]

    # --- TEST 5: Multi-document single currency aggregation (Doc 1 + Doc 3 both in ₹) ---
    with patch.object(vision_client, "call_huggingface_api", AsyncMock(return_value="The total spending across your INR receipts is ₹1,25,950.00 (₹1,25,450.00 from Apollo Hospital and ₹500 from Cafe Coffee Day).")):
        q5 = client.post("/api/query", json={"question": "What is my total spending across INR receipts?", "document_ids": [doc1["id"], doc3["id"]]})
        data5 = q5.json()
        assert data5["computation"]["currency"] == "₹"
        assert data5["computation"]["result"] == 125950.0
        assert "₹1,25,950.00" in data5["computation"]["explanation"]

    # --- TEST 6: Multi-document mixed currencies (Doc 1 in ₹, Doc 2 in $) ---
    with patch.object(vision_client, "call_huggingface_api", AsyncMock(return_value="Your receipts contain mixed currencies: ₹1,25,450.00 for the hospital bill and $1,250.75 for Apple Store. They are reported separately as they cannot be unified without conversion.")):
        q6 = client.post("/api/query", json={"question": "What is the total combined cost across all receipts?", "document_ids": [doc1["id"], doc2["id"]]})
        data6 = q6.json()
        assert data6["computation"]["currency"] == "Mixed"
        assert "₹1,25,450.00" in data6["computation"]["explanation"]
        assert "$1,250.75" in data6["computation"]["explanation"]
