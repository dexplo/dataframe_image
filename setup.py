import setuptools
import re

with open('README.md', 'r') as fh:
    long_description = fh.read()

pat = r'!\[png\]\('
repl = r'![png](https://raw.githubusercontent.com/dexplo/dataframe_image/master/'

long_description = re.sub(pat, repl, long_description)

setuptools.setup(
    name='dataframe_image',
    version='0.0.7',
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
    install_requires=['pandas>=0.24', 'nbconvert>=5', 'pillow'],
    include_package_data=True,
    entry_points = {
        'console_scripts': ['dataframe_image=dataframe_image._command_line:main'],
        'nbconvert.exporters': ['dataframe_image_bundler_pdf=dataframe_image._exporters:DataFramePDFExporter']
    },
)