from enum import IntEnum
from typing import Union, Optional

from binexport import ProgramBinExport, FunctionBinExport, BasicBlockBinExport, InstructionBinExport


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


class AlgorithmMixin(object):
    """
    Mixin class representing the matching algorithm as given by bindiff
    """

    _algorithm = None

    @property
    def algorithm(self) -> Optional[Union[BasicBlockAlgorithm, FunctionAlgorithm]]:
        return self._algorithm

    @algorithm.setter
    def algorithm(self, value: Union[BasicBlockAlgorithm, FunctionAlgorithm]) -> None:
        self._algorithm = value


class SimilarityMixin(object):
    """
    Mixing class to represent a similarity between to entities, with confidence level.
    """

    _similarity = None
    _confidence = None

    @property
    def similarity(self) -> Optional[float]:
        return self._similarity

    @similarity.setter
    def similarity(self, value: float) -> None:
        self._similarity = float("{0:.3f}".format(value))

    @property
    def confidence(self) -> Optional[float]:
        return self._confidence

    @confidence.setter
    def confidence(self, value: float) -> None:
        self._confidence = float("{0:.3f}".format(value))


class MatchMixin(object):
    """
    Mixin class to represent a match between two object.
    """

    _match = None

    @property
    def match(self) -> Optional[object]:
        return self._match

    @match.setter
    def match(self, value: object) -> None:
        self._match = value

    def is_matched(self) -> bool:
        return self._match is not None


class DictMatchMixin(MatchMixin):
    """
    Extension of MatchMixin applied on dict object to compute
    the number of matched / unmatched object within the dict.
    """

    @property
    def nb_match(self) -> int:
        return sum(1 for x in self.values() if x.is_matched())

    @property
    def nb_unmatch(self) -> int:
        return sum(1 for x in self.values() if not x.is_matched())


class ProgramBinDiff(DictMatchMixin, SimilarityMixin, ProgramBinExport):
    """
    Program class to represent a diffed binary. Basically enrich
    a ProgramBinExport class with match, similarity, confidence
    attributes and the associated methods.
    """
    pass


class FunctionBinDiff(DictMatchMixin, AlgorithmMixin, SimilarityMixin, FunctionBinExport):
    """
    Function class to represent a diffed function. Enrich FunctionBinExport
    with math, similarity, confidence and algorithm attributes.
    """
    pass


class BasicBlockBinDiff(DictMatchMixin, AlgorithmMixin, BasicBlockBinExport):
    """
    Diffed basic block. Enrich BasicBlockBinExport with the match and
    algorithm attributes (and theirs associated methods).
    """
    pass


class InstructionBinDiff(MatchMixin, InstructionBinExport):
    """
    Diff instruction. Simply add the match attribute to the
    InstructionBinExport class.
    """
    pass
