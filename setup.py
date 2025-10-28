from setuptools import setup, find_packages

setup(
    name='cash_flow_app',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['frappe'],
)
