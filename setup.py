from distutils.core import setup


setup(
    name = 'end2',
    packages = ['end2'],
    version = '1.0',
    license='MIT',        # Chose a license from here: https://help.github.com/articles/licensing-a-repository
    description = 'A Minimal E2E Test Automation Framework',
    author = 'Jon Wesneski',
    author_email = 'jonwes2@gmail.com',
    url = 'https://github.com/jonwesneski/end2',
    download_url = 'https://github.com/jonwesneski/end2/v_01.tar.gz',    # I explain this later on
    keywords = ['end-2-end', 'end2end', 'end-to-end', 'endtoend', 'e2e', 'end2', 'testing', 'qa', 'automation'],
    install_requires=[],
    classifiers=[
        'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Testing :: Acceptance',
        'License :: OSI Approved :: MIT License',   # Again, pick a license
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)