import setuptools
import re

with open("README.md", "r") as fh:
    long_description = fh.read()

pat = r'!\[gif\]\('
repl = r'![gif](https://raw.githubusercontent.com/dexplo/dataframe_image/master/'
long_description = re.sub(pat, repl, long_description)

setuptools.setup(
    name="dataframe_image",
    version="0.0.1",
    author="Ted Petrou",
    author_email="petrou.theodore@gmail.com",
    description="Embed pandas DataFrames as images in pdf and markdown files when converting Jupyter Notebooks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dexplo/dataframe_image",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True
)