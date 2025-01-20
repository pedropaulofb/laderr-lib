import os
import tomllib
from urllib.parse import urlparse

from icecream import ic
from loguru import logger
from pyshacl import validate
from rdflib import Graph, Namespace, RDF, Literal, XSD
from rdflib.exceptions import ParserError


class Laderr:
    """
    A utility class for providing methods to operate on RDF data and SHACL validation.
    This class is not meant to be instantiated.
    """

    def __init__(self):
        raise TypeError(f"{self.__class__.__name__} is a utility class and cannot be instantiated.")

    LADER_NS = Namespace("https://w3id.org/pedropaulofb/laderr#")

    @classmethod
    def _validate_base_uri(cls, metadata: dict[str, object]) -> str:
        """
        Validates the base URI provided in the metadata dictionary. If the base URI is invalid or missing,
        a default value of "https://laderr.laderr#" is returned.

        :param metadata: Metadata dictionary.
        :type metadata: Dict[str, object]
        :return: A valid base URI.
        :rtype: str
        """
        base_uri = metadata.get("base_uri", "https://laderr.laderr#")

        # Check if base_uri is a valid URI
        parsed = urlparse(base_uri)
        if not all([parsed.scheme, parsed.netloc]):
            logger.warning(f"Invalid base URI '{base_uri}' provided. Using default 'https://laderr.laderr#'.")

        return base_uri

    @classmethod
    def _load_spec_data(cls, spec_metadata: dict[str, object], spec_data: dict[str, object]) -> Graph:
        """
        Loads the data section from the specification into an RDFLib graph.

        If the `id` property is not explicitly defined within a section, the id is automatically set to the section's
        key name (e.g., "X" from [RiskEvent.X]).

        The base URI from `spec_metadata` is used as the namespace for the data.

        :param spec_metadata: Metadata dictionary containing the base URI.
        :type spec_metadata: dict[str, object]
        :param spec_data: Dictionary representing the `data` section of the specification.
        :type spec_data: dict[str, object]
        :return: RDFLib graph containing the data.
        :rtype: Graph
        """
        # Initialize an empty graph
        graph = Graph()

        # Get the base URI from metadata (use default if not defined)
        base_uri = cls._validate_base_uri(spec_metadata)
        data_ns = Namespace(base_uri)
        graph.bind("", data_ns)  # Use "" for the default namespace

        # Iterate over the sections in the data
        for class_type, instances in spec_data.items():
            if not isinstance(instances, dict):
                raise ValueError(f"Invalid structure for {class_type}. Expected a dictionary of instances.")

            for key, properties in instances.items():
                if not isinstance(properties, dict):
                    raise ValueError(
                        f"Invalid structure for instance '{key}' in '{class_type}'. Expected a dictionary of properties.")

                # Determine the `id` of the instance (default to section key if not explicitly set)
                instance_id = properties.get("id", key)

                # Create the RDF node for the instance
                instance_uri = data_ns[instance_id]
                graph.add((instance_uri, RDF.type, cls.LADER_NS[class_type]))

                # Add properties to the instance
                for prop, value in properties.items():
                    if prop == "id":
                        continue  # Skip `id`, it's already used for the URI

                    # Add properties to the graph
                    if isinstance(value, list):
                        for item in value:
                            graph.add((instance_uri, cls.LADER_NS[prop], Literal(item)))
                    else:
                        graph.add((instance_uri, cls.LADER_NS[prop], Literal(value)))

        return graph

    @classmethod
    def _load_spec_metadata(cls, metadata: dict[str, object]) -> Graph:
        """
        Creates an RDF graph containing only the provided metadata.

        Handles cases where metadata values are lists (e.g., `createdBy`), adding each list element as a separate triple.
        Also ensures that values are correctly typed according to SHACL expectations.

        :param metadata: Metadata dictionary to add to the graph.
        :type metadata: dict[str, object]
        :return: A new RDFLib graph containing only the metadata.
        :rtype: Graph
        """
        # Define expected datatypes for metadata keys
        expected_datatypes = {"title": XSD.string, "description": XSD.string, "version": XSD.string,
                              "createdBy": XSD.string, "createdOn": XSD.dateTime, "modifiedOn": XSD.dateTime,
                              "baseURI": XSD.anyURI, }

        # Validate base URI and bind namespace for data with ":" prefix
        base_uri = cls._validate_base_uri(metadata)
        data_ns = Namespace(base_uri)

        # Create a new graph
        graph = Graph()
        graph.bind("", data_ns)  # Use "" for the ":" prefix

        # Create or identify LaderrSpecification instance in the data namespace
        specification = data_ns.LaderrSpecification
        graph.add((specification, RDF.type, cls.LADER_NS.LaderrSpecification))  # Reference schema from laderr namespace

        # Add metadata as properties of the specification
        for key, value in metadata.items():
            property_uri = cls.LADER_NS[key]  # Schema properties come from laderr namespace
            datatype = expected_datatypes.get(key, XSD.string)  # Default to xsd:string if not specified

            # Handle lists
            if isinstance(value, list):
                for item in value:
                    graph.add((specification, property_uri, Literal(item, datatype=datatype)))
            else:
                # Add single value with specified datatype
                graph.add((specification, property_uri, Literal(value, datatype=datatype)))

        return graph

    @classmethod
    def _validate_with_shacl(cls, data_graph: Graph) -> tuple[bool, str, Graph]:
        """
        Validates an RDF graph against a SHACL shapes file.

        :param data_graph: RDF graph to validate.
        :type data_graph: Graph
        :return: A tuple containing:
            - A boolean indicating if the graph is valid.
            - A string with validation results.
            - A graph with validation report.
        :rtype: Tuple[bool, str, Graph]
        """
        shacl_graph = Graph()

        shacl_file_path = "C:\\Users\\FavatoBarcelosPP\\Dev\\laderr\\shapes\\laderr-shape-laderrspecification-v0.3.1.shacl"
        shacl_graph.parse(shacl_file_path, format="turtle")

        conforms, report_graph, report_text = validate(data_graph=data_graph, shacl_graph=shacl_graph, inference="both",
                                                       allow_infos=True, allow_warnings=True)

        return conforms, report_graph, report_text

    @classmethod
    def validate(cls, laderr_file_path: str):

        # syntactical validation
        spec_metadata_dict, spec_data_dict = Laderr._read_specification(laderr_file_path)

        # semantic validation
        spec_metadata_graph = Laderr._load_spec_metadata(spec_metadata_dict)
        spec_data_graph = Laderr._load_spec_data(spec_metadata_dict, spec_data_dict)

        unified_graph = Graph()
        unified_graph += spec_metadata_graph
        unified_graph += spec_data_graph

        conforms, _, report_text = Laderr._validate_with_shacl(unified_graph)
        Laderr._report_validation_result(conforms, report_text)
        Laderr._save_graph(unified_graph, "../result.ttl")
        return conforms

    @classmethod
    def _load_schema(cls) -> Graph:
        """
        Safely reads an RDF file into an RDFLib graph.

        :return: An RDFLib graph containing the data from the file.
        :rtype: Graph
        :raises FileNotFoundError: If the specified file does not exist.
        :raises ValueError: If the file is not a valid RDF file or cannot be parsed.
        """

        rdf_file_path = "C:\\Users\\FavatoBarcelosPP\\Dev\\laderr\\laderr-schema-v0.1.0.ttl"

        # Initialize the graph
        graph = Graph()

        try:
            # Parse the file into the graph
            graph.parse(rdf_file_path)
        except (ParserError, ValueError) as e:
            raise ValueError(f"Failed to parse the RDF file '{rdf_file_path}'. Ensure it is a valid RDF file.") from e

        return graph

    @classmethod
    def _read_specification(cls, laderr_file_path: str) -> tuple[dict[str, object], dict[str, object]]:
        """
        Reads a TOML file, parses its content into a Python dictionary, and extracts preamble keys into a `metadata` dict.

        This function uses Python's built-in `tomllib` library to parse TOML files. The file must be passed as a binary
        stream, as required by `tomllib`. It processes the top-level keys that are not part of any section (preamble) and
        stores them in a separate `metadata` dictionary. Handles cases where `createdBy` is a string or a list of strings.

        :param laderr_file_path: The path to the TOML file to be read.
        :type laderr_file_path: str
        :return: A tuple containing:
            - `metadata`: A dictionary with preamble keys and their values.
            - `data`: A dictionary with the remaining TOML data (sections and their contents).
        :rtype: tuple[dict[str, object], dict[str, object]]
        :raises FileNotFoundError: If the specified file does not exist or cannot be found.
        :raises tomllib.TOMLDecodeError: If the TOML file contains invalid syntax or cannot be parsed.
        """
        try:
            with open(laderr_file_path, "rb") as file:
                data: dict[str, object] = tomllib.load(file)

            # Separate metadata and data
            spec_metadata = {key: value for key, value in data.items() if not isinstance(value, dict)}
            spec_data = {key: value for key, value in data.items() if isinstance(value, dict)}

            # Add `id` to each item in spec_data if missing
            for class_type, instances in spec_data.items():
                if isinstance(instances, dict):
                    for key, properties in instances.items():
                        if isinstance(properties, dict) and "id" not in properties:
                            properties["id"] = key  # Default `id` to the section key

            # Normalize `createdBy` to always be a list if it's a string
            if "createdBy" in spec_metadata and isinstance(spec_metadata["createdBy"], str):
                spec_metadata["createdBy"] = [spec_metadata["createdBy"]]

            logger.success("LaDeRR specification's syntax successfully validated.")
            return spec_metadata, spec_data

        except FileNotFoundError as e:
            logger.error(f"Error: File '{laderr_file_path}' not found.")
            raise e
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Error: Syntactical error. Failed to parse LaDeRR/TOML file. {e}")
            raise e

    @staticmethod
    def _save_graph(graph: Graph, file_path: str, format: str = "turtle") -> None:
        """
        Saves an RDF graph to a file in the specified format.

        :param graph: The RDF graph to save.
        :type graph: Graph
        :param file_path: The path where the graph will be saved.
        :type file_path: str
        :param format: The serialization format (e.g., "turtle", "xml", "nt", "json-ld").
                       Default is "turtle".
        :type format: str
        :raises ValueError: If the format is not supported.
        :raises OSError: If the file cannot be written.
        """
        try:
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Serialize and save the graph
            graph.serialize(destination=file_path, format=format)
            print(f"Graph saved successfully to '{file_path}' in format '{format}'.")
        except ValueError as e:
            raise ValueError(f"Serialization format '{format}' is not supported.") from e
        except OSError as e:
            raise OSError(f"Could not write to file '{file_path}': {e}") from e

    @classmethod
    def _report_validation_result(cls, conforms: bool, report_text: str) -> None:
        """
        Reports the results of SHACL validation to the user.

        :param conforms: Boolean indicating if the RDF graph conforms to the SHACL shapes.
        :type conforms: bool
        :param report_text: String with the validation results in text format.
        :type report_text: str
        """

        if conforms:
            logger.success("The LaDeRR specification is correct.")
        else:
            logger.error("The LaDeRR specification is not correct.")

        # Print the full textual validation report
        logger.info(f"\nFull Validation Report: {report_text}")
