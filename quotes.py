"""AegisBot Professional PDF Quotation & Proposal Generator.

Generates branded, executive-grade PDF quotations for captured WhatsApp leads
using ReportLab with itemized pricing, GST calculation, warranty terms, and client details.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import config
import db

logger = logging.getLogger("aegisbot.quotes")

QUOTES_DIR = Path(__file__).parent / "static" / "quotes"
try:
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    QUOTES_DIR = Path("/tmp/quotes")
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)


def _format_inr(amount: float) -> str:
    """Format float into INR currency string (e.g. 15,000.00)."""
    return f"Rs {amount:,.2f}"


def estimate_line_items(requirement: str, budget_str: str = "") -> List[Dict[str, Any]]:
    """Intelligently match customer requirement to catalog products."""
    req = (requirement or "").lower()
    items = []

    # Match items from Aegis catalog
    if "ergo pro" in req or "pro 3d" in req:
        items.append({
            "name": "Aegis Ergo Pro 3D Ergonomic Task Chair",
            "desc": "3D adjustable armrests, dynamic lumbar support, breathable Korean mesh, Class 4 gas lift.",
            "qty": 5,
            "unit_price": 14999.00,
        })
    elif "boss" in req or "executive" in req:
        items.append({
            "name": "Aegis Executive Boss High-Back Ergonomic Chair",
            "desc": "Genuine top-grain Nappa leather, synchronous multi-angle tilt, integrated headrest.",
            "qty": 2,
            "unit_price": 28500.00,
        })
    elif "chair" in req or "seating" in req:
        items.append({
            "name": "Aegis Ergo Lite Ergonomic Mesh Chair",
            "desc": "S-curve backrest, pneumatic height adjustment, dual-wheel nylon casters.",
            "qty": 8,
            "unit_price": 7499.00,
        })

    if "standing" in req or "smartdesk" in req or "height adjustable" in req or "motor" in req:
        items.append({
            "name": "Aegis SmartDesk Pro Dual-Motor Standing Desk",
            "desc": "140x70cm scratch-resistant melamine top, dual quiet motors (35mm/s), 4-preset memory keypad.",
            "qty": 4,
            "unit_price": 24999.00,
        })
    elif "workstation" in req or "desk" in req or "office" in req:
        items.append({
            "name": "Aegis Modular Linear Workstation Pod (4-Person Setup)",
            "desc": "Powder-coated steel frame, integrated wire-management raceway, acoustic privacy screen (120x60cm per seat).",
            "qty": 2,
            "unit_price": 42000.00,
        })

    # If no specific product matched, create a tailored corporate consultation package
    if not items:
        items.append({
            "name": f"Aegis Custom Turnkey Workstation Package",
            "desc": f"Tailored ergonomic setup as requested: '{requirement[:120]}'. Includes delivery, assembly, and setup.",
            "qty": 1,
            "unit_price": 45000.00,
        })

    return items


def generate_pdf_quotation(
    lead_id: int,
    customer_name: str,
    phone: str,
    requirement: str,
    location: str = "",
    budget: str = "",
    timeline: str = "",
) -> Path:
    """Generate a high-end corporate quotation PDF and save to static/quotes/ (or /tmp/quotes in serverless)."""
    global QUOTES_DIR
    try:
        QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        QUOTES_DIR = Path("/tmp/quotes")
        QUOTES_DIR.mkdir(parents=True, exist_ok=True)

    quote_num = f"QT-{datetime.now().year}-{lead_id:04d}"
    out_file = QUOTES_DIR / f"quote_{lead_id}.pdf"

    doc = SimpleDocTemplate(
        str(out_file),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle(
        "BrandHeader",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
    )
    sub_style = ParagraphStyle(
        "BrandSub",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748B"),
    )
    quote_title_style = ParagraphStyle(
        "QuoteTitle",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=2,  # right align
        textColor=colors.HexColor("#10B981"),
    )
    quote_meta_style = ParagraphStyle(
        "QuoteMeta",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        alignment=2,
        textColor=colors.HexColor("#475569"),
    )
    sec_title_style = ParagraphStyle(
        "SecTitle",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E293B"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_norm = ParagraphStyle(
        "CellNorm",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )
    cell_price = ParagraphStyle(
        "CellPrice",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        alignment=2,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # ── 1. Top Header (Brand & Quotation Reference) ──────────────────────────
    top_table_data = [
        [
            Paragraph(f"<b>{config.BUSINESS_NAME}</b>", header_style),
            Paragraph(f"<b>COMMERCIAL PROPOSAL</b>", quote_title_style),
        ],
        [
            Paragraph(
                "Corporate Experience Center: 100 Feet Rd, Indiranagar, Bangalore<br/>"
                "Email: enterprise@aegisworkspace.com | Tel: +91 80 4123 9900<br/>"
                "GSTIN: 29AABCA1234F1Z8 | Web: www.aegisworkspace.com",
                sub_style,
            ),
            Paragraph(
                f"<b>Quotation #:</b> {quote_num}<br/>"
                f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}<br/>"
                f"<b>Valid Until:</b> 30 Days from issue",
                quote_meta_style,
            ),
        ],
    ]
    top_table = Table(top_table_data, colWidths=[330, 200])
    top_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(top_table)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#10B981"), spaceAfter=14))

    # ── 2. Bill To & Project Details ─────────────────────────────────────────
    bill_data = [
        [
            Paragraph("<b>PROPOSAL PREPARED FOR:</b>", sec_title_style),
            Paragraph("<b>PROJECT SPECIFICATIONS:</b>", sec_title_style),
        ],
        [
            Paragraph(
                f"<b>Client Name:</b> {customer_name or 'Valued Customer'}<br/>"
                f"<b>WhatsApp Contact:</b> +{phone}<br/>"
                f"<b>Delivery Location:</b> {location or 'Bangalore'}",
                cell_norm,
            ),
            Paragraph(
                f"<b>Stated Requirement:</b> {requirement or 'Workstation Solutions'}<br/>"
                f"<b>Target Timeline:</b> {timeline or 'Immediate'}<br/>"
                f"<b>Budget Range:</b> {budget or 'Standard Corporate'}",
                cell_norm,
            ),
        ],
    ]
    bill_table = Table(bill_data, colWidths=[265, 265])
    bill_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 16))

    # ── 3. Line Items Table ──────────────────────────────────────────────────
    items = estimate_line_items(requirement, budget)
    table_rows = [
        [
            Paragraph("<b>#</b>", cell_bold),
            Paragraph("<b>Item Description & Specifications</b>", cell_bold),
            Paragraph("<b>Qty</b>", cell_bold),
            Paragraph("<b>Unit Price (INR)</b>", cell_bold),
            Paragraph("<b>Total (INR)</b>", cell_price),
        ]
    ]

    subtotal = 0.0
    for idx, itm in enumerate(items, 1):
        line_total = itm["qty"] * itm["unit_price"]
        subtotal += line_total
        table_rows.append([
            Paragraph(str(idx), cell_norm),
            Paragraph(f"<b>{itm['name']}</b><br/><font color='#64748B'>{itm['desc']}</font>", cell_norm),
            Paragraph(str(itm["qty"]), cell_norm),
            Paragraph(_format_inr(itm["unit_price"]), cell_norm),
            Paragraph(_format_inr(line_total), cell_price),
        ])

    gst = subtotal * 0.18
    grand_total = subtotal + gst

    # Subtotals and tax
    table_rows.append(["", "", "", Paragraph("<b>Subtotal:</b>", cell_norm), Paragraph(_format_inr(subtotal), cell_price)])
    table_rows.append(["", "", "", Paragraph("<b>GST (18%):</b>", cell_norm), Paragraph(_format_inr(gst), cell_price)])
    table_rows.append(["", "", "", Paragraph("<b>Grand Total:</b>", cell_bold), Paragraph(f"<b>{_format_inr(grand_total)}</b>", cell_price)])

    items_table = Table(table_rows, colWidths=[25, 275, 40, 95, 95])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, len(items)), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, len(items) + 1), (-1, -1), colors.HexColor("#F8FAFC")),
        ("LINEABOVE", (0, len(items) + 3), (-1, len(items) + 3), 1.5, colors.HexColor("#10B981")),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 16))

    # ── 4. Commercial Terms & Warranty ───────────────────────────────────────
    terms_text = (
        "<b>Commercial Terms & Warranty:</b><br/>"
        "1. <b>Comprehensive Warranty:</b> 3-Year Onsite Manufacturer Warranty on mechanical structure and gas-lift cylinders.<br/>"
        "2. <b>Delivery & Installation:</b> Complimentary delivery and professional on-site assembly included.<br/>"
        "3. <b>Payment Terms:</b> 50% advance on PO confirmation, 50% upon successful delivery and sign-off.<br/>"
        "4. <b>Validity:</b> Prices are valid for 30 calendar days from the date of this document."
    )
    terms_box = Table([[Paragraph(terms_text, cell_norm)]], colWidths=[530])
    terms_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BBF7D0")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(terms_box)
    story.append(Spacer(1, 18))

    # ── 5. Signature / Authorization ─────────────────────────────────────────
    sig_data = [
        [
            Paragraph("Prepared By: <b>Aegis AI Sales Engine</b><br/>Verified by: <b>Enterprise Commercial Desk</b>", cell_norm),
            Paragraph("Authorized Signature & Stamp:<br/><br/>___________________________________<br/><b>Aegis Workspace Solutions</b>", quote_meta_style),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(sig_table)

    # Build document
    doc.build(story)
    logger.info("Generated PDF quotation #%s at %s", quote_num, out_file)
    return out_file
