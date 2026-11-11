"""
build_nitw_12page_report.py
===========================
Generates a publication-grade, 12-page academic project report for NIT Warangal,
strictly matching the typography, layout, color palette, booktabs tables, figures,
page numbering, and sectioning of the reference NIT Warangal report.

Deliverables generated:
1. NITW_Topic6_Imagined_Words_Final_Report.pdf (Exact 12-page PDF)
2. NITW_Topic6_Imagined_Words_Final_Report.docx (Complete Microsoft Word Document)

Topic 6: Prediction of Imagined Words (Help, Hungry, Thirsty, Fire, etc.) Using Brain EEG Signals
Department of Computer Science and Engineering, National Institute of Technology Warangal
Team: Saurabh Bharrdwaj (26CSM2R20, Lead) • Badvath Jaipal (26CSM2R04) • Saurabh Kumar (26CSM2R20)
Date: November 2026
"""

import os
import sys
import io
import zlib
from PIL import Image

# -----------------------------------------------------------------------------
# Standard Type 1 AFM Character Widths for Times-Roman & Times-Bold (1/1000 em)
# -----------------------------------------------------------------------------
TR_WIDTHS = {
    ' ': 250, '!': 333, '"': 408, '#': 500, '$': 500, '%': 833, '&': 778, '\'': 333,
    '(': 333, ')': 333, '*': 500, '+': 564, ',': 250, '-': 333, '.': 250, '/': 278,
    '0': 500, '1': 500, '2': 500, '3': 500, '4': 500, '5': 500, '6': 500, '7': 500,
    '8': 500, '9': 500, ':': 278, ';': 278, '<': 564, '=': 564, '>': 564, '?': 444,
    '@': 921, 'A': 722, 'B': 667, 'C': 667, 'D': 722, 'E': 611, 'F': 556, 'G': 722,
    'H': 722, 'I': 333, 'J': 389, 'K': 722, 'L': 611, 'M': 889, 'N': 722, 'O': 722,
    'P': 556, 'Q': 722, 'R': 667, 'S': 556, 'T': 611, 'U': 722, 'V': 667, 'W': 889,
    'X': 667, 'Y': 611, 'Z': 611, '[': 333, '\\': 278, ']': 333, '^': 469, '_': 500,
    '`': 333, 'a': 444, 'b': 500, 'c': 444, 'd': 500, 'e': 444, 'f': 278, 'g': 500,
    'h': 500, 'i': 278, 'j': 278, 'k': 444, 'l': 278, 'm': 722, 'n': 500, 'o': 500,
    'p': 500, 'q': 500, 'r': 333, 's': 389, 't': 278, 'u': 500, 'v': 500, 'w': 722,
    'x': 500, 'y': 500, 'z': 444, '{': 480, '|': 200, '}': 480, '~': 541,
    '•': 500, '–': 500, '—': 1000, '“': 444, '”': 444, '‘': 333, '’': 333, '…': 1000,
    'é': 444, 'ñ': 500, 'ó': 500, 'í': 278, 'á': 444, 'ú': 500, 'γ': 500, 'λ': 500,
    'σ': 500, 'μ': 500, 'θ': 500, 'κ': 500, 'α': 500, 'β': 500, '≤': 564, '≥': 564,
    '±': 564, '×': 564, '·': 250, '∈': 564, '∑': 722, '√': 564, '≈': 564
}

TB_WIDTHS = {k: min(1000, int(v * 1.08)) for k, v in TR_WIDTHS.items()}
TB_WIDTHS[' '] = 250

def get_text_width(text, font, size):
    table = TB_WIDTHS if font in ('F2', 'F4') else TR_WIDTHS
    return sum(table.get(c, 500) for c in text) * size / 1000.0

class NITWReportPDF:
    def __init__(self, filename="NITW_Topic6_Imagined_Words_Final_Report.pdf"):
        self.filename = filename
        self.pages = []            # List of streams per page
        self.page_images = []       # List of list of image names on each page
        self.current_stream = []
        self.current_images = []
        self.images = {}           # name -> (w, h, jpeg_bytes)
        self.page_width = 595.28   # A4 width (pt)
        self.page_height = 841.89  # A4 height (pt)
        self.margin_x = 54.0       # 0.75 in
        self.margin_top = 54.0
        self.margin_bottom = 54.0
        self.content_width = self.page_width - (2 * self.margin_x)
        self.y = self.page_height - self.margin_top
        self.page_num = 0

    def register_image(self, name, img_path):
        if not os.path.exists(img_path):
            print(f"[!] Warning: Image not found: {img_path}")
            return False
        try:
            im = Image.open(img_path).convert('RGB')
            buf = io.BytesIO()
            im.save(buf, format='JPEG', quality=88, optimize=True)
            self.images[name] = (im.width, im.height, buf.getvalue())
            return True
        except Exception as e:
            print(f"[!] Error registering image {img_path}: {e}")
            return False

    def new_page(self, footer_num=None):
        if self.page_num > 0:
            self.pages.append("".join(self.current_stream))
            self.page_images.append(list(self.current_images))
            self.current_stream = []
            self.current_images = []
        self.page_num += 1
        self.y = self.page_height - self.margin_top

        # Draw footer page number if specified (Centered at y = 35 pt, matching reference)
        if footer_num is not None:
            num_str = str(footer_num)
            w = get_text_width(num_str, "F1", 9.5)
            x_pos = (self.page_width - w) / 2.0
            self.draw_text_line(num_str, x_pos, 35.0, "F1", 9.5, (0.05, 0.05, 0.05))

    def set_color(self, r, g, b, is_fill=True):
        cmd = f"{r:.3f} {g:.3f} {b:.3f} {'rg' if is_fill else 'RG'}\n"
        self.current_stream.append(cmd)

    def draw_line(self, x1, y1, x2, y2, color=(0.1, 0.1, 0.1), width=0.5):
        self.set_color(color[0], color[1], color[2], is_fill=False)
        self.current_stream.append(f"{width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n")

    def draw_rect(self, x, y, w, h, fill_color=None, stroke_color=None, width=0.5):
        cmd = ""
        if fill_color:
            self.set_color(fill_color[0], fill_color[1], fill_color[2], is_fill=True)
            cmd += f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f\n"
        if stroke_color:
            self.set_color(stroke_color[0], stroke_color[1], stroke_color[2], is_fill=False)
            cmd += f"{width:.2f} w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S\n"
        self.current_stream.append(cmd)

    def _escape(self, text):
        clean = ""
        # PDF Latin-1 mappings for special academic symbols
        replacements = {
            '—': '---', '–': '--', '“': '"', '”': '"', '‘': "'", '’': "'", '…': '...',
            '•': '*', 'é': 'e', 'ñ': 'n', 'ó': 'o', 'í': 'i', 'á': 'a', 'ú': 'u',
            'γ': 'gamma', 'λ': 'lambda', 'σ': 'sigma', 'μ': 'mu', 'θ': 'theta',
            'κ': 'kappa', 'α': 'alpha', 'β': 'beta', '≤': '<=', '≥': '>=', '±': '+/-',
            '×': 'x', '·': '.', '∈': 'in', '∑': 'sum', '√': 'sqrt', '≈': '~'
        }
        for ch in text:
            if ch in replacements:
                clean += replacements[ch]
            elif ord(ch) < 128:
                clean += ch
            else:
                clean += ch
        return clean.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    def draw_text_line(self, text, x, y, font="F1", size=10.0, color=(0.05, 0.05, 0.05)):
        self.set_color(color[0], color[1], color[2], is_fill=True)
        esc = self._escape(text)
        self.current_stream.append(f"BT /{font} {size:.1f} Tf {x:.2f} {y:.2f} Td ({esc}) Tj ET\n")

    def wrap_text(self, text, max_width, font="F1", size=10.0):
        words = text.split(' ')
        if not words:
            return [""]
        lines = []
        cur_line = []
        cur_w = 0.0

        for word in words:
            w_len = get_text_width(word + ' ', font, size)
            if cur_w + w_len <= max_width:
                cur_line.append(word)
                cur_w += w_len
            else:
                if cur_line:
                    lines.append(" ".join(cur_line))
                cur_line = [word]
                cur_w = w_len
        if cur_line:
            lines.append(" ".join(cur_line))
        return lines

    def add_paragraph(self, text, font="F1", size=9.8, leading=13.6, color=(0.05, 0.05, 0.05), indent=0.0):
        lines = self.wrap_text(text, self.content_width - indent, font, size)
        for line in lines:
            self.draw_text_line(line, self.margin_x + indent, self.y - size, font, size, color)
            self.y -= leading
        self.y -= 3.5

    def add_sec_heading(self, text, size=13.5, space_before=12.0, space_after=8.0):
        self.y -= space_before
        self.draw_text_line(text, self.margin_x, self.y - size, "F2", size, (0.0, 0.0, 0.0))
        self.y -= (size + space_after)

    def add_subsec_heading(self, text, size=11.2, space_before=9.0, space_after=5.5):
        self.y -= space_before
        self.draw_text_line(text, self.margin_x, self.y - size, "F2", size, (0.0, 0.0, 0.0))
        self.y -= (size + space_after)

    def add_bullet(self, bold_prefix, text, size=9.5, leading=13.0):
        full_text = f"{bold_prefix} {text}" if bold_prefix else text
        lines = self.wrap_text(full_text, self.content_width - 16.0, "F1", size)
        for i, line in enumerate(lines):
            if i == 0:
                # Small neat bullet
                self.draw_rect(self.margin_x + 3.0, self.y - size + 3.0, 2.5, 2.5, fill_color=(0.1, 0.1, 0.1))
            self.draw_text_line(line, self.margin_x + 14.0, self.y - size, "F1", size, (0.05, 0.05, 0.05))
            self.y -= leading
        self.y -= 2.5

    def add_image(self, img_name, target_w, target_h, caption=None):
        if img_name not in self.images:
            return
        if img_name not in self.current_images:
            self.current_images.append(img_name)

        # Center image horizontally
        x = self.margin_x + (self.content_width - target_w) / 2.0
        y = self.y - target_h

        # Transformation matrix: [w 0 0 h x y] cm
        self.current_stream.append(f"q {target_w:.2f} 0 0 {target_h:.2f} {x:.2f} {y:.2f} cm /{img_name} Do Q\n")
        self.y -= (target_h + 5.5)

        if caption:
            cap_lines = self.wrap_text(caption, self.content_width, "F1", 8.8)
            for cline in cap_lines:
                w = get_text_width(cline, "F1", 8.8)
                cx = self.margin_x + (self.content_width - w) / 2.0
                self.draw_text_line(cline, cx, self.y - 8.8, "F1", 8.8, (0.1, 0.1, 0.1))
                self.y -= 11.2
            self.y -= 5.0

    def add_booktabs_table(self, title, headers, rows, col_widths, font_size=8.4, row_height=13.6):
        table_width = sum(col_widths)
        start_x = self.margin_x + (self.content_width - table_width) / 2.0

        if title:
            # Table caption above table (LaTeX standard)
            self.draw_text_line(title, start_x, self.y - 8.8, "F1", 8.8, (0.05, 0.05, 0.05))
            self.y -= 14.5

        # \toprule (1.2 pt)
        self.draw_line(start_x, self.y, start_x + table_width, self.y, (0.0, 0.0, 0.0), 1.2)
        self.y -= (row_height * 0.88)

        # Header Row
        cx = start_x
        for h, cw in zip(headers, col_widths):
            self.draw_text_line(h, cx + 2.0, self.y - font_size, "F2", font_size, (0.0, 0.0, 0.0))
            cx += cw
        self.y -= (font_size + 3.8)

        # \midrule (0.6 pt)
        self.draw_line(start_x, self.y, start_x + table_width, self.y, (0.2, 0.2, 0.2), 0.6)
        self.y -= 3.8

        # Body Rows
        for r_idx, row in enumerate(rows):
            cx = start_x
            for c_idx, (val, cw) in enumerate(zip(row, col_widths)):
                f = "F2" if c_idx == 0 and ("Proposed" in val or "CMRA" in val) else "F1"
                self.draw_text_line(val, cx + 2.0, self.y - font_size, f, font_size, (0.05, 0.05, 0.05))
                cx += cw
            self.y -= row_height

        # \bottomrule (1.2 pt)
        self.draw_line(start_x, self.y + 3.0, start_x + table_width, self.y + 3.0, (0.0, 0.0, 0.0), 1.2)
        self.y -= 9.0

    def add_toc_line(self, title, page_str, level=1, font_size=9.8):
        indent = 16.0 if level == 2 else 0.0
        f = "F2" if level == 1 and not title.startswith("Abstract") and not title.startswith("References") else "F1"
        x_left = self.margin_x + indent
        self.draw_text_line(title, x_left, self.y - font_size, f, font_size, (0.05, 0.05, 0.05))

        title_w = get_text_width(title, f, font_size)
        page_w = get_text_width(page_str, "F1", font_size)
        x_right = self.page_width - self.margin_x - page_w

        # Draw page number on right
        self.draw_text_line(page_str, x_right, self.y - font_size, "F1", font_size, (0.05, 0.05, 0.05))

        # Dotted leader between title and page
        dot_start = x_left + title_w + 8.0
        dot_end = x_right - 8.0
        dot_str = ". " * int((dot_end - dot_start) / 7.5)
        self.draw_text_line(dot_str, dot_start, self.y - font_size, "F1", 7.5, (0.35, 0.35, 0.35))
        self.y -= 17.5

    def build_pdf(self):
        # Finalize the last page
        if self.page_num > 0 and len(self.pages) < self.page_num:
            self.pages.append("".join(self.current_stream))
            self.page_images.append(list(self.current_images))

        # PDF Object Table Construction
        objects = []
        def add_obj(content):
            objects.append(content)
            return len(objects)

        # 1: Catalog
        # 2: Pages
        # 3,4,5,6: Fonts (F1, F2, F3, F4)
        add_obj(None) # Catalog placeholder (obj 1)
        add_obj(None) # Pages placeholder (obj 2)

        obj_f1 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>")
        obj_f2 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>")
        obj_f3 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic >>")
        obj_f4 = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Times-BoldItalic >>")

        # Image objects
        img_obj_map = {}
        for img_name, (w, h, data) in self.images.items():
            head = f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>\nstream\n"
            tail = "\nendstream"
            img_obj_id = add_obj((head.encode('latin1'), data, tail.encode('latin1')))
            img_obj_map[img_name] = img_obj_id

        # Page and Content objects
        page_obj_ids = []
        for p_idx, page_stream in enumerate(self.pages):
            stream_bytes = page_stream.encode('latin1')
            comp_stream = zlib.compress(stream_bytes)
            content_dict = f"<< /Length {len(comp_stream)} /Filter /FlateDecode >>\nstream\n"
            content_tail = "\nendstream"
            content_obj_id = add_obj((content_dict.encode('latin1'), comp_stream, content_tail.encode('latin1')))

            # Page Resources
            imgs_on_page = self.page_images[p_idx]
            xobj_str = ""
            if imgs_on_page:
                xobj_entries = " ".join(f"/{im} {img_obj_map[im]} 0 R" for im in imgs_on_page if im in img_obj_map)
                xobj_str = f"/XObject << {xobj_str} >>" if xobj_entries else ""

            page_dict = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.page_width:.2f} {self.page_height:.2f}] " \
                        f"/Contents {content_obj_id} 0 R " \
                        f"/Resources << /Font << /F1 {obj_f1} 0 R /F2 {obj_f2} 0 R /F3 {obj_f3} 0 R /F4 {obj_f4} 0 R >> "
            if imgs_on_page:
                xobj_dict = " ".join(f"/{im} {img_obj_map[im]} 0 R" for im in imgs_on_page if im in img_obj_map)
                page_dict += f"/XObject << {xobj_dict} >> "
            page_dict += ">> >>"
            page_obj_id = add_obj(page_dict)
            page_obj_ids.append(page_obj_id)

        # Update Pages (obj 2) and Catalog (obj 1)
        kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>"
        objects[0] = f"<< /Type /Catalog /Pages 2 0 R >>"

        # Serialize to binary PDF
        out = io.BytesIO()
        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets = []
        for i, obj in enumerate(objects):
            offsets.append(out.tell())
            obj_num = i + 1
            out.write(f"{obj_num} 0 obj\n".encode('latin1'))
            if isinstance(obj, tuple):
                for part in obj:
                    out.write(part)
            else:
                out.write(obj.encode('latin1'))
            out.write(b"\nendobj\n")

        xref_pos = out.tell()
        out.write(f"xref\n0 {len(objects) + 1}\n".encode('latin1'))
        out.write(b"0000000000 65535 f \n")
        for off in offsets:
            out.write(f"{off:010d} 00000 n \n".encode('latin1'))

        trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
        out.write(trailer.encode('latin1'))

        with open(self.filename, 'wb') as f:
            f.write(out.getvalue())
        print(f"[+] Successfully wrote {len(page_obj_ids)}-page PDF: '{self.filename}' ({len(out.getvalue())} bytes)")
        return self.filename


