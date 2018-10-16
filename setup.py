"""Build setup for package"""
from setuptools import setup

def readme():
    """Method to add readme file as long_description."""
    with open('README.rst') as fhandle:
        return fhandle.read()

setup(name='heatmisercontroller',
      version='0.36',
      description='Python implementation of Heatmiser protocol for serial connected thermostats ',
      long_description=readme(),
      classifiers=[
        'Programming Language :: Python :: 2.7',
      ],
      url='https://github.com/ianhorsley/heatmisercontroller',
      author='Ian Horsley',
      #author_email='flyingcircus@example.com',
      license='GNU v3.0',
      packages=['heatmisercontroller'],
      install_requires=[
        'datetime',
        'logging',
        'pyserial',
        'configobj'
      ],
      test_suite="tests",
      scripts=[
        'bin/hm_get_example.py',
        'bin/hm_set_example.py'
      ],

      include_package_data=True,
      zip_safe=False)
