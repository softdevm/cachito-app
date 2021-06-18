# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
from collections import OrderedDict

import pytest

from cachito.errors import CachitoError
from cachito.utils import sort_packages_and_deps_in_place, unique_packages, PackagesData
from cachito.web.utils import deep_sort_icm


@pytest.mark.parametrize(
    "orig_items",
    [
        [
            {
                "metadata": {"image_layer_index": -1, "icm_spec": "sample-URL", "icm_version": 1},
                "image_contents": [
                    {
                        "dependencies": [
                            {"purl": "5sample-URL"},
                            {"purl": "4sample-URL"},
                            {"purl": "3sample-URL"},
                            {"purl": "2sample-URL"},
                            {"purl": "1sample-URL"},
                            {"purl": "0sample-URL"},
                        ],
                        "purl": "1sample-URL",
                        "sources": [],
                    },
                    {
                        "dependencies": [],
                        "purl": "0sample-URL",
                        "sources": [{"purl": "1sample-URL"}, {"purl": "0sample-URL"}],
                    },
                ],
            }
        ],
    ],
)
def test_deep_sort_icm(orig_items):
    expected = [
        OrderedDict(
            {
                "image_contents": [
                    OrderedDict(
                        {
                            "dependencies": [],
                            "purl": "0sample-URL",
                            "sources": [
                                OrderedDict({"purl": "0sample-URL"}),
                                OrderedDict({"purl": "1sample-URL"}),
                            ],
                        }
                    ),
                    OrderedDict(
                        {
                            "dependencies": [
                                OrderedDict({"purl": "0sample-URL"}),
                                OrderedDict({"purl": "1sample-URL"}),
                                OrderedDict({"purl": "2sample-URL"}),
                                OrderedDict({"purl": "3sample-URL"}),
                                OrderedDict({"purl": "4sample-URL"}),
                                OrderedDict({"purl": "5sample-URL"}),
                            ],
                            "purl": "1sample-URL",
                            "sources": [],
                        }
                    ),
                ],
                "metadata": OrderedDict(
                    {"icm_spec": "sample-URL", "icm_version": 1, "image_layer_index": -1}
                ),
            }
        ),
    ]
    assert deep_sort_icm(orig_items) == expected


@pytest.mark.parametrize(
    "packages,expected",
    [
        [[], []],
        [
            [{"name": "p1", "type": "gomod", "version": "1"}],
            [{"name": "p1", "type": "gomod", "version": "1"}],
        ],
        [
            # Unsorted packages
            [
                {"name": "p3", "type": "npm", "version": "3"},
                {"name": "p1", "type": "gomod", "version": "1"},
                {"name": "p2", "type": "go-package", "version": "2"},
                {"name": "p3", "type": "npm", "version": "3"},
            ],
            [
                {"name": "p3", "type": "npm", "version": "3"},
                {"name": "p1", "type": "gomod", "version": "1"},
                {"name": "p2", "type": "go-package", "version": "2"},
                {"name": "p3", "type": "npm", "version": "3"},
            ],
        ],
        [
            # Sorted packages
            [
                {"name": "p1", "type": "gomod", "version": "1"},
                {"name": "p1", "type": "gomod", "version": "1"},
                {"name": "p2", "type": "go-package", "version": "2"},
                {"name": "p4", "type": "yarn", "version": "4", "dev": True},
                {"name": "p4", "type": "yarn", "version": "4"},
                {"name": "p3", "type": "npm", "version": "3"},
                {"name": "p3", "type": "npm", "version": "3"},
            ],
            [
                {"name": "p1", "type": "gomod", "version": "1"},
                {"name": "p2", "type": "go-package", "version": "2"},
                {"name": "p4", "type": "yarn", "version": "4", "dev": True},
                {"name": "p4", "type": "yarn", "version": "4"},
                {"name": "p3", "type": "npm", "version": "3"},
            ],
        ],
    ],
)
def test_unique_packages(packages, expected):
    assert expected == list(unique_packages(packages))


