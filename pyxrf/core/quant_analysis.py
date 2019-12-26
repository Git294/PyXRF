import os
import yaml
import jsonschema
import numpy as np
import math
import json
from .xrf_utils import split_compound_mass

# ==========================================================================================
#    Functions for operations with YAML files used for keeping descriptions of XRF standards

_xrf_standard_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "serial", "description", "compounds"],
    "properties": {
        "name": {"type": "string"},
        "serial": {"type": "string"},
        "description": {"type": "string"},
        "compounds": {"type": "object",
                      # Chemical formula should always start with a captial letter (Fe2O3)
                      "patternProperties": {"^[A-Z][A-Za-z0-9]*$": {"type": "number"}},
                      "additionalProperties": False,
                      "minProperties": 1
                      },
        "density": {"type": "number"}  # Total density is an optional parameter
    }
}

_xrf_standard_schema_instructions = """
# The file was automatically generated.
#
# Instructions for editing this file:
#
# Description of each standard starts with '- name: ...'. Every following line
#   must be indented by 4 spaces. Each description contains the following items:
#   'name' (name of the standard, arbitrary string), 'serial' (serial number, of
#   the standard, but can be arbitrary string, 'description' (string that contains
#   description of the standard). Those fields may be filled with arbitrary information,
#   best suited to distinguish the standard later. If string consists of only digits
#   (in case of serial number) it must be enclosed in quotes.
#
# The field 'compounds' lists all compounds in the standard. The compounds are
#   presented in the form <compound_formula>: <concentration>.
#   <compound_formula> has to be a valid chemical formula, representing a pure
#   element (C, Fe, Ga, etc.) or compound (Fe2O3, GaAs, etc). Element names
#   must start with a capital letter followed by a lowercase letter (if present).
#   No characters except 'A-Z', 'a-z' and '0-1' are allowed. Lines containing
#   compound specifications must be indented by extra 4 spaces.
#
# The optional field 'density' specifies total density of the sample and used
#   to check integrity of the data (the sum of densities of all compounds
#   must be equaly to 'density' value.
#
# All density values (for compounds and total density) are specified in ug/cm^2
#
# Example (the lines contain extra '#' character, which is not part of YAML file):
#
#-   name: Micromatter 41164
#    serial: '41164'
#    description: CeF3 21.1 / Au 20.6
#    compounds:
#        CeF3: 21.1
#        Au: 20.6
#    density: 41.7
#
# The easiest way to start creating the list of custom standards is to uncomment
#   and edit the following example. To create extra records, duplicate and
#   edit the example or any existing record.

#-    name: Name of the Standard
#     serial: '32654'
#     description: CeF3 21.1 / Au 20.6 (any convenient description)
#     compounds:
#         CeF3: 21.1
#         Au: 20.6

"""


def save_xrf_standard_yaml_file(file_path, standard_data, *, overwrite_existing=False):
    r"""
    Save descriptions of of XRF standards to YAML file

    Parameters
    ----------

    file_path: str
        absolute or relative path to the saved YAML file. If the path does not exist, then
        it is created.

    standard_data: list(dict)
        list of dictionaries, each dictionary is representing the description of one
        XRF standard. Sending ``[]`` will create YAML file, which contains only instructions
        for manual editing of records. Such file can be read by the function
        ``load_xrf_standard_yaml_file``, which returns ``[]``.

    overwrite_existing: bool
        indicates if existing file should be overwritten. Default is False, since
        overwriting of an existing parameter file will lead to loss of data.

    Returns
    -------

        no value is returned

    Raises
    ------

    IOError if the YAML file already exists and ``overwrite_existing`` is not enabled.
    """

    # Make sure that the directory exists
    file_path = os.path.expanduser(file_path)
    file_path = os.path.abspath(file_path)
    flp, _ = os.path.split(file_path)
    os.makedirs(flp, exist_ok=True)

    if not overwrite_existing and os.path.isfile(file_path):
        raise IOError(f"File '{file_path}' already exists")

    s_output = _xrf_standard_schema_instructions
    s_output += yaml.dump(standard_data, default_flow_style=False, sort_keys=False, indent=4)
    with open(file_path, "w") as f:
        f.write(s_output)


