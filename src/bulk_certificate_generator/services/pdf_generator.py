from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from bulk_certificate_generator.models.certificate import CertificateJob, CertificateRecipient


class PdfCertificateGenerator:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def generate(self, job: CertificateJob, recipient: CertificateRecipient) -> Path:
        job_dir = self.output_dir / job.id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / f"{recipient.id}.pdf"

        canvas = Canvas(str(path), pagesize=landscape(A4))
        width, height = landscape(A4)
        margin = 0.45 * inch

        canvas.setStrokeColor(colors.HexColor("#1F2937"))
        canvas.setLineWidth(4)
        canvas.rect(margin, margin, width - 2 * margin, height - 2 * margin)

        canvas.setStrokeColor(colors.HexColor("#C9A227"))
        canvas.setLineWidth(1.5)
        canvas.rect(margin + 14, margin + 14, width - 2 * (margin + 14), height - 2 * (margin + 14))

        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.setFont("Helvetica-Bold", 30)
        canvas.drawCentredString(width / 2, height - 1.45 * inch, "Certificate of Completion")

        canvas.setFont("Helvetica", 15)
        canvas.drawCentredString(width / 2, height - 2.25 * inch, "This certificate is proudly presented to")

        canvas.setFont("Helvetica-Bold", 34)
        canvas.setFillColor(colors.HexColor("#0F766E"))
        canvas.drawCentredString(width / 2, height - 3.05 * inch, recipient.name or "Recipient")

        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.setFont("Helvetica", 15)
        canvas.drawCentredString(width / 2, height - 3.75 * inch, f"For successfully completing {job.title}")

        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(width / 2, height - 4.35 * inch, f"Issued by {job.issuer}")
        canvas.drawCentredString(width / 2, height - 4.7 * inch, f"Issue date: {job.issue_date.isoformat()}")

        if recipient.custom_fields:
            details = " | ".join(f"{key}: {value}" for key, value in recipient.custom_fields.items())
            canvas.setFont("Helvetica", 10)
            canvas.setFillColor(colors.HexColor("#4B5563"))
            canvas.drawCentredString(width / 2, height - 5.25 * inch, details[:130])

        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(margin + 24, margin + 22, f"Recipient ID: {recipient.id}")
        canvas.save()
        return path
