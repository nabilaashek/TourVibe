"""PDF invoice for an order (ReportLab)."""
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GREEN = colors.HexColor('#0f766e')


def bdt(amount):
    # Built-in PDF fonts have no Taka sign
    return f'BDT {int(amount):,}'


def make_invoice(order):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=f'Invoice {order.reference}')
    styles = getSampleStyleSheet()
    big = ParagraphStyle('big', parent=styles['Title'], textColor=GREEN, alignment=0, fontSize=20)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#475569'))

    story = [
        Paragraph('TourVibe', big),
        Paragraph('Pack, Go &amp; Explore Bangladesh', small),
        Spacer(1, 10),
        Paragraph(f'<b>Invoice</b> {escape(order.reference)}', styles['Heading3']),
        Paragraph(f'Date: {timezone.localtime(order.created_at):%d %b %Y} &nbsp; | &nbsp; '
                  f'Status: <b>{escape(order.get_status_display())}</b>', small),
        Spacer(1, 8),
        Paragraph(f'Customer: {escape(order.contact_name)} ({escape(order.contact_phone)})', styles['Normal']),
        Spacer(1, 12),
    ]

    rows = [['Tour', 'Dates', 'Travelers', 'Price', 'Amount']]
    for item in order.items.select_related('package'):
        p = item.package
        rows.append([Paragraph(escape(p.title), styles['Normal']), f'{p.start_date:%d %b} - {p.end_date:%d %b %Y}',
                     str(item.travelers), bdt(item.unit_price), bdt(item.subtotal)])
    rows.append(['', '', '', 'Total', bdt(order.total_price)])

    table = Table(rows, colWidths=[62 * mm, 40 * mm, 20 * mm, 24 * mm, 26 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -2), 0.4, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story += [table, Spacer(1, 16),
              Paragraph('Pay at our office or by mobile banking after the order is confirmed. '
                        'You can cancel from your account before the tour starts.', small)]
    doc.build(story)
    return buffer.getvalue()
