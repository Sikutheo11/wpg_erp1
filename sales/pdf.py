from django.template.loader import render_to_string
from django.http import HttpResponse

from weasyprint import HTML



def generate_invoice_pdf(invoice):


    html_string = render_to_string(
        "sales/invoice_pdf.html",
        {
            "invoice": invoice
        }
    )


    pdf = HTML(
        string=html_string
    ).write_pdf()



    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )


    filename = (
        f"{invoice.invoice_no}.pdf"
    )


    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{filename}"'
    )


    return response