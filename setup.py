from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in payment_commision_update/__init__.py
from payment_commision_update import __version__ as version

setup(
	name='payment_commision_update',
	version=version,
	description='Payment Commision Update',
	author='Mentum Group',
	author_email='aryrosa.fuentes@MENTUM.group',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
