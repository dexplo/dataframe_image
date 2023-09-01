import re

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dataframe_image",
    author="Ted Petrou",
    author_email="petrou.theodore@gmail.com",
    description="Embed pandas DataFrames as images in pdf and markdown files when "
    "converting from Jupyter Notebooks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="jupyter notebook pandas dataframe image pdf markdown",
    url="https://github.com/dexplo/dataframe_image",
    packages=setuptools.find_packages(),
    license="MIT",
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=0.24",
        "nbconvert>=5",
        "aiohttp",
        "requests",
        "pillow",
        "packaging",
        "mistune",
        "lxml",
        "beautifulsoup4",
        "cssutils",
        "html2image",
        "ChromeController",
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": ["dataframe_image=dataframe_image._command_line:main"]
    },
    data_files=[
        (
            "etc/jupyter/nbconfig/notebook.d",
            ["jupyter-config/nbconfig/notebook.d/dataframe_image.json"],
        )
    ],
    use_scm_version={
        "write_to": "dataframe_image/_version.py",
        "write_to_template": '__version__ = "{version}"',
        "local_scheme": "node-and-date"
        # 'tag_regex': r'^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$',
    },
    setup_requires=["setuptools_scm"],
)