def load_xrf_standard_yaml_file(file_path, *, schema=_xrf_standard_schema):
    r"""
    Load the list of XRF standard descriptions from YAML file and verify the schema.

    Parameters
    ----------

    file_path: str
        absolute or relative path to YAML file. If file does not exist then IOError is raised.

    schema: dict
        reference to schema used for validation of the descriptions. If ``schema`` is ``None``,
        then validation is disabled (this is not the default behavior).

    Returns
    -------

        list of dictionaries, each dictionary is representing the description of one XRF
        standard samples. Empty dictionary is returned if the file contains no data.

    Raises
    ------

    IOError is raised if the YAML file does not exist.

    jsonschema.ValidationError is raised if schema validation fails.

    RuntimeError if the sum of areal densities of all compounds does not match the
    total density of the sample for at least one sample. The list of all sample
    records for which the data integrity is not confirmed is returned in the
    error message. For records that do not contain 'density' field the integrity
    check is not performed.
    """

    if not os.path.isfile(file_path):
        raise IOError(f"File '{file_path}' does not exist")

    with open(file_path, 'r') as f:
        standard_data = yaml.load(f, Loader=yaml.FullLoader)

    if schema is not None:
        for data in standard_data:
            jsonschema.validate(instance=data, schema=schema)

    # Now check if all densities of compounds sums to total density in every record
    msg = []
    for data in standard_data:
        if "density" in data:
            # The sum of all densities must be equal to total density
            sm = np.sum(list(data["compounds"].values()))
            if not math.isclose(sm, data["density"], abs_tol=1e-6):
                msg.append(f"Record #{data['serial']} ({data['name']}): "
                           f"computed {sm} vs total {data['density']}")
    if msg:
        msg = [f"    {_}" for _ in msg]
        msg = '\n'.join(msg)
        msg = "Sum of areal densities does not match total density:\n" + msg
        raise RuntimeError(msg)

    return standard_data


def load_included_xrf_standard_yaml_file():
    r"""
    Load YAML file with descriptions of XRF standards that is part of the
    package.

    Returns
    -------

    List of dictionaries, each dictionary represents description of one XRF standard.

    Raises
    ------

    Exceptions may be raised by ``load_xrf_standard_yaml_file`` function
    """

    # Generate file name (assuming that YAML file is in the same directory)
    file_name = "xrf_quant_standards.yaml"
    file_path = os.path.realpath(__file__)
    file_path, _ = os.path.split(file_path)
    file_path = os.path.join(file_path, file_name)

    return load_xrf_standard_yaml_file(file_path)


def compute_standard_element_densities(compounds):
    r"""
    Computes areal density of each element in the mix of compounds.
    Some compounds in the mix may contain the same elements.

    Parameters
    ----------

    compounds: dict

        dictionary of compound densities: key - compound formula,
        value - density (typically ug/cm^2)

    Returns
    -------

    Dictionary of element densities: key - element name (symbolic),
    value - elmenet density.
    """

    element_densities = {}

    for key, value in compounds.items():
        el_dens = split_compound_mass(key, value)
        for el, dens in el_dens.items():
            if el in element_densities:
                element_densities[el] += dens
            else:
                element_densities[el] = dens

    return element_densities


# ==========================================================================================
#    Functions for operations with JSON files used for keeping quantitative data obtained
#      after processing of XRF standard samples. The data is saved after processing
#      XRF scan of standard samples and later used for quantitative analysis of
#      experimental samples.

