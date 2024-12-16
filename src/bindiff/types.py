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


def basicblock_algorithm_str(algo: BasicBlockAlgorithm) -> str:
    match algo:
        case BasicBlockAlgorithm.edges_prime_product: return "edges prime product"
        case BasicBlockAlgorithm.hash_matching_four_inst_min: return "hash matching (4 instructions minimum)"
        case BasicBlockAlgorithm.prime_matching_four_inst_min: return "prime matching (4 instructions minimum)"
        case BasicBlockAlgorithm.call_reference_matching: return "call reference matching"
        case BasicBlockAlgorithm.string_references_matching: return "string reference matching"
        case BasicBlockAlgorithm.edges_md_index_top_down: return "edges MD index (top down)"
        case BasicBlockAlgorithm.md_index_matching_top_down: return "MD index matching (top down)"
        case BasicBlockAlgorithm.edges_md_index_bottom_up: return "edges MD index (bottom up)"
        case BasicBlockAlgorithm.md_index_matching_bottom_up: return "MD index matching (bottom up)"
        case BasicBlockAlgorithm.relaxed_md_index_matching: return "relaxed MD index matching"
        case BasicBlockAlgorithm.prime_matching_no_inst_min: return "prime matching (0 instructions minimum)"
        case BasicBlockAlgorithm.edges_lengauer_tarjan_dominated: return "edges Lengauer Tarjan dominated"
        case BasicBlockAlgorithm.loop_entry_matching: return "loop entry matching"
        case BasicBlockAlgorithm.self_loop_matching: return "self loop matching"
        case BasicBlockAlgorithm.entry_point_matching: return "entry point matching"
        case BasicBlockAlgorithm.exit_point_matching: return "exit point matching"
        case BasicBlockAlgorithm.instruction_count_matching: return "instruction count matching"
        case BasicBlockAlgorithm.jump_sequence_matching: return "jump sequence matching"
        case BasicBlockAlgorithm.propagation_size_one: return "propagation (size==1)"
        case BasicBlockAlgorithm.manual: return "manual"
        case _:
            assert False


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

def function_algorithm_str(algo: FunctionAlgorithm) -> str:
    match algo:
        case FunctionAlgorithm.name_hash_matching: return "name hash matching"
        case FunctionAlgorithm.hash_matching: return "hash matching"
        case FunctionAlgorithm.edges_flowgraph_md_index: return "edges flowgraph MD index"
        case FunctionAlgorithm.edges_callgraph_md_index: return "edges callgraph MD index"
        case FunctionAlgorithm.md_index_matching_flowgraph_top_down: return "MD index matching (flowgraph MD index, top down)"
        case FunctionAlgorithm.md_index_matching_flowgraph_bottom_up: return "MD index matching (flowgraph MD index, bottom up)"
        case FunctionAlgorithm.prime_signature_matching: return "signature matching"
        case FunctionAlgorithm.md_index_matching_callGraph_top_down: return "MD index matching (callGraph MD index, top down)"
        case FunctionAlgorithm.md_index_matching_callGraph_bottom_up: return "MD index matching (callGraph MD index, bottom up)"
        case FunctionAlgorithm.relaxed_md_index_matching: return "MD index matching"
        case FunctionAlgorithm.instruction_count: return "instruction count"
        case FunctionAlgorithm.address_sequence: return "address sequence"
        case FunctionAlgorithm.string_references: return "string references"
        case FunctionAlgorithm.loop_count_matching: return "loop count matching"
        case FunctionAlgorithm.call_sequence_matching_exact: return "call sequence matching(exact)"
        case FunctionAlgorithm.call_sequence_matching_topology: return "call sequence matching(topology)"
        case FunctionAlgorithm.call_sequence_matching_sequence: return "call sequence matching(sequence)"
        case FunctionAlgorithm.call_reference_matching: return "call rerferences matching"
        case FunctionAlgorithm.manual: return "manual"
        case _: assert False
