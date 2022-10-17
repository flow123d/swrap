import setuptools

__version__="0.1.0"

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="swrap",
    version=__version__,
    license='GPL 3.0',
    description='Utility for full (singularity) containerization of MPI based applications.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Jan Brezina',
    author_email='jan.brezina@tul.cz',
    url='https://github.com/flow123d/swrap',
    download_url='https://github.com/flow123d/swrap/archive/v{__version__}.tar.gz',
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        # uncomment if you test on these interpreters:
        # 'Programming Language :: Python :: Implementation :: IronPython',
        # 'Programming Language :: Python :: Implementation :: Jython',
        # 'Programming Language :: Python :: Implementation :: Stackless',
        'Topic :: Scientific/Engineering',
    ],

    keywords=[
        'MPI', 'containers', 'singularity',
    ],
    # include_package_data=True, # package includes all files of the package directory
    zip_safe=False,
    install_requires=[],
    python_requires='>=3',

    packages=['swrap'],
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': ['smpiexec=swrap.smpiexec:main']
    }
)



        

        
