"""Tests for reading pip packages from conda environment.yml / environment.yaml (#494)."""

from __future__ import annotations

import pytest
from test_cli import run

from wheelgap.sources import (
    SourceError,
    _BlockYaml,
    _conda_package_name,
    _YamlError,
    file_kind,
    load_file,
    load_inputs,
)


@pytest.mark.parametrize(
    "name", ["environment.yml", "environment.yaml", "environment-dev.yml", "environment.gpu.yaml", "environment_ci.yml"]
)
def test_file_kind_recognizes_environment_yml_and_yaml(tmp_path, name):
    assert file_kind(tmp_path / name) == "conda-env"


@pytest.mark.parametrize("name", ["other.yml", "env.yaml", "my-environment.yml", "environment.yml.bak"])
def test_file_kind_refuses_other_yaml_names(tmp_path, name):
    with pytest.raises(SourceError, match="don't know how to read"):
        file_kind(tmp_path / name)


def test_environment_dev_yml_is_read(tmp_path):
    env = tmp_path / "environment-dev.yml"
    env.write_text("dependencies:\n  - pip:\n    - purewheel==3.1\n", encoding="utf-8")
    assert [(p.name, p.version) for p in load_file(env).packages] == [("purewheel", "3.1")]


def test_directory_search_ignores_environment_yml(tmp_path):
    (tmp_path / "environment.yml").write_text("dependencies:\n  - pip:\n    - purewheel==3.1\n", encoding="utf-8")
    with pytest.raises(SourceError, match="no lockfile found"):
        load_inputs([str(tmp_path)])


def test_missing_environment_yml_is_file_not_found(tmp_path):
    with pytest.raises(SourceError, match="no such file"):
        load_inputs(["environment.yml"])
    with pytest.raises(SourceError, match="no such file"):
        load_inputs(["environment.yaml"])


