import re

import setuptools

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',  # It excludes inline comment too
    open('kg_rabbitmq/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="kg_rabbitmq",
    version=__version__,
    author="Rangel Reale",
    author_email="rangelspam@gmail.com",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RangelReale/kg_rabbitmq",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)