def generate_exact_12page_report():
    pdf = NITWReportPDF("NITW_Topic6_Imagined_Words_Final_Report.pdf")

    # Paths to figures in results
    res_dir = r"c:\Users\st983\Downloads\ml\imagined_speech_eeg\results"
    fig1_path = os.path.join(res_dir, "architecture_flow_diagram.png")
    fig2_path = os.path.join(res_dir, "fig2_aga_optimization.png")
    fig3_path = os.path.join(res_dir, "fig3_accuracy_comparison.png")
    fig4_path = os.path.join(res_dir, "confusion_matrix_improved.png")
    fig5_path = os.path.join(res_dir, "live_decoded_signal.png")

    pdf.register_image("Im1", fig1_path)
    pdf.register_image("Im2", fig2_path)
    pdf.register_image("Im3", fig3_path)
    pdf.register_image("Im4", fig4_path)
    pdf.register_image("Im5", fig5_path)

    # =========================================================================
    # PAGE 1: STANDALONE TITLE / COVER PAGE (No footer page number)
    # =========================================================================
    pdf.new_page(footer_num=None)

    # Institution and Course
    pdf.y = pdf.page_height - 180.0
    inst = "National Institute of Technology Warangal"
    w_inst = get_text_width(inst, "F2", 18.5)
    pdf.draw_text_line(inst, (pdf.page_width - w_inst) / 2.0, pdf.y, "F2", 18.5, (0.0, 0.0, 0.0))
    pdf.y -= 26.0

    course = "CS26001: Advanced Algorithms - Course Project"
    w_course = get_text_width(course, "F1", 11.5)
    pdf.draw_text_line(course, (pdf.page_width - w_course) / 2.0, pdf.y, "F1", 11.5, (0.1, 0.1, 0.1))

    # Main Title
    pdf.y = 520.0
    t1 = "Prediction of Imagined Words Using"
    t2 = "Brain EEG Signals"
    w_t1 = get_text_width(t1, "F2", 21.0)
    w_t2 = get_text_width(t2, "F2", 21.0)
    pdf.draw_text_line(t1, (pdf.page_width - w_t1) / 2.0, pdf.y, "F2", 21.0, (0.0, 0.0, 0.0))
    pdf.y -= 28.0
    pdf.draw_text_line(t2, (pdf.page_width - w_t2) / 2.0, pdf.y, "F2", 21.0, (0.0, 0.0, 0.0))

    # Subtitle
    pdf.y -= 36.0
    s1 = "Multi-Domain Riemannian Covariance with Adaptive Genetic Feature Selection"
    s2 = "and Calibrated Stacking Ensemble"
    s3 = "with Real-Time Signal Ingestion"
    w_s1 = get_text_width(s1, "F1", 12.0)
    w_s2 = get_text_width(s2, "F1", 12.0)
    w_s3 = get_text_width(s3, "F1", 11.0)
    pdf.draw_text_line(s1, (pdf.page_width - w_s1) / 2.0, pdf.y, "F1", 12.0, (0.1, 0.1, 0.1))
    pdf.y -= 20.0
    pdf.draw_text_line(s2, (pdf.page_width - w_s2) / 2.0, pdf.y, "F1", 12.0, (0.1, 0.1, 0.1))
    pdf.y -= 22.0
    pdf.draw_text_line(s3, (pdf.page_width - w_s3) / 2.0, pdf.y, "F1", 11.0, (0.2, 0.2, 0.2))

    # Dataset notice
    pdf.y = 260.0
    dnote1 = "A reproducible study on the EEGIS 14-Channel Multi-Class"
    dnote2 = "Imagined Speech Database (Mendeley Data 73g4fw884c.1)"
    w_dn1 = get_text_width(dnote1, "F1", 10.5)
    w_dn2 = get_text_width(dnote2, "F1", 10.5)
    pdf.draw_text_line(dnote1, (pdf.page_width - w_dn1) / 2.0, pdf.y, "F1", 10.5, (0.15, 0.15, 0.15))
    pdf.y -= 16.0
    pdf.draw_text_line(dnote2, (pdf.page_width - w_dn2) / 2.0, pdf.y, "F1", 10.5, (0.15, 0.15, 0.15))

    # Team Members & Date
    pdf.y = 175.0
    tlabel = "Team:"
    w_tl = get_text_width(tlabel, "F1", 10.5)
    pdf.draw_text_line(tlabel, (pdf.page_width - w_tl) / 2.0, pdf.y, "F1", 10.5, (0.15, 0.15, 0.15))
    pdf.y -= 17.0

    team = "Saurabh Bharrdwaj  *  Badvath Jaipal  *  Saurabh Kumar"
    w_tm = get_text_width(team, "F1", 10.5)
    pdf.draw_text_line(team, (pdf.page_width - w_tm) / 2.0, pdf.y, "F1", 10.5, (0.05, 0.05, 0.05))
    pdf.y -= 38.0

    date_str = "November 2026"
    w_dt = get_text_width(date_str, "F1", 10.5)
    pdf.draw_text_line(date_str, (pdf.page_width - w_dt) / 2.0, pdf.y, "F1", 10.5, (0.15, 0.15, 0.15))

    # =========================================================================
    # PAGE 2: STANDALONE ABSTRACT PAGE (Footer: 1)
    # =========================================================================
    pdf.new_page(footer_num=1)
    pdf.y = pdf.page_height - 90.0

    pdf.draw_text_line("Abstract", pdf.margin_x, pdf.y - 15.5, "F2", 15.5, (0.0, 0.0, 0.0))
    pdf.y -= 34.0

    abs_p1 = (
        "Imagined speech electroencephalography (EEG) provides a direct, non-invasive communication "
        "modality for individuals suffering from profound motor and vocal impairments, including locked-in "
        "syndrome, brainstem stroke, and amyotrophic lateral sclerosis (ALS). However, decoding covert "
        "phonological and semantic intentions directly from raw scalp potentials remains an intrinsically ill-posed "
        "inverse problem characterized by ultra-low signal-to-noise ratios (< -10 dB), dynamic inter-subject scalp "
        "non-stationarity, and substantial spatial smearing caused by cranial volume conduction. Traditional "
        "common spatial pattern (CSP) filtering and linear discriminant classifiers yield fragile representations "
        "that degrade near random chance under multi-subject cognitive loads. In this investigation, we address "
        "these fundamental constraints on the full 4,044-trial Mendeley EEGIS database through an end-to-end framework "
        "termed Multi-Domain Riemannian Covariance with Adaptive Genetic Optimization (MDRC-AGA). Our framework introduces "
        "three methodological contributions: (i) a unified dual-stream representation combining 322 multi-domain temporal, "
        "spectral, and Hjorth moments with 105 Log-Euclidean Riemannian tangent-space covariance projections on the manifold "
        "of Symmetric Positive Definite (SPD) matrices; (ii) a diversity-driven Adaptive Genetic Algorithm (AGA) that "
        "modulates mutation probabilities dynamically via population phenotypic variance, pruning 69.3% of noisy features "
        "(427 initial dimensions down to 131 optimal descriptors); and (iii) a calibrated soft-voting ensemble combining "
        "RBF Support Vector Machines, Histogram Gradient Boosting, and Multi-Layer Perceptrons."
    )
    pdf.add_paragraph(abs_p1, "F1", 9.8, 14.2)

    abs_p2 = (
        "All experiments were executed exclusively on all 4,044 real in-vivo human EEG recordings across nine semantic targets "
        "('Rest', 'Help', 'Bathroom', 'Pain', 'Thanks', 'Hungry', 'No', 'Thirsty', 'Yes') from 10 participants (Mendeley Data "
        "10.17632/73g4fw884c.1), with zero synthetic fallbacks and 100% organic inference (zero artificial prediction overrides). "
        "On a balanced 9-class cohort (720 trials: 540 train / 180 holdout; random chance = 11.11%), replicating the baseline "
        "Static GA + SVM pipeline (102/322 features) achieves 36.11% accuracy (0.3453 Macro F1). Adding Riemannian tangent-space "
        "covariance, AGA feature selection, and ensemble soft-voting raises test accuracy to 44.44% (+8.33 percentage points, "
        "0.4392 Macro F1, 4.0x chance) while attaining 80.0% recall on emergency command 'Help'. Pure Riemannian geometry alone "
        "(105 features) reaches 46.11% on the balanced cohort and improves mixed 10-subject 4,044-trial generalization from "
        "20.08% to 27.10%. On full-dataset emergency binary pairs ('Help vs Pain', N=996; 'Help vs Rest', N=960), Riemannian "
        "fusion lifts accuracy from 61.45% to 67.07% and 63.33% to 67.92%. End-to-end real-time inference over raw patient CSV "
        "streams achieves 5/9 (55.6%) accuracy across unlabeled trials at 95.6 ms mean latency per 1.0-second epoch."
    )
    pdf.add_paragraph(abs_p2, "F1", 9.8, 14.2)

    pdf.y -= 12.0
    kw_bold = "Keywords:"
    kw_text = " brain-computer interface (BCI); imagined speech; electroencephalography (EEG); Riemannian covariance; adaptive genetic algorithm; stacking ensemble; EEGIS dataset."
    w_kwb = get_text_width(kw_bold, "F2", 9.6)
    pdf.draw_text_line(kw_bold, pdf.margin_x, pdf.y - 9.6, "F2", 9.6, (0.05, 0.05, 0.05))
    lines_kw = pdf.wrap_text(kw_text, pdf.content_width - w_kwb - 4.0, "F1", 9.6)
    for i, lkw in enumerate(lines_kw):
        x_k = pdf.margin_x + w_kwb + 4.0 if i == 0 else pdf.margin_x
        pdf.draw_text_line(lkw, x_k, pdf.y - 9.6, "F1", 9.6, (0.1, 0.1, 0.1))
        pdf.y -= 13.5

    # =========================================================================
    # PAGE 3: STANDALONE CONTENTS PAGE (Footer: 2)
    # =========================================================================
    pdf.new_page(footer_num=2)
    pdf.y = pdf.page_height - 90.0

    pdf.draw_text_line("Contents", pdf.margin_x, pdf.y - 15.5, "F2", 15.5, (0.0, 0.0, 0.0))
    pdf.y -= 38.0

    pdf.add_toc_line("Abstract", "1", level=1)
    pdf.y -= 6.0
    pdf.add_toc_line("1  Introduction", "3", level=1)
    pdf.y -= 6.0
    pdf.add_toc_line("2  Related Work", "3", level=1)
    pdf.y -= 6.0
    pdf.add_toc_line("3  Methodology", "4", level=1)
    pdf.add_toc_line("3.1  Overview", "4", level=2)
    pdf.add_toc_line("3.2  14-Channel Montage and Preprocessing", "4", level=2)
    pdf.add_toc_line("3.3  Dual-Stream Multi-Domain & Riemannian Feature Extraction", "4", level=2)
    pdf.add_toc_line("3.4  Adaptive Genetic Algorithm (AGA) Optimization", "5", level=2)
    pdf.add_toc_line("3.5  Calibrated Stacking Ensemble Inference", "5", level=2)
    pdf.y -= 6.0
    pdf.add_toc_line("4  Experiment and Results", "5", level=1)
    pdf.add_toc_line("4.1  Setup Used", "5", level=2)
    pdf.add_toc_line("4.2  Benchmark Dataset", "6", level=2)
    pdf.add_toc_line("4.3  Performance Metrics", "6", level=2)
    pdf.add_toc_line("4.4  Results", "7", level=2)
    pdf.add_toc_line("4.5  Academic Integrity & Real-Dataset Insights", "8", level=2)
    pdf.add_toc_line("4.6  Bedside Desktop Oscilloscope & Real-Time Testing", "9", level=2)
    pdf.y -= 6.0
    pdf.add_toc_line("5  Conclusion and Future Work", "9", level=1)
    pdf.y -= 6.0
    pdf.add_toc_line("References", "10", level=1)

    # =========================================================================
    # PAGE 4: INTRODUCTION & RELATED WORK (Footer: 3)
    # =========================================================================
    pdf.new_page(footer_num=3)
    pdf.y = pdf.page_height - 60.0

    pdf.add_sec_heading("1  Introduction", size=14.0, space_before=4.0, space_after=10.0)

    intro_p1 = (
        "Brain-computer interfaces (BCIs) represent a transformative frontier in clinical neuro-engineering, "
        "offering a direct communication pathway between the human central nervous system and external assistive "
        "devices. For patients afflicted by neurodegenerative disorders such as amyotrophic lateral sclerosis (ALS), "
        "severe cerebral palsy, or brainstem stroke, peripheral neuromuscular pathways become permanently severed "
        "while cognitive faculties remain intact. In such conditions, known as locked-in syndrome, the ability to "
        "express fundamental human desires—such as requesting emergency medical assistance, hydration, or relief "
        "from acute pain—is entirely extinguished. Imagined speech, wherein a subject mentally articulates specific "
        "words or phonemes without producing audible sound or observable muscle movement, constitutes the most intuitive "
        "and ecologically valid communication paradigm. Unlike P300 visual evoked potentials or steady-state visual "
        "evoked potentials (SSVEP), which require intact gaze control and provoke severe ocular fatigue, imagined speech "
        "relies exclusively on internal phonological planning within Broca's area (Brodmann areas 44/45), Wernicke's "
        "area, and the supplementary motor cortex."
    )
    pdf.add_paragraph(intro_p1, "F1", 9.8, 13.6)

    intro_p2 = (
        "Primary Research Paper Benchmark: The foundational baseline for this project is the study by Lara-Arellano "
        "et al. published in Eng (MDPI, 2025), titled 'Feature Generation with Genetic Algorithms for Imagined Speech "
        "Electroencephalogram Signal Classification'. Their method extracted 322 temporal-spectral moments across 14 channels "
        "on the EEGIS dataset, employed a standard Genetic Algorithm (GA) with fixed mutation (Pm=0.03), and classified features "
        "using a single Support Vector Machine (RBF kernel), reporting up to 77.78% in isolated single-band/subject protocols. "
        "Under strict multi-subject raw 1.0-second epoch evaluation on real Mendeley data (no band pre-isolation), their "
        "pipeline reaches 36.11% accuracy (102/322 features), exposing three core limitations: (1) Static mutation causes diversity "
        "loss, trapping chromosomes on noisy channels; (2) Scalar moments ignore inter-electrode spatial covariance on the scalp "
        "manifold; and (3) A single SVM margin boundary degrades rapidly under non-stationary scalp impedance drift."
    )
    pdf.add_paragraph(intro_p2, "F1", 9.8, 13.6)

    pdf.draw_text_line("Proposed Methodological Improvements Over the Benchmark Paper:", pdf.margin_x, pdf.y - 10.0, "F2", 10.0, (0.0, 0.0, 0.0))
    pdf.y -= 15.5

    pdf.add_bullet(
        "Improvement 1: Dual-Stream Riemannian Manifold Covariance Fusing (105 Novel Features):",
        "We compute regularized spatial covariance matrices on the SPD manifold and project them onto the Euclidean tangent "
        "space via Matrix Logarithm, capturing inter-electrode synchronization and raising real-data accuracy by +7% to +10%."
    )
    pdf.add_bullet(
        "Improvement 2: Diversity-Driven Adaptive Genetic Algorithm (AGA):",
        "We replace static mutation with dynamic phenotypic variance tracking, automatically scaling mutation Pm(t) (0.0397 "
        "to 0.0437) to prevent stagnation and pruning 69.3% of redundant noise (427 dimensions down to 131 optimal features)."
    )
    pdf.add_bullet(
        "Improvement 3: Calibrated Soft-Voting Stacking Ensemble (Multi-Model Consensus):",
        "We replace the brittle single SVM with a weighted soft-voting ensemble of RBF-SVM (3.0), HistGradientBoosting (1.0), "
        "and Multi-Layer Perceptron (1.0), elevating balanced 9-class accuracy from 36.11% to 44.44% with 80.0% Help recall."
    )
    pdf.add_bullet(
        "Improvement 4: Real-Time Signal-Driven Bedside Verification Suite (95.6 ms Mean Latency):",
        "We eliminate synthetic fallbacks and artificial overrides, validating directly against raw 14-channel microvolt recordings "
        "(.csv/.npy) from the official 4,044-trial Mendeley database with an interactive oscilloscope GUI."
    )

    pdf.y -= 3.0
    intro_p3 = (
        "The report is organised as follows: Section 2 reviews related work, Section 3 describes the methodology, "
        "Section 4 presents real-dataset experiments and ablation results, and Section 5 concludes with future work."
    )
    pdf.add_paragraph(intro_p3, "F1", 9.8, 13.6)

    pdf.add_sec_heading("2  Related Work", size=13.5, space_before=8.0, space_after=8.0)
    pdf.add_paragraph(
        "Traditional methods: Early motor imagery and speech BCIs heavily utilized Common Spatial Patterns (CSP) "
        "and Filter Bank CSP (FBCSP) coupled with Linear Discriminant Analysis (LDA) (Blankertz et al., 2011). While "
        "effective for binary motor tasks, linear CSP/LDA degrades near random chance in multiclass imagined speech (25.00%)."
    )
    pdf.add_paragraph(
        "CNN-based methods: Lawhern et al. (2018) introduced EEGNet, utilizing depthwise separable convolutions "
        "to extract spatio-temporal features. While compact (~2,500 parameters), deep models remain prone to severe "
        "calibration variance and overfitting when trained across heterogeneous patient scalp recordings."
    )
    pdf.add_paragraph(
        "Evolutionary feature selection: Lara-Arellano et al. (2025) pioneered genetic feature generation on the "
        "EEGIS dataset. However, fixed mutation causes premature genetic drift and univariate scalar features miss inter-channel "
        "spatial synchronization, limiting raw 9-class generalization on real multi-subject epochs to 36.11%."
    )

    # =========================================================================
    # PAGE 5: METHODOLOGY OVERVIEW, MONTAGE & FEATURE EXTRACTION (Footer: 4)
    # =========================================================================
    pdf.new_page(footer_num=4)
    pdf.y = pdf.page_height - 60.0

    pdf.add_paragraph(
        "Riemannian geometry approaches: Barachant et al. (2012) and Congedo et al. (2017) demonstrated that covariance "
        "matrices computed from multi-channel EEG lie on a differentiable Riemannian manifold of Symmetric Positive Definite "
        "(SPD) matrices. Projecting these matrices onto an affine-invariant tangent space enables linear Euclidean classifiers "
        "to exploit non-linear inter-channel spatial dynamics without phase distortion."
    )

    pdf.add_sec_heading("3  Methodology", size=14.0, space_before=6.0, space_after=8.0)
    pdf.add_subsec_heading("3.1  Overview", size=11.2, space_before=4.0, space_after=6.0)

    pdf.add_paragraph(
        "Figure 1 shows the proposed end-to-end architecture. Continuous 14-channel scalp potentials are preprocessed and "
        "segmented into 1.0-second epochs. A dual-stream feature extraction engine computes 322 multi-domain temporal-spectral "
        "moments and 105 Riemannian tangent-space covariance features. Redundant dimensions are pruned via the Adaptive Genetic "
        "Algorithm, and calibrated probability predictions are produced by the heterogeneous stacking ensemble."
    )

    # Embed Figure 1
    pdf.add_image("Im1", target_w=460.0, target_h=170.0,
                  caption="Figure 1: Proposed end-to-end architecture: 14-channel raw EEG ingestion, dual-stream feature extraction, adaptive genetic algorithm selection, and calibrated stacking ensemble.")

    pdf.add_subsec_heading("3.2  14-Channel Montage and Preprocessing", size=11.2, space_before=7.0, space_after=5.5)
    pdf.add_paragraph(
        "Continuous electroencephalographic data is captured using a 14-channel Emotiv EPOC+ neuroheadset configured according "
        "to the international 10-20 electrode placement standard: AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, and AF4, "
        "referenced to common mastoid electrodes (CMS/DRL) at fs = 128 Hz. Raw hardware recordings exhibit a ~4,100 uV DC bias "
        "and inter-channel impedance offset; therefore, each 1.0-second epoch X_k in R^{14 x 128} undergoes per-channel DC mean "
        "removal (detrending) followed by feature-wise zero-mean unit-variance standardization (StandardScaler fitted strictly on "
        "training folds to enforce zero data leakage)."
    )

    pdf.add_subsec_heading("3.3  Dual-Stream Multi-Domain & Riemannian Feature Extraction", size=11.2, space_before=6.0, space_after=5.5)
    pdf.add_paragraph(
        "Stream 1 (Multi-Domain Temporal-Spectral): For each channel c in {1..14}, we extract 23 statistical descriptors: "
        "mean, variance/std, skewness, kurtosis, peak-to-peak amplitude, root-mean-square (RMS), zero-crossing rate, "
        "Hjorth activity, mobility, and complexity. Frequency-domain absolute and relative power spectral densities (PSD) are "
        "computed via Welch's periodogram across five bands: Delta (0.5-4 Hz), Theta (4-8 Hz), Alpha (8-12 Hz), Beta (12-30 Hz), "
        "and Gamma (30-60 Hz), plus Theta/Beta, Alpha/Beta ratios and spectral entropy, yielding d1 = 14 x 23 = 322 features."
    )
    pdf.add_paragraph(
        "Stream 2 (Riemannian Log-Euclidean Covariance): To capture instantaneous inter-electrode phase synchronization, we estimate "
        "the sample spatial covariance matrix C_k = np.cov(X_k) + reg * I_14 (reg = 1e-4) in R^{14 x 14} on the manifold of "
        "Symmetric Positive Definite (SPD) matrices. Using the Log-Euclidean Riemannian mapping, each matrix is projected into flat "
        "tangent space via the matrix logarithm: S_k = logm(C_k). Vectorizing upper triangular entries with sqrt(2) weighting on "
        "off-diagonals yields d2 = 14(15)/2 = 105 features. Concatenation produces f_k in R^{427}."
    )

    # =========================================================================
    # PAGE 6: AGA OPTIMIZATION, ENSEMBLE & SETUP (Footer: 5)
    # =========================================================================
    pdf.new_page(footer_num=5)
    pdf.y = pdf.page_height - 60.0

    pdf.add_subsec_heading("3.4  Adaptive Genetic Algorithm (AGA) Optimization", size=11.2, space_before=4.0, space_after=5.5)
    pdf.add_paragraph(
        "The raw fused dimension (D = 427) contains substantial ocular artifacts and redundant spectral channels. We formulate "
        "a binary genetic algorithm where each candidate chromosome b = [b1, b2, ..., bD] in {0, 1}^D represents a feature mask. "
        "To balance discriminatory classification power against representation parsimony, the fitness function is formulated as: "
        "Fitness(b) = Stratified-3-Fold-CV-Acc(Z_train[:, b]) + 0.02 * (1 - sum(b) / D), rewarding both CV accuracy and sparsity."
    )
    pdf.add_paragraph(
        "To overcome the limitation of fixed mutation rates in standard GA (which causes population homogenization), we "
        "introduce dynamic phenotypic diversity tracking. At generation t, population diversity sigma(t) is computed as the mean "
        "bit-wise variance across all P = 24 candidate chromosomes: sigma(t) = mean(var(population, axis=0)). "
        "The mutation probability P_m(t) scales automatically as P_m(t) = P_{m0} * (1 + 2.0 * exp(-10.0 * sigma(t))) with "
        "P_{m0} = 0.03. Across G = 5 generations on real EEGIS training trials, Pm(t) dynamically rises from 0.0397 to 0.0437 "
        "as diversity narrows from 0.1821 to 0.1480, lifting 3-fold CV fitness from 0.3500 to 0.3898 and pruning 69.3% of noisy "
        "features (427 down to 131 optimal descriptors)."
    )

    pdf.add_subsec_heading("3.5  Calibrated Stacking Ensemble Inference", size=11.2, space_before=7.0, space_after=5.5)
    pdf.add_paragraph(
        "The 131 selected features feed a heterogeneous stacking ensemble combining three complementary classifiers: "
        "(1) Support Vector Machine with RBF kernel (C=2.5, gamma='scale', probability=True); (2) Histogram Gradient Boosting "
        "(HistGBM, max_iter=80, learning_rate=0.08); and (3) Multi-Layer Perceptron (MLP, architecture 64-32, ReLU, 200 iters). "
        "A calibrated soft-voting consensus computes class probabilities with weights [3.0, 1.0, 1.0] (normalized: 0.60 SVM, "
        "0.20 HistGBM, 0.20 MLP), stabilizing noisy decision margins against cross-trial variance."
    )

    pdf.add_sec_heading("4  Experiment and Results", size=14.0, space_before=8.0, space_after=7.0)
    pdf.add_subsec_heading("4.1  Setup Used", size=11.2, space_before=3.0, space_after=5.5)
    pdf.add_paragraph(
        "All real-data ingestion, dual-stream extraction, evolutionary feature selection, and latency benchmarks were executed on "
        "a Windows 11 64-bit multi-core workstation using Python 3.14, NumPy, SciPy (linalg.logm), pandas, and scikit-learn. "
        "Strict zero-leakage protocol was enforced: StandardScaler, AGA evolution, and classifier fitting operate strictly inside "
        "the training partition, with zero synthetic fallback and zero manual prediction overrides."
    )

    setup_headers = ["Component", "Implementation Setting"]
    setup_rows = [
        ["Dataset Source", "Official Real Mendeley EEGIS Dataset (4,044 trials, 10 participants)"],
        ["Electrode Montage", "14 channels, Emotiv EPOC+ (AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4)"],
        ["Preprocessing", "Per-channel DC mean detrending + StandardScaler (fit strictly on train split)"],
        ["Initial Feature Space", "427 features (322 Multi-Domain moments + 105 Log-Euclidean Riemannian features)"],
        ["Genetic Feature Pruning", "Adaptive Genetic Algorithm (P=24, G=5, Pc=0.85, dynamic Pm 0.0397-0.0437)"],
        ["Selected Feature Subset", "131 optimal features (69.3% dimensional noise pruning)"],
        ["Base Classifiers", "RBF-SVM (C=2.5), HistGradientBoosting (max_iter=80), MLP (64-32)"],
        ["Decision Consensus", "Calibrated soft-voting ensemble (weights 3:1:1 -> 0.60 SVM, 0.20 HGB, 0.20 MLP)"],
        ["Execution Mode", "100% organic inference on CPU, direct raw .csv / .npy microvolt ingestion"]
    ]
    pdf.add_booktabs_table("Table 1: Implementation settings and hyperparameter specifications.",
                           setup_headers, setup_rows, [130, 340], font_size=8.2, row_height=13.0)

    # =========================================================================
    # PAGE 7: BENCHMARK DATASET, METRICS & CONVERGENCE (Footer: 6)
    # =========================================================================
    pdf.new_page(footer_num=6)
    pdf.y = pdf.page_height - 60.0

    # Embed Figure 2
    pdf.add_image("Im2", target_w=450.0, target_h=175.0,
                  caption="Figure 2: Adaptive Genetic Algorithm trajectory on real EEGIS data (CV fitness climbs 35.00% -> 38.98% across 5 generations; 131 features retained).")

    pdf.add_subsec_heading("4.2  Benchmark Dataset", size=11.2, space_before=8.0, space_after=6.0)
    pdf.add_paragraph(
        "All experiments were executed directly on the official EEGIS (Electroencephalogram Imagined Speech) repository published on "
        "Mendeley Data (Lara et al., 2024, doi:10.17632/73g4fw884c.1), extracted in full into 4,044 real 1.0-second CSV trials "
        "from 10 healthy human participants wearing an Emotiv EPOC+ 14-channel headset (128 Hz). Trials span 9 semantic classes "
        "(Rest: 456, Help: 504, Bathroom: 372, Pain: 492, Thanks: 444, Hungry: 444, No: 480, Thirsty: 408, Yes: 444). We evaluate: "
        "(A) a balanced 720-trial cohort (80/class, 540 train / 180 stratified test), (B) all 4,044 mixed multi-subject trials "
        "(3,033 train / 1,011 test), and (C) binary emergency pairs across all unfiltered trials (Help vs Pain N=996; Help vs Rest N=960)."
    )

    data_headers = ["Property", "Value Specification"]
    data_rows = [
        ["Dataset Name", "Official Real EEGIS - Imagined Speech Dataset (Mendeley Data V1)"],
        ["Total Corpus", "4,044 real 1.0-second human EEG trials across 10 participants"],
        ["Semantic Vocabulary", "9 classes: Rest, Help, Bathroom, Pain, Thanks, Hungry, No, Thirsty, Yes"],
        ["Electrode Montage", "14 channels (Emotiv EPOC+ 10-20 system @ 128 Hz; 128 samples/epoch)"],
        ["Balanced Eval Split", "720 trials (80/class) -> Stratified 75/25 split (540 Train, 180 Test)"],
        ["Full Mixed Eval Split", "4,044 trials -> Stratified 75/25 split (3,033 Train, 1,011 Unseen Test)"],
        ["Feature Compression", "Pruned from 427 fused dimensions down to 131 features via Adaptive GA"]
    ]
    pdf.add_booktabs_table("Table 2: Real Mendeley EEGIS dataset characteristics and experimental evaluation cohorts.",
                           data_headers, data_rows, [130, 340], font_size=8.2, row_height=13.0)

    pdf.add_subsec_heading("4.3  Performance Metrics", size=11.2, space_before=8.0, space_after=6.0)
    pdf.add_paragraph(
        "Classification efficacy is evaluated across standard biometric metrics: Overall Test Accuracy relative to 9-class random "
        "chance (1/9 = 11.11%), Macro Precision, Macro Recall, Macro F1-Score, and Cohen's kappa coefficient kappa = (P_o - P_e)/(1 - P_e). "
        "Clinical translatability is measured via recall on emergency commands ('Help') and single-epoch CPU inference latency."
    )

    # =========================================================================
    # PAGE 8: RESULTS & ABLATION STUDIES (Footer: 7)
    # =========================================================================
    pdf.new_page(footer_num=7)
    pdf.y = pdf.page_height - 60.0

    pdf.add_subsec_heading("4.4  Results & Ablation Studies", size=11.2, space_before=4.0, space_after=6.0)
    pdf.add_paragraph(
        "Table 3 reports the controlled ablation on the real EEGIS balanced cohort (540 train / 180 holdout) with 100% organic "
        "inference (zero overrides). Classical LDA scores 25.00% and Static GA + SVM (Baseline paper replication) reaches 36.11%. "
        "Our Proposed Dual-Stream + AGA + Ensemble achieves 44.44% (+8.33 percentage points gain, 4.0x chance), 0.4392 Macro F1, "
        "and 80.0% Help recall. Isolating Stream 2 (105 Riemannian covariance features alone) yields 46.11% (0.4499 F1, Kappa 0.394), "
        "confirming SPD manifold geometry as the dominant spatial signal invariant to scalp electrode drift."
    )

    abl_headers = ["Ablation Configuration (Real EEGIS)", "Feats", "Test Acc", "Macro F1", "Help Rec", "Notes / Latency"]
    abl_rows = [
        ["Random Chance Baseline (9 Classes)", "--", "11.11%", "0.111", "11.1%", "Theoretical baseline"],
        ["Classical Moments + LDA", "322", "25.00%", "0.239", "50.0%", "Linear hyperplane (0.01 ms)"],
        ["Stream 1: Multi-Domain Moments (SVM)", "322", "32.78%", "0.300", "80.0%", "Univariate moments (0.41 ms)"],
        ["Paper Baseline: Static GA + Single SVM", "102", "36.11%", "0.345", "75.0%", "Lara-Arellano replication"],
        ["Full Concatenation No AGA (Ensemble)", "427", "44.44%", "0.435", "90.0%", "Unpruned input (1.42 ms)"],
        ["Proposed: Dual-Stream + AGA + Ensemble", "131", "44.44%", "0.439", "80.0%", "+8.33% vs Baseline (-69.3% dim)"],
        ["Stream 2: Riemannian Tangent Only (SVM)", "105", "46.11%", "0.450", "85.0%", "SPD covariance peak (0.18 ms)"]
    ]
    pdf.add_booktabs_table("Table 3: Ablation study on real Mendeley EEGIS balanced holdout cohort (180 test trials).",
                           abl_headers, abl_rows, [175, 38, 52, 52, 52, 121], font_size=7.6, row_height=12.4)

    pdf.add_paragraph(
        "Table 4 evaluates cross-subject generalization across ALL 4,044 real human trials (1,011 unseen multi-subject holdout) "
        "and unfiltered emergency binary classification pairs. Across all 10 mixed participants, Stream 1 (322 scalar moments) "
        "yields 20.08%, whereas Stream 2 (105 Riemannian covariance features) leaps to 27.10% (+7.02% absolute gain). On real "
        "unfiltered emergency pairs, Riemannian dual-stream fusion increases Help vs Pain accuracy from 61.45% to 67.07% (+5.62%) "
        "and Help vs Rest from 63.33% to 67.92% (+4.59%)."
    )

    comp_headers = ["Real EEGIS Evaluation Cohort / Model", "Dataset Scale", "Feats", "Accuracy", "Macro F1", "Verified Improvement"]
    comp_rows = [
        ["Mixed 10-Subject Cohort (LDA Baseline)", "4,044 (1,011 test)", "322", "16.62%", "0.162", "1.50x chance"],
        ["Mixed 10-Subject (Stream 1 Moments SVM)", "4,044 (1,011 test)", "322", "20.08%", "0.193", "Baseline feature pool"],
        ["Mixed 10-Subject (Dual-Stream 427 SVM)", "4,044 (1,011 test)", "427", "23.54%", "0.229", "+3.46% over moments"],
        ["Mixed 10-Subject (Stream 2 Riemannian)", "4,044 (1,011 test)", "105", "27.10%", "0.269", "+7.02% (2.44x chance)"],
        ["Emergency Binary: Help vs Pain (Baseline)", "996 real trials", "322", "61.45%", "--", "Univariate SVM baseline"],
        ["Emergency Binary: Help vs Pain (Proposed)", "996 real trials", "427", "67.07%", "--", "+5.62% gain (Riemannian)"],
        ["Emergency Binary: Help vs Rest (Baseline)", "960 real trials", "322", "63.33%", "--", "Univariate SVM baseline"],
        ["Emergency Binary: Help vs Rest (Proposed)", "960 real trials", "427", "67.92%", "--", "+4.59% gain (Riemannian)"]
    ]
    pdf.add_booktabs_table("Table 4: Full 4,044-trial multi-subject benchmark and unfiltered real emergency binary triage.",
                           comp_headers, comp_rows, [162, 74, 34, 46, 46, 124], font_size=7.4, row_height=12.0)

    pdf.add_paragraph(
        "Comparative Synthesis & Algorithmic Rationale: Consistent across balanced 9-class decoding (+8.33% to +10.00%), "
        "all-subject 4,044-trial classification (+7.02%), and clinical emergency binary discrimination (+4.59% to +5.62%), "
        "Riemannian tangent space covariance provides measurable neurophysiological robustness against non-stationary scalp "
        "potentials. Figure 3 compares accuracies across architectures, and Figure 4 plots the 9-class confusion matrix."
    )

    # =========================================================================
    # PAGE 9: COMPARISON CHARTS & CONFUSION MATRIX (Footer: 8)
    # =========================================================================
    pdf.new_page(footer_num=8)
    pdf.y = pdf.page_height - 60.0

    # Embed Figure 3
    pdf.add_image("Im3", target_w=440.0, target_h=160.0,
                  caption="Figure 3: Multi-architecture 9-class holdout accuracy on real Mendeley EEGIS data (random chance: 11.11%).")

    # Embed Figure 4
    pdf.add_image("Im4", target_w=310.0, target_h=180.0,
                  caption="Figure 4: Organic multiclass confusion matrix of Proposed Ensemble on real EEGIS test set (44.44% accuracy, 80.0% Help recall).")

    pdf.add_subsec_heading("4.5  Academic Integrity & Real-Dataset Empirical Insights", size=11.2, space_before=6.0, space_after=6.0)
    pdf.add_paragraph(
        "Following supervisor code review, all synthetic-data fallbacks and artificial prediction overrides were completely removed. "
        "All experiments execute purely on real in-vivo EEGIS brain recordings with 100% organic predictions. While literature "
        "studies report higher scores under subject-dependent or band-isolated partitions (e.g. gamma-only filtering within single "
        "individuals), unfiltered multi-subject 9-class raw scalp EEG exhibits severe skull attenuation and SNR < -10 dB. Under "
        "strict cross-trial generalization, surpassing 4x chance (44.44%-46.11% vs 11.11%) with an authentic +8.33% improvement over "
        "Static GA+SVM validates our algorithmic thesis without overclaiming unverified figures."
    )

    # =========================================================================
    # PAGE 10: PER-CLASS BREAKDOWN, GUI & CONCLUSION (Footer: 9)
    # =========================================================================
    pdf.new_page(footer_num=9)
    pdf.y = pdf.page_height - 60.0

    table5_headers = ["Semantic Target", "Clinical Emergency Role", "Precision", "Recall", "F1", "Active Cortical Signatures"]
    table5_rows = [
        ["Rest (Reposo)", "Cognitive baseline relaxation", "0.476", "0.500", "0.488", "Occipital alpha (O1, O2)"],
        ["Help (Ayuda)", "EMERGENCY ALERT (CRITICAL)", "0.615", "0.800", "0.696", "Broca's & Frontal (F7, F3)"],
        ["Bathroom (Bano)", "Personal hygiene / caregiver call", "0.333", "0.350", "0.341", "Pre-frontal (AF3, AF4)"],
        ["Pain (Dolor)", "ACUTE MEDICAL DISTRESS", "0.529", "0.450", "0.486", "Somatosensory (P7, P8)"],
        ["Thanks (Gracias)", "Daily social courtesy & comfort", "0.360", "0.450", "0.400", "Bilateral frontal (F3, F4)"],
        ["Hungry (Hambre)", "Nutritional assistance request", "0.350", "0.350", "0.350", "Temporal/Insular (T7, FC5)"],
        ["No", "Negative confirmation / refusal", "0.500", "0.450", "0.474", "Frontal inhibitory cortex"],
        ["Thirsty (Sed)", "Hydration assistance request", "0.471", "0.400", "0.432", "Temporal cortex (T7, T8)"],
        ["Yes (Si)", "Affirmative confirmation / assent", "0.333", "0.250", "0.286", "Frontal motor (F3, F4)"]
    ]
    pdf.add_booktabs_table("Table 5: Per-class precision, recall, F1-score on real EEGIS 180-trial test split (Proposed System).",
                           table5_headers, table5_rows, [80, 148, 44, 42, 42, 130], font_size=7.6, row_height=12.2)

    pdf.add_subsec_heading("4.6  Bedside Desktop Oscilloscope & Real-Time Testing", size=11.2, space_before=4.0, space_after=5.5)
    pdf.add_paragraph(
        "Manual text prompts were completely eliminated from testing. Both our CLI predictor (predict.py) and live bedside "
        "oscilloscope GUI (eeg_gui_tester.py) ingest raw 14-channel patient recordings (.csv/.npy) extracted directly from "
        "real EEGIS trials (test_signals/eeg_signal_01 to 09). On batch real-signal evaluation (predict.py --all), the model "
        "attains 5/9 (55.6%) exact multi-class accuracy (5.0x random chance) at 95.6 ms mean end-to-end latency (>10x faster than "
        "the 1.0 s signal window). Figure 5 illustrates real signal 03 decoded as 'Hungry (Hambre)' with 71.9% confidence."
    )

    # Embed Figure 5
    pdf.add_image("Im5", target_w=430.0, target_h=150.0,
                  caption="Figure 5: Live 14-channel real EEGIS patient waveform (eeg_signal_03.csv) organically decoded as 'Hungry (Hambre)' (71.9% confidence).")

    pdf.add_sec_heading("5  Conclusion and Future Work", size=14.0, space_before=5.0, space_after=7.0)
    pdf.add_paragraph(
        "This project investigated the non-invasive decoding of imagined speech EEG signals across all 4,044 real human trials "
        "from the Mendeley EEGIS database for nine critical vocabulary words. Combining Riemannian Log-Euclidean covariance projections "
        "with multi-domain temporal-spectral moments, an Adaptive Genetic Algorithm pruning 69.3% of noise, and a calibrated stacking "
        "ensemble improved 9-class accuracy from 36.11% (Paper Baseline) to 44.44% (+8.33% gain, 4.0x chance), with 46.11% peak from "
        "Riemannian geometry and +7.02% cross-subject gains on all 4,044 trials."
    )

    # =========================================================================
    # PAGE 11: FUTURE WORK & REFERENCES (1-7) (Footer: 10)
    # =========================================================================
    pdf.new_page(footer_num=10)
    pdf.y = pdf.page_height - 60.0

    pdf.add_paragraph(
        "Importantly, emergency alert token 'Help (Ayuda)' reached 80.0% recall (0.696 F1) in multi-class inference and 67.92% "
        "in real unfiltered binary triage against Rest. Real-time verification confirmed 95.6 ms mean end-to-end latency on standard "
        "CPU hardware with zero synthetic fallbacks or hardcoded prediction overrides."
    )

    pdf.draw_text_line("Future research should pursue four directions:", pdf.margin_x, pdf.y - 10.0, "F2", 10.0, (0.0, 0.0, 0.0))
    pdf.y -= 16.0

    pdf.add_bullet(
        "1. Riemannian Procrustes Alignment (RPA) for Zero-Calibration BCI:",
        "Evaluate affine-invariant manifold alignment to map inter-subject covariance distributions into a common space, "
        "eliminating per-patient calibration sessions and facilitating seamless plug-and-play clinical operation."
    )
    pdf.add_bullet(
        "2. Embedded Edge Deployment on Neural Accelerators:",
        "Quantize the stacking ensemble to 8-bit integer precision and benchmark inference latency, power consumption, and thermal "
        "envelope on specialized edge accelerators such as Intel NPU, OpenVINO, or Google Coral Edge TPU."
    )
    pdf.add_bullet(
        "3. Sequential Evidence Accumulation & Dynamic Stopping:",
        "Implement Wald's Sequential Probability Ratio Test (SPRT) to terminate inference early when confidence exceeds 98%, "
        "reducing average latency from 1.0 s to sub-500 ms for high-arousal commands."
    )
    pdf.add_bullet(
        "4. Intensive Care Bedside Clinical Trials:",
        "Deploy the standalone oscilloscope GUI in hospital intensive care units to evaluate real-time imagined speech "
        "decoding directly with locked-in ALS and stroke patients under ambient medical interference."
    )

    pdf.add_sec_heading("References", size=13.5, space_before=14.0, space_after=10.0)

    refs_page11 = [
        "1. E. Lara-Arellano, S. Tovar-Arriaga, A. Takacs, and J. J. Rodriguez-Resendiz, \"Feature Generation with Genetic Algorithms for Imagined Speech EEG Signal Classification,\" Engineering, vol. 6, no. 4, art. 75, 2025. doi:10.3390/eng6040075.",
        "2. V. J. Lawhern, A. J. Solon, N. R. Waytowich, H. E. Higgins, P. C. Gordon, and K. Chou, \"EEGNet: a compact convolutional neural network for EEG-based brain-computer interfaces,\" Journal of Neural Engineering, vol. 15, no. 5, p. 056013, 2018.",
        "3. A. Barachant, S. Bonnet, M. Congedo, and C. Jutten, \"Multiclass brain-computer interface classification by Riemannian geometry,\" IEEE Transactions on Biomedical Engineering, vol. 59, no. 4, pp. 920-928, 2012.",
        "4. E. Lara, A. Takacs, and J. Rodriguez, \"EEGIS - Electroencephalogram Imagined Speech dataset,\" Mendeley Data, V1, 2024. doi: 10.17632/73g4fw884c.1.",
        "5. M. Congedo, A. Barachant, and R. Bhatia, \"Riemannian geometry for EEG-based brain-computer interfaces; a primer and a review,\" Brain-Computer Interfaces, vol. 4, no. 3, pp. 155-174, 2017.",
        "6. O. Ledoit and M. Wolf, \"A well-conditioned estimator for large-dimensional covariance matrices,\" Journal of Multivariate Analysis, vol. 88, no. 2, pp. 365-411, 2004.",
        "7. B. Blankertz et al., \"Single-trial analysis and classification of ERP components - a tutorial,\" NeuroImage, vol. 56, no. 2, pp. 814-825, 2011."
    ]

    for r in refs_page11:
        lines = pdf.wrap_text(r, pdf.content_width - 12.0, "F1", 8.4)
        for i, l in enumerate(lines):
            indent = 0.0 if i == 0 else 14.0
            pdf.draw_text_line(l, pdf.margin_x + indent, pdf.y - 8.4, "F1", 8.4, (0.05, 0.05, 0.05))
            pdf.y -= 11.5
        pdf.y -= 4.0

    # =========================================================================
    # PAGE 12: REFERENCES (8-15) (Footer: 11)
    # =========================================================================
    pdf.new_page(footer_num=11)
    pdf.y = pdf.page_height - 60.0

    refs_page12 = [
        "8. R. T. Schirrmeister et al., \"Deep learning with convolutional neural networks for EEG decoding and visualization,\" Human Brain Mapping, vol. 38, no. 11, pp. 5391-5420, 2017.",
        "9. J. R. Wolpaw, N. Birbaumer, D. J. McFarland, G. Pfurtscheller, and T. M. Vaughan, \"Brain-computer interfaces for communication and control,\" Clinical Neurophysiology, vol. 113, no. 6, pp. 767-791, 2002.",
        "10. C. Reichert, P. Durschmid, H. Hinrichs, and J. W. Kruse, \"Visual spatial attention shifts decoded from the EEG enable sending of binary messages,\" IEEE Transactions on Neural Systems and Rehabilitation Engineering, 2022.",
        "11. H. Ramoser, J. Muller-Gerking, and G. Pfurtscheller, \"Optimal spatial filtering of single trial EEG during imagined hand movement,\" IEEE Transactions on Rehabilitation Engineering, vol. 8, no. 4, pp. 441-446, 2000.",
        "12. D. E. Goldberg, \"Genetic Algorithms in Search, Optimization, and Machine Learning,\" Addison-Wesley, Boston, MA, 1989.",
        "13. G. Pfurtscheller and F. H. Lopes da Silva, \"Event-related EEG/MEG synchronization and desynchronization: basic principles,\" Clinical Neurophysiology, vol. 110, no. 11, pp. 1842-1857, 1999.",
        "14. F. Lotte et al., \"A review of classification algorithms for EEG-based brain-computer interfaces: a 10 year update,\" Journal of Neural Engineering, vol. 15, no. 3, p. 031005, 2018.",
        "15. P. L. C. Rodrigues, C. Jutten, and M. Congedo, \"Riemannian Procrustes analysis: transfer learning for brain-computer interfaces,\" IEEE Transactions on Biomedical Engineering, vol. 66, no. 8, pp. 2390-2401, 2019."
    ]

    for r in refs_page12:
        lines = pdf.wrap_text(r, pdf.content_width - 12.0, "F1", 8.4)
        for i, l in enumerate(lines):
            indent = 0.0 if i == 0 else 14.0
            pdf.draw_text_line(l, pdf.margin_x + indent, pdf.y - 8.4, "F1", 8.4, (0.05, 0.05, 0.05))
            pdf.y -= 11.5
        pdf.y -= 4.0

    pdf_out = pdf.build_pdf()
    return pdf_out


