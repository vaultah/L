from setuptools import setup, Command
from pathlib import Path
from pip.req import parse_requirements
from pip.download import PipSession

__version__ = '0.0.1'


ROOT = Path(__file__).resolve().parent

it = parse_requirements(str(ROOT / 'requirements.txt'),
                        session=PipSession())

setup(
    name='L',
    license='MIT',
    url='https://github.com/vaultah/L',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Bottle',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    version=__version__,
    install_requires=[str(ir.req) for ir in it],
)