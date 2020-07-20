import setuptools
import re

with open('dataframe_image/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split("'")[1]

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='dataframe_image',
    version=version,
    author='Ted Petrou',
    author_email='petrou.theodore@gmail.com',
    description='Embed pandas DataFrames as images in pdf and markdown files when '
                'converting from Jupyter Notebooks',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='jupyter notebook pandas dataframe image pdf markdown',
    url='https://github.com/dexplo/dataframe_image',
    packages=setuptools.find_packages(),
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=['pandas>=0.24', 'nbconvert>=5', 'aiohttp', 
                      'matplotlib>=3.1', 'beautifulsoup4'],
    include_package_data=True,
    entry_points = {'console_scripts': ['dataframe_image=dataframe_image._command_line:main']},
    data_files=[("etc/jupyter/nbconfig/notebook.d", [
                "jupyter-config/nbconfig/notebook.d/dataframe_image.json"])],
)
