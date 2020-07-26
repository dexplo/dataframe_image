from pathlib import Path
import base64
import io
import re

import mistune
import requests
from nbconvert.preprocessors import Preprocessor


def get_image_files(md_source, only_http=False):
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
        is_http = p.startswith('http://') or p.startswith('https://')
        is_attachment = p.startswith('attachment')
        if p not in image_files:
            if is_http:
                if only_http:
                    image_files.append(p)
            elif not (is_attachment or only_http):
                image_files.append(p)
    return image_files


def replace_md_tables(image_data_dict, md_source, converter, cell_index):
    i = 0
    table = re.compile(r'^ *\|(.+)\n *\|( *[-:]+[-| :]*)\n((?: *\|.*(?:\n|$))*)\n*', re.M)
    nptable = re.compile(r'^ *(\S.*\|.*)\n *([-:]+ *\|[-| :]*)\n((?:.*\|.*(?:\n|$))*)\n*', re.M)
    
    def md_table_to_image(match):
        nonlocal i
        md = match.group()
        html = mistune.markdown(md, escape=False)
        html = '<div>' + html + '</div>'
        image_data = base64.b64decode(converter(html))
        new_image_name = f'markdown_{cell_index}_table_{i}.png'
        image_data_dict[new_image_name] = image_data
        i += 1
        return f'![]({new_image_name})\n\n'
    
    md_source = nptable.sub(md_table_to_image, md_source)
    md_source = table.sub(md_table_to_image, md_source)
    return md_source


def get_image_tags(md_source, only_http=False):
    pat_img_tag = r'''(<img.*?[sS][rR][Cc]\s*=\s*['"](.*?)['"].*?/>)'''
    img_tag_files = re.findall(pat_img_tag, md_source)

    kept_files = []
    for entire_tag, src in img_tag_files:
        is_http = src.startswith('http://') or src.startswith('https://')
        if is_http:
            if only_http:
                kept_files.append((entire_tag, src))
        elif not only_http:
            kept_files.append((entire_tag, src))

    return kept_files


class MarkdownPreprocessor(Preprocessor):

    def preprocess_cell(self, cell, resources, cell_index):
        nb_home = Path(resources['metadata']['path'])
        image_data_dict = resources['image_data_dict']
        if cell['cell_type'] == 'markdown':
            # find normal markdown images 
            all_image_files = get_image_files(cell['source'])
            for i, image_file in enumerate(all_image_files):
                ext = Path(image_file).suffix
                if ext.startswith('.jpg'):
                    ext = '.jpeg'
                new_image_name = f'markdown_{cell_index}_normal_image_{i}{ext}'
                image_data = open(nb_home / image_file, 'rb').read()
                cell['source'] = cell['source'].replace(image_file, new_image_name)
                image_data_dict[new_image_name] = image_data

            # find HTML <img> tags
            all_image_tag_files = get_image_tags(cell['source'])
            for i, (entire_tag, src) in enumerate(all_image_tag_files):
                ext = Path(src).suffix
                if ext.startswith('.jpg'):
                    ext = '.jpeg'
                new_image_name = f'markdown_{cell_index}_local_image_tag_{i}{ext}'
                image_data = open(nb_home / src, 'rb').read()
                image_data_dict[new_image_name] = image_data
                cell['source'] = cell['source'].replace(entire_tag, f'![]({new_image_name})')

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
                    cell['source'] = cell['source'].replace(f'attachment:{image_name}', new_image_name)

            # find markdown tables
            cell['source'] = replace_md_tables(image_data_dict, cell['source'], 
                                               resources['converter'], cell_index)
            
        return cell, resources

# converts DataFrames to images when not executing notebook first
# also converts gifs to png for outputs since jinja template is missing this
# could write a custom template to handle this
class NoExecuteDataFramePreprocessor(Preprocessor):
        
    def preprocess_cell(self, cell, resources, index):
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


# Images displayed with output_type equal to execute_result cause 
# LaTeX formatting issues (undefull hbox). Changing this to display_data
# fixes this, but only works when the execution count number is removed
# This is a hack for a possible bug in nbconvert
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


# Images in markdown from the web must be downloaded locally to make available 
# for latex pdf and markdown conversion. requests is used to get image data
class MarkdownHTTPPreprocessor(Preprocessor):

    def preprocess_cell(self, cell, resources, cell_index):
        temp_dir = resources['temp_dir']
        if cell['cell_type'] == 'markdown':
            all_image_files = get_image_files(cell['source'], True)
            for i, image_file in enumerate(all_image_files):
                ext = Path(image_file).suffix
                if ext.startswith('.jpg'):
                    ext = '.jpeg'
                
                image_data = requests.get(image_file).content
                new_image_name = f'markdown_{cell_index}_normal_http_image_{i}{ext}'
                new_image_name = str(temp_dir / new_image_name)
                cell['source'] = cell['source'].replace(image_file, new_image_name)
                with open(new_image_name, 'wb') as f:
                    f.write(image_data)

            # find HTML <img> tags
            all_image_tag_files = get_image_tags(cell['source'], True)
            for i, (entire_tag, src) in enumerate(all_image_tag_files):
                ext = Path(src).suffix
                if ext.startswith('.jpg'):
                    ext = '.jpeg'

                image_data = requests.get(src).content
                new_image_name = f'markdown_{cell_index}_html_image_tag_{i}{ext}'
                new_image_name = str(temp_dir / new_image_name)
                cell['source'] = cell['source'].replace(entire_tag, f'![]({new_image_name})')
                with open(new_image_name, 'wb') as f:
                    f.write(image_data)

        return cell, resources 