def test_sort_packages_and_deps_in_place():
    # using different package managers to test sorting by type
    packages = [
        # test sorting by dev
        {"name": "pkg6", "type": "pip", "version": "1.0.0", "dev": False},
        {"name": "pkg5", "type": "pip", "version": "1.0.0", "dev": True},
        # test sorting by name
        {"name": "pkg3", "type": "npm", "version": "1.0.0", "dev": False},
        {"name": "pkg2", "type": "npm", "version": "1.2.3", "dev": False},
        # test sorting by version
        {"name": "pkg4", "type": "npm", "version": "1.2.5", "dev": False},
        {"name": "pkg4", "type": "npm", "version": "1.2.0", "dev": False},
        {
            "name": "pkg1",
            "type": "gomod",
            "version": "1.0.0",
            "dependencies": [
                # test sorting of dependencies
                {"name": "pkg1-dep2", "type": "gomod", "version": "1.0.0"},
                {"name": "pkg1-dep1", "type": "gomod", "version": "1.0.0"},
            ],
        },
    ]

    sorted_packages = [
        {
            "name": "pkg1",
            "type": "gomod",
            "version": "1.0.0",
            "dependencies": [
                {"name": "pkg1-dep1", "type": "gomod", "version": "1.0.0"},
                {"name": "pkg1-dep2", "type": "gomod", "version": "1.0.0"},
            ],
        },
        {"name": "pkg2", "type": "npm", "version": "1.2.3", "dev": False},
        {"name": "pkg3", "type": "npm", "version": "1.0.0", "dev": False},
        {"name": "pkg4", "type": "npm", "version": "1.2.0", "dev": False},
        {"name": "pkg4", "type": "npm", "version": "1.2.5", "dev": False},
        {"name": "pkg6", "type": "pip", "version": "1.0.0", "dev": False},
        {"name": "pkg5", "type": "pip", "version": "1.0.0", "dev": True},
    ]

    sort_packages_and_deps_in_place(packages)

    assert packages == sorted_packages