def test_parse_conda_env_reads_pip_and_skips_conda(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text(
        "name: demo\n"
        "channels:\n"
        "  - conda-forge\n"
        "dependencies:\n"
        "  - python=3.12\n"
        "  - conda-forge::numpy>=1.26\n"
        "  - pip\n"
        "  - pip:\n"
        "    - purewheel==3.1\n"
        "    - nowheels==0.9; sys_platform == 'linux'\n"
        "    - -e ./local\n"
        "    - git+https://github.com/org/repo.git#egg=fromgit\n",
        encoding="utf-8",
    )
    source = load_file(env)
    assert source.kind == "conda-env"
    assert source.requirements is True
    assert source.pypi_only is True

    checked = [p for p in source.packages if not p.skip]
    assert [(p.name, p.version, p.markers) for p in checked] == [
        ("purewheel", "3.1", None),
        ("nowheels", "0.9", ['sys_platform == "linux"']),
    ]

    skipped = [(p.name, p.skip) for p in source.packages if p.skip]
    assert skipped == [
        ("./local", "editable"),
        ("fromgit", "url"),
        ("python", "conda"),
        ("numpy", "conda"),
        ("pip", "conda"),
    ]


def test_parse_conda_env_follows_dash_r_include(tmp_path):
    (tmp_path / "requirements-extra.txt").write_text("nowheels==0.9\n", encoding="utf-8")
    env = tmp_path / "environment.yaml"
    env.write_text(
        "dependencies:\n  - python=3.12\n  - pip:\n    - purewheel==3.1\n    - -r requirements-extra.txt\n",
        encoding="utf-8",
    )
    source = load_file(env)
    checked = [(p.name, p.version) for p in source.packages if not p.skip]
    assert checked == [("purewheel", "3.1"), ("nowheels", "0.9")]


@pytest.mark.parametrize(
    "option",
    [
        "--index-url https://private.example/simple",
        "--extra-index-url https://private.example/simple",
        "-i https://private.example/simple",
    ],
)
def test_parse_conda_env_index_url_marks_not_pypi_only(tmp_path, option):
    env = tmp_path / "environment.yml"
    env.write_text(
        f"dependencies:\n  - python=3.12\n  - pip:\n    - {option}\n    - purewheel==3.1\n",
        encoding="utf-8",
    )
    source = load_file(env)
    assert source.pypi_only is False
    assert [(p.name, p.version) for p in source.packages if not p.skip] == [("purewheel", "3.1")]


@pytest.mark.parametrize(
    "content",
    [
        "dependencies: [numpy, pip]\n",
        "dependencies:\n  - pip: [purewheel==3.1]\n",
        "dependencies:\n  - [numpy]\n",
        "channels: [conda-forge, [nested]]\ndependencies:\n  - numpy\n",
        "channels: ['conda-forge']\ndependencies:\n  - numpy\n",
        "channels: [conda-forge,\n  defaults]\ndependencies:\n  - numpy\n",
        'dependencies:\n  - pip:\n    - "purewheel==3.1"# no space before the comment\n',
        "dependencies:\n\t- numpy\n",
        "- just-a-list\n",
        "dependencies: not-a-list\n",
        "dependencies:\n  - other:\n    - foo\n",
        "dependencies:\n  - pip: not-a-list\n",
        "dependencies:\n  - {}\n",
    ],
)
def test_cli_unreadable_conda_env_exits_2(capsys, fake_pypi, tmp_path, content):
    env = tmp_path / "environment.yml"
    env.write_text(content, encoding="utf-8")
    code, _, err = run(capsys, str(env), "-p", "3.13", "-t", "linux-x86_64", "--color", "never")
    assert code == 2
    assert "wheelgap: error:" in err


@pytest.mark.parametrize(
    "content",
    [
        "dependencies:\n  - python=3.12\n  - numpy\n  - pip: []\n",
        "dependencies:\n  - python=3.12\n  - pip:\n",
        "dependencies:\n  - python=3.12\n",
    ],
)
def test_cli_empty_pip_list_says_no_packages_to_check(capsys, fake_pypi, tmp_path, content):
    env = tmp_path / "environment.yml"
    env.write_text(content, encoding="utf-8")
    code, out, _ = run(capsys, str(env), "-p", "3.13", "-t", "linux-x86_64", "--color", "never")
    assert code == 0
    assert "No packages to check." in out
    assert "python (conda)" in out


def test_cli_conda_env_checks_pip_and_reports_gaps(capsys, fake_pypi, tmp_path):
    (tmp_path / "extra.txt").write_text("nowheels==0.9\n", encoding="utf-8")
    env = tmp_path / "environment.yml"
    env.write_text(
        "name: ml\ndependencies:\n  - python=3.12\n  - numpy\n  - pip:\n    - purewheel==3.1\n    - -r extra.txt\n",
        encoding="utf-8",
    )
    code, out, _ = run(capsys, str(env), "-p", "3.13", "-t", "linux-x86_64", "--color", "never")
    assert code == 1
    assert "nowheels" in out
    assert "python (conda)" in out
    assert "numpy (conda)" in out


def test_empty_mapping_in_dependencies_names_no_keys(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text("dependencies:\n  - {}\n", encoding="utf-8")
    with pytest.raises(SourceError, match=r"unsupported empty mapping in `dependencies`$"):
        load_file(env)


def test_parse_conda_env_reads_comments(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text(
        "# Created for the demo project\n"
        "name: demo  # the env name\n"
        "channels:  # where conda looks\n"
        "  # the main channel\n"
        "  - conda-forge # community builds\n"
        "dependencies:   # all of them\n"
        "  - python=3.12  # pinned minor\n"
        "    # an indented comment line\n"
        "  - pip\n"
        "  - pip:\n"
        "# a comment at column 0 inside the list\n"
        "    - purewheel==3.1   # pinned\n"
        '    - "nowheels==0.9"  # a quoted entry\n'
        "    - 'otherpkg==1.0' # single-quoted\n"
        "    - git+https://github.com/org/repo.git#egg=fromgit\n",
        encoding="utf-8",
    )
    source = load_file(env)
    assert [(p.name, p.version) for p in source.packages if not p.skip] == [
        ("purewheel", "3.1"),
        ("nowheels", "0.9"),
        ("otherpkg", "1.0"),
    ]
    assert [(p.name, p.skip) for p in source.packages if p.skip] == [
        ("fromgit", "url"),
        ("python", "conda"),
        ("pip", "conda"),
    ]


def test_quoted_pip_entry_reaches_the_requirements_reader_whole(tmp_path):
    # YAML keeps " # pinned" inside the quotes; conda writes the line to a requirements file as it is, where pip
    # reads " # pinned" as a comment.
    env = tmp_path / "environment.yml"
    env.write_text('dependencies:\n  - pip:\n    - "purewheel==3.1 # pinned"\n', encoding="utf-8")
    assert [(p.name, p.version) for p in load_file(env).packages] == [("purewheel", "3.1")]


def test_empty_key_with_a_comment_is_an_empty_key(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text("name: demo\ndependencies:  # none yet\n", encoding="utf-8")
    assert load_file(env).packages == []


def test_flow_channels_are_read(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text(
        "channels: [conda-forge, defaults]  # both\ndependencies:\n  - numpy\n  - pip:\n    - purewheel==3.1\n",
        encoding="utf-8",
    )
    source = load_file(env)
    assert [(p.name, p.skip) for p in source.packages] == [("purewheel", None), ("numpy", "conda")]


def test_pixi_reader_still_refuses_comments():
    with pytest.raises(_YamlError, match="comments"):
        _BlockYaml("# c\nversion: 6\n").read()
    with pytest.raises(_YamlError, match="unsupported YAML"):
        _BlockYaml("version: 6 # c\n").read()
    with pytest.raises(_YamlError, match="unsupported YAML"):
        _BlockYaml("channels: [a, b]\n").read()


def test_deeper_indented_pip_list(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text("dependencies:\n  - python=3.12\n  - pip:\n      - purewheel==3.1\n", encoding="utf-8")
    assert [(p.name, p.skip) for p in load_file(env).packages] == [("purewheel", None), ("python", "conda")]


def test_indentless_dependencies(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text("dependencies:\n- python=3.12\n- pip:\n  - purewheel==3.1\n", encoding="utf-8")
    assert [(p.name, p.skip) for p in load_file(env).packages] == [("purewheel", None), ("python", "conda")]


def test_conda_env_export_file(tmp_path):
    env = tmp_path / "environment.yml"
    env.write_text(
        "name: myenv\n"
        "channels:\n"
        "  - conda-forge\n"
        "  - defaults\n"
        "dependencies:\n"
        "  - _libgcc_mutex=0.1=conda_forge\n"
        "  - python=3.12.1=hab00c5b_1_cpython\n"
        "  - pip=24.0=pyhd8ed1ab_0\n"
        "  - pip:\n"
        "      - purewheel==3.1\n"
        "      - nowheels==0.9\n"
        "prefix: /home/user/miniconda3/envs/myenv\n",
        encoding="utf-8",
    )
    source = load_file(env)
    assert [(p.name, p.version) for p in source.packages if not p.skip] == [("purewheel", "3.1"), ("nowheels", "0.9")]
    assert [p.name for p in source.packages if p.skip == "conda"] == ["_libgcc_mutex", "python", "pip"]


@pytest.mark.parametrize(
    ("spec", "name"),
    [
        ("numpy", "numpy"),
        ("numpy 1.26.*", "numpy"),
        ("pytorch::pytorch[build=*cuda*]", "pytorch"),
        ("conda-forge/linux-64::numpy", "numpy"),
        ("conda-forge::numpy>=1.26", "numpy"),
        ("python>=3.10", "python"),
        ("python=3.12", "python"),
        ("pip!=24.0", "pip"),
    ],
)
def test_conda_package_name(spec, name):
    assert _conda_package_name(spec) == name
