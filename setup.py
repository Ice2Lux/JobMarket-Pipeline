from setuptools import find_packages, setup

setup(
    name='formation-de-project_parse',
    description='Allianz FR workflow formation-de-project with Prefect',
    url='https://github.developer.allianz.io/azf-h1-datascience/azfr-formation-de-project.git',

    long_description='file: README.md',

    author='Allianz France AI/Big Data Team',
    author_email='azfrbd@allianz.fr',

    license='UNLICENSED',

    packages=find_packages(include='workflow'),
    python_requires='>=3.10',

    use_azfr_versioning=True
)
