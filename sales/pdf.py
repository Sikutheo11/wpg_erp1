from io import BytesIO

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def render_enterprise_invoice_pdf(invoice):
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 55
    page.setTitle(invoice.invoice_number)
    page.setFont("Helvetica-Bold", 18)
    page.drawString(45, y, "WISDOM PALACE GROUP")
    y -= 30
    page.setFont("Helvetica-Bold", 15)
    page.drawString(45, y, f"INVOICE {invoice.invoice_number}")
    y -= 25
    page.setFont("Helvetica", 10)
    page.drawString(45, y, f"Customer: {invoice.customer.display_name}")
    y -= 16
    page.drawString(45, y, f"Phone: {invoice.customer.phone or invoice.order.customer_phone}")
    y -= 16
    page.drawString(45, y, f"Email: {invoice.customer.email or invoice.order.customer_email or '-'}")
    y -= 16
    page.drawString(45, y, f"Order: {invoice.order.order_number}")
    page.drawRightString(width - 45, y, f"Date: {invoice.invoice_date:%d/%m/%Y}")
    y -= 16
    page.drawRightString(width - 45, y, f"Due: {invoice.due_date:%d/%m/%Y}")
    y -= 30
    page.setFont("Helvetica-Bold", 9)
    page.drawString(45, y, "ITEM")
    page.drawRightString(390, y, "QTY")
    page.drawRightString(470, y, "UNIT PRICE")
    page.drawRightString(width - 45, y, "TOTAL")
    y -= 8
    page.line(45, y, width - 45, y)
    y -= 16
    page.setFont("Helvetica", 9)
    for item in invoice.order.items.all():
        if y < 100:
            page.showPage()
            y = height - 55
        page.drawString(45, y, (item.product_name or str(item.product))[:48])
        page.drawRightString(390, y, str(item.quantity))
        page.drawRightString(470, y, f"{item.price:,.2f}")
        page.drawRightString(width - 45, y, f"{item.subtotal:,.2f}")
        y -= 16
    y -= 10
    page.line(330, y, width - 45, y)
    for label, value in (
        ("Subtotal", invoice.subtotal),
        ("Discount", invoice.discount),
        ("Tax", invoice.tax),
        ("TOTAL", invoice.total_amount),
        ("BALANCE", invoice.balance),
    ):
        y -= 18
        page.setFont("Helvetica-Bold" if label in {"TOTAL", "BALANCE"} else "Helvetica", 10)
        page.drawRightString(470, y, f"{label}:")
        page.drawRightString(width - 45, y, f"{value:,.2f} RWF")
    page.setFont("Helvetica", 8)
    page.drawString(45, 45, "Thank you for doing business with Wisdom Palace Group.")
    page.save()
    return buffer.getvalue()


def enterprise_invoice_pdf_response(invoice, *, inline=False):
    response = HttpResponse(render_enterprise_invoice_pdf(invoice), content_type="application/pdf")
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{invoice.invoice_number}.pdf"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Referrer-Policy"] = "no-referrer"
    return response


def generate_invoice_pdf(invoice):
    raise ValueError("Legacy invoices are read-only; use EnterpriseInvoice.")
