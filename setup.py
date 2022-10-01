import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="swrap",
    version="0.1.0",
    license='GPL 3.0',
    description='B-spline modelling CAD and meshing tools.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Jan Brezina',
    author_email='jan.brezina@tul.cz',
    url='https://github.com/geomop/bgem',
    download_url='https://github.com/geomop/bgem/archive/v{__version__}.tar.gz',
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 2 - Pre-Alpha',
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
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    packages=['swrap'],
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': ['smpiexec=swrap.smpiexec:main', ]
    }
)



        


setuptools.setup(
    name='bgem',
    version=__version__,

    include_package_data=True,
    zip_safe=False,
    install_requires=['numpy>=1.13.4', 'pandas', 'scipy', 'bih', 'gmsh>=4.10.4'],
    python_requires='>=3',
    entry_points={
        'console_scripts': [
            'smpiexec = swrap.smpiexec:main',
        ]
    }
)
        
        
        
