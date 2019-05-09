from setuptools import setup, find_packages
from os import path
from io import open

setup_dir = path.abspath(path.dirname(__file__))
with open(path.join(setup_dir, 'README.md'),
          encoding='utf-8') as readme_file:
    long_description = readme_file.read()

setup(
    name="cr_download",
    version="0.92.1",
    package_dir={'':'packages'},
    packages=find_packages(),

    scripts=["bin/critrole_download",
             "bin/autocut_vod"],

    include_package_data=True,

    install_requires=[
        'pyacoustid',
        'streamlink',
        'ruamel.yaml>=0.15.0, <=0.15.87',
        'requests',
        'google-api-python-client',
        'progressbar2',
        'future',
        'pathlib'
    ],

    author="Teddy Weisman",
    author_email="tjweisman@gmail.com",
    license='MIT',
    url="https://github.com/tjweisman/cr_download",

    description="""Tool to download and automatically edit Critical Role
    episodes.""",

    long_description=long_description,
    long_description_content_type='text/markdown'
)
