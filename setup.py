from setuptools import setup, find_packages
from os import path

setup_dir = path.abspath(path.dirname(__file__))
with open(path.join(setup_dir, 'README.md'),
          encoding='utf-8') as readme_file:
    long_description = readme_file.read()

setup(
    name="cr_download",
    version="0.9",
    packages=find_packages(),
    scripts=["bin/critrole_download",
             "bin/autocut_vod"],

    package_data={
        '':['share/config.yaml',
            'share/sound_files/*']
    },

    install_requires=[
        'pyacoustid',
        'streamlink',
        'tqdm',
        'pyyaml',
        'requests',
        'google-api-python-client',
        'progressbar2'
    ],

    author="Teddy Weisman",
    author_email="tjweisman@gmail.com",
    license='MIT',
    url="https://github.com/tjweisman/cr_download",

    description="""Tool to download Critical Role episodes from
    the Geek & Sundry Twitch channel, convert to audio, and recut.""",

    long_description=long_description,
    long_description_content_type='text/markdown'
)
