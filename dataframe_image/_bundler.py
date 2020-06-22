from pathlib import Path
import json
import base64

from tornado import gen


def _jupyter_bundlerextension_paths():
    return [{
        "name": "dataframe_image_bundler",
        "module_name": "dataframe_image._bundler",
        "label" : "DataFrame as Image",
        "group" : "download",
    }]


def convert(model, handler):
    from ._convert import Converter

    arguments = ['to', 'use', 'centerdf', 'latex_command', 'max_rows', 'max_cols', 
                 'ss_width', 'ss_height', 'resize', 'chrome_path', 'limit', 
                 'document_name', 'execute', 'save_notebook', 'output_dir', 'image_dir_name']

    kwargs = {arg: handler.get_query_argument(arg, None) for arg in arguments}
    path = model['path']
    kwargs['filename'] = path
    kwargs['to'] = kwargs['to']
    if kwargs['to'] == 'both':
        kwargs['to'] = ['md', 'pdf']
    kwargs['use'] == kwargs['use'] or None
    kwargs['centerdf'] = kwargs['centerdf'] == "True"
    kwargs['latex_command'] = [tag.strip() for tag in kwargs['latex_command'].split()]
    kwargs['max_rows'] = 30 if kwargs['max_rows'] == '' else int(kwargs['max_rows'])
    kwargs['max_cols'] = 10 if kwargs['max_cols'] == '' else int(kwargs['max_cols'])
    kwargs['ss_width'] = 1000 if kwargs['ss_width'] == '' else int(kwargs['ss_width'])
    kwargs['ss_height'] = 900 if kwargs['ss_height'] == '' else int(kwargs['ss_height'])
    kwargs['resize'] = 1 if kwargs['resize'] == '' else float(kwargs['resize'])
    kwargs['chrome_path'] = kwargs['chrome_path'] or None
    kwargs['limit'] = None if kwargs['limit'] == '' else int(kwargs['limit'])
    kwargs['document_name'] = kwargs['document_name'] or None
    kwargs['execute'] = kwargs['execute'] == "True"
    kwargs['save_notebook'] = kwargs['save_notebook'] == "True"
    kwargs['output_dir'] = kwargs['output_dir'] or None
    kwargs['image_dir_name'] = kwargs['image_dir_name'] or None
    kwargs['web_app'] = True
   
    try:
        print(kwargs['centerdf'] )
        c = Converter(**kwargs)
        print(c.centerdf)
        c.convert()
        data = c.return_data
    except Exception as e:
        data = {'app_status': 'fail', 
                'error_data': str(e)}
    else:
        if 'pdf_data' in data or 'md_data' in data:
            data['app_status'] = "success"
        else:
            data = {'app_status': 'fail', 
                    'error_data': 'Error: \n' + str(data)}

    return data


def read_static_file(name):
    mod_path = Path(__file__).parent
    html_path = mod_path / 'static' / name
    return open(html_path).read()


def get_html_fail(data):
    error_data = data['error_data']
    error_message = json.dumps(error_data)
    html = read_static_file('fail.html')
    return html.format(error_message=error_message)


# synchronous execution
def bundle(handler, model):
    """
    Parameters
    ----------
    handler : tornado.web.RequestHandler
        Handler that serviced the bundle request
    model : dict
        Notebook model from the configured ContentManager
    """
    app_status = handler.get_query_argument('app_status', None)
    
    if app_status is None:
        html = read_static_file('form.html')
        handler.write(html)
    elif app_status == 'waiting':
        print('in waiting')
        data = convert(model, handler)        
        if data['app_status'] == 'fail':
            html = get_html_fail(data)
            handler.write(html)
            handler.finish()
        else:
            filename = Path(model['name']).stem
            s = base64.b64encode(data['pdf_data']).decode()
            js = read_static_file('download.html').format(s=s, filename=filename)
            handler.write(js)
