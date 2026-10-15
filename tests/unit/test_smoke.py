import aerorag


def test_package_exposes_version() -> None:
    assert isinstance(aerorag.__version__, str)
