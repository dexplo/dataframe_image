import base64
import io
import textwrap

import cssutils
import numpy as np
from lxml.cssselect import CSSSelector
from lxml.html import fromstring
from matplotlib import lines as mlines
from matplotlib import patches as mpatches
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox


class MatplotlibTableConverter:
    def __init__(
        self,
        fontsize=14,
        encode_base64=True,
        crop_top=True,
        for_document=True,
        savefig_dpi=None,
        format="png",
    ):
        self.original_fontsize = fontsize
        self.encode_base64 = encode_base64
        self.crop_top = crop_top
        self.for_document = for_document
        self.figwidth = 1
        self.figheight = 1
        self.wrap_length = 30
        if self.for_document:
            self.figwidth = 20
            self.figheight = 4
            self.wrap_length = 10
        self.dpi = 100
        self.savefig_dpi = savefig_dpi
        self.format = format

    def parse_html(self, tree):

        rows, num_header_rows = self.parse_into_rows(tree)
        num_cols = sum(val[-1] for val in rows[0])
        new_rows = []
        rowspan = {}
        # deal with muti-row or multi col cells
        for i, row in enumerate(rows):
            new_row = []
            col_loc = 0
            j = 0
            while col_loc < num_cols:
                if col_loc in rowspan:
                    val = rowspan[col_loc]
                    val[-2] -= 1
                    cur_col_loc = 0
                    for _ in range(val[-1]):
                        cur_col_loc += 1
                        new_row.append(val[:5])
                    if val[-2] == 1:
                        del rowspan[col_loc]
                    col_loc += cur_col_loc
                else:
                    val = row[j]
                    if val[-2] > 1:  # new rowspan detected
                        rowspan[col_loc] = val
                    col_loc += val[-1]  # usually 1
                    for _ in range(val[-1]):
                        new_row.append(val[:5])
                    j += 1
            new_rows.append(new_row)
        return new_rows, num_header_rows

    def get_text_align(self, element):
        style = element.get("style", "").lower()
        if "text-align" in style:
            idx = style.find("text-align")
            text_align = style[idx + 10 :].split(":")[1].strip()
            for val in ("left", "right", "center"):
                if text_align.startswith(val):
                    return val

    def parse_into_rows(self, tree):
        def get_property(element, property_name):
            for rule in sheet:
                cssselector = CSSSelector(rule.selectorText)
                matching = cssselector(element)
                if matching:
                    for style_property in rule.style:
                        if style_property.name == property_name:
                            return style_property.value

        def parse_row(row):
            values = []
            # rowspan_dict = {}
            # colspan_total = 0
            row_align = self.get_text_align(row)
            for el in row.xpath(".//td|.//th"):
                bold = el.tag == "th"
                colspan = int(el.get("colspan", 1))
                rowspan = int(el.get("rowspan", 1))
                text_align = self.get_text_align(el) or row_align
                text = el.text_content().strip()
                if "id" in el.attrib:
                    values.append(
                        [
                            text,
                            bold,
                            text_align,
                            get_property(el, "background-color"),
                            get_property(el, "color"),
                            rowspan,
                            colspan,
                        ]
                    )
                else:
                    values.append(
                        [text, bold, text_align, "#ffffff", "#000000", rowspan, colspan]
                    )
            return values

        style = tree.find(".//style")
        if style is not None:
            sheet = cssutils.parseString(style.text)
        else:
            sheet = []

        rows = []
        thead = tree.find(".//thead")
        tbody = tree.find(".//tbody")

        if thead is not None:
            head_rows = thead.findall(".//tr")
            if head_rows:
                for row in head_rows:
                    rows.append(parse_row(row))
            else:
                rows.append(parse_row(thead))

        num_header_rows = len(rows)

        if tbody is not None:
            for row in tbody.findall(".//tr"):
                rows.append(parse_row(row))

        if not len(thead) and not len(tbody):
            for row in tree.findall(".//tr"):
                rows.append(parse_row(row))

        return rows, num_header_rows

    def get_text_width(self, text, weight=None):
        fig = self.text_fig
        t = fig.text(0, 0, text, size=self.fontsize, weight=weight)
        bbox = t.get_window_extent(renderer=self.renderer)
        return bbox.width

    def get_all_text_widths(self, rows):
        all_text_widths = []
        for i, row in enumerate(rows):
            row_widths = []
            for vals in row:
                cell_max_width = 0
                for text in vals[0].split("\n"):
                    weight = "bold" if i == 0 else None
                    cell_max_width = max(
                        cell_max_width, self.get_text_width(text, weight)
                    )
                row_widths.append(cell_max_width)
            all_text_widths.append(row_widths)
        # pad = 10  # number of pixels to pad columns with
        return np.array(all_text_widths) + 15

    def calculate_col_widths(self):
        all_text_widths = self.get_all_text_widths(self.rows)
        max_col_widths = all_text_widths.max(axis=0)
        mult = 1
        total_width = self.figwidth * self.dpi
        if self.for_document and sum(max_col_widths) >= total_width:
            while mult > 0.5:
                mult *= 0.9
                for idx in np.argsort(-max_col_widths):
                    col_widths = all_text_widths[:, idx]
                    rows = self.wrap_col(idx, col_widths, mult)
                    all_text_widths = self.get_all_text_widths(rows)
                    max_col_widths = all_text_widths.max(axis=0)
                    if sum(max_col_widths) < total_width:
                        break

            if mult <= 0.5 and self.fontsize > 12:
                self.fontsize *= 0.9
                return self.calculate_col_widths()
            else:
                self.rows = rows
                total_width = sum(max_col_widths)

        col_prop = [width / total_width for width in max_col_widths]
        return col_prop

    def wrap_col(self, idx, col_widths, mult):
        rows = self.rows.copy()
        max_width = max(col_widths)
        texts = [row[idx][0] for row in self.rows]
        new_texts = []
        new_max_width = 0
        for i, (text, col_width) in enumerate(zip(texts, col_widths)):
            if col_width > mult * max_width and len(text) > self.wrap_length:
                width = max(self.wrap_length, int(len(text) * mult))
                new_text = textwrap.fill(text, width, break_long_words=False)
                new_texts.append(new_text)
                new_max_width = max(new_max_width, self.get_text_width(new_text))
            else:
                new_texts.append(text)

        if new_max_width < max_width:
            for row, text in zip(rows, new_texts):
                row[idx][0] = text
        return rows

    def get_row_heights(self):
        row_heights = []
        for row in self.rows:
            row_count = max([val[0].count("\n") + 1 for val in row])
            height = (row_count + 1) * self.fontsize / 72
            row_heights.append(height)

        return row_heights

    def print_table(self):
        figheight = sum(self.row_heights)

        # check table caption
        caption = self.tree.find(".//table//caption")
        if caption is not None:
            caption_text = caption.text_content().strip()
            figheight += self.fontsize / 72

        self.fig = Figure(dpi=self.dpi, figsize=(self.figwidth, figheight))

        row_colors = ["#f5f5f5", "#ffffff"]
        # padding 0.5 em
        padding = self.fontsize / (self.figwidth * self.dpi) * 0.5
        total_width = sum(self.col_widths)

        row_locs = [height / figheight for height in self.row_heights]

        header_text_align = [vals[2] for vals in self.rows[0]]
        x0 = (1 - total_width) / 2
        x = x0
        yd = row_locs[0]
        y = 1

        # table caption
        if caption is not None:
            self.fig.text(
                0.5,
                1 - yd / 2,
                caption_text,
                size=self.fontsize,
                ha="center",
                va="center",
                weight="bold",
            )
            y -= yd

        for i, (yd, row) in enumerate(zip(row_locs, self.rows)):
            x = x0
            y -= yd
            # table zebra stripes
            diff = i - self.num_header_rows
            if diff >= 0 and diff % 2 == 0:
                p = mpatches.Rectangle(
                    (x0, y),
                    width=total_width,
                    height=yd,
                    fill=True,
                    color=row_colors[0],
                    transform=self.fig.transFigure,
                )
                self.fig.add_artist(p)
            for j, (xd, val) in enumerate(zip(self.col_widths, row)):
                text = val[0]
                weight = "bold" if val[1] else None
                ha = val[2] or header_text_align[j] or "right"
                fg = val[4] if val[4] else "#000000"
                bg = val[3] if val[3] else None

                if bg:
                    rect_bg = mpatches.Rectangle(
                        (x, y),
                        width=xd,
                        height=yd,
                        fill=True,
                        color=bg,
                        transform=self.fig.transFigure,
                    )
                    self.fig.add_artist(rect_bg)

                if ha == "right":
                    x_pos = x + xd - padding
                elif ha == "center":
                    x_pos = x + xd / 2
                elif ha == "left":
                    x_pos = x + padding

                self.fig.text(
                    x_pos,
                    y + yd / 2,
                    text,
                    size=self.fontsize,
                    ha=ha,
                    va="center",
                    weight=weight,
                    color=fg,
                    # backgroundcolor=bg
                )
                x += xd

            if i == self.num_header_rows - 1:
                line = mlines.Line2D([x0, x0 + total_width], [y, y], color="black")
                self.fig.add_artist(line)

        w, h = self.fig.get_size_inches()
        start = self.figwidth * min(x0, 0.1)
        end = self.figwidth - start
        bbox = Bbox([[start - 0.1, y * h], [end + 0.1, h]])
        buffer = io.BytesIO()
        self.fig.savefig(
            buffer, bbox_inches=bbox, dpi=self.savefig_dpi, format=self.format
        )
        img_str = buffer.getvalue()
        if self.encode_base64:
            img_str = base64.b64encode(img_str).decode()
        return img_str

    def run(self, html):
        self.fontsize = self.original_fontsize
        self.text_fig = Figure(dpi=self.dpi)
        self.renderer = RendererAgg(self.figwidth, self.figheight, self.dpi)
        html = html.replace("<br></br>", "\n").replace("<br>", "\n").replace("<br/>", "\n")
        self.tree = fromstring(html)
        self.rows, self.num_header_rows = self.parse_html(self.tree)
        self.col_widths = self.calculate_col_widths()
        self.row_heights = self.get_row_heights()
        return self.print_table()
