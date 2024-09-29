from setuptools import setup, find_packages

setup(
    name="wavetabler",  # The name of your package
    version="0.1.0-alpha",  # Correct version for your alpha release
    author="Rich Rath",  # Your name
    author_email="rath@way.net",  # Your email
    description="A tool for creating wavetables from audio files",  # Project description
    long_description=open("README.md").read(),  # Long description from README.md
    long_description_content_type="text/markdown",
    url="https://github.com/rcrath/wavetabler",  # GitHub URL
    packages=find_packages(where="src"),  # Package discovery inside the 'src' directory
    package_dir={"": "src"},  # Specify src as the package directory
    python_requires=">=3.11",  # Minimum Python version
    install_requires=[
        "numpy",
        "scipy",
        "librosa",
        "resampy",
        "soundfile",
        "pydub",
        "matplotlib",
        "pandas",
        "tabulate"
    ],  # Dependencies
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",  # Correct license
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",  # Alpha release
    ],
    entry_points={
        "console_scripts": [
            "wvtbl=wavetabler.a_wvtbl:main",  # Entry point for wvtbl command
        ],
    },
)
