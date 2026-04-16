import os
import re
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def find_font(font_name):
    """Finds a font in common system locations."""
    # Priority paths: local, linux common, debian/ubuntu
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

    # Define replacements
    replacements = {
        "NAMANGAN MUHANDISLIK-QURILISH INSTITUTI": "Namangan texnika universiteti",
        "Rustamov Javohir Rustam o'g'lining": "Ataboyev Islombekning",
        "Rustamov Javohir Rustam o'g'li": "Ataboyev Islombek",
        "Mardiyev Azamat Rustamo'g'li": "Ataboyev Islombek",
        "JAVOXIR OMAD-FAYZ": "seyshel consalt"
    }

    modified_text = content
    for old, new in replacements.items():
        modified_text = modified_text.replace(old, new)

    pages = re.split(r'--- PAGE \d+ ---', modified_text)
    pages = [p.strip() for p in pages if p.strip()]

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Font Discovery
    font_path = find_font('DejaVuSans')
    font_bold_path = find_font('DejaVuSans-Bold')

    if not font_path:
        print("Warning: DejaVuSans.ttf not found. PDF might not render Uzbek characters correctly.")
        pdf.set_font('helvetica', '', 11) # Fallback
    else:
        pdf.add_font('DejaVu', '', font_path)
        if font_bold_path:
            pdf.add_font('DejaVu', 'B', font_bold_path)
        else:
            pdf.add_font('DejaVu', 'B', font_path) # Fallback to normal if bold missing
        pdf.set_font('DejaVu', '', 11)

    for i, page_content in enumerate(pages):
        pdf.add_page()

        lines = page_content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(5)
                continue

            if re.match(r'^\d+$', line):
                continue

            if i == 0:
                # Cover page logic
                if font_path:
                    pdf.set_font('DejaVu', 'B', 11)
                else:
                    pdf.set_font('helvetica', 'B', 11)
                pdf.multi_cell(170, 8, line, align='C')
            elif line.isupper() and len(line) < 60:
                # Section headers
                if font_path:
                    pdf.set_font('DejaVu', 'B', 12)
                else:
                    pdf.set_font('helvetica', 'B', 12)
                pdf.ln(5)
                pdf.multi_cell(170, 10, line, align='C')
                pdf.ln(2)
            else:
                # Body text
                if font_path:
                    pdf.set_font('DejaVu', '', 11)
                else:
                    pdf.set_font('helvetica', '', 11)
                pdf.multi_cell(170, 7, line, align='J')

    pdf.output("output.pdf")
    print("PDF generated: output.pdf")

if __name__ == "__main__":
    generate_pdf()
