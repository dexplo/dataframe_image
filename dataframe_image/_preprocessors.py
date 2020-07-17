from pathlib import Path
from tempfile import TemporaryDirectory
import base64
import io
import re
import urllib.parse

import mistune
import requests
from nbconvert.preprocessors import ExecutePreprocessor, Preprocessor


def get_image_files(md_source, is_pdf):
    '''
    Return all image files from a markdown cell

    Parameters
    ----------
    md_source : str
        Markdown text from cell['source']
    '''
    pat_inline = r'\!\[.*?\]\((.*?\.(?:gif|png|jpg|jpeg|tiff|svg))'
    pat_ref = r'\[.*?\]:\s*(.*?\.(?:gif|png|jpg|jpeg|tiff|svg))'
    inline_files = re.findall(pat_inline, md_source)
    ref_files = re.findall(pat_ref, md_source)
    possible_image_files = inline_files + ref_files
    image_files = []
    for file in possible_image_files:
        p = file.strip()
        save_http = is_pdf or not p.startswith('http')
        if p not in image_files and not p.startswith('attachment') and save_http:
            image_files.append(p)
    return image_files


def replace_md_tables(md_source, converter, cell_index):
    i = 0
    table = re.compile(r'^ *\|(.+)\n *\|( *[-:]+[-| :]*)\n((?: *\|.*(?:\n|$))*)\n*', re.M)
    nptable = re.compile(r'^ *(\S.*\|.*)\n *([-:]+ *\|[-| :]*)\n((?:.*\|.*(?:\n|$))*)\n*', re.M)
    
    def md_table_to_image(match):
        nonlocal i
        md = match.group()
        html = mistune.markdown(md, escape=False)
        image_data = base64.b64decode(converter(html))
        new_image_name = f'markdown_{cell_index}_table_{i}.png'
        image_data_dict[new_image_name] = image_data
        i += 1
        return f'![]({new_image_name})'
    
    md_source = nptable.sub(md_table_to_image, md_source)
    md_source = table.sub(md_table_to_image, md_source)
    return md_source


def get_image_tags(md_source):
    pat_img_tag = r'''(<img.*?[sS][rR][Cc]\s*=\s*['"](.*?)['"].*?/>)'''
    img_tag_files = re.findall(pat_img_tag, md_source)
    return img_tag_files


class MarkdownPreprocessor(Preprocessor):

    def preprocess_cell(self, cell, resources, cell_index):
        nb_home = Path(resources['metadata']['path'])
        image_data_dict = resources['image_data_dict']
        temp_dir = resources.get('temp_dir')
        is_pdf = bool(temp_dir)
        if cell['cell_type'] == 'markdown':

            # find normal markdown images 
            # can normal images be http?
            all_image_files = get_image_files(cell['source'], is_pdf)
            for i, image_file in enumerate(all_image_files):
                if image_file.startswith('http://') or image_file.startswith('https://'):
                    r = requests.get(image_file)
                    image_data = r.content
                else:
                    image_data = open(nb_home / image_file, 'rb').read()
                ext = Path(image_file).suffix
                if ext.startswith('.jpg'):
                    ext = '.jpeg'

                if ext == '.gif':
                    from PIL import Image
                    gif = Image.open(io.BytesIO(image_data))
                    buffer = io.BytesIO()
                    gif.save(buffer, 'png')
                    image_data = buffer.getvalue()
                    ext = '.png'
                    
                new_image_name = f'markdown_{cell_index}_normal_image_{i}{ext}'
                if is_pdf:
                    new_image_name = str(temp_dir / new_image_name)
                    open(new_image_name, 'wb').write(image_data)
                cell['source'] = cell['source'].replace(image_file, new_image_name)
                image_data_dict[new_image_name] = image_data

            # find HTML <img> tags
            all_image_tag_files = get_image_tags(cell['source'])
            for i, (entire_tag, src) in enumerate(all_image_tag_files):
                if src.startswith('http://') or src.startswith('https://'):
                    if is_pdf:
                        r = requests.get(src)
                        image_data = r.content
                    else:
                        cell['source'] = cell['source'].replace(entire_tag, f'![]({src})')
                        next
                else:
                    image_data = open(nb_home / src, 'rb').read()
                    ext = Path(src).suffix
                    if ext.startswith('.jpg'):
                        ext = '.jpeg'
                
                new_image_name = f'markdown_{cell_index}_html_image_tag_{i}{ext}'
                if temp_dir:
                    new_image_name = str(temp_dir / new_image_name)
                    open(new_image_name, 'wb').write(image_data)
                replace_str = f'![]({new_image_name})'
                image_data_dict[new_image_name] = image_data
                cell['source'] = cell['source'].replace(entire_tag, replace_str)

            # find images attached to markdown through dragging and dropping
            attachments = cell.get('attachments', {})
            for i, (image_name, data) in enumerate(attachments.items()):
                # I think there is only one image per attachment
                # Though there can be multiple attachments per cell
                # So, this should only loop once
                for j, (mime_type, base64_data) in enumerate(data.items()):
                    ext = mime_type.split('/')[-1]
                    if ext == 'jpg':
                        ext = 'jpeg'
                    new_image_name = f'markdown_{cell_index}_attachment_{i}_{j}.{ext}'
                    
                    image_data = base64.b64decode(base64_data)
                    image_data_dict[new_image_name] = image_data
                    if temp_dir:
                        new_image_name = str(temp_dir / new_image_name)
                        open(new_image_name, 'wb').write(image_data)
                    cell['source'] = cell['source'].replace(f'attachment:{image_name}', new_image_name)

            # find markdown tables
            cell['source'] = replace_md_tables(cell['source'], resources['converter'], cell_index)
            
        return cell, resources


class NoExecuteDataFramePreprocessor(Preprocessor):
        
    def preprocess_cell(self, cell, resources, index):
        nb_home = Path(resources['metadata']['path'])
        converter = resources['converter']
        if cell['cell_type'] == 'code':
            outputs = cell.get('outputs', [])
            for output in outputs:
                if 'data' in output:
                    has_image_mimetype = False
                    for key, value in output['data'].items():
                        if key.startswith('image'):
                            has_image_mimetype = True
                            if key == 'image/gif':
                                # gifs not in jinja template
                                key = 'image/png'
                            output['data'] = {key: value}
                            break

                    if not has_image_mimetype and 'text/html' in output['data']:
                        html = output['data']['text/html']
                        if '</table>' in html and '</style>' in html:
                            output['data'] = {'image/png': converter(html)}
                        elif html.startswith('<img src'):
                            # TODO: Necessary when images from IPython.display module used
                            pass
        return cell, resources 


class ChangeOutputTypePreprocessor(Preprocessor):

    def preprocess_cell(self, cell, resources, cell_index):
        outputs = cell.get('outputs', [])
        for output in outputs:
            if 'data' in output:
                if {'image/png', 'image/jpeg', 'image/gif', 'image/tiff'} & output['data'].keys():
                    if output['output_type'] == 'execute_result':
                        output['output_type'] = 'display_data'
                        del output['execution_count']
        return cell, resources
