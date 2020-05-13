def _jupyter_bundlerextension_paths():
    return [{
        'name': 'dataframe_image_bundler_pdf',                
        'label': 'PDF - DataFrames as Images',             
        'module_name': 'dataframe_image._notebook_bundler',   
        'group': 'download'
    }]

def bundle(handler, model):
    """Transform, convert, bundle, etc. the notebook referenced by the given
    model.

    Then issue a Tornado web response using the `handler` to redirect
    the user's browser, download a file, show a HTML page, etc. This function
    must finish the handler response before returning either explicitly or by
    raising an exception.

    Content manager API
    https://jupyter-notebook.readthedocs.io/en/stable/extending/contents.html

    Parameters
    ----------
    handler : tornado.web.RequestHandler
        Handler that serviced the bundle request
    model : dict
        Notebook model from the configured ContentManager
    """
    from ._convert import convert
    convert(model['path'], 'md', limit=15, save_notebook=True, document_name='test returner',
            image_dir_name='some_images', output_dir='Desktop')
    handler.finish('I bundled {}!'.format(model['path']))