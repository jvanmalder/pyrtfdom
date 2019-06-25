from distutils.core import setup
import setuptools
setup(
  name = 'pyrtfdom',
  packages = setuptools.find_packages(),
  version = '1.0',
  license='gpl-3.0',
  description = 'Parses RTF documents into a DOM-like structure',
  author = 'https://github.com/crankycyclops',
  url = 'https://github.com/jvanmalder/pyrtfdom',
  keywords = ['RTF', 'DOM'],
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: GPL 3.0 License',
    'Programming Language :: Python :: 3'
  ],
)
