from distutils.core import setup


setup(
    name = 'end2',
    packages = ['end2'],
    version = '1.3',
    license='MIT',  # https://help.github.com/articles/licensing-a-repository
    description = 'A Minimal E2E Test Automation Framework',
    author = 'Jon Wesneski',
    author_email = 'jonwes2@gmail.com',
    url = 'https://github.com/jonwesneski/end2',
    keywords = ['end-2-end', 'end2end', 'end-to-end', 'endtoend', 'e2e', 'end2', 'testing', 'qa', 'automation'],
    install_requires=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Testing :: Acceptance',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
