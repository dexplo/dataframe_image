from pathlib import Path
import base64
import io
import re

import requests
from nbconvert.preprocessors import ExecutePreprocessor, Preprocessor

from ._screenshot import make_repr_png

def get_image_files(md_source):
    '''
    Return all image files from a markdown cell

    Parameters
    ----------
    md_source : str
        Markdown text from cell['source']
    '''
    pat_inline = r'\!\[.*?\]\((.*?\.(?:gif|png|jpg|jpeg|tiff))'
    pat_ref = r'\[.*?\]:\s*(.*?\.(?:gif|png|jpg|jpeg|tiff))'
    inline_files = re.findall(pat_inline, md_source)
    ref_files = re.findall(pat_ref, md_source)
    possible_image_files = inline_files + ref_files
    image_files = []
    for file in possible_image_files:
        p = file.strip()
        if p not in image_files and not p.startswith('attachment'):
            image_files.append(p)
    return image_files

def get_image_tags(md_source):
    pat_img_tag = r'''(<img.*?[sS][rR][Cc]\s*=\s*['"](.*?)['"].*?/>)'''
    img_tag_files = re.findall(pat_img_tag, md_source)
    return img_tag_files

class MarkdownPreprocessor(Preprocessor):

    def __init__(self, nb_home, final_nb_home, output_files_dir):
        super().__init__()
        self.nb_home = nb_home
        self.final_nb_home = final_nb_home
        self.output_files_dir = Path(output_files_dir)
        self.cwd_relative_image_dir = self.final_nb_home / self.output_files_dir

    def preprocess_cell(self, cell, resources, cell_index):
        if cell['cell_type'] == 'markdown':
            all_image_files = get_image_files(cell['source'])
            # find normal markdown images
            for i, image_file in enumerate(all_image_files):
                if image_file.startswith('http'):
                    response = requests.get(image_file)
                    image_data = response.content
                    ext = '.' + response.headers['Content-Type'].split('/')[-1]
                else:
                    image_data = open(self.nb_home / image_file, 'rb').read()
                    ext = Path(image_file).suffix

                if ext == '.gif':
                    from PIL import Image
                    gif = Image.open(io.BytesIO(image_data))
                    image_data = io.BytesIO()
                    gif.save(image_data, 'png')
                    image_data.seek(0)
                    image_data = image_data.read()
                    ext = '.png'
                    
                new_image_name = f'markdown_{cell_index}_normal_image_{i}{ext}'
                # Relative to where this conversion is run
                cwd_relative_image_fn = self.cwd_relative_image_dir / new_image_name
                # Relative to .ipynb notebook
                nb_relative_image_fn = self.output_files_dir / new_image_name
                with open(cwd_relative_image_fn, 'wb') as f:
                    f.write(image_data)
                replace_str = str(nb_relative_image_fn).replace(' ', '%20')
                cell['source'] = cell['source'].replace(image_file, replace_str)

            # find HTML <img> tags
            all_image_tag_files = get_image_tags(cell['source'])
            for i, (entire_tag, src) in enumerate(all_image_tag_files):
                if src.startswith('http'):
                    response = requests.get(src)
                    image_data = response.content
                    ext = '.' + response.headers['Content-Type'].split('/')[-1]
                else:
                    image_data = open(self.nb_home / src, 'rb').read()
                    ext = Path(src).suffix

                new_image_name = f'markdown_{cell_index}_html_image_tag_{i}{ext}'
                # Relative to where this conversion is run
                cwd_relative_image_fn = self.cwd_relative_image_dir / new_image_name
                # Relative to .ipynb notebook
                nb_relative_image_fn = self.output_files_dir / new_image_name
                with open(cwd_relative_image_fn, 'wb') as f:
                    f.write(image_data)
                
                replace_str = f'![]({nb_relative_image_fn})'.replace(' ', '%20')
                cell['source'] = cell['source'].replace(entire_tag, replace_str)

            # find images attached to markdown through dragging and dropping
            attachments = cell.get('attachments', {})
            for i, (image_name, data) in enumerate(attachments.items()):
                # I think there is only one image per attachment
                # Though there can be multiple attachments per cell
                # So, this should only loop once
                for j, (mime_type, base64_data) in enumerate(data.items()):
                    ext = '.' + mime_type.split('/')[-1]
                    new_image_name = f'markdown_{cell_index}_attachment_{i}_{j}{ext}'
                    # Relative to where this conversion is run
                    cwd_relative_image_fn = self.cwd_relative_image_dir / new_image_name
                    # Relative to .ipynb notebook
                    nb_relative_image_fn = self.output_files_dir / new_image_name
                    b64_bytes = base64.b64decode(base64_data)
                    with open(cwd_relative_image_fn, 'wb') as f:
                        f.write(b64_bytes)
                    replace_str = str(nb_relative_image_fn).replace(' ', '%20')
                    cell['source'] = cell['source'].replace(f'attachment:{image_name}', replace_str)
        return cell, resources
    

class ChangeOutputTypeExecutePreprocessor(ExecutePreprocessor):

    def preprocess_cell(self, cell, resources, cell_index):
        cell, resources = super().preprocess_cell(cell, resources, cell_index)
        outputs = cell.get('outputs', [])
        for output in outputs:
            if 'data' in output:
                if {'image/png', 'image/jpeg', 'image/gif', 'image/tiff'} & output['data'].keys():
                    if output['output_type'] == 'execute_result':
                        output['output_type'] = 'display_data'
                        del output['execution_count']
        return cell, resources


class NoExecuteDataFramePreprocessor(Preprocessor):

    ss_creator = staticmethod(make_repr_png())  
        
    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            outputs = cell.get('outputs', [])
            for output in outputs:
                if 'data' in output and 'text/html' in output['data']:
                    html = output['data']['text/html']
                    if '</table>' in html and '</style>' in html:
                        output['data']['image/png'] = self.ss_creator(html)
                    if output['output_type'] == 'execute_result':
                        output['output_type'] = 'display_data'
                        del output['execution_count']
        return cell, resources
