from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in kartoza/__init__.py
from kartoza import __version__ as version

setup(
	name="kartoza",
	version=version,
	description="kartoza",
	author="Aerele",
	author_email="kartoza@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
