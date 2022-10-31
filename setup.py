from setuptools import find_packages, setup

VERSION = '0.0.1'

setup(
    name='LogCheck',
    version=VERSION,
    description='Logsight AutoLogger',
    long_description='',
    long_description_content_type='text/x-rst',
    author='logsight.ai',
    author_email='support@logsight.ai',
    license='unlicense',
    packages=find_packages(),
    package_data={'': ['license.txt']},
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
    install_requires=[
        "requests",
        "python-dateutil",
        "tree-sitter==0.20.0"
    ],
    zip_safe=False
)
