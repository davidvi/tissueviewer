import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='ImmunoViewer',
    author='David van IJzendoorn',
    author_email='davidvanijzendoorn@gmail.com',
    description='Discover and annotate your (multi-channel) big TIF files with this user-friendly viewer',
    keywords='big tif, immuno, viewer, annotate, annotation, discover, discovery, image, images, tif, tiff, multi-channel, multi c',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tomchen/example_pypi_package',
    project_urls={
        'Documentation': 'https://github.com/davidvi/ImmunoViewer',
        'Bug Reports':
        'https://github.com/davidvi/ImmunoViewer/issues',
        'Source Code': 'https://github.com/davidvi/ImmunoViewer'
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=[
        # see https://pypi.org/classifiers/
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'flask==2.2.3',
        'numpy==1.24.2',
        'openslide-python==1.2.0',
        'pillow==9.4.0',
        'opencv-python==4.7.0.72',
        'matplotlib==3.7.1',
        'Flask-Cors==3.0.10',
        ],
    entry_points={
    'console_scripts': [
        'ImmunoViewerProcess=ImmunoViewer.process_folder:main',
        'ImmunoViewerServer=ImmunoViewer.server:main',
    ],
},
)