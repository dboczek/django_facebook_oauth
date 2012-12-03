from setuptools import setup

setup(
    name='django-facebook-oauth',
    version='3.0a6-dev',
    description="Facebook OAuth2 authentication for Django.",
    long_description=open('README.markdown').read(),
    author='Jeff Dickey',
    author_email='me@jeffdickey.info',
    url='https://github.com/dickeytk/django_facebook_oauth',
    packages=['facebook', 'facebook.migrations',],
    package_dir={'facebook': 'facebook'},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    zip_safe=False,
)
