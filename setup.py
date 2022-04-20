from setuptools import setup, find_packages
from walnut import __version__ as version

setup(
    name="walnut",
    version=version,
    url="https://github.com/iuga/Walnut",
    author="@aperitivo",
    author_email="esteban.delboca@gmail.com",
    install_requires=["click==8.1.2", "chevron==0.14.0"],
    setup_requires=["setuptools", "wheel"],
    python_requires="~=3.9",
    packages=find_packages("src"),
)
