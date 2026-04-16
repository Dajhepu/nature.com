import os
import re
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 10)
        self.cell(0, 10, f'{self.page_no()}', 0, 0, 'C')

def find_font(font_name):
    """Finds a font in common system locations."""
    paths = [
        f"{font_name}.ttf",
        f"/usr/share/fonts/truetype/dejavu/{font_name}.ttf",
        f"/usr/share/fonts/dejavu/{font_name}.ttf",
        f"~/.fonts/{font_name}.ttf"
    ]
    for path in paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            return expanded_path
    return None

def generate_pdf():
    # Read transcription
    with open('full_transcription.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into pages
    pages = re.split(r'--- PAGE \d+ ---', content)
    pages = [p.strip() for p in pages if p.strip()]

    # PDF instantiation with academic margins
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(left=30, top=20, right=15)
    pdf.set_auto_page_break(auto=True, margin=20)

    # Font Discovery
    font_path = find_font('DejaVuSans')
    font_bold_path = find_font('DejaVuSans-Bold')

    if not font_path:
        print("Warning: DejaVuSans.ttf not found.")
        pdf.set_font('helvetica', '', 12)
    else:
        pdf.add_font('DejaVu', '', font_path)
        if font_bold_path:
            pdf.add_font('DejaVu', 'B', font_bold_path)
        else:
            pdf.add_font('DejaVu', 'B', font_path)
        pdf.set_font('DejaVu', '', 12)

    # Use a fixed width to avoid 'Not enough horizontal space' issues with multi_cell(0, ...)
    # Page width is 210mm. Margins are 30mm (L) + 15mm (R) = 45mm.
    # Effective width = 210 - 45 = 165mm.
    eff_width = 165

    for i, page_content in enumerate(pages):
        pdf.add_page()

        lines = page_content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(6)
                continue

            if i == 0:
                pdf.set_font('DejaVu', 'B', 14 if "HISOBOTI" in line or "UNIVERSITETI" in line else 12)
                pdf.multi_cell(eff_width, 8, line, align='C')
            elif line.isupper() and len(line) < 60:
                pdf.set_font('DejaVu', 'B', 14)
                pdf.ln(5)
                pdf.multi_cell(eff_width, 10, line, align='C')
                pdf.ln(3)
            else:
                pdf.set_font('DejaVu', '', 12)
                pdf.multi_cell(eff_width, 8, line, align='J')

    pdf.output("output.pdf")
    print("30-page PDF generated: output.pdf")

if __name__ == "__main__":
    generate_pdf()
