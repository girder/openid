from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = [
    'girder>=3.0.0a1',
    'python-openid2'
]

setup(
    author="Zach Mullen",
    author_email='zach.mullen@kitware.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    description='Allows users to log into Girder using OpenID 1.0 providers',
    install_requires=requirements,
    license='Apache Software License 2.0',
    long_description=readme,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='girder-plugin, openid',
    name='girder-openid',
    packages=find_packages(exclude=['test', 'test.*']),
    url='https://github.com/girder/openid',
    version='0.1.0',
    zip_safe=False,
    entry_points={
        'girder.plugin': [
            'openid = girder_openid:GirderPlugin'
        ]
    }
)
