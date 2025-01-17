import tomllib
from icecream import ic
from loguru import logger


def load_laderr(laderr_file_path: str) -> tuple[dict[str, object], dict[str, object]]:
    """
    Reads a TOML file, parses its content into a Python dictionary, and extracts preamble keys into a `metadata` dict.

    This function uses Python's built-in `tomllib` library to parse TOML files. The file must be passed as a binary
    stream, as required by `tomllib`. It processes the top-level keys that are not part of any section (preamble) and
    stores them in a separate `metadata` dictionary.

    :param laderr_file_path: str
        The path to the TOML file to be read.
    :return: Tuple[Dict[str, object], Dict[str, object]]
        A tuple containing:
        - `metadata`: A dictionary with preamble keys and their values.
        - `data`: A dictionary with the remaining TOML data (sections and their contents).
    :raises FileNotFoundError:
        If the specified file does not exist or cannot be found.
    :raises tomllib.TOMLDecodeError:
        If the TOML file contains invalid syntax or cannot be parsed.
    """
    try:
        with open(laderr_file_path, "rb") as file:
            data: dict[str, object] = tomllib.load(file)

        # Separate preamble keys (those not in sections) into a `metadata` dictionary
        metadata = {key: value for key, value in data.items() if not isinstance(value, dict)}
        sections = {key: value for key, value in data.items() if isinstance(value, dict)}

        return metadata, sections

    except FileNotFoundError as e:
        logger.error(f"Error: File '{laderr_file_path}' not found.")
        raise e
    except tomllib.TOMLDecodeError as e:
        logger.error(f"Error: Failed to parse LaDeRR/TOML file. {e}")
        raise e


# For testing
if __name__ == "__main__":
    metadata, sections = load_laderr("../test files/my_spec.toml")
    ic(metadata)
    ic(sections)
