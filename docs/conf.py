# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'ELabFTW API'
copyright = '2024, Joshua Taillon'
author = 'Joshua Taillon'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinxcontrib.apidoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'myst_parser'
]
autosummary_generate = True  
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
source_suffix = ['.rst', '.md']

apidoc_module_dir = '../elabapi'
apidoc_output_dir = 'api_reference'
apidoc_excluded_paths = ['tests']
apidoc_separate_modules = False

autodoc_typehints = "description"
autodoc_typehints_format = "short"
autodoc_class_signature = "separated"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']

# -- Options for intersphinx extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': (' https://requests.readthedocs.io/en/master', None)
}
