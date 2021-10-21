"""
Setup file for swdict
"""

from setuptools import setup, find_packages

setup(
    name='swdict',
    version='0.1.0',
    license='MIT',
    description='SW dictionary utilities',
    long_description='',

    author='Tadahiro Matsumoto',
    author_mail='tad@gifu-u.ac.jp',
    url='http://www.mat.info.gifu-u.ac.jp/jspad/',

    packages=['swdict'],

    include_package_data=True
)
#    packages=find_packages(where='src'),
#    package_dir={'': 'src'},
