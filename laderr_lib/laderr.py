import os
import tomllib
from urllib.parse import urlparse

from icecream import ic
from loguru import logger
from pyshacl import validate
from rdflib import Graph, Namespace, RDF, Literal, XSD, RDFS
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
    def _validate_base_uri(cls, spec_metadata_dict: dict[str, object]) -> str:
        """
        Validates the base URI provided in the metadata dictionary. If the base URI is invalid or missing,
        a default value of "https://laderr.laderr#" is returned.

        :param spec_metadata_dict: Metadata dictionary.
        :type spec_metadata_dict: Dict[str, object]
        :return: A valid base URI.
        :rtype: str
        """
        base_uri = spec_metadata_dict.get("baseUri", "https://laderr.laderr#")
        # Check if base_uri is a valid URI
        parsed = urlparse(base_uri)
        if not all([parsed.scheme, parsed.netloc]):
            ic("here")
            logger.warning(f"Invalid base URI '{base_uri}' provided. Using default 'https://laderr.laderr#'.")

        return base_uri

    @classmethod
    def _load_spec_data(cls, spec_metadata: dict[str, object], spec_data: dict[str, object]) -> Graph:
        """
        Loads the data section from the specification into an RDFLib graph and adds the `composedOf` relationship.

        If the `id` property is not explicitly defined within a section, the id is automatically set to the section's
        key name (e.g., "X" from [RiskEvent.X]).

        The base URI from `spec_metadata` is used as the namespace for the data.

        :param spec_metadata: Metadata dictionary containing the base URI.
        :type spec_metadata: dict[str, object]
        :param spec_data: Dictionary representing the `data` section of the specification.
        :type spec_data: dict[str, object]
        :return: RDFLib graph containing the data and `composedOf` relationship.
        :rtype: Graph
        """
        # Initialize an empty graph
        graph = Graph()

        # Get the base URI from spec_metadata_dict and bind namespaces
        base_uri = cls._validate_base_uri(spec_metadata)
        data_ns = Namespace(base_uri)
        laderr_ns = cls.LADER_NS
        graph.bind("", data_ns)  # Bind the `:` namespace
        graph.bind("laderr", laderr_ns)  # Bind the `laderr:` namespace

        # Create or identify the single RiskSpecification instance
        specification_uri = data_ns.LaderrSpecification
        graph.add((specification_uri, RDF.type, laderr_ns.LaderrSpecification))

        # Iterate over the sections in the data
        for class_type, instances in spec_data.items():
            if not isinstance(instances, dict):
                raise ValueError(f"Invalid structure for {class_type}. Expected a dictionary of instances.")

            for key, properties in instances.items():
                if not isinstance(properties, dict):
                    raise ValueError(
                        f"Invalid structure for instance '{key}' in '{class_type}'. Expected a dictionary of properties."
                    )

                # Determine the `id` of the instance (default to section key if not explicitly set)
                instance_id = properties.get("id", key)

                # Create the RDF node for the instance
                instance_uri = data_ns[instance_id]
                graph.add((instance_uri, RDF.type, laderr_ns[class_type]))

                # Add properties to the instance
                for prop, value in properties.items():
                    if prop == "id":
                        continue  # Skip `id`, it's already used for the URI

                    if prop == "label":
                        # Map 'label' to 'rdfs:label'
                        graph.add((instance_uri, RDFS.label, Literal(value)))
                    else:
                        # Map other properties to laderr namespace
                        if isinstance(value, list):
                            for item in value:
                                graph.add((instance_uri, laderr_ns[prop], Literal(item)))
                        else:
                            graph.add((instance_uri, laderr_ns[prop], Literal(value)))

                # Add the composedOf relationship
                graph.add((specification_uri, laderr_ns.composedOf, instance_uri))

        return graph

    @classmethod
    def _load_spec_metadata(cls, metadata: dict[str, object]) -> Graph:
        """
        Creates an RDF graph containing only the provided spec_metadata_dict.

        :param metadata: Metadata dictionary to add to the graph.
        :type metadata: dict[str, object]
        :return: A new RDFLib graph containing only the spec_metadata_dict.
        :rtype: Graph
        """
        # Define expected datatypes for spec_metadata_dict keys
        expected_datatypes = {
            "title": XSD.string,
            "description": XSD.string,
            "version": XSD.string,
            "createdBy": XSD.string,
            "createdOn": XSD.dateTime,
            "modifiedOn": XSD.dateTime,
            "baseUri": XSD.anyURI,
        }

        # Validate base URI and bind namespaces
        base_uri = cls._validate_base_uri(metadata)
        data_ns = Namespace(base_uri)
        laderr_ns = cls.LADER_NS

        # Create a new graph
        graph = Graph()
        graph.bind("", data_ns)  # Bind the `:` namespace
        graph.bind("laderr", laderr_ns)  # Bind the `laderr:` namespace

        # Create or identify LaderrSpecification instance
        specification = data_ns.LaderrSpecification
        graph.add((specification, RDF.type, laderr_ns.LaderrSpecification))

        # Add spec_metadata_dict as properties of the specification
        for key, value in metadata.items():
            property_uri = laderr_ns[key]  # Schema properties come from laderr namespace
            datatype = expected_datatypes.get(key, XSD.anyURI)  # Default to xsd:string if not specified

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
        shacl_files_path = "C:\\Users\\FavatoBarcelosPP\\Dev\\laderr\\shapes"
        shacl_graph = Laderr._merge_shacl_files(shacl_files_path)
        ic(len(shacl_graph))

        conforms, report_graph, report_text = validate(data_graph=data_graph, shacl_graph=shacl_graph, inference="both",
                                                       allow_infos=True, allow_warnings=True)

        return conforms, report_graph, report_text

    @classmethod
    def _merge_shacl_files(cls, shacl_files_path: str) -> Graph:
        """
        Merges all SHACL files in the given path into a single RDFLib graph.

        :param shacl_files_path: The directory path containing SHACL files.
        :type shacl_files_path: str
        :return: A single RDFLib graph containing all merged SHACL shapes.
        :rtype: Graph
        :raises FileNotFoundError: If the directory or files are not found.
        :raises ValueError: If the directory does not contain valid SHACL files.
        """
        # Initialize an empty RDFLib graph
        merged_graph = Graph()

        # Ensure the provided path is valid
        if not os.path.isdir(shacl_files_path):
            raise FileNotFoundError(f"The path '{shacl_files_path}' does not exist or is not a directory.")

        # Iterate over all files in the directory
        for filename in os.listdir(shacl_files_path):
            ic(filename)
            file_path = os.path.join(shacl_files_path, filename)

            # Skip non-files
            if not os.path.isfile(file_path):
                continue

            # Attempt to parse the SHACL file
            try:
                merged_graph.parse(file_path, format="turtle")
            except Exception as e:
                logger.warning(f"Failed to parse SHACL file '{filename}': {e}")

        if len(merged_graph) == 0:
            raise ValueError(f"No valid SHACL files found in the directory '{shacl_files_path}'.")

        return merged_graph

    @classmethod
    def validate(cls, laderr_file_path: str):
        # Syntactical validation
        spec_metadata_dict, spec_data_dict = Laderr._read_specification(laderr_file_path)

        # Semantic validation
        spec_metadata_graph = Laderr._load_spec_metadata(spec_metadata_dict)
        spec_data_graph = Laderr._load_spec_data(spec_metadata_dict, spec_data_dict)

        # Combine graphs
        unified_graph = Graph()
        unified_graph += spec_metadata_graph
        unified_graph += spec_data_graph

        # Combine instances with Schema for correct SHACL evaluation
        laderr_schema = Laderr._load_schema()
        validation_graph = Graph()
        validation_graph += unified_graph
        validation_graph += laderr_schema

        # Bind namespaces in the unified graph
        base_uri = cls._validate_base_uri(spec_metadata_dict)
        unified_graph.bind("", Namespace(base_uri))  # Bind `:` to the base URI
        unified_graph.bind("laderr", cls.LADER_NS)  # Bind `laderr:` to the schema namespace

        ic(len(spec_metadata_graph), len(spec_data_graph), len(unified_graph), len(laderr_schema), len(validation_graph))

        conforms, _, report_text = Laderr._validate_with_shacl(validation_graph)
        Laderr._report_validation_result(conforms, report_text)
        Laderr._save_graph(unified_graph, "./result.ttl")
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

        rdf_file_path = "C:\\Users\\FavatoBarcelosPP\\Dev\\laderr\\laderr-schema-v0.2.0.ttl"

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
        Reads a TOML file, parses its content into a Python dictionary, and extracts preamble keys into a `spec_metadata_dict` dict.

        This function uses Python's built-in `tomllib` library to parse TOML files. The file must be passed as a binary
        stream, as required by `tomllib`. It processes the top-level keys that are not part of any section (preamble) and
        stores them in a separate `spec_metadata_dict` dictionary. Handles cases where `createdBy` is a string or a list of strings.

        :param laderr_file_path: The path to the TOML file to be read.
        :type laderr_file_path: str
        :return: A tuple containing:
            - `spec_metadata_dict`: A dictionary with preamble keys and their values.
            - `data`: A dictionary with the remaining TOML data (sections and their contents).
        :rtype: tuple[dict[str, object], dict[str, object]]
        :raises FileNotFoundError: If the specified file does not exist or cannot be found.
        :raises tomllib.TOMLDecodeError: If the TOML file contains invalid syntax or cannot be parsed.
        """
        try:
            with open(laderr_file_path, "rb") as file:
                data: dict[str, object] = tomllib.load(file)

            # Separate spec_metadata_dict and data
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
