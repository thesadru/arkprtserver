"""Nox file."""
from __future__ import annotations

import logging
import pathlib
import typing

import nox

nox.options.sessions = ["reformat", "lint", "type-check", "prettier"]
nox.options.reuse_existing_virtualenvs = True
PACKAGE = "arkprtserver"
GENERAL_TARGETS = ["./arkprtserver", "./noxfile.py"]
PYRIGHT_ENV = {"PYRIGHT_PYTHON_FORCE_VERSION": "latest"}

LOGGER = logging.getLogger("nox")


def isverbose() -> bool:
    """Whether the verbose flag is set."""
    return LOGGER.getEffectiveLevel() == logging.DEBUG - 1


def verbose_args() -> typing.Sequence[str]:
    """Return --verbose if the verbose flag is set."""
    return ["--verbose"] if isverbose() else []


def install_requirements(session: nox.Session, *requirements: str, literal: bool = False) -> None:
    """Install requirements."""
    if not literal and all(requirement.isalpha() for requirement in requirements):
        files = ["requirements.txt"]
        files += [f"./dev-requirements/{requirement}.txt" for requirement in requirements]
        requirements = tuple(arg for file in files for arg in ("-r", file))

    session.install("--upgrade", "pip", *requirements, silent=not isverbose())


@nox.session()
def lint(session: nox.Session) -> None:
    """Run this project's modules against ruff."""
    install_requirements(session, "lint")
    session.run("python", "-m", "ruff", "check", *GENERAL_TARGETS, *verbose_args())
    session.run("python", "-m", "slotscheck", "-m", PACKAGE, *verbose_args())


@nox.session()
def reformat(session: nox.Session) -> None:
    """Reformat this project's modules to fit the standard style."""
    install_requirements(session, "reformat")
    session.run("python", "-m", "black", *GENERAL_TARGETS, *verbose_args())
    session.run("python", "-m", "ruff", "--fix-only", "--fixable", "ALL", *GENERAL_TARGETS, *verbose_args())

    session.log("sort-all")
    LOGGER.disabled = True
    session.run("sort-all", *map(str, pathlib.Path(PACKAGE).glob("**/*.py")), success_codes=[0, 1])
    LOGGER.disabled = False


@nox.session(name="type-check")
def type_check(session: nox.Session) -> None:
    """Statically analyse and veirfy this project using pyright and mypy."""
    install_requirements(session, "typecheck")
    session.run("pyright", PACKAGE, *verbose_args(), env=PYRIGHT_ENV)


@nox.session(name="verify-types")
def verify_types(session: nox.Session) -> None:
    """Verify the "type completeness" of types exported by the library using pyright."""
    install_requirements(session, ".", "--force-reinstall", "--no-deps")
    install_requirements(session, "typecheck")

    session.run("pyright", "--verifytypes", PACKAGE, "--ignoreexternal", *verbose_args(), env=PYRIGHT_ENV)


def _try_install_prettier(session: nox.Session) -> bool:
    """Try to install prettier. Return False if failed."""
    try:
        session.run("npm", "install", "prettier", "--global", external=True)
    except Exception as exception:  # noqa: BLE001: Nox throws a bare Exception
        if str(exception) != "Program npm not found":
            raise
    else:
        return True

    return False
