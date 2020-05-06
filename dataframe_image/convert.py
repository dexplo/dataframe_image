import os
import shutil
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import MarkdownExporter, PDFExporter


class MetaExecutePreprocessor(ExecutePreprocessor):

    def preprocess_cell(self, cell, resources, cell_index):
        cell, resources = super().preprocess_cell(cell, resources, cell_index)
        # maybe use tags later
        tags = cell['metadata'].get('tags', [])
            
        outputs = cell.get('outputs', [])
        for output in outputs:
            if 'data' in output:
                if 'image/png' in output['data']:
                    if output['output_type'] == 'execute_result':
                        output['output_type'] = 'display_data'
                        del output['execution_count']
        return cell, resources

def execute_notebook(name, nb_home, limit):
    with open(name) as f:
        nb = nbformat.read(f, as_version=4)

    if limit > -1:
        nb['cells'] = nb['cells'][:limit]

    resources = {'metadata': {'path': './' + nb_home}}
    ep = MetaExecutePreprocessor(timeout=600, kernel_name='python3', allow_errors=True, 
                                 extra_arguments=["--InteractiveShellApp.code_to_run='from dataframe_image._to_image import pd'"])

    ep.preprocess(nb, resources)
    return nb

def convert(name, limit=-1):
    nb_home = os.path.dirname(name)
    images_home = os.path.join(nb_home, 'images_from_dataframe_image')
    if os.path.isdir(images_home):
        shutil.rmtree(images_home)
    os.mkdir(images_home)
    nb = execute_notebook(name, nb_home, limit)

    resources = {'metadata': {'path': nb_home}, 
                 'output_files_dir': images_home}
    # TODO: need to list all types
    me = MarkdownExporter(config={'NbConvertBase': {'display_data_priority': ['image/png', 'text/html', 'text/plain']}})
    md_data, output_resources = me.from_notebook_node(nb, resources)

    # the base64 encoded binary files are saved in output_resources
    for filename, data in output_resources['outputs'].items():
        with open(filename, 'wb') as f:
            f.write(data)

    final_file = name[:-name[::-1].find('.') - 1]

    with open(f'{final_file}.md', mode='w') as f:
        f.write(md_data)

    pdf = PDFExporter()
    pdf_data, resources = pdf.from_notebook_node(nb, resources={'metadata':{'name': final_file, 'path': nb_home}})
    with open(f'{final_file}.pdf', mode='wb') as f:
        f.write(pdf_data)

    return nb