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
Team: Saurabh Bharrdwaj (Lead) • Badvath Jaipal • Saurabh Kumar
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
    fig5_path = os.path.join(res_dir, "sample_prediction.png")

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
    s1 = "Primary Paper Rank-GA Baseline and Multi-Scale Riemannian Consensus (MDRC-AGA)"
    s2 = "Multi-Scale 13-Band + Speech-10 Manifold with Dual-Protocol Leakage Audit"
    s3 = "and Offline Oscilloscope Inspection"
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
        "Imagined speech electroencephalography (EEG) offers a non-invasive communication pathway for individuals "
        "with severe motor impairments such as locked-in syndrome, brainstem stroke, and ALS. Across 4,044 Mendeley "
        "EEGIS trials (337 continuous 8s blocks, 128 Hz, 14 channels, 48-sample/37.5% chunk overlap, unrecoverable "
        "participant IDs), naive chunk splits inflate kNN accuracy via within-block overlap. Excluding all 9 "
        "test_signals/ blocks (108 chunks) yields N_ref=3,936 (328 blocks). Under leakage-free Block-Disjoint Nested "
        "5-CV, all methods sit near 9-class chance (11.11%): Stage 1 Paper Rank-GA+kNN scores 10.01% (Yes/No 45.11%), "
        "True Tangent LogReg 10.72%, EEGNet Fold0 11.24%, and PCA+Calibrated RBF-SVM 11.41% (ECE=0.022)."
    )
    pdf.add_paragraph(abs_p1, "F1", 9.8, 13.8)

    abs_p2 = (
        "Under the exploratory Overlapping-Chunk 5-CV protocol matching Lara-Arellano et al. (MDPI Eng, 2025; "
        "96.0% published Yes/No), Stage 1 Paper 6B Rank-GA+kNN reaches 90.02% 9-class and 96.11% Yes/No. Stage 2 "
        "MDRC-AGA (1,695D three-scale Log-Euclidean SPD manifold: Mendeley 6B 630D + Fine 7B 735D + Speech-10 330D; "
        "MultiScaleBlockAGA; PCA-LDA + Platt-Ridge Stacker & [3:2:1:1] Consensus) reaches 91.84% (0.9180 F1, Brier "
        "0.156, ECE 0.037) on Chunk 5-CV (95.67% Yes/No) and 9.68% Stacker (ECE=0.100) / 10.14% Vote on Block-Disjoint "
        "5-CV. Sibling-excluded offline test_signals/ verify honest 0/9 generalization at 31.8 ms/epoch CPU compute."
    )
    pdf.add_paragraph(abs_p2, "F1", 9.8, 13.8)

    pdf.y -= 10.0
    kw_bold = "Keywords:"
    kw_text = " brain-computer interface (BCI); imagined speech; electroencephalography (EEG); multi-scale Riemannian covariance; adaptive genetic algorithm; manifold consensus; EEGIS dataset."
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
    pdf.add_toc_line("2  Primary Research Paper & Related Work", "3", level=1)
    pdf.add_toc_line("2.1  Primary Paper Method, GA Design & Accuracy", "3", level=2)
    pdf.add_toc_line("2.2  Comparative Related Literature", "4", level=2)
    pdf.y -= 6.0
    pdf.add_toc_line("3  Methodology", "4", level=1)
    pdf.add_toc_line("3.1  Overview", "4", level=2)
    pdf.add_toc_line("3.2  Stage 1 Paper Baseline & 13-Band Filter-Bank + Speech-10", "4", level=2)
    pdf.add_toc_line("3.3  Multi-Scale Riemannian SPD Tangent Mapping (1,695D)", "4", level=2)
    pdf.add_toc_line("3.4  Multi-Scale Block AGA Optimization", "5", level=2)
    pdf.add_toc_line("3.5  BLAS Multi-Metric Manifold Consensus Inference", "5", level=2)
    pdf.y -= 6.0
    pdf.add_toc_line("4  Experiment and Results", "5", level=1)
    pdf.add_toc_line("4.1  Setup Used", "5", level=2)
    pdf.add_toc_line("4.2  Benchmark Dataset", "6", level=2)
    pdf.add_toc_line("4.3  Performance Metrics", "6", level=2)
    pdf.add_toc_line("4.4  Results", "7", level=2)
    pdf.add_toc_line("4.5  Academic Integrity & Window-Overlap Transparency", "8", level=2)
    pdf.add_toc_line("4.6  Offline Oscilloscope GUI & Latency Testing", "9", level=2)
    pdf.y -= 6.0
    pdf.add_toc_line("5  Conclusion and Future Work", "9", level=1)
    pdf.y -= 6.0
    pdf.add_toc_line("References", "10", level=1)

    # =========================================================================
    # PAGE 4: INTRODUCTION & PRIMARY RESEARCH PAPER OVERVIEW (Footer: 3)
    # =========================================================================
    pdf.new_page(footer_num=3)
    pdf.y = pdf.page_height - 60.0

    pdf.add_sec_heading("1  Introduction", size=14.0, space_before=4.0, space_after=8.0)

    intro_p1 = (
        "Brain-computer interfaces (BCIs) explore non-invasive communication pathways for individuals with severe motor "
        "impairments such as ALS or brainstem stroke whose motor tracts are disrupted while cognition remains intact. Unlike gaze-dependent "
        "P300 or SSVEP paradigms, imagined speech analyzes scalp EEG correlates of internal phonological planning across "
        "fronto-temporal speech-related channels and sensorimotor leads without audible sound or physical movement."
    )
    pdf.add_paragraph(intro_p1, "F1", 9.6, 13.0)

    intro_p2 = (
        "Building on Lara-Arellano et al. (Eng MDPI 2025; 96.0% binary Yes/No under exploratory chunk splits), "
        "we implement Stage 1 (Paper Rank-GA + kNN over 6-Band SPD covariance) and Stage 2 MDRC-AGA with equal-"
        "emphasis Dual-Protocol auditing across Leakage-Safe Block-Disjoint 5-CV (N_ref=3,936) and Exploratory Chunk 5-CV:"
    )
    pdf.add_paragraph(intro_p2, "F1", 9.6, 13.0)

    pdf.add_bullet(
        "Contribution 1: Multi-Scale 13-Band + Speech-10 SPD Manifold (1,695 Features):",
        "Fuses Mendeley 6-Band SPD (630D), Fine 7-Band sub-rhythms (735D, 4-45 Hz), and Speech-10 scalp montage (330D)."
    )
    pdf.add_bullet(
        "Contribution 2: Fold-Safe Tangent Fit, MultiScaleBlockAGA & PCA-LDA/Ridge Stacker:",
        "Precomputes trial SPDs, fits C_ref only per train fold, evolves w ([0.85,0.66,1.49] blk; [1.30,0.98,0.72] chk)."
    )
    pdf.add_bullet(
        "Contribution 3: Dual-Protocol Evaluation with Calibration (Brier, ECE, 95% CI):",
        "Chunk 5-CV: Stage 1 90.02% -> Stage 2 91.84% Vote (ECE 0.037) | Block-Disjoint: ~10.14%-11.41% (chance 11.11%)."
    )
    pdf.add_bullet(
        "Contribution 4: Forensic Audit, Leakage Remediation & Offline Compute Bench (31.8 ms):",
        "Discloses 48-sample overlap, excludes all 108 test_signals/ sibling chunks (0/9 honest), and adds 8 unit tests."
    )

    pdf.add_sec_heading("2  Primary Research Paper & Related Work", size=13.5, space_before=6.0, space_after=6.0)
    pdf.add_subsec_heading("2.1  Primary Reference Paper: Method, GA Design & Published Accuracy", size=10.8, space_before=2.0, space_after=4.5)
    pdf.add_paragraph(
        "Our work directly builds upon Lara-Arellano, Takacs, Tovar-Arriaga, and Rodriguez-Resendiz, \"Feature Generation with "
        "Genetic Algorithms for Imagined Speech Electroencephalogram Signal Classification\" (Eng MDPI, vol. 6, no. 4, art. 75, "
        "Apr. 2025; DOI: 10.3390/eng6040075). Using the 14-channel Emotiv EPOC+ Mendeley EEGIS database (128 Hz; raw + Delta, "
        "Theta, Alpha, Beta, Gamma), the authors evaluated binary 'Yes (Si) vs No' classification (N=924: 444 Si, 480 No) under an "
        "80/20% train-test split, explicitly chosen instead of exhaustive k-fold CV so their large GA search remained tractable."
    )
    pdf.add_paragraph(
        "Methodology Used: Each EEG epoch yielded 214 statistical and spectral features across the 6 bands, encoded alongside 14 "
        "channel-activation bits into a 228-bit binary chromosome (P=100 individuals, G=100 generations). Optimization applied Rank "
        "Selection, Homogeneous Crossover, Bit-Flip Mutation, and an internal heuristic k search comparing SVM, Random Forest, "
        "Decision Tree, and kNN classifiers. Published Accuracy & Findings: Whereas baseline pre-GA kNN averaged below 70%, their "
        "evolved Rank-GA + kNN selected 8 electrodes (AF3, T7, O1, O2, P8, T8, F4, F8) and 103 features, achieving 96% binary "
        "accuracy (0.97 Recall, 0.94 F1-score). However, univariate stats alone omit cross-channel covariance and full 9-class decoding."
    )

    # =========================================================================
    # PAGE 5: PAPER SUMMARY TABLE, RELATED WORK & METHODOLOGY OVERVIEW (Footer: 4)
    # =========================================================================
    pdf.new_page(footer_num=4)
    pdf.y = pdf.page_height - 56.0

    ppr_headers = ["Primary Paper Attribute (Eng 2025)", "Published Specification / Reported Result"]
    ppr_rows = [
        ["Reference & Task Scope", "Lara-Arellano et al. (DOI: 10.3390/eng6040075) | Binary Yes(Si) vs No (N=924, 80/20)"],
        ["228-Bit GA Genome & Operators", "14 channel bits + 214 feature bits | Rank Selection, Homogeneous Crossover, Bit-Flip"],
        ["Optimal Subset & Heuristic Classifier", "kNN (heuristic k search) | 8 electrodes (AF3,T7,O1,O2,P8,T8,F4,F8), 103 features"],
        ["Published Accuracy & Metrics", "<70% pre-GA kNN -> 96% Binary Accuracy, 0.97 Recall, 0.94 F1 (binary only)"]
    ]
    pdf.add_booktabs_table("Table 1: Methodological profile and published accuracy of the primary reference paper (Lara-Arellano et al., 2025).",
                           ppr_headers, ppr_rows, [145, 325], font_size=7.6, row_height=11.4)

    pdf.add_subsec_heading("2.2  Comparative Related Literature", size=10.8, space_before=4.0, space_after=4.5)
    pdf.add_paragraph(
        "CSP, CNN & Riemannian BCIs: Under strict Block-Disjoint Nested 5-CV, FBCSP+SVM (Blankertz et al., 2011; 9.96%), "
        "scalar 6-band stats (10.34% SVM / 10.16% kNN7), MDM (8.74%), and 40-epoch EEGNetAttention (Lawhern et al., 2018; "
        "11.24% Fold 0) all remain near 9-class chance (11.11%). Under Exploratory Chunk 5-CV matching Lara-Arellano et al., "
        "SPD tangent geometry enables Stage 1 (90.02% / 96.11% Yes/No) and Stage 2 Vote (91.84% / 95.67% Yes/No)."
    )

    pdf.add_sec_heading("3  Methodology", size=13.5, space_before=4.0, space_after=5.0)
    pdf.add_subsec_heading("3.1  Overview", size=11.0, space_before=2.0, space_after=4.0)

    pdf.add_paragraph(
        "Figure 1 contrasts Stage 1 (Paper 6B Rank-GA + kNN: 10.01% Blk-Disj / 90.02% Chunk) against Stage 2 MDRC-AGA "
        "(1,695D Three-Scale SPD -> Fold-Safe C_ref -> MultiScaleBlockAGA -> Calibrated Stacker [PCA-LDA + Platt-Ridge, "
        "ECE=0.100] & [3:2:1:1] Consensus reaching 91.84% Chunk 5-CV / 10.14% Blk-Disj at 31.8 ms/epoch offline CPU compute)."
    )

    # Embed Figure 1
    pdf.add_image("Im1", target_w=440.0, target_h=150.0,
                  caption="Figure 1: Stage 1 Paper Rank-GA Baseline (top track) vs Stage 2 MDRC-AGA 13-Band + Speech-10 pipeline (bottom track).")

    pdf.add_subsec_heading("3.2  Stage 1 Paper Baseline & 13-Band + Speech-10 Preprocessing", size=11.0, space_before=4.0, space_after=4.0)
    pdf.add_paragraph(
        "Real 14-channel Emotiv EPOC+ epochs (128 Hz, 128 samples) supply 6 canonical bands (Raw, Delta 0.5-4, Theta 4-8, "
        "Alpha 8-12, Beta 12-30, Gamma 30-60 Hz). Stage 1 runs PaperRankGeneticSelector on 6B SPD tangent vectors. Stage 2 "
        "adds causal/sosfilt 4th-order Butterworth IIR sub-bands across 7 fine non-overlapping rhythms (4-45 Hz) plus Speech-10."
    )

    pdf.add_subsec_heading("3.3  Multi-Scale Riemannian SPD Tangent Mapping (1,695D)", size=11.0, space_before=4.0, space_after=4.0)
    pdf.add_paragraph(
        "Precomputed trial SPD matrices C = C0/tr(C0) + 1e-4*I are projected fold-strictly onto the tangent space at the "
        "training-only Log-Euclidean Frechet mean C_ref via S = C_ref^{-1/2} logm(C_ref^{-1/2} C C_ref^{-1/2}) C_ref^{1/2} "
        "and Band-L2 norm: Mendeley 6B 14-Ch (630D) + Fine 7B 14-Ch (735D) + Speech-10 6B (330D) yield z_k in R^{1695}."
    )

    # =========================================================================
    # PAGE 6: AGA OPTIMIZATION, ENSEMBLE & SETUP (Footer: 5)
    # =========================================================================
    pdf.new_page(footer_num=5)
    pdf.y = pdf.page_height - 60.0

    pdf.add_subsec_heading("3.4  Multi-Scale Block AGA Optimization", size=11.2, space_before=4.0, space_after=5.5)
    pdf.add_paragraph(
        "Stage 1 evolves 6-band SPD tangent masks using PaperRankGeneticSelector (Rank Selection + Homogeneous Crossover + "
        "Bit-Flip Mutation). To preserve intra-block SPD symmetry while re-weighting scales inside each outer fold without test "
        "leakage, Stage 2 applies vectorized float32 MultiScaleBlockAGA across the three manifold blocks (630D / 735D / 330D)."
    )
    pdf.add_paragraph(
        "Across 5 outer folds (inner 3-fold CV), MultiScaleBlockAGA selects mean block weights w = [0.8493, 0.6632, 1.4875] "
        "under Leakage-Safe Block-Disjoint GroupKFold and w = [1.2962, 0.9847, 0.7192] under Exploratory Chunk 5-CV, while "
        "controlled 5-seed ablation confirms adaptive vs fixed mutation remains statistically equivalent within seed variance."
    )

    pdf.add_subsec_heading("3.5  Calibrated Stacker & BLAS Manifold Consensus Inference", size=11.2, space_before=7.0, space_after=5.5)
    pdf.add_paragraph(
        "CalibratedManifoldStacker fuses 4 out-of-fold base estimators: LogReg(C=0.1), Pipeline(PCA(64), Shrinkage-LDA), "
        "Calibrated RidgeClassifier(alpha=100), and [3:2:1:1] MultiMetricSoftVotingClassifier (Cosine+Corr k=1,3) via "
        "LogReg(C=0.25) meta learner. Soft Vote hits 91.84% Chunk 5-CV (ECE=0.037); Stacker cuts Blk-Disj ECE to 0.100."
    )

    pdf.add_sec_heading("4  Experiment and Results", size=14.0, space_before=8.0, space_after=7.0)
    pdf.add_subsec_heading("4.1  Setup Used", size=11.2, space_before=3.0, space_after=5.5)
    pdf.add_paragraph(
        "All ingestion, Butterworth IIR filtering, fold-strict C_ref tangent projection, Rank-GA / Block-AGA search, nested "
        "5-CV, calibration (Brier, 10-bin ECE, block-cluster bootstrap 95% CI), and offline CPU timing ran on Python 3.14 CPU."
    )

    setup_headers = ["Component", "Implementation Setting (v2.0.0-audit-remediated)"]
    setup_rows = [
        ["Dataset & Exclusions", "Mendeley EEGIS (4,044 epochs, 337 blks) -> exclude 9 test_signals/ blks (108) -> N_ref=3,936"],
        ["Stage 1 Paper Model", "PaperRankGeneticSelector + Heuristic kNN (6B SPD tangent, nested per-fold fit)"],
        ["Stage 2 Multi-Scale", "1,695D: Mendeley 6B (630D) + Fine 7B (735D, 4-45 Hz) + Speech-10 (330D)"],
        ["Manifold Representation", "Trace-norm SPD (reg=1e-4) -> Fold-only C_ref Eigen-Log Tangent -> Band-L2"],
        ["Stage 2 Block AGA", "Vectorized MultiScaleBlockAGA (w=[0.85,0.66,1.49] blk; [1.30,0.98,0.72] chk)"],
        ["Stage 2 Ensembles", "Calibrated OOF Stacker (LogReg+PCA-LDA+Platt-Ridge+Vote) & [3:2:1:1] Soft Vote"],
        ["Offline Epoch Compute", "31.77 ms/epoch CPU (14.75 ms load + 0.04 preproc + 9.59 feat + 7.40 cls; NOT real-time BCI)"],
        ["Dual-Protocol Validation", "Primary Block-Disjoint Nested GroupKFold (328 blks) vs Exploratory Chunk 5-CV"]
    ]
    pdf.add_booktabs_table("Table 2: Audit-remediated Stage 1 vs Stage 2 specifications (equal-emphasis dual protocol).",
                           setup_headers, setup_rows, [130, 340], font_size=8.0, row_height=12.6)

    # =========================================================================
    # PAGE 7: BENCHMARK DATASET, METRICS & CONVERGENCE (Footer: 6)
    # =========================================================================
    pdf.new_page(footer_num=6)
    pdf.y = pdf.page_height - 60.0

    # Embed Figure 2
    pdf.add_image("Im2", target_w=450.0, target_h=175.0,
                  caption="Figure 2: Dual-protocol MultiScaleBlockAGA evolution and learned 3-scale weights w=[0.849,0.663,1.488] (Blk-Disj) & [1.296,0.985,0.719] (Chunk).")

    pdf.add_subsec_heading("4.2  Benchmark Dataset", size=11.2, space_before=8.0, space_after=6.0)
    pdf.add_paragraph(
        "Experiments run on the full 6-band EEGIS corpus (Lara et al., Mendeley 10.17632/73g4fw884c.1): 4,044 real 1.0-s CSVs "
        "(128 Hz, 14 channels). Forensic audit confirms 337 continuous 8s blocks (within-block max abs diff 0.0 uV; between-"
        "block mean diff 197.40 uV) sliced with 48-sample/37.5% overlap; Mendeley participant IDs are unrecoverable. Excluding all "
        "9 test_signals/ blocks (108 sibling chunks) yields N_ref=3,936 across 328 disjoint blocks."
    )

    data_headers = ["Property", "Value Specification"]
    data_rows = [
        ["Dataset Source", "Official Real EEGIS Dataset (4,044 epochs x 6 bands; participant IDs unrecoverable)"],
        ["Block Structure", "337 continuous 8s blocks x 12 chunks (48-sample overlap); 0 discontinuities, 0 rejected"],
        ["Semantic Vocabulary", "9 classes: Rest, Help, Bathroom, Pain, Thanks, Hungry, No, Thirsty, Yes"],
        ["Electrode Montage", "14 Ch Global + 10-Ch Speech-10 (AF3, F7, F3, FC5, T7, T8, FC6, F4, F8, AF4)"],
        ["Sibling Exclusion Audit", "All 9 test_signals/ blocks (108 chunks) excluded -> N_ref=3,936 (328 disjoint blocks)"],
        ["Paper Binary Cohort", "Yes (Si) vs No: 75 blocks / 900 ref trials (Primary Blk-Disj 5-CV & Chunk 5-CV)"],
        ["Primary vs Exploratory", "Primary: Nested Block-Disjoint GroupKFold 5-CV | Secondary: Exploratory Chunk 5-CV"]
    ]
    pdf.add_booktabs_table("Table 3: Audited Mendeley EEGIS corpus properties and dual-protocol cohort breakdown.",
                           data_headers, data_rows, [130, 340], font_size=8.0, row_height=12.6)

    pdf.add_subsec_heading("4.3  Performance Metrics", size=11.2, space_before=8.0, space_after=6.0)
    pdf.add_paragraph(
        "Classification efficacy is evaluated across standard biometric metrics: Overall Test Accuracy relative to 9-class random "
        "chance (1/9 = 11.11%), Macro Precision, Macro Recall, Macro F1-Score, and Cohen's kappa coefficient kappa = (P_o - P_e)/(1 - P_e). "
        "Command discriminability is tracked via recall on target words ('Help') and offline per-epoch CPU compute latency."
    )

    # =========================================================================
    # PAGE 8: RESULTS & ABLATION STUDIES (Footer: 7)
    # =========================================================================
    pdf.new_page(footer_num=7)
    pdf.y = pdf.page_height - 60.0

    pdf.add_subsec_heading("4.4  Results & Ablation Studies", size=11.2, space_before=4.0, space_after=6.0)
    pdf.add_paragraph(
        "Table 4 presents BOTH evaluation protocols side by side across all N_ref=3,936 epochs (328 blocks). Under strict Block-"
        "Disjoint 5-CV, all methods cluster near 9-class chance (11.11%; Stage 2 PCA+RBF-SVM hits 11.41%, ECE=0.022). Under "
        "Exploratory Chunk 5-CV matching Lara-Arellano et al., Stage 1 reaches 90.02% and Stage 2 Soft Vote reaches 91.84% (ECE=0.037)."
    )

    abl_headers = ["Method (N_ref=3,936, 328 Blocks)", "Blk-Disj 5-CV", "Blk ECE", "Chunk 5-CV*", "Chk F1", "Calibration / Audit Notes"]
    abl_rows = [
        ["Random Chance Baseline (9 Classes)", "11.11%", "--", "11.11%", "0.111", "9 balanced semantic classes"],
        ["Scalar 322 Stats + RBF SVM", "10.34%", "--", "19.39%", "0.180", "Scalar moments lack phase geometry"],
        ["Scalar 322 Stats + kNN (k=7)", "10.16%", "--", "18.22%", "0.178", "Yes/No Stage1 blk: 45.11%"],
        ["FBCSP + Calibrated SVM", "9.96%", "0.049", "19.46%", "0.168", "Brier 0.895 blk / 0.877 chk"],
        ["MDM 6-Band Log-Euclidean", "8.74%", "--", "16.11%", "0.138", "Single Riemannian mean centroid"],
        ["True Fold-Tangent LogReg 6B", "10.72%", "0.667", "20.78%", "0.207", "Fold-strict C_ref linear baseline"],
        ["EEGNetAttention (Fold 0 Holdout)", "11.24%", "0.103", "16.62%", "0.159", "40 epochs on 6x14x128 tensor"],
        ["Stage 1 Paper (6B Rank-GA + kNN)", "10.01%", "0.327", "90.02%", "0.899", "F0: 14.65% blk / 91.62% chk | k=1"],
        ["Stage 2 MDRC-AGA Stacker (OOF)", "9.68%", "0.100", "74.67%", "0.744", "Best calibration blk Brier=0.913"],
        ["Stage 2 MDRC-AGA Soft Vote [3:2:1:1]", "10.14%", "0.728", "91.84%", "0.918", "Chk Brier=0.156, ECE=0.037, K=0.908"],
        ["Stage 2 Head: PCA(256)+Cal.RBF-SVM", "11.41%", "0.022", "20.17%", "--", "Best Blk-Disj acc & lowest ECE"]
    ]
    pdf.add_booktabs_table("Table 4: Equal-emphasis 9-class comparison across Block-Disjoint Primary and Exploratory Chunk* 5-CV.",
                           abl_headers, abl_rows, [148, 52, 40, 52, 42, 152], font_size=7.2, row_height=11.0)

    pdf.add_paragraph(
        "Table 5 compares Stage 1 vs Stage 2 across binary pairs, sibling-excluded offline test_signals/, and controlled ablations "
        "(5-seed mutation control, sub-band overlap, and continuous 8s windowing). Binary pairs track the same overlap boundary."
    )

    comp_headers = ["Binary Task / Controlled Ablation", "Blk Stage 1", "Blk Stg 2", "Chk Stage 1*", "Chk Stg 2*", "Protocol / Control Finding"]
    comp_rows = [
        ["Published Target (Lara et al., 2025)", "--", "--", "96.00%", "--", "80/20 chunk protocol (N=924)"],
        ["Yes(Si) vs No (N=900, 75 blks)", "45.11%", "46.33%", "96.11%", "95.67%", "Blk Stacker 46.3% / Chk Vote 95.7%"],
        ["Help vs Rest (N=936, 78 blks)", "47.33%", "48.08%", "97.12%", "97.44%", "Target vs Rest (*chunk overlap)"],
        ["Help vs Pain (N=972, 81 blks)", "46.91%", "46.40%", "96.19%", "96.50%", "High-priority word separation"],
        ["Hungry vs Thirsty (N=828, 69 blks)", "47.34%", "49.88%", "95.41%", "96.38%", "Blk Vote 49.9% / Chk Vote 96.4%"],
        ["Yes vs Help (N=924, 77 blks)", "49.35%", "47.84%", "96.00%", "96.86%", "Confirm vs Help (*chunk overlap)"],
        ["5-Seed Mutation (fix/adapt/stag F0)", "--", "11.5/11.5%", "--", "93.6/93.5%", "Adaptive & fixed eq. within std <=0.22%"],
        ["Continuous 8s Window (1s/2s/8s agg)", "--", "11.9/12.2%", "--", "--", "10.06% @ 8s; IIR edge=0.018 uV"],
        ["Offline test_signals/ (held-out)", "0/9 (blk)", "9/9 (chk)", "96.0%", "90.85%", "100% demo match; 9.4 ms/epoch"]
    ]
    pdf.add_booktabs_table("Table 5: Binary benchmarks, controlled ablations, and sibling-excluded offline verification (*chunk overlap).",
                           comp_headers, comp_rows, [146, 46, 46, 48, 48, 152], font_size=7.1, row_height=10.8)

    pdf.add_paragraph(
        "Montage & Geometry Controls: Under Fold 0, 14-Ch reaches 12.63% blk LogReg / 92.26% chk Vote vs Left-7 (13.38% / 60.41%) "
        "and Speech-10 (11.24% / 82.49%). Tangent_fold vs identity_log_euclid differs minimally (10.14% vs 10.34% blk; 91.84% vs 91.77% chk)."
    )

    # =========================================================================
    # PAGE 9: COMPARISON CHARTS & CONFUSION MATRIX (Footer: 8)
    # =========================================================================
    pdf.new_page(footer_num=8)
    pdf.y = pdf.page_height - 60.0

    # Embed Figure 3
    pdf.add_image("Im3", target_w=440.0, target_h=160.0,
                  caption="Figure 3: Dual-protocol comparison contrasting Block-Disjoint Primary (~10%-11.4%) vs Exploratory Chunk* 5-CV (Stage 1 90.02% -> Stage 2 91.84%).")

    # Embed Figure 4
    pdf.add_image("Im4", target_w=310.0, target_h=180.0,
                  caption="Figure 4: Dual confusion matrices comparing Stage 2 Blk-Disj Stacker (9.68% / Vote 10.14%) and Exploratory Chunk Vote (91.84%).")

    pdf.add_subsec_heading("4.5  Academic Integrity & Window-Overlap Transparency", size=11.2, space_before=6.0, space_after=6.0)
    pdf.add_paragraph(
        "Dataset audit proves Mendeley 1.0s epochs are 48-sample/37.5%-overlapping windows cut from 337 continuous 8s recordings, "
        "and source CSVs/docs lack recoverable subject IDs. Chunk-stratified 5-CV (*~90%-91.8%) lets adjacent chunks span train/test; "
        "disjoint Block-GroupKFold (9.68%-11.41%) and excluding all 108 sibling test_signals/ chunks (0/9) expose the true cross-block frontier."
    )

    # =========================================================================
    # PAGE 10: PER-CLASS BREAKDOWN, GUI & CONCLUSION (Footer: 9)
    # =========================================================================
    pdf.new_page(footer_num=9)
    pdf.y = pdf.page_height - 60.0

    table5_headers = ["Semantic Target", "Assistive Lexicon Role", "Blk-Disj R / F1", "Chunk* P / R / F1", "Scalp EEG Montage Notes"]
    table5_rows = [
        ["Rest (Reposo)", "Baseline relaxation", "0.074 / 0.082", "0.919 / 0.919 / 0.919", "Occipital scalp (O1, O2)"],
        ["Help (Ayuda)", "High-priority command", "0.165 / 0.128", "0.929 / 0.931 / 0.930", "Anterior frontal (F7, F3)"],
        ["Bathroom (Bano)", "Personal hygiene call", "0.028 / 0.038", "0.908 / 0.906 / 0.907", "Pre-frontal scalp (AF3, AF4)"],
        ["Pain (Dolor)", "High-priority command", "0.171 / 0.139", "0.930 / 0.908 / 0.919", "Parietal scalp (P7, P8)"],
        ["Thanks (Gracias)", "Social courtesy word", "0.074 / 0.081", "0.933 / 0.938 / 0.935", "Bilateral frontal (F3, F4)"],
        ["Hungry (Hambre)", "Nutritional request", "0.118 / 0.116", "0.915 / 0.924 / 0.919", "Temporal scalp (T7, FC5)"],
        ["No", "Negative confirmation", "0.088 / 0.084", "0.931 / 0.921 / 0.926", "Frontal scalp leads"],
        ["Thirsty (Sed)", "Hydration request", "0.033 / 0.039", "0.922 / 0.919 / 0.920", "Temporal scalp (T7, T8)"],
        ["Yes (Si)", "Affirmative confirmation", "0.088 / 0.098", "0.876 / 0.898 / 0.887", "Frontal scalp (F3, F4)"]
    ]
    pdf.add_booktabs_table("Table 6: Stage 2 per-class metrics across Blk-Disj Stacker (9.68%) and Exploratory Chunk* Vote (91.84%, N_ref=3,936).",
                           table5_headers, table5_rows, [76, 128, 74, 90, 118], font_size=7.4, row_height=12.0)

    pdf.add_subsec_heading("4.6  Offline Oscilloscope GUI & Latency Testing", size=11.2, space_before=4.0, space_after=5.5)
    pdf.add_paragraph(
        "Our CLI predictor (predict.py) and Qt oscilloscope GUI (eeg_gui_tester.py) inspect offline 14-channel CSVs (9.4 ms/epoch "
        "CPU compute on held-out test signals matching 9/9 100.0%, alongside the 31.8 ms/epoch full pipeline benchmark). "
        "Under block-disjoint cross-validation without overlap, performance settles at the 11.11% chance baseline."
    )

    # Embed Figure 5
    pdf.add_image("Im5", target_w=430.0, target_h=150.0,
                  caption="Figure 5: Offline 14-channel EEGIS waveform (eeg_signal_02.csv, ref Help) decoded with calibrated posterior as 'Help (Ayuda)' (91.2%).")

    pdf.add_sec_heading("5  Conclusion and Future Work", size=14.0, space_before=5.0, space_after=7.0)
    pdf.add_paragraph(
        "This study audited all 4,044 real EEGIS epochs under equal-emphasis Block-Disjoint Primary and Exploratory Chunk 5-CV. "
        "Under Chunk 5-CV matching Lara-Arellano et al. (2025), Stage 1 matches 96.11% Yes/No (90.02% 9-Cl) and Stage 2 Vote "
        "reaches 91.84% (0.9180 F1, Brier 0.156, ECE 0.037). Under Block-Disjoint 5-CV (N_ref=3,936) and 0/9 sibling-excluded CSVs,"
    )

    # =========================================================================
    # PAGE 11: FUTURE WORK & REFERENCES (1-7) (Footer: 10)
    # =========================================================================
    pdf.new_page(footer_num=10)
    pdf.y = pdf.page_height - 60.0

    pdf.add_paragraph(
        "all methods cluster near 11.11% chance (PCA+RBF-SVM 11.41%, ECE=0.022; Stacker 9.68%, ECE=0.100), pinpointing non-"
        "stationary cross-block transfer and missing subject IDs as the core scientific bottleneck (31.8 ms/epoch offline compute)."
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
        "4. Prospective Clinical Validation (Subject to Transfer Calibration):",
        "Once cross-block and cross-subject generalization exceed chance reliably, integrate low-latency "
        "streaming acquisition and validate assistive communication workflows with clinical stroke/ALS cohorts."
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
    doc_body.append(make_p("Primary Paper Rank-GA Baseline and Multi-Scale Riemannian Consensus (MDRC-AGA)", size_pt=13.0, align="center", space_after=100))
    doc_body.append(make_p("with Dual-Protocol Leakage Audit and Offline Inspection", size_pt=12.0, align="center", space_after=2200))

    doc_body.append(make_p("A reproducible study on the EEGIS 14-Channel Multi-Class Imagined Speech Database (Mendeley Data)", size_pt=11.0, align="center", space_after=1200))

    doc_body.append(make_p("Team:", size_pt=11.0, align="center", space_after=100))
    doc_body.append(make_p("Saurabh Bharrdwaj  •  Badvath Jaipal  •  Saurabh Kumar", size_pt=11.5, align="center", space_after=300))
    doc_body.append(make_p("November 2026", size_pt=11.0, align="center", space_after=0))

    # Page Break -> Abstract
    doc_body.append(make_page_break())
    doc_body.append(make_p("Abstract", bold=True, size_pt=16.0, space_before=400, space_after=200))
    doc_body.append(make_p(
        "Imagined speech electroencephalography (EEG) provides a direct, non-invasive communication pathway for individuals "
        "with severe motor and vocal impairments, including locked-in syndrome, brainstem stroke, and ALS. Across 4,044 Mendeley "
        "EEGIS trials (337 continuous 8s blocks, 128 Hz, 14 channels, 48-sample/37.5% chunk overlap, unrecoverable participant IDs), "
        "naive chunk splits inflate kNN accuracy via within-block overlap. Excluding all 9 test_signals/ blocks (108 sibling chunks) "
        "leaves N_ref=3,936 (328 disjoint blocks). Under leakage-safe Block-Disjoint Nested 5-CV, all models sit near 9-class chance "
        "(11.11%): Stage 1 Paper Rank-GA+kNN scores 10.01% (Yes/No 45.11%), True Fold-Tangent LogReg 10.72%, EEGNet Fold 0 11.24%, "
        "and PCA(256)+Calibrated RBF-SVM 11.41% (ECE=0.022).",
        size_pt=10.0, space_after=160
    ))
    doc_body.append(make_p(
        "Under the exploratory Overlapping-Chunk 5-CV protocol matching Lara-Arellano et al. (MDPI Eng, 2025; 96.0% published Yes/No), "
        "Stage 1 Paper 6B Rank-GA+kNN reaches 90.02% 9-class and 96.11% Yes/No. Stage 2 MDRC-AGA (1,695D three-scale Log-Euclidean "
        "SPD manifold: Mendeley 6B 630D + Fine 7B 735D + Speech-10 330D; MultiScaleBlockAGA; PCA-LDA + Platt-Ridge Stacker & [3:2:1:1] "
        "Soft Vote) achieves 91.84% (0.9180 F1, Brier 0.156, ECE 0.037) on Chunk 5-CV (95.67% Yes/No) and 9.68% Stacker (ECE=0.100) / "
        "10.14% Vote on Block-Disjoint 5-CV. Sibling-excluded offline test_signals/ verify honest 0/9 generalization at 31.77 ms/epoch compute.",
        size_pt=10.0, space_after=200
    ))
    doc_body.append(make_p("Keywords: brain-computer interface (BCI); imagined speech; electroencephalography (EEG); multi-scale Riemannian covariance; adaptive genetic algorithm; manifold consensus; EEGIS dataset.", italic=True, size_pt=9.5, space_after=400))

    # Page Break -> Table of Contents
    doc_body.append(make_page_break())
    doc_body.append(make_p("Contents", bold=True, size_pt=16.0, space_before=400, space_after=300))
    toc_items = [
        ("Abstract", "1"),
        ("1  Introduction", "3"),
        ("2  Primary Research Paper & Related Work", "3"),
        ("    2.1  Primary Paper Method, GA Design & Accuracy", "3"),
        ("    2.2  Comparative Related Literature", "4"),
        ("3  Methodology", "4"),
        ("    3.1  Overview", "4"),
        ("    3.2  Stage 1 Paper Baseline & 13-Band Filter-Bank + Speech-10", "4"),
        ("    3.3  Multi-Scale Riemannian SPD Tangent Mapping (1,695D)", "4"),
        ("    3.4  Multi-Scale Block AGA Optimization", "5"),
        ("    3.5  BLAS Multi-Metric Manifold Consensus Inference", "5"),
        ("4  Experiment and Results", "5"),
        ("    4.1  Setup Used", "5"),
        ("    4.2  Benchmark Dataset", "6"),
        ("    4.3  Performance Metrics", "6"),
        ("    4.4  Results", "7"),
        ("    4.5  Academic Integrity & Window-Overlap Transparency", "8"),
        ("    4.6  Offline Oscilloscope GUI & Latency Testing", "9"),
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
        "syndrome, the ability to express fundamental human needs—such as requesting help, hydration, or communicating discomfort—"
        "is severely limited. Imagined speech, wherein a subject mentally articulates specific words or phonemes "
        "without producing audible sound or observable muscle movement, offers an intuitive, gaze-independent "
        "communication paradigm. Unlike P300 visual evoked potentials or steady-state visual evoked potentials (SSVEP), which require intact gaze control "
        "and provoke ocular fatigue, imagined speech analyzes scalp EEG correlates of internal phonological planning across "
        "fronto-temporal speech-related channels and sensorimotor leads.",
        size_pt=10.0, space_after=140
    ))
    doc_body.append(make_p("Stage 1 Primary Paper Benchmark & Stage 2 MDRC-AGA Dual-Protocol Audit:", bold=True, size_pt=10.5, space_before=100, space_after=80))
    doc_body.append(make_p("• Stage 1 Primary Paper Baseline (Lara-Arellano et al., 2025): Nested per-fold PaperRankGeneticSelector + heuristic kNN over 6-band SPD covariance reaches 90.02% 9-class / 96.11% Yes/No under Exploratory Chunk 5-CV, and 10.01% 9-class / 45.11% Yes/No under Leakage-Safe Block-Disjoint 5-CV.", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Enhancement 1: Multi-Scale 13-Band + Speech-10 SPD Manifold (1,695D): Fuses Mendeley 6-Band Global (630D), Fine 7-Band sub-rhythms (735D, 4-45 Hz), and speech-related 10-channel Speech-10 scalp montage (330D) using fold-strict C_ref tangent projection.", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Enhancement 2: Vectorized MultiScaleBlockAGA & Calibrated Stacker: Evolves w = [0.8493, 0.6632, 1.4875] (Blk-Disj) and [1.2962, 0.9847, 0.7192] (Chunk), fusing LogReg(C=0.1), PCA-LDA, Platt-Ridge, and [3:2:1:1] Consensus.", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Enhancement 3: Dual-Protocol Evaluation with Calibration: Exploratory Chunk 5-CV Soft Vote hits 91.84% (0.9180 F1, Brier 0.156, ECE 0.037, Yes/No 95.67%); Block-Disjoint 5-CV sits near chance (9.68% Stacker ECE=0.100; 11.41% PCA+RBF-SVM ECE=0.022).", size_pt=9.5, space_after=60))
    doc_body.append(make_p("• Enhancement 4: Forensic Audit & Offline Verification (31.77 ms/epoch CPU): Discloses 48-sample overlap across 337 8s blocks and unrecoverable subject IDs; excludes all 108 sibling test_signals/ chunks -> honest 0/9 generalization.", size_pt=9.5, space_after=160))

    doc_body.append(make_p("2  Primary Research Paper & Related Work", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p("2.1  Primary Reference Paper: Method, GA Design & Published Accuracy", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Our work directly builds upon Lara-Arellano, Takacs, Tovar-Arriaga, and Rodriguez-Resendiz, \"Feature Generation with Genetic Algorithms for Imagined Speech Electroencephalogram Signal Classification\" (Eng MDPI, vol. 6, no. 4, art. 75, Apr. 2025; DOI: 10.3390/eng6040075). Using the 14-channel Emotiv EPOC+ Mendeley EEGIS database (128 Hz; raw + Delta, Theta, Alpha, Beta, Gamma), the authors evaluated binary 'Yes (Si) vs No' classification (N=924: 444 Si, 480 No) under an 80/20% train-test split, explicitly chosen instead of exhaustive k-fold CV so their large GA search remained tractable.", size_pt=10.0, space_after=100))
    doc_body.append(make_p("Methodology Used: Each EEG epoch yielded 214 statistical and spectral features across the 6 bands, encoded alongside 14 channel-activation bits into a 228-bit binary chromosome (P=100 individuals, G=100 generations). Optimization applied Rank Selection, Homogeneous Crossover, Bit-Flip Mutation, and an internal heuristic k search comparing SVM, Random Forest, Decision Tree, and kNN classifiers. Published Accuracy & Findings: Whereas baseline pre-GA kNN averaged below 70%, their evolved Rank-GA + kNN selected 8 electrodes (AF3, T7, O1, O2, P8, T8, F4, F8) and 103 features, achieving 96% binary accuracy (0.97 Recall, 0.94 F1-score). However, univariate stats alone omit cross-channel covariance and full 9-class decoding.", size_pt=10.0, space_after=100))
    doc_body.append(make_p("Table 1: Methodological profile and published accuracy of the primary reference paper (Lara-Arellano et al., 2025).", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Primary Paper Attribute (Eng 2025)", "Published Specification / Reported Result"],
        [
            ["Reference & Task Scope", "Lara-Arellano et al. (DOI: 10.3390/eng6040075) | Binary Yes(Si) vs No (N=924, 80/20)"],
            ["228-Bit GA Genome & Operators", "14 channel bits + 214 feature bits | Rank Selection, Homogeneous Crossover, Bit-Flip"],
            ["Optimal Subset & Heuristic Classifier", "kNN (heuristic k search) | 8 electrodes (AF3,T7,O1,O2,P8,T8,F4,F8), 103 features"],
            ["Published Accuracy & Metrics", "<70% pre-GA kNN -> 96% Binary Accuracy, 0.97 Recall, 0.94 F1 (binary only)"],
        ]
    ))
    doc_body.append(make_p("2.2  Comparative Related Literature", bold=True, size_pt=11.5, space_before=120, space_after=80))
    doc_body.append(make_p("Traditional spatial filters: Under strict Block-Disjoint 5-CV, FBCSP+SVM (Blankertz et al., 2011; 9.96%) and scalar 6-band moments (10.34% SVM / 10.16% kNN7) remain near 11.11% chance.", size_pt=10.0, space_after=100))
    doc_body.append(make_p("CNN-based methods: A multi-band EEGNetAttention network (Lawhern et al., 2018 style, 40 epochs) achieves 11.24% (Blk-Disj F0) and 16.62% (Chunk F0) on 6x14x128 tensors.", size_pt=10.0, space_after=100))
    doc_body.append(make_p("Evolutionary & kNN selection: Stage 1 matches the primary paper under Exploratory Chunk 5-CV (96.11% Yes/No, 90.02% 9-Cl) while exposing 10.01% (Blk-Disj) transfer.", size_pt=10.0, space_after=100))
    doc_body.append(make_p("Riemannian geometry approaches: Stage 2 MDRC-AGA fuses 1,695D SPD tangent features with fold-strict C_ref, MultiScaleBlockAGA, PCA-LDA+Platt-Ridge stacking, and [3:2:1:1] Consensus to reach 91.84% Chunk 5-CV (ECE=0.037) and 9.68%-11.41% Block-Disjoint 5-CV.", size_pt=10.0, space_after=140))

    # Methodology
    doc_body.append(make_page_break())
    doc_body.append(make_p("3  Methodology", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p("3.1  Overview", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Our pipeline contrasts Stage 1 (Paper 6-Band Rank-GA + kNN) against Stage 2 MDRC-AGA (1,695D Multi-Scale SPD + Fold-Strict C_ref + MultiScaleBlockAGA + Calibrated Stacker & Soft Vote) across N_ref=3,936 sibling-excluded EEGIS epochs.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.2  Stage 1 Paper Baseline & 13-Band + Speech-10 Preprocessing", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Emotiv EPOC+ 14 channels (128 Hz, T = 128 samples/epoch) yield 6 canonical bands (Raw, Delta, Theta, Alpha, Beta, Gamma). Stage 2 expands spectral resolution via 4th-order Butterworth IIR filtering into 7 fine non-overlapping sub-bands (4-45 Hz) plus the speech-related 10-channel Speech-10 scalp montage.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.3  Multi-Scale Riemannian SPD Tangent Mapping (1,695D)", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Precomputed trial SPDs C = C0/tr(C0) + 1e-4*I are projected per outer fold using only training-fold Log-Euclidean Frechet means C_ref and Band-L2 norm across Mendeley 6B 14-Ch (630D), Fine 7B 14-Ch (735D), and Speech-10 6B (330D) for D = 1,695 features.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.4  Multi-Scale Block AGA Optimization", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Vectorized float32 MultiScaleBlockAGA evolves 3-scale weights w = [0.8493, 0.6632, 1.4875] (Block-Disjoint) and w = [1.2962, 0.9847, 0.7192] (Exploratory Chunk) via inner 3-fold CV while preserving intra-block SPD symmetry.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("3.5  Calibrated Stacker & BLAS Manifold Consensus Inference", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("CalibratedManifoldStacker combines OOF predictions from LogReg(C=0.1), Pipeline(PCA, Shrinkage-LDA), Calibrated Ridge(alpha=100), and [3:2:1:1] MultiMetricSoftVotingClassifier at 31.77 ms/epoch offline workstation CPU compute with zero overrides.", size_pt=10.0, space_after=140))

    # Experiment and Results
    doc_body.append(make_page_break())
    doc_body.append(make_p("4  Experiment and Results", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p("4.1  Setup Used", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("All experiments ran on CPU using Python 3.14, NumPy, SciPy, and scikit-learn over all 4,044 real Mendeley trials (3,936 after excluding all 9 test_signals/ blocks) with fold-strict C_ref fitting and 0 convergence warnings.", size_pt=10.0, space_after=120))

    # Table 1
    doc_body.append(make_p("Table 2: Audit-remediated Stage 1 vs Stage 2 specifications (equal-emphasis dual protocol).", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Component", "Implementation Setting (v2.0.0-audit-remediated)"],
        [
            ["Dataset & Exclusions", "Mendeley EEGIS (4,044 epochs, 337 blks) -> exclude 9 test_signals/ blks -> N_ref=3,936"],
            ["Stage 1 Paper Model", "PaperRankGeneticSelector + Heuristic kNN (6B SPD tangent, nested per-fold fit)"],
            ["Stage 2 Multi-Scale", "1,695D: Mendeley 6B (630D) + Fine 7B (735D, 4-45 Hz) + Speech-10 (330D)"],
            ["Manifold Features", "Trace-norm SPD (reg=1e-4) -> Fold-only C_ref Eigen-Log Tangent -> Band-L2"],
            ["Stage 2 Block AGA", "Vectorized MultiScaleBlockAGA (w=[0.85,0.66,1.49] blk; [1.30,0.98,0.72] chk)"],
            ["Stage 2 Ensembles", "Calibrated OOF Stacker (LogReg+PCA-LDA+Platt-Ridge+Vote) & [3:2:1:1] Soft Vote"],
            ["Offline Epoch Compute", "31.77 ms/epoch CPU (14.75 load + 0.04 preproc + 9.59 feat + 7.40 cls; NOT real-time BCI)"],
            ["Dual Validation", "Primary: Nested Block-Disjoint GroupKFold 5-CV | Secondary: Exploratory Chunk 5-CV"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Table 2
    doc_body.append(make_p("4.2  Benchmark Dataset", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Evaluated on Mendeley EEGIS (DOI: 10.17632/73g4fw884c.1): 4,044 1.0-s epochs across 337 continuous 8s blocks (48-sample/37.5% overlap; 0.0 uV within-block max diff; 197.40 uV between-block mean diff; subject IDs unrecoverable). Excluding 9 test_signals/ blocks yields N_ref=3,936 (328 blocks).", size_pt=10.0, space_after=120))

    doc_body.append(make_p("Table 3: Audited Mendeley EEGIS dataset characteristics and dual-protocol cohorts.", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Property", "Value Specification"],
        [
            ["Dataset Source", "Official Real EEGIS Dataset (4,044 epochs x 6 bands; participant IDs unrecoverable)"],
            ["Block Structure", "337 continuous 8s blocks x 12 chunks (48-sample overlap); 0 discontinuities, 0 rejected"],
            ["Vocabulary", "9 classes: Rest, Help, Bathroom, Pain, Thanks, Hungry, No, Thirsty, Yes"],
            ["Electrode Montages", "14 Ch Global + 10-Ch Speech-10 (AF3, F7, F3, FC5, T7, T8, FC6, F4, F8, AF4)"],
            ["Sibling Exclusion", "All 9 test_signals/ blocks (108 chunks) excluded -> N_ref=3,936 (328 disjoint blocks)"],
            ["Primary vs Exploratory", "Block-Disjoint GroupKFold 5-CV (Unbiased) vs Exploratory Chunk 5-CV (*overlap)"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Table 3 & 4
    doc_body.append(make_page_break())
    doc_body.append(make_p("4.4  Results & Ablation Studies", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Table 4: Equal-emphasis 9-class comparison across Block-Disjoint Primary and Exploratory Chunk* 5-CV (N_ref=3,936).", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Method (N_ref=3,936)", "Blk-Disj 5-CV", "Blk ECE", "Chunk 5-CV*", "Notes"],
        [
            ["Random Chance (9 Classes)", "11.11%", "--", "11.11%", "Theoretical lower bound"],
            ["Scalar 322 Stats + RBF SVM", "10.34%", "--", "19.39%", "Scalar stats lack spatial phase"],
            ["Scalar 322 Stats + kNN7", "10.16%", "--", "18.22%", "Univariate baseline"],
            ["FBCSP + Calibrated SVM", "9.96%", "0.049", "19.46%", "Brier 0.895 blk / 0.877 chk"],
            ["MDM 6-Band Log-Euclidean", "8.74%", "--", "16.11%", "Single SPD centroid"],
            ["True Fold-Tangent LogReg 6B", "10.72%", "0.667", "20.78%", "Fold-strict C_ref baseline"],
            ["EEGNetAttention (Fold 0)", "11.24%", "0.103", "16.62%", "40ep on 6x14x128 tensor"],
            ["Stage 1 Paper (6B Rank-GA+kNN)", "10.01%", "0.327", "90.02%", "F0: 14.65% blk / 91.62% chk"],
            ["Stage 2 MDRC-AGA Stacker", "9.68%", "0.100", "74.67%", "Well-calibrated (Blk Brier 0.913)"],
            ["Stage 2 MDRC-AGA Soft Vote", "10.14%", "0.728", "91.84%", "Chk F1=0.918, Brier=0.156, ECE=0.037"],
            ["Stage 2 PCA(256)+Cal.RBF-SVM", "11.41%", "0.022", "20.17%", "Best Blk-Disj accuracy & ECE"]
        ]
    ))
    doc_body.append(make_p("", space_after=140))

    doc_body.append(make_p("Table 5: Binary benchmarks, controlled ablations, and sibling-excluded offline verification (*chunk overlap).", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Binary Task / Controlled Ablation", "Blk Stg 1", "Blk Stg 2", "Chk Stg 1*", "Chk Stg 2*", "Key Finding"],
        [
            ["Published Paper (Lara et al., 2025)", "--", "--", "96.00%", "--", "80/20 chunk split (N=924)"],
            ["Yes(Si) vs No (N=900, 75 blks)", "45.11%", "46.33%", "96.11%", "95.67%", "Blk Stacker 46.3% / Chk Vote 95.7%"],
            ["Help vs Rest (N=936, 78 blks)", "47.33%", "48.08%", "97.12%", "97.44%", "Target vs Rest (*chunk overlap)"],
            ["Help vs Pain (N=972, 81 blks)", "46.91%", "46.40%", "96.19%", "96.50%", "High-priority word separation"],
            ["Hungry vs Thirsty (N=828, 69 blks)", "47.34%", "49.88%", "95.41%", "96.38%", "Blk Vote 49.9% / Chk Vote 96.4%"],
            ["Yes vs Help (N=924, 77 blks)", "49.35%", "47.84%", "96.00%", "96.86%", "Confirm vs Help (*chunk overlap)"],
            ["5-Seed Mutation (fix/adapt/stag F0)", "--", "11.5/11.5%", "--", "93.6/93.5%", "Equivalent within seed std <=0.22%"],
            ["Continuous 8s Window (1s/2s/8s)", "--", "11.9/12.2%", "--", "--", "10.06% @ 8s; IIR edge=0.018 uV"],
            ["Offline test_signals/ (held-out)", "0/9 (blk)", "9/9 (chk)", "96.0%", "90.85%", "100% demo match (9.4 ms/epoch)"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Table 5
    doc_body.append(make_page_break())
    doc_body.append(make_p("Table 6: Stage 2 per-class metrics across Blk-Disj Stacker (9.68%) and Exploratory Chunk* Vote (91.84%, N_ref=3,936).", italic=True, size_pt=9.5, space_after=80))
    doc_body.append(make_table(
        ["Semantic Target", "Assistive Lexicon Role", "Blk-Disj R / F1", "Chunk* P / R / F1", "Scalp EEG Montage Notes"],
        [
            ["Rest (Reposo)", "Baseline relaxation", "0.074 / 0.082", "0.919 / 0.919 / 0.919", "Occipital scalp leads (O1, O2)"],
            ["Help (Ayuda)", "High-priority command", "0.165 / 0.128", "0.929 / 0.931 / 0.930", "Anterior frontal scalp (F7, F3)"],
            ["Bathroom (Bano)", "Personal hygiene call", "0.028 / 0.038", "0.908 / 0.906 / 0.907", "Pre-frontal scalp leads (AF3, AF4)"],
            ["Pain (Dolor)", "High-priority command", "0.171 / 0.139", "0.930 / 0.908 / 0.919", "Parietal scalp leads (P7, P8)"],
            ["Thanks (Gracias)", "Social courtesy word", "0.074 / 0.081", "0.933 / 0.938 / 0.935", "Bilateral frontal scalp (F3, F4)"],
            ["Hungry (Hambre)", "Nutritional request", "0.118 / 0.116", "0.915 / 0.924 / 0.919", "Temporal scalp leads (T7, FC5)"],
            ["No", "Negative confirmation", "0.088 / 0.084", "0.931 / 0.921 / 0.926", "Frontal scalp leads"],
            ["Thirsty (Sed)", "Hydration request", "0.033 / 0.039", "0.922 / 0.919 / 0.920", "Temporal scalp leads (T7, T8)"],
            ["Yes (Si)", "Affirmative confirmation", "0.088 / 0.098", "0.876 / 0.898 / 0.887", "Frontal scalp leads (F3, F4)"]
        ]
    ))
    doc_body.append(make_p("", space_after=160))

    # Offline GUI & Conclusion
    doc_body.append(make_p("4.6  Offline Oscilloscope GUI & Latency Testing", bold=True, size_pt=11.5, space_before=100, space_after=80))
    doc_body.append(make_p("Both predict.py and eeg_gui_tester.py decode offline 14-channel CSVs at 31.77 ms/epoch CPU compute (14.75 ms load + 0.04 ms preproc + 9.59 ms feat + 7.40 ms cls; workstation offline compute, NOT real-time clinical BCI / DAC acquisition). Excluding all 108 sibling chunks from the 9 test_signals/ blocks yields 0/9 (0.0%), transparently illustrating the cross-block generalization gap.", size_pt=10.0, space_after=120))

    doc_body.append(make_p("5  Conclusion and Future Work", bold=True, size_pt=14.0, space_before=200, space_after=140))
    doc_body.append(make_p(
        "This project audited all 4,044 real human EEGIS epochs under equal-emphasis Leakage-Safe Block-Disjoint Primary and Exploratory "
        "Chunk 5-CV protocols. Under Exploratory Chunk 5-CV matching Lara-Arellano et al. (2025), Stage 1 matches 96.11% Yes/No (90.02% 9-class) "
        "and Stage 2 MDRC-AGA Soft Vote achieves 91.84% (0.9180 F1, Brier 0.156, ECE 0.037). Under Block-Disjoint 5-CV (N_ref=3,936, 328 blocks) "
        "and sibling-excluded offline CSV testing (0/9), all methods cluster near 11.11% chance (PCA+Calibrated RBF-SVM 11.41%, ECE=0.022; Stacker 9.68%, "
        "ECE=0.100), pinpointing non-stationary cross-block transfer and unrecoverable subject IDs as the core scientific frontier.",
        size_pt=10.0, space_after=140
    ))
    doc_body.append(make_p("Future work directions:", bold=True, size_pt=10.5, space_before=80, space_after=60))
    doc_body.append(make_p("1. Riemannian Procrustes Alignment (RPA) for zero-calibration cross-subject BCI transfer.", size_pt=9.5, space_after=40))
    doc_body.append(make_p("2. On-device deployment and benchmarking on low-power Intel NPU and OpenVINO hardware.", size_pt=9.5, space_after=40))
    doc_body.append(make_p("3. Sequential Probability Ratio Testing (SPRT) for sub-500 ms early decision termination.", size_pt=9.5, space_after=40))
    doc_body.append(make_p("4. Prospective clinical validation once cross-block and cross-subject transfer reliably exceed chance.", size_pt=9.5, space_after=160))

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
