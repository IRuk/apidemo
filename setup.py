from setuptools import find_packages
from setuptools import setup

setup(name='demo-api',
      version='0.1',
      description='A demo API',
      url=None,
      author='Ian Rankin',
      author_email='ian.in.text@gmail.com',
      license='MIT',
      packages=find_packages(),
      namespace_packages=['demo'],
      include_package_data=True,
      zip_safe=True,
      test_suite='demo.api.tests',
      install_requires=[
          'colander==1.7.0',
          'cornice==0.17',
          'httplib2',
          'docopt',
          'Jinja2',
          'PyMySQL',
          'pyramid==1.10.4',
          'pyramid-jinja2==1.6',
          'pyramid-tm==2.2.1',
          'pytz',
          'requests',
          'rpdb',
          'SQLAlchemy',
          'waitress',
          'zope.sqlalchemy',
          'cryptography'
      ],
      entry_points="""\
      [paste.app_factory]
      main = demo.api:main
      [console_scripts]
      demo-api-initialisedb = demo.api.scripts.init_db:main
      demo-api-updatedb = demo.api.scripts.update_db:main
      """)