_xrf_quant_fluor_schema = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "serial", "description", "element_lines",
                 "incident_energy", "scaler_name", "distance_to_sample"],
    "properties": {
        # 'name', 'serial' and 'description' (optional) are copied
        #   from the structure used for description of XRF standard samples
        "name": {"type": "string"},
        "serial": {"type": "string"},
        "description": {"type": "string"},
        # The list of element lines. The list is not expected to be comprehensive:
        #   it includes only the lines selected for processing of standard samples.
        "element_lines": {
            "type": "object",
            "additionalProperties": False,
            "minProperties": 1,
            # Symbolic expression representing an element line:
            # Fe - represents all lines, Fe_K - K-lines, Fe_Ka - K alpha lines,
            # Fe_Ka1 - K alpha 1 line. Currently only selections that contain
            # all K, L or M lines is supported.
            "patternProperties": {
                r"^[A-Z][a-z]?(_[KLM]([ab]\d?)?)?$": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["density", "fluorescence"],
                    "properties": {
                        "density": {"type": "number"},
                        "fluorescence": {"type": ["number", "null"]}
                    }
                }
            },
        },
        # Incident energy used in the processing experiment
        "incident_energy": {"type": "number"},
        # Name of the valid scaler name (specific for data recorded on the beamline
        "scaler_name": {"type": "string"},
        # Distance to the sample (number or null)
        "distance_to_sample": {"type": ["number", "null"]},
    }
}


def save_xrf_quant_fluor_json_file(file_path, fluor_data, *, overwrite_existing=False):
    r"""
    Save the results of processing of a scan data for XRF standard sample to a JSON file.
    The saved data will be used later for quantitative analysis of experimental samples.

    Parameters
    ----------

    file_path: str
        absolute or relative path to the saved JSON file. If the path does not exist, then
        it is created.

    fluor_data: dict
        dictionary, which contains the results of processing of a scan of an XRF standard.
        The dictionary should conform to ``_xrf_quantitative_fluorescence_schema``.
        The schema is verified before saving to ensure that the data can be successfully read.

    overwrite_existing: bool
        indicates if existing file should be overwritten. Default is False, since
        overwriting of an existing parameter file will lead to loss of data.

    Returns
    -------

        no value is returned

    Raises
    ------

    IOError if the JSON file already exists and ``overwrite_existing`` is not enabled.

    jsonschema.ValidationError if schema validation fails
    """

    # Note: the schema is fixed (not passed as a parameter). If data format is changed,
    #   then the built-in schema must be changed. The same schema is always used
    #   both for reading and writing of data.
    jsonschema.validate(instance=fluor_data, schema=_xrf_quant_fluor_schema)

    # Make sure that the directory exists
    file_path = os.path.expanduser(file_path)
    file_path = os.path.abspath(file_path)
    flp, _ = os.path.split(file_path)
    os.makedirs(flp, exist_ok=True)

    if not overwrite_existing and os.path.isfile(file_path):
        raise IOError(f"File '{file_path}' already exists")

    s_output = json.dumps(fluor_data, sort_keys=False, indent=4)
    with open(file_path, "w") as f:
        f.write(s_output)


def load_xrf_quant_fluor_json_file(file_path, *, schema=_xrf_quant_fluor_schema):
    r"""
    Load the quantitative data for XRF standard sample from JSON file and verify the schema.

    Parameters
    ----------

    file_path: str
        absolute or relative path to JSON file. If file does not exist then IOError is raised.

    schema: dict
        reference to schema used for validation of the descriptions. If ``schema`` is ``None``,
        then validation is disabled (this is not the default behavior).

    Returns
    -------

        dictionary containing quantitative fluorescence data on XRF sample.

    Raises
    ------

    IOError is raised if the YAML file does not exist.

    jsonschema.ValidationError is raised if schema validation fails.
    """

    if not os.path.isfile(file_path):
        raise IOError(f"File '{file_path}' does not exist")

    with open(file_path, 'r') as f:
        fluor_data = json.load(f)

    if schema is not None:
        jsonschema.validate(instance=fluor_data, schema=schema)

    return fluor_data
