from setuptools import setup, find_packages
setup(
    name="cr_download",
    version="1.0",
    packages=find_packages(),
    scripts=["bin/critrole_download",
             "bin/autocut_vod"],

    package_data={
        '':['share/config.yaml',
            'share/sound_files/*']
    },

    author="Teddy Weisman"
)
