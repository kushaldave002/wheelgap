"""Tests for reading pip packages from conda environment.yml / environment.yaml (#494)."""

from __future__ import annotations

import pytest
from test_cli import run

from wheelgap.sources import SourceError, file_kind, load_file, load_inputs


def test_file_kind_recognizes_environment_yml_and_yaml(tmp_path):
    assert file_kind(tmp_path / "environment.yml") == "conda-env"
    assert file_kind(tmp_path / "environment.yaml") == "conda-env"
    with pytest.raises(SourceError):
        file_kind(tmp_path / "other.yml")


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
        "# a comment is rejected by _BlockYaml\ndependencies:\n  - pip:\n    - purewheel==3.1\n",
        "dependencies: [numpy, pip]\n",
        "dependencies:\n\t- numpy\n",
        "- just-a-list\n",
        "dependencies: not-a-list\n",
        "dependencies:\n  - other:\n    - foo\n",
        "dependencies:\n  - pip: not-a-list\n",
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
