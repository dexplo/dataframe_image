import io
import base64
import textwrap

from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib import patches as mpatches, lines as mlines
from matplotlib.transforms import Bbox
from matplotlib.backends.backend_agg import RendererAgg


class TableMaker:
    
    def __init__(self, fontsize=14, encode_base64=True, limit_crop=True, for_document=True):
        self.original_fontsize = fontsize
        self.encode_base64 = encode_base64
        self.limit_crop = limit_crop
        self.for_document = for_document
        self.figwidth = .1
        self.figheight = .1
        self.wrap_length = 30
        if self.for_document:
            self.figwidth = 20
            self.figheight = 4
            self.wrap_length = 10
        self.dpi = 100
        
    def parse_html(self, html):
        html = html.replace('<br>', '\n')
        rows, num_header_rows = self.parse_into_rows(html)
        num_cols = sum(val[-1] for val in rows[0])
        new_rows = []
        rowspan = {}
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
                        new_row.append(val[:3])
                    if val[-2] == 1:
                        del rowspan[col_loc]
                    col_loc += cur_col_loc
                else:
                    val = row[j]
                    if val[-2] > 1: # new rowspan detected
                        rowspan[col_loc] = val
                    col_loc += val[-1]  # usually 1
                    for _ in range(val[-1]):
                        new_row.append(val[:3])
                    j += 1
            new_rows.append(new_row)
        return new_rows, num_header_rows
    
    def get_text_align(self, element):
        style = element.get('style', '').lower()
        if 'text-align' in style:
            idx = style.find('text-align')
            text_align = style[idx + 10:].split(':')[1].strip()
            for val in ('left', 'right', 'center'):
                if text_align.startswith(val):
                    return val
    
    def parse_into_rows(self, html):
        def parse_row(row):
            values = []
            rowspan_dict = {}
            colspan_total = 0
            row_align = self.get_text_align(row)
            for el in row.find_all(['td', 'th']):
                bold = el.name == 'th'
                colspan = int(el.attrs.get('colspan', 1))
                rowspan = int(el.attrs.get('rowspan', 1))
                text_align = self.get_text_align(el) or row_align
                text = el.get_text()
                values.append([text, bold, text_align, rowspan, colspan])
            return values

        soup = BeautifulSoup(html, features="lxml")
        # get number of columns from first row
        num_cols = sum(int(el.get('colspan', 1)) for el in soup.find('tr').find_all(['td', 'th']))
        thead = soup.find('thead')
        tbody = soup.find('tbody')
        
        rows = []
        if thead:
            head_rows = thead.find_all('tr')
            if head_rows:
                for row in head_rows:
                    rows.append(parse_row(row))
            else:
                rows.append(parse_row(thead))
                
        num_header_rows = len(rows)
        
        if tbody:
            for row in tbody.find_all('tr'):
                rows.append(parse_row(row))
                
        if not thead and not tbody:
            for row in soup.find_all('tr'):
                rows.append(parse_row(row))
        return rows, num_header_rows
    
    def get_text_width(self, text):
        fig = self.text_fig
        t = fig.text(0, 0, text, size=self.fontsize)
        bbox = t.get_window_extent(renderer=self.renderer)
        return bbox.width
    
    def get_all_text_widths(self, rows):
        all_text_widths = []
        for row in rows:
            row_widths = []
            for vals in row:
                cell_max_width = 0
                for text in vals[0].split('\n'):
                    cell_max_width = max(cell_max_width, self.get_text_width(text))
                row_widths.append(cell_max_width)
            all_text_widths.append(row_widths)
        pad = 10 # number of pixels to pad columns with
        return np.array(all_text_widths) + 15
    
    def calculate_col_widths(self):
        all_text_widths = self.get_all_text_widths(self.rows)
        max_col_widths = all_text_widths.max(axis=0)        
        mult = 1
        total_width = self.figwidth * self.dpi
        if self.for_document and sum(max_col_widths) >= total_width:
            while mult > .5:
                mult *= .9
                for idx in np.argsort(-max_col_widths):
                    col_widths = all_text_widths[:, idx]
                    rows = self.wrap_col(idx, col_widths, mult)
                    all_text_widths = self.get_all_text_widths(rows)
                    max_col_widths = all_text_widths.max(axis=0)
                    if sum(max_col_widths) < total_width:
                        break
                    
            if mult <= .5 and self.fontsize > 12:
                self.fontsize *= .9
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
            row_count = max([val[0].count('\n') + 1 for val in row])
            height = (row_count + 1) * self.fontsize / 72
            row_heights.append(height)
            
        return row_heights
    
    def create_figure(self):
        figheight = sum(self.row_heights)
        fig = Figure(dpi=self.dpi, figsize=(self.figwidth, figheight))
        return fig
        
    def print_table(self):
        row_colors = ["#f5f5f5", "#ffffff"]
        total_width = sum(self.col_widths)
        figheight = self.fig.get_figheight()
        row_locs = [height / figheight for height in self.row_heights]
            
        header_text_align = [vals[2] for vals in self.rows[0]]
        x0 = (1 - total_width) / 2
        x = x0
        yd = row_locs[0]
        y = 1
            
        for i, (yd, row) in enumerate(zip(row_locs, self.rows)):
            x = x0
            y -= yd
            for j, (xd, val) in enumerate(zip(self.col_widths, row)):
                text = val[0]
                weight = 'bold' if val[1] else None
                ha = val[2] or header_text_align[j] or 'right'

                if ha == 'right':
                    x += xd
                elif ha == 'center':
                    x += xd / 2
                self.fig.text(x, y + yd / 2, text, family='Helvetica', 
                              size=self.fontsize, ha=ha, va='center', weight=weight)
                if ha == 'left':
                    x += xd
                elif ha == 'center':
                    x += xd / 2
                
            diff = i - self.num_header_rows
            if diff >= 0 and  diff % 2 == 0:
                p = mpatches.Rectangle((x0, y), width=total_width, height=yd, fill=True, 
                                       color='#f5f5f5', transform=self.fig.transFigure)
                self.fig.add_artist(p)  
                
            if i == self.num_header_rows - 1:
                line = mlines.Line2D([x0, x0 + total_width], [y, y], color='black')
                self.fig.add_artist(line)
                
        w, h = self.fig.get_size_inches()
        start = self.figwidth * min(x0, .1)
        end = self.figwidth - start
        bbox = Bbox([[start - .1, y * h], [end + .1, h]])
        buffer = io.BytesIO()
        self.fig.savefig(buffer, bbox_inches=bbox)
        img_str = buffer.getvalue()
        if self.encode_base64:
            img_str = base64.b64encode(img_str).decode()
        return img_str

    def run(self, html):
        self.fontsize = self.original_fontsize
        self.text_fig = Figure(dpi=self.dpi)
        self.renderer = RendererAgg(self.figwidth, self.figheight, self.dpi)
        self.rows, self.num_header_rows = self.parse_html(html)
        self.col_widths = self.calculate_col_widths()
        self.row_heights = self.get_row_heights()
        self.fig = self.create_figure()
        return self.print_table()
