Development environment setup
=============================

1. Clone the nexgen repository

.. code-block:: console

    git clone git@github.com:DiamondLightSource/nexgen.git
    cd nexgen


2. Create virtual environment and pip install

.. code-block:: console

    python -m venv .venv
    source .venv/bin/activate

    pip install -e .[dev]


3. Install pre-commits

.. code-block:: console

    pre-commit install


4. Run pytest

.. code-block:: console

    pytest .



Creating a release using bump-my-version
========================================

From inside a development environment, a release can be created from the command line using bump-my-version. If not present, tha package can be pip installed.

.. code-block:: console

    pip install bump-my-version


First, choose a release number and run bump2version in "pretend" mode with the to check that the final version will be updated correctly.

.. code-block:: console

    bump-my-version bump --dry-run {major,minor,patch} --verbose


Once sure of the release number, run bump2version and push the the tags for the new version.


.. code-block:: console

    bump-my-version bump {major,minor,patch} --verbose
    git push --tags
    git push


After the second `git push`, the release will be published automatically both to Github and PYPI.


Creating a release from Github
==============================

1. Create a new branch from main named pre followed by the release version e.g. pre_v0.1.0. The release versions should look like v{major}.{minor}.{patch}.
2. If you haven't run bump2version without creating tags, on this branch change manually change the version in `pyproject.toml` and `src/nexgen/__init__.py`.
3. Go `here https://github.com/DiamondLightSource/nexgen/releases/new`.
4. Select Choose a new tag and type the version of the release, then select the branch created in step 1 as the target.
5. Click on Generate release notes. This will create a starting set of release notes based on PR titles since the last release.
6. You should now manually go through each line on the release notes and read it from the perspective of a beamline scientist. It should be clear from each what the change means to the beamline and should have links to easily find further info.
7. Publish the release



Deciding release numbers
------------------------

Releases should obviously be versioned higher than the previous latest release. Otherwise you should follow this guide:

    * **Major** - Large code rewrites
    * **Minor** - New features
    * **Patch** - Small changes and bug fixes


Keeping the changelog up to date
--------------------------------

Please make sure before every release that a few lines are added to the `CHANGELOG.md` file describing the changes.

    * **Added** - New NXobjects, such as fields or NXgroups, writers or utilities.
    * **Fixes** - Bug fixes
    * **Changed** - Code changes/improvements that don't affect output nexus file.
    * **Removed** - Obsolete functionalities being deleted, old python versions support.


Updating the documentation
==========================

The documentation is published on ReadtheDocs `here https://nexgen.readthedocs.io` and written using `sphinx https://www.sphinx-doc.org/en/master/`.
For every new feature, please add a docstring and update the API page on the documentation to show it.
If adding new writers or command line tools, please also update the usage page with an explaination on how to use them.
