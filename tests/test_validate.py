import os
import tomllib

import pytest

from laderr_lib.laderr import Laderr


def generate_test_cases_from_folder(folder_path: str):
    """
    Generator that yields file paths for all TOML files in the specified folder.

    :param folder_path: Path to the folder containing TOML files.
    :type folder_path: str
    :yield: Paths to individual TOML files.
    :rtype: Iterator[str]
    """
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".toml"):
            yield os.path.join(folder_path, file_name)


@pytest.mark.parametrize("file_path", generate_test_cases_from_folder("test_files/invalid/syntax"))
def test_validate_syntax_errors(file_path: str) -> None:
    """
    Tests that the validate method raises TOMLDecodeError for syntactical errors in TOML files.

    :param file_path: Path to the invalid TOML file.
    :type file_path: str
    :raises AssertionError: If the expected exception is not raised.
    """
    try:
        with open(file_path, "rb") as f:
            tomllib.load(f)  # Attempt to load the TOML file
    except tomllib.TOMLDecodeError:
        # If a decode error occurs, we consider the test passed
        return

    pytest.fail(f"No TOMLDecodeError was raised for file: {file_path}")


@pytest.mark.parametrize("file_path", generate_test_cases_from_folder("test_files/invalid/metadata/datatype"))
def test_validate_metadata_datatype(file_path: str) -> None:
    """
    Tests that the `validate` method correctly identifies and reports metadata datatype errors.

    The test dynamically retrieves TOML files from the specified folder, where each file is expected
    to contain invalid datatype metadata. The `validate` method should return `False` for these cases,
    indicating that the SHACL semantic validation has failed.

    :param file_path: Path to the invalid TOML file with datatype issues.
    :type file_path: str
    :raises AssertionError: If the validation returns `True` for a file that is expected to fail.
    """
    assert not Laderr.validate(file_path), f"Validation incorrectly passed for file: {file_path}"


@pytest.mark.parametrize("file_path", generate_test_cases_from_folder("test_files/invalid/metadata/multiplicity"))
def test_validate_metadata_multiplicity(file_path: str) -> None:
    """
    Tests that the validate method correctly identifies multiplicity errors in metadata.

    :param file_path: Path to the invalid TOML file with multiplicity issues.
    :type file_path: str
    :raises AssertionError: If the validation does not raise the expected error.
    """
    assert not Laderr.validate(file_path), f"Validation incorrectly passed for file: {file_path}"


@pytest.mark.parametrize("file_path", generate_test_cases_from_folder("test_files/invalid/metadata/undefined"))
def test_validate_metadata_undefined(file_path: str) -> None:
    """
    Tests that the validate method correctly identifies undefined metadata keys.

    :param file_path: Path to the invalid TOML file with undefined metadata keys.
    :type file_path: str
    :raises AssertionError: If the validation does not raise the expected error.
    """
    assert not Laderr.validate(file_path), f"Validation incorrectly passed for file: {file_path}"


@pytest.mark.parametrize("file_path", generate_test_cases_from_folder("test_files/invalid/metadata/combined"))
def test_validate_metadata_combined(file_path: str) -> None:
    """
    Tests that the validate method correctly identifies combined metadata keys.

    :param file_path: Path to the invalid TOML file with combined metadata keys.
    :type file_path: str
    :raises AssertionError: If the validation does not raise the expected error.
    """
    assert not Laderr.validate(file_path), f"Validation incorrectly passed for file: {file_path}"