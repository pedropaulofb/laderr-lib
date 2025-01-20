from icecream import ic

from laderr_lib.laderr import Laderr

if __name__ == "__main__":
    # Load spec_metadata_dict and data from the specification
    laderr_file = "resources/my_spec.toml"


    # ic(Laderr._read_specification(laderr_file))
    Laderr.validate(laderr_file)
