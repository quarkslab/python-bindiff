from enum import IntEnum


class BindiffNotFound(Exception):
    """
    Exception raised if Bindiff binary cannot be found
    when trying to diff two binaries.
    """
    pass


class BasicBlockAlgorithm(IntEnum):
    """
    Basic block matching algorithm enum. (id's does not seem to change in
    bindiff so hardcoded here)
    """

    edges_prime_product = 1
    hash_matching_four_inst_min = 2
    prime_matching_four_inst_min = 3
    call_reference_matching = 4
    string_references_matching = 5
    edges_md_index_top_down = 6
    md_index_matching_top_down = 7
    edges_md_index_bottom_up = 8
    md_index_matching_bottom_up = 9
    relaxed_md_index_matching = 10
    prime_matching_no_inst_min = 11
    edges_lengauer_tarjan_dominated = 12
    loop_entry_matching = 13
    self_loop_matching = 14
    entry_point_matching = 15
    exit_point_matching = 16
    instruction_count_matching = 17
    jump_sequence_matching = 18
    propagation_size_one = 19
    manual = 20


class FunctionAlgorithm(IntEnum):
    """
    Function matching algorithm enum. (id's does not seem to change in
    bindiff so hardcoded here)
    """

    name_hash_matching = 1
    hash_matching = 2
    edges_flowgraph_md_index = 3
    edges_callgraph_md_index = 4
    md_index_matching_flowgraph_top_down = 5
    md_index_matching_flowgraph_bottom_up = 6
    prime_signature_matching = 7
    md_index_matching_callGraph_top_down = 8
    md_index_matching_callGraph_bottom_up = 9
    relaxed_md_index_matching = 10
    instruction_count = 11
    address_sequence = 12
    string_references = 13
    loop_count_matching = 14
    call_sequence_matching_exact = 15
    call_sequence_matching_topology = 16
    call_sequence_matching_sequence = 17
    call_reference_matching = 18
    manual = 19
