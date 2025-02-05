# DataLad NEXT extension

[![Build status](https://ci.appveyor.com/api/projects/status/dxomp8wysjb7x2os/branch/main?svg=true)](https://ci.appveyor.com/project/mih/datalad-next/branch/main)
[![codecov.io](https://codecov.io/github/datalad/datalad-next/coverage.svg?branch=main)](https://codecov.io/github/datalad/datalad-next?branch=main)
[![crippled-filesystems](https://github.com/datalad/datalad-next/workflows/crippled-filesystems/badge.svg)](https://github.com/datalad/datalad-next/actions?query=workflow%3Acrippled-filesystems)
[![docs](https://github.com/datalad/datalad-next/workflows/docs/badge.svg)](https://github.com/datalad/datalad-next/actions?query=workflow%3Adocs)
[![Documentation Status](https://readthedocs.org/projects/datalad-next/badge/?version=latest)](http://docs.datalad.org/projects/next/en/latest/?badge=latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/release/datalad/datalad-next.svg)](https://GitHub.com/datalad/datalad-next/releases/)
[![PyPI version fury.io](https://badge.fury.io/py/datalad-next.svg)](https://pypi.python.org/pypi/datalad-next/)

This DataLad extension can be thought of as a staging area for additional
functionality, or for improved performance and user experience. Unlike other
topical or more experimental extensions, the focus here is on functionality
with broad applicability. This is extension is a suitable dependency for other
software packages that intend to build on this improved set of functionality.

## Installation

```
# create and enter a new virtual environment (optional)
$ virtualenv --python=python3 ~/env/dl-next
$ . ~/env/dl-next/bin/activate
# install from PyPi
$ python -m pip install datalad-next
```

## How to use

Additional commands provided by this extension are immediately available
after installation. However, in order to fully benefit from all improvements,
the extension has to be enabled for auto-loading by executing:

    git config --global --add datalad.extensions.load next

Doing so will enable the extension to also alter the behavior the core DataLad
package and its commands.

## Summary of functionality

- A new sub-system for credential handling that is able to handle arbitrary
  properties for annotating a secret, and facilitates determining suitable
  credentials while minimizing avoidable user interaction, without compromising
  configurability.
- A user-facing `credentials` command to set, remove, and query credentials.
- The `create-sibling-...` commands for the platforms GitHub, GIN, GOGS, Gitea
  are equipped with improved credential handling that, for example, only stores
  entered credentials after they were confirmed working, or auto-selects the
  most recently used, matching credentials, when none are specified.
- `git-remote-datalad-annex` is a Git remote helper to push/fetch to any
  location accessible by any git-annex special remote.
- `git-annex-backend-XDLRA` (originally available from the `mihextras` extension)
  is a custom external git-annex backend used by git-remote-datalad-annex. A base
  class to facilitate development of external backends in Python is also provided.