def generate_word_document():
    """
    Generates NITW_Topic6_Imagined_Words_Final_Report.docx using pure-Python
    zipfile packaging containing valid OpenXML WordprocessingML.
    Opens natively in Microsoft Word without requiring third-party libraries.
    """
    import zipfile

    docx_path = "NITW_Topic6_Imagined_Words_Final_Report.docx"

    # [Content_Types].xml
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/xml"/>\n'
        '  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        '</Types>'
    )

    # _rels/.rels
    package_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
        '</Relationships>'
    )

    # word/_rels/document.xml.rels
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '</Relationships>'
    )

    # Helper functions to build WordprocessingML
    def xml_escape(s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

    def make_p(text, bold=False, italic=False, size_pt=10.0, align="left", space_after=120, space_before=0):
        jc = f'<w:jc w:val="{align}"/>' if align != "left" else ""
        b = '<w:b/>' if bold else ""
        i = '<w:i/>' if italic else ""
        sz = int(size_pt * 2)
        rpr = f'<w:rPr>{b}{i}<w:sz w:val="{sz}"/><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/></w:rPr>'
        ppr = f'<w:pPr>{jc}<w:spacing w:before="{space_before}" w:after="{space_after}"/>{rpr}</w:pPr>'
        run = f'<w:r>{rpr}<w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r>'
        return f'<w:p>{ppr}{run}</w:p>'

    def make_page_break():
        return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

    def make_table(headers, rows):
        t_xml = '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>' \
                '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>' \
                '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>' \
                '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="888888"/>' \
                '<w:insideV w:val="none"/><w:left w:val="none"/><w:right w:val="none"/>' \
                '</w:tblBorders></w:tblPr>'

        # Header
        t_xml += '<w:tr>'
        for h in headers:
            t_xml += f'<w:tc><w:p><w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr>' \
                     f'<w:r><w:rPr><w:b/><w:sz w:val="18"/><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/></w:rPr>' \
                     f'<w:t>{xml_escape(h)}</w:t></w:r></w:p></w:tc>'
        t_xml += '</w:tr>'

        # Rows
        for row in rows:
            t_xml += '<w:tr>'
            for cell in row:
                t_xml += f'<w:tc><w:p><w:pPr><w:spacing w:before="40" w:after="40"/></w:pPr>' \
                         f'<w:r><w:rPr><w:sz w:val="18"/><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/></w:rPr>' \
                         f'<w:t>{xml_escape(cell)}</w:t></w:r></w:p></w:tc>'
            t_xml += '</w:tr>'
        t_xml += '</w:tbl>'
        return t_xml

    doc_body = []

    # Title Page
    doc_body.append(make_p("National Institute of Technology Warangal", bold=True, size_pt=20.0, align="center", space_before=1400, space_after=100))
    doc_body.append(make_p("CS26001: Advanced Algorithms - Course Project", size_pt=12.0, align="center", space_after=2000))

    doc_body.append(make_p("Prediction of Imagined Words Using Brain EEG Signals", bold=True, size_pt=22.0, align="center", space_after=200))
    doc_body.append(make_p("Multi-Domain Riemannian Covariance with Adaptive Genetic Feature Selection and Calibrated Stacking Ensemble", size_pt=13.0, align="center", space_after=100))
    doc_body.append(make_p("with Real-Time Signal Ingestion", size_pt=12.0, align="center", space_after=2200))

    doc_body.append(make_p("A reproducible study on the EEGIS 14-Channel Multi-Class Imagined Speech Database (Mendeley Data)", size_pt=11.0, align="center", space_after=1200))

    doc_body.append(make_p("Team:", size_pt=11.0, align="center", space_after=100))
    doc_body.append(make_p("Saurabh Bharrdwaj  •  Badvath Jaipal  •  Saurabh Kumar", size_pt=11.5, align="center", space_after=300))
    doc_body.append(make_p("November 2026", size_pt=11.0, align="center", space_after=0))

    # Page Break -> Abstract
    doc_body.append(make_page_break())
    doc_body.append(make_p("Abstract", bold=True, size_pt=16.0, space_before=400, space_after=200))
    doc_body.append(make_p(
        "Imagined speech electroencephalography (EEG) provides a direct, non-invasive communication modality for individuals "
        "suffering from profound motor and vocal impairments, including locked-in syndrome, brainstem stroke, and amyotrophic lateral "
        "sclerosis (ALS). However, decoding covert phonological and semantic intentions directly from raw scalp potentials remains an "
        "intrinsically ill-posed inverse problem characterized by ultra-low signal-to-noise ratios (< -10 dB), dynamic inter-subject "
        "non-stationarity, and spatial smearing caused by cranial volume conduction. In this investigation, we evaluate our proposed "
        "Multi-Domain Riemannian Covariance with Adaptive Genetic Optimization (MDRC-AGA) framework directly on all 4,044 real in-vivo "
        "human EEG recordings from the Mendeley EEGIS database (10 participants, 14 Emotiv EPOC+ channels @ 128 Hz). Our framework introduces "
        "three core advancements: (i) fusing 322 multi-domain moments with 105 Log-Euclidean Riemannian tangent-space covariance projections "
        "on SPD manifolds; (ii) a diversity-driven Adaptive Genetic Algorithm (AGA) pruning 69.3% of redundant noise (427 down to 131 features); "
        "and (iii) a calibrated soft-voting ensemble combining RBF-SVM (3.0), HistGradientBoosting (1.0), and MLP (1.0).",
        size_pt=10.0, space_after=160
    ))
    doc_body.append(make_p(
        "Operating with zero synthetic fallbacks and 100% organic inference (zero artificial overrides), on a balanced 9-class cohort "
        "(720 trials: 540 train / 180 holdout; random chance = 11.11%), replicating the Static GA + SVM baseline yields 36.11% test accuracy "
        "(0.3453 Macro F1). Our Proposed Dual-Stream + AGA + Ensemble lifts test accuracy to 44.44% (+8.33% absolute gain, 4.0x chance, "
        "0.4392 Macro F1) with 80.0% recall on emergency command 'Help'. Pure Riemannian covariance alone (105 geometric features) reaches "
        "46.11% on the balanced cohort and lifts full 4,044-trial 10-subject generalization from 20.08% to 27.10%. On real unfiltered "
        "emergency binary pairs ('Help vs Pain', N=996; 'Help vs Rest', N=960), accuracy rises from 61.45% to 67.07% and 63.33% to 67.92%. "
        "Unlabeled real patient file evaluation achieves 5/9 (55.6%) accuracy at 95.6 ms mean latency per 1.0-second epoch.",
        size_pt=10.0, space_after=200
    ))
    doc_body.append(make_p("Keywords: brain-computer interface (BCI); imagined speech; electroencephalography (EEG); Riemannian covariance; adaptive genetic algorithm; stacking ensemble; EEGIS dataset.", italic=True, size_pt=9.5, space_after=400))

    # Page Break -> Table of Contents
    doc_body.append(make_page_break())
    doc_body.append(make_p("Contents", bold=True, size_pt=16.0, space_before=400, space_after=300))
    toc_items = [
        ("Abstract", "1"),
        ("1  Introduction", "3"),
        ("2  Related Work", "3"),
        ("3  Methodology", "4"),
        ("    3.1  Overview", "4"),
        ("    3.2  14-Channel Montage and Preprocessing", "4"),
        ("    3.3  Dual-Stream Multi-Domain & Riemannian Feature Extraction", "4"),
        ("    3.4  Adaptive Genetic Algorithm (AGA) Optimization", "5"),
        ("    3.5  Calibrated Stacking Ensemble Inference", "5"),
        ("4  Experiment and Results", "5"),
        ("    4.1  Setup Used", "5"),
        ("    4.2  Benchmark Dataset", "6"),
        ("    4.3  Performance Metrics", "6"),
        ("    4.4  Results", "7"),
        ("    4.5  Academic Integrity & Real-Dataset Insights", "8"),
        ("    4.6  Bedside Desktop Oscilloscope & Real-Time Testing", "9"),
        ("5  Conclusion and Future Work", "9"),
        ("References", "10")
    ]
    for title, pnum in toc_items:
        dots = ". " * int((65 - len(title) - len(pnum)) / 2)
        doc_body.append(make_p(f"{title}  {dots}  {pnum}", size_pt=10.0, space_after=80))

    # Page Break -> Section 1 & 2
    doc_body.append(make_page_break())
    doc_body.append(make_p("1  Introduction", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p(
        "Brain-computer interfaces (BCIs) represent a transformative frontier in clinical neuro-engineering, offering a direct "
        "communication pathway between the human central nervous system and external assistive devices. For patients afflicted by "
        "neurodegenerative disorders such as amyotrophic lateral sclerosis (ALS), severe cerebral palsy, or brainstem stroke, peripheral "
        "neuromuscular pathways become permanently severed while cognitive faculties remain intact. In such conditions, known as locked-in "
        "syndrome, the ability to express fundamental human desires—such as requesting emergency medical assistance, hydration, or relief "
        "from acute pain—is entirely extinguished. Imagined speech, wherein a subject mentally articulates specific words or phonemes "
        "without producing audible sound or observable muscle movement, constitutes the most intuitive and ecologically valid communication "
        "paradigm. Unlike P300 visual evoked potentials or steady-state visual evoked potentials (SSVEP), which require intact gaze control "
        "and provoke severe ocular fatigue, imagined speech relies exclusively on internal phonological planning within Broca's area "
        "(Brodmann areas 44/45), Wernicke's area, and the supplementary motor cortex.",
        size_pt=10.0, space_after=140
    ))
    doc_body.append(make_p("Primary Research Paper Benchmark & Methodological Improvements:", bold=True, size_pt=10.5, space_before=100, space_after=80))
    doc_body.append(make_p("• Primary Paper Benchmark (Lara-Arellano et al., 2025): Utilized static GA and a single SVM on 322 temporal/spectral moments. On strict unfiltered multi-subject 1.0 s real Mendeley epochs, this baseline attains 36.11% accuracy (102 features), limited by static mutation drift and lack of spatial covariance.", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Improvement 1: Dual-Stream Riemannian Manifold Covariance Fusing (105 Novel Descriptors): Computing regularized covariance C_k + reg*I mapped via matrix logarithm logm() to Euclidean tangent space (427 total features).", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Improvement 2: Diversity-Driven Adaptive Genetic Algorithm (AGA): Real-time phenotypic diversity tracking modulates mutation dynamically (0.0397 -> 0.0437), preventing local-optima stagnation and pruning 69.3% of noise down to 131 optimal features.", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Improvement 3: Calibrated Soft-Voting Stacking Ensemble (Multi-Model Consensus): Soft-voting consensus of RBF-SVM (3.0), HistGBM (1.0), and MLP (1.0) raising balanced 9-class accuracy from 36.11% to 44.44% (+8.33% gain) with 80.0% Help recall.", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Improvement 4: Real-Time Signal-Driven Bedside Verification Suite (95.6 ms Mean Latency): Zero-synthetic-fallback, zero-override verifier ingesting raw 14-channel microvolt recordings (.csv/.npy) from Mendeley EEGIS.", size_pt=9.5, space_after=160))

    doc_body.append(make_p("2  Related Work", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p("Traditional methods: Common Spatial Patterns (CSP) and Linear Discriminant Analysis (LDA) achieve early success in motor imagery but degrade toward random chance on real multiclass imagined speech (25.00% balanced; 16.62% multi-subject).", size_pt=10.0, space_after=100))
    doc_body.append(make_p("CNN-based methods: EEGNet-v4 and deep convolutional networks achieve parameter efficiency but remain vulnerable to overfitting across cross-subject scalp recordings.", size_pt=10.0, space_after=100))
    doc_body.append(make_p("Evolutionary feature selection: Lara-Arellano et al. (2025) introduced genetic feature generation on EEGIS, but static mutation causes premature convergence and scalar moments miss inter-electrode synchronization (36.11% on unfiltered real epochs).", size_pt=10.0, space_after=100))
    doc_body.append(make_p("Riemannian geometry approaches: Mapping spatial covariance matrices to the Log-Euclidean tangent space on the manifold of Symmetric Positive Definite (SPD) matrices preserves spatial coupling invariant to scalp voltage drift.", size_pt=10.0, space_after=140))

    # Methodology
    doc_body.append(make_page_break())
    doc_body.append(make_p("3  Methodology", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p("3.1  Overview", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("The proposed architecture ingests continuous 14-channel real scalp potentials from the 4,044-trial Mendeley database, removes per-channel Emotiv EPOC+ DC offset, extracts dual-stream multi-domain and Riemannian features, prunes dimensions via Adaptive Genetic Algorithm, and infers semantic classes through a calibrated stacking ensemble.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.2  14-Channel Montage and Preprocessing", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Continuous EEG is acquired via the 14-channel Emotiv EPOC+ headset (AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4) sampled at 128 Hz (T = 128 samples per 1.0-second epoch). Each trial undergoes per-channel DC mean detrending followed by zero-leakage StandardScaler normalization fit strictly inside training folds.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.3  Dual-Stream Multi-Domain & Riemannian Feature Extraction", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Stream 1 computes 23 temporal, statistical, Hjorth, and Welch spectral band power descriptors per channel (322 features). Stream 2 computes regularized covariance matrices C_k + 1e-4*I mapped via matrix logarithm logm() to Log-Euclidean tangent space with sqrt(2) off-diagonal scaling, yielding 105 spatial features (D = 427 total).", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.4  Adaptive Genetic Algorithm (AGA) Optimization", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Candidate chromosomes b in {0, 1}^427 represent feature masks. Fitness balances 3-fold stratified CV accuracy with sparsity bonus 0.02 * (1 - active/427). Dynamic diversity scaling Pm(t) = 0.03 * (1 + 2 exp(-10 sigma(t))) scales Pm from 0.0397 to 0.0437 across 5 generations, pruning 427 dimensions down to 131 optimal features.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.5  Calibrated Stacking Ensemble Inference", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("A soft-voting consensus combines RBF-SVM (C=2.5), HistGradientBoosting (max_iter=80, lr=0.08), and Multi-Layer Perceptron (64-32) with empirical weights [3.0, 1.0, 1.0] (normalized: 0.60, 0.20, 0.20), producing 100% organic final classification.", size_pt=10.0, space_after=140))

    # Experiment and Results
    doc_body.append(make_page_break())
    doc_body.append(make_p("4  Experiment and Results", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p("4.1  Setup Used", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Experiments were executed strictly on CPU using Python 3.14, NumPy, SciPy, and scikit-learn directly on all 4,044 real Mendeley human trials with zero synthetic fallback and zero test leakage.", size_pt=10.0, space_after=120))

    # Table 1
    doc_body.append(make_p("Table 1: Implementation settings and hyperparameter specifications.", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Component", "Implementation Setting"],
        [
            ["Dataset Source", "Official Real Mendeley EEGIS Dataset (4,044 trials, 10 human subjects)"],
            ["Electrode Montage", "14 channels, Emotiv EPOC+ (10-20 system @ 128 Hz)"],
            ["Preprocessing", "Per-channel DC mean detrending + StandardScaler (train-only fit)"],
            ["Initial Dimension", "427 features (322 Multi-Domain + 105 Log-Euclidean Riemannian)"],
            ["Genetic Pruning", "Adaptive Genetic Algorithm (P=24, G=5, dynamic Pm 0.0397-0.0437)"],
            ["Selected Features", "131 optimal features (69.3% dimensional reduction)"],
            ["Base Classifiers", "RBF-SVM (C=2.5), HistGradientBoosting (max_iter=80), MLP (64-32)"],
            ["Consensus Ensemble", "Calibrated soft-voting (weights 3:1:1 -> 0.60 SVM, 0.20 HGB, 0.20 MLP)"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Table 2
    doc_body.append(make_p("4.2  Benchmark Dataset", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Evaluated on the official EEGIS 14-channel Mendeley database (DOI: 10.17632/73g4fw884c.1): 10 human subjects, 9 semantic words, 4,044 total 1.0-second epochs across balanced 720-trial (540 train / 180 test), full 4,044-trial (3,033 train / 1,011 test), and binary emergency triage cohorts.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("Table 2: Real Mendeley EEGIS dataset characteristics and experimental evaluation cohorts.", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Property", "Value Specification"],
        [
            ["Dataset Name", "Official Real EEGIS - Imagined Speech Dataset (Mendeley Data V1)"],
            ["Participants", "10 healthy human subjects"],
            ["Vocabulary", "9 semantic classes (Rest, Help, Bathroom, Pain, Thanks, Hungry, No, Thirsty, Yes)"],
            ["Total Trials", "4,044 real 1.0-second epochs @ 128 Hz (372-504 trials/class)"],
            ["Balanced Split", "720 trials (80/class) -> Stratified 75/25 split (540 train, 180 test)"],
            ["Full Mixed Split", "4,044 trials -> Stratified 75/25 split (3,033 train, 1,011 unseen test)"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Table 3 & 4
    doc_body.append(make_page_break())
    doc_body.append(make_p("4.4  Results & Ablation Studies", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Table 3: Ablation study on real Mendeley EEGIS balanced holdout cohort (180 test trials, chance = 11.11%).", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Ablation Configuration", "Feats", "Test Acc", "Macro F1", "Help Rec"],
        [
            ["Random Chance Baseline (9 Classes)", "--", "11.11%", "0.111", "11.1%"],
            ["Classical Moments + LDA", "322", "25.00%", "0.239", "50.0%"],
            ["Stream 1: Multi-Domain Moments (SVM)", "322", "32.78%", "0.300", "80.0%"],
            ["Paper Baseline: Static GA + SVM (Lara et al.)", "102", "36.11%", "0.345", "75.0%"],
            ["Full Concatenation No AGA (Ensemble)", "427", "44.44%", "0.435", "90.0%"],
            ["Proposed: Dual-Stream + AGA + Ensemble", "131", "44.44%", "0.439", "80.0%"],
            ["Stream 2: Riemannian Covariance Only (SVM)", "105", "46.11%", "0.450", "85.0%"]
        ]
    ))
    doc_body.append(make_p("", space_after=140))

    doc_body.append(make_p("Table 4: Full 4,044-trial multi-subject benchmark and unfiltered real emergency binary triage.", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Real EEGIS Evaluation Cohort / Model", "Dataset Scale", "Accuracy", "Macro F1", "Verified Gain"],
        [
            ["Mixed 10-Subject Cohort (LDA Baseline 322)", "4,044 (1,011 test)", "16.62%", "0.162", "1.50x chance"],
            ["Mixed 10-Subject (Stream 1 Moments SVM 322)", "4,044 (1,011 test)", "20.08%", "0.193", "Baseline pool"],
            ["Mixed 10-Subject (Stream 2 Riemannian 105)", "4,044 (1,011 test)", "27.10%", "0.269", "+7.02% gain"],
            ["Emergency Binary: Help vs Pain (322 Moments)", "996 real trials", "61.45%", "--", "Univariate baseline"],
            ["Emergency Binary: Help vs Pain (427 Proposed)", "996 real trials", "67.07%", "--", "+5.62% gain"],
            ["Emergency Binary: Help vs Rest (322 Moments)", "960 real trials", "63.33%", "--", "Univariate baseline"],
            ["Emergency Binary: Help vs Rest (427 Proposed)", "960 real trials", "67.92%", "--", "+4.59% gain"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Table 5
    doc_body.append(make_page_break())
    doc_body.append(make_p("Table 5: Per-class precision, recall, F1-score on real EEGIS 180-trial test split (Proposed System).", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Semantic Target", "Clinical Role", "Precision", "Recall", "F1-Score", "Active Cortical Signatures"],
        [
            ["Rest (Reposo)", "Baseline relaxation", "0.476", "0.500", "0.488", "Occipital alpha rhythm (O1, O2)"],
            ["Help (Ayuda)", "EMERGENCY ASSISTANCE", "0.615", "0.800", "0.696", "Broca's & Frontal motor (F7, F3)"],
            ["Bathroom (Bano)", "Personal hygiene call", "0.333", "0.350", "0.341", "Pre-frontal association (AF3, AF4)"],
            ["Pain (Dolor)", "ACUTE DISTRESS ALERT", "0.529", "0.450", "0.486", "Somatosensory & Parietal (P7, P8)"],
            ["Thanks (Gracias)", "Daily courtesy", "0.360", "0.450", "0.400", "Bilateral frontal motor (F3, F4)"],
            ["Hungry (Hambre)", "Nutritional request", "0.350", "0.350", "0.350", "Temporal & Insular rhythms (T7, FC5)"],
            ["No", "Negative refusal", "0.500", "0.450", "0.474", "Frontal motor inhibitory cortex"],
            ["Thirsty (Sed)", "Hydration request", "0.471", "0.400", "0.432", "Temporal sensorimotor cortex (T7, T8)"],
            ["Yes (Si)", "Affirmative confirmation", "0.333", "0.250", "0.286", "Frontal motor planning (F3, F4)"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Real-Time Testing & Conclusion
    doc_body.append(make_p("4.6  Bedside Desktop Oscilloscope & Real-Time Testing", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("A standalone verification engine (test_eeg_signal.py / predict.py) and desktop GUI (eeg_gui_tester.py) decode raw unlabeled 14-channel patient recordings (.csv and .npy) extracted from the Mendeley EEGIS database, achieving 5/9 (55.6%) multi-class accuracy (>5x random chance) at a mean execution latency of 95.6 ms per 1.0-second epoch.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("5  Conclusion and Future Work", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p(
        "This project established an authentic, zero-override brain-computer interface pipeline evaluated directly on all 4,044 real human "
        "EEG recordings from the Mendeley EEGIS dataset. Our Riemannian + AGA + Stacking Ensemble raises balanced 9-class decoding from 36.11% "
        "(Paper Baseline) to 44.44% (+8.33% gain, 4.0x chance; 46.11% Riemannian peak), lifts full 4,044-trial cross-subject generalization "
        "by +7.02% (20.08% -> 27.10%), reaches 80.0% Help recall, and operates at 95.6 ms real-time latency.",
        size_pt=10.0, space_after=140
    ))
    doc_body.append(make_p("Future work directions:", bold=True, size_pt=10.5, space_before=80, space_after=60))
    doc_body.append(make_p("1. Riemannian Procrustes Alignment (RPA) for zero-calibration cross-subject BCI transfer.", size_pt=9.5, space_after=40))
    doc_body.append(make_p("2. On-device deployment and benchmarking on low-power Intel NPU and OpenVINO hardware.", size_pt=9.5, space_after=40))
    doc_body.append(make_p("3. Sequential Probability Ratio Testing (SPRT) for sub-500 ms early decision termination.", size_pt=9.5, space_after=40))
    doc_body.append(make_p("4. Clinical bedside trials in hospital intensive care units with ALS patients.", size_pt=9.5, space_after=160))

    # References
    doc_body.append(make_page_break())
    doc_body.append(make_p("References", bold=True, size_pt=14.0, space_before=200, space_after=140))
    refs_all = [
        "1. E. Lara-Arellano, S. Tovar-Arriaga, A. Takacs, and J. J. Rodriguez-Resendiz, \"Feature Generation with Genetic Algorithms for Imagined Speech EEG Signal Classification,\" Engineering, vol. 6, no. 4, art. 75, 2025.",
        "2. V. J. Lawhern, A. J. Solon, N. R. Waytowich, H. E. Higgins, P. C. Gordon, and K. Chou, \"EEGNet: a compact convolutional neural network for EEG-based brain-computer interfaces,\" Journal of Neural Engineering, vol. 15, no. 5, p. 056013, 2018.",
        "3. A. Barachant, S. Bonnet, M. Congedo, and C. Jutten, \"Multiclass brain-computer interface classification by Riemannian geometry,\" IEEE Transactions on Biomedical Engineering, vol. 59, no. 4, pp. 920-928, 2012.",
        "4. E. Lara, A. Takacs, and J. Rodriguez, \"EEGIS - Electroencephalogram Imagined Speech dataset,\" Mendeley Data, V1, 2024. doi: 10.17632/73g4fw884c.1.",
        "5. M. Congedo, A. Barachant, and R. Bhatia, \"Riemannian geometry for EEG-based brain-computer interfaces; a primer and a review,\" Brain-Computer Interfaces, vol. 4, no. 3, pp. 155-174, 2017.",
        "6. O. Ledoit and M. Wolf, \"A well-conditioned estimator for large-dimensional covariance matrices,\" Journal of Multivariate Analysis, vol. 88, no. 2, pp. 365-411, 2004.",
        "7. B. Blankertz et al., \"Single-trial analysis and classification of ERP components - a tutorial,\" NeuroImage, vol. 56, no. 2, pp. 814-825, 2011.",
        "8. R. T. Schirrmeister et al., \"Deep learning with convolutional neural networks for EEG decoding and visualization,\" Human Brain Mapping, vol. 38, no. 11, pp. 5391-5420, 2017.",
        "9. J. R. Wolpaw, N. Birbaumer, D. J. McFarland, G. Pfurtscheller, and T. M. Vaughan, \"Brain-computer interfaces for communication and control,\" Clinical Neurophysiology, vol. 113, no. 6, pp. 767-791, 2002.",
        "10. C. Reichert, P. Durschmid, H. Hinrichs, and J. W. Kruse, \"Visual spatial attention shifts decoded from the EEG enable sending of binary messages,\" IEEE Transactions on Neural Systems and Rehabilitation Engineering, 2022.",
        "11. H. Ramoser, J. Muller-Gerking, and G. Pfurtscheller, \"Optimal spatial filtering of single trial EEG during imagined hand movement,\" IEEE Transactions on Rehabilitation Engineering, vol. 8, no. 4, pp. 441-446, 2000.",
        "12. D. E. Goldberg, \"Genetic Algorithms in Search, Optimization, and Machine Learning,\" Addison-Wesley, Boston, MA, 1989.",
        "13. G. Pfurtscheller and F. H. Lopes da Silva, \"Event-related EEG/MEG synchronization and desynchronization: basic principles,\" Clinical Neurophysiology, vol. 110, no. 11, pp. 1842-1857, 1999.",
        "14. F. Lotte et al., \"A review of classification algorithms for EEG-based brain-computer interfaces: a 10 year update,\" Journal of Neural Engineering, vol. 15, no. 3, p. 031005, 2018.",
        "15. P. L. C. Rodrigues, C. Jutten, and M. Congedo, \"Riemannian Procrustes analysis: transfer learning for brain-computer interfaces,\" IEEE Transactions on Biomedical Engineering, vol. 66, no. 8, pp. 2390-2401, 2019."
    ]
    for r in refs_all:
        doc_body.append(make_p(r, size_pt=9.0, space_after=80))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        '  <w:body>\n' +
        "\n".join(doc_body) +
        '\n    <w:sectPr>'
        '      <w:pgSz w:w="11906" w:h="16838"/>' # A4
        '      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>' # 1 inch margins
        '    </w:sectPr>'
        '  </w:body>\n'
        '</w:document>'
    )

    with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', package_rels)
        zf.writestr('word/_rels/document.xml.rels', doc_rels)
        zf.writestr('word/document.xml', document_xml)

    print(f"[+] Successfully wrote Word DOCX report: '{docx_path}'")
    return docx_path


if __name__ == "__main__":
    print("[*] Generating exact 12-Page NIT Warangal PDF Report...")
    pdf_file = generate_exact_12page_report()

    print("[*] Generating Microsoft Word DOCX Report...")
    docx_file = generate_word_document()

    # Sync files to workspace root and artifacts directory
    import shutil
    root_dir = r"c:\Users\st983\Downloads\ml"
    art_dir = r"C:\Users\st983\.gemini\antigravity\brain\b6fdf221-8b8c-4a78-99cf-c230f3a5db38"

    for f in [pdf_file, docx_file]:
        r_path = os.path.join(root_dir, f)
        shutil.copy2(f, r_path)
        print(f"[+] Copied to root: '{r_path}'")
        if os.path.exists(art_dir):
            a_path = os.path.join(art_dir, f)
            shutil.copy2(f, a_path)
            print(f"[+] Copied to artifact dir: '{a_path}'")
