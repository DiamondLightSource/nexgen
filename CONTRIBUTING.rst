Development environment
=======================

TBD


.. console::
    python -m venv .venv
    source .venv/bin/activate

    pip install -e .[dev]




Creating a release using bump2version
=====================================

From indie a development environment, a release can be created from the command line using bump2version. If not present, tha package can be pip installed.

.. console::
    pip install bump2version


First, choose a release number and run bump2version in "pretend" mode with the to check that the final version will be updated correctly.

.. console::
    bump2version --dry-run {major,minor,patch} --verbose


Once sure of the release number, run bump2version and push the the tags for the new version.


.. console::
    bump2version {major,minor,patch} --verbose
    git push --tags
    git push


Creating a release from github
==============================

1. Create a new branch from main named pre followed by the release version e.g. pre_v0.1.0. The release versions should look like v{major}.{minor}.{patch}.
2. On this branch pin the up-to-date version of dodal and the latest release of nexgen if necessary.
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