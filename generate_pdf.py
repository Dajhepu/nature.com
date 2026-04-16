import os
import re
from fpdf import FPDF

class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_unicode = False

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        if self.use_unicode:
            self.set_font('DejaVu', '', 10)
        else:
            self.set_font('helvetica', '', 10)
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
    with open('full_transcription.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    pages = re.split(r'--- PAGE \d+ ---', content)
    pages = [p.strip() for p in pages if p.strip()]

    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(left=30, top=20, right=15)
    pdf.set_auto_page_break(auto=True, margin=20)

    font_path = find_font('DejaVuSans')
    font_bold_path = find_font('DejaVuSans-Bold')

    if font_path:
        pdf.add_font('DejaVu', '', font_path)
        if font_bold_path:
            pdf.add_font('DejaVu', 'B', font_bold_path)
        else:
            pdf.add_font('DejaVu', 'B', font_path)
        pdf.use_unicode = True
        body_font = 'DejaVu'
    else:
        print("Warning: DejaVuSans.ttf not found. Using Helvetica fallback.")
        body_font = 'helvetica'

    # Width: 210 - 30 - 15 = 165
    eff_width = 165

    for i, page_content in enumerate(pages):
        pdf.add_page()

        lines = page_content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(9) # Spacing
                continue

            if i == 0:
                # Cover
                pdf.set_font(body_font, 'B', 14 if any(x in line for x in ["HISOBOTI", "UNIVERSITETI", "OLIY"]) else 12)
                pdf.multi_cell(eff_width, 8, line, align='C')
            elif line.isupper() and len(line) < 70:
                # Headers
                pdf.set_font(body_font, 'B', 14)
                pdf.ln(5)
                pdf.multi_cell(eff_width, 10, line, align='C')
                pdf.ln(3)
            elif "---" in line or "|" in line:
                # Tables or markers - use standard alignment
                pdf.set_font(body_font, '', 11)
                pdf.multi_cell(eff_width, 8, line, align='L')
            else:
                # Body
                pdf.set_font(body_font, '', 12)
                pdf.multi_cell(eff_width, 9, line, align='J') # 9mm height to fill page

    pdf.output("output.pdf")
    print("30-page PDF generated: output.pdf")

if __name__ == "__main__":
    generate_pdf()