class TestPackagesData:
    """Test class PackagesData."""

    @pytest.mark.parametrize(
        "params,expected",
        [
            [
                [[{"name": "pkg1", "type": "gomod", "version": "1.0.0"}, "path1", []]],
                [
                    {
                        "name": "pkg1",
                        "type": "gomod",
                        "version": "1.0.0",
                        "path": "path1",
                        "dependencies": [],
                    },
                ],
            ],
            [
                [
                    [{"name": "pkg1", "type": "gomod", "version": "1.0.0"}, "path1", []],
                    [{"name": "pkg2", "type": "yarn", "version": "2.3.1"}, os.curdir, []],
                    [
                        {"name": "pkg3", "type": "npm", "version": "1.2.3"},
                        os.curdir,
                        [{"name": "async@15.0.0"}],
                    ],
                ],
                [
                    {
                        "name": "pkg1",
                        "type": "gomod",
                        "version": "1.0.0",
                        "path": "path1",
                        "dependencies": [],
                    },
                    {"name": "pkg2", "type": "yarn", "version": "2.3.1", "dependencies": []},
                    {
                        "name": "pkg3",
                        "type": "npm",
                        "version": "1.2.3",
                        "dependencies": [{"name": "async@15.0.0"}],
                    },
                ],
            ],
            [
                [
                    [{"name": "pkg1", "type": "gomod", "version": "1.0.0"}, "path1", []],
                    [
                        {"name": "pkg1", "type": "gomod", "version": "1.0.0"},
                        "somewhere/",
                        [{"name": "golang.org/x/text/internal/tag"}],
                    ],
                ],
                pytest.raises(CachitoError, match="Duplicate package"),
            ],
        ],
    )
    def test_add_package(self, params, expected):
        """Test method add_package."""
        pd = PackagesData()
        if isinstance(expected, list):
            for pkg_info, path, deps in params:
                pd.add_package(pkg_info, path, deps)
            assert expected == pd._packages
        else:
            with expected:
                for pkg_info, path, deps in params:
                    pd.add_package(pkg_info, path, deps)

    @pytest.mark.parametrize(
        "params,expected",
        [
            [[], {"packages": []}],
            [
                [
                    [{"name": "pkg1", "type": "gomod", "version": "1.0.0"}, "path1", []],
                    [
                        {"name": "pkg3", "type": "npm", "version": "1.2.3"},
                        os.curdir,
                        [{"name": "async", "type": "npm", "version": "15.0.0"}],
                    ],
                ],
                {
                    "packages": [
                        {
                            "name": "pkg1",
                            "type": "gomod",
                            "version": "1.0.0",
                            "path": "path1",
                            "dependencies": [],
                        },
                        {
                            "name": "pkg3",
                            "type": "npm",
                            "version": "1.2.3",
                            "dependencies": [{"name": "async", "type": "npm", "version": "15.0.0"}],
                        },
                    ],
                },
            ],
        ],
    )
    def test_write_to_file(self, params, expected, tmpdir):
        """Test method write_to_file."""
        pd = PackagesData()
        for pkg_info, path, deps in params:
            pd.add_package(pkg_info, path, deps)
        filename = os.path.join(tmpdir, "data.json")
        pd.write_to_file(filename)
        with open(filename, "r") as f:
            assert expected == json.load(f)

    @pytest.mark.parametrize(
        "packages_data,expected",
        [
            [None, []],
            [{}, []],
            [{"data": []}, []],
            [
                {
                    "packages": [
                        {
                            "name": "pkg1",
                            "type": "gomod",
                            "version": "1.0.0",
                            "path": "path1",
                            "dependencies": [],
                        },
                        {
                            "name": "pkg3",
                            "type": "npm",
                            "version": "1.2.3",
                            "dependencies": [{"name": "async@15.0.0"}],
                        },
                    ],
                },
                [
                    {
                        "name": "pkg1",
                        "type": "gomod",
                        "version": "1.0.0",
                        "path": "path1",
                        "dependencies": [],
                    },
                    {
                        "name": "pkg3",
                        "type": "npm",
                        "version": "1.2.3",
                        "dependencies": [{"name": "async@15.0.0"}],
                    },
                ],
            ],
        ],
    )
    def test_load_from_file(self, packages_data, expected, tmpdir):
        """Test method load."""
        filename = os.path.join(tmpdir, "data.json")
        if packages_data is not None:
            with open(filename, "w") as f:
                f.write(json.dumps(packages_data))
        pd = PackagesData()
        pd.load(filename)
        assert expected == pd._packages

    @pytest.mark.parametrize(
        "packages_data,expected_dependencies",
        [
            [
                {
                    "packages": [
                        {"name": "n2", "type": "go-package", "version": "v2", "dependencies": []},
                        {"name": "n1", "type": "gomod", "version": "v1", "dependencies": []},
                    ],
                },
                [],
            ],
            [
                {
                    "packages": [
                        {
                            "name": "n2",
                            "type": "go-package",
                            "version": "v2",
                            "dependencies": [
                                {"name": "d1", "type": "go-package", "version": "1"},
                                {
                                    "name": "d2",
                                    "replaces": None,
                                    "type": "go-package",
                                    "version": "2",
                                },
                            ],
                        },
                        {
                            "name": "n1",
                            "type": "gomod",
                            "version": "v1",
                            "dependencies": [
                                {"name": "d1", "type": "gomod", "version": "1"},
                                {"name": "d2", "replaces": None, "type": "gomod", "version": "2"},
                            ],
                        },
                        {
                            "name": "p1",
                            "type": "npm",
                            "version": "v2",
                            "dependencies": [{"name": "async", "type": "npm", "version": "1.2.0"}],
                        },
                        {
                            "name": "p2",
                            "type": "npm",
                            "version": "20210621",
                            "dependencies": [
                                {"name": "async", "type": "npm", "version": "1.2.0"},
                                {"name": "underscore", "type": "npm", "version": "1.13.0"},
                            ],
                        },
                    ],
                },
                [
                    {"name": "d1", "type": "go-package", "version": "1"},
                    {"name": "d2", "replaces": None, "type": "go-package", "version": "2"},
                    {"name": "d1", "type": "gomod", "version": "1"},
                    {"name": "d2", "replaces": None, "type": "gomod", "version": "2"},
                    # Only one async in the final dependencies list
                    {"name": "async", "type": "npm", "version": "1.2.0"},
                    {"name": "underscore", "type": "npm", "version": "1.13.0"},
                ],
            ],
        ],
    )
    def test_all_dependencies(self, packages_data, expected_dependencies, tmpdir):
        """Test property all_dependencies."""
        filename = os.path.join(tmpdir, "data.json")
        with open(filename, "w") as f:
            f.write(json.dumps(packages_data))
        pd = PackagesData()
        pd.load(filename)
        assert expected_dependencies == pd.all_dependencies
