import os
import sys


class PtrItem:
    """ Write to global pointers """

    mapping_dict = dict()
    wasm_objs_dict = dict()
    clang_objs_dict = dict()

    @staticmethod
    def set_dict(mapping_dict: dict, wasm_objs_dict: dict, clang_objs_dict: dict) -> None:
        PtrItem.mapping_dict = mapping_dict
        PtrItem.wasm_objs_dict = wasm_objs_dict
        PtrItem.clang_objs_dict = clang_objs_dict

    def __init__(self, ptr_name: str, ptr_value):
        self.ptr_name = ptr_name
        self.value = ptr_value

    def __eq__(self, other):
        if self.value in PtrItem.wasm_objs_dict or self.value in PtrItem.clang_objs_dict:
            if other.value in PtrItem.wasm_objs_dict or other.value in PtrItem.clang_objs_dict:
                if (self.value, other.value) not in PtrItem.mapping_dict:
                    return False  # point to different objs
            else:
                return False  # other.value points to unknown obj
        elif other.value in PtrItem.wasm_objs_dict or other.value in PtrItem.clang_objs_dict:
            return False  # self.value points to unknown obj
        else:
            pass  # both point to unknown objs
        return True


class FuncItem:
    """ Function call/return """
    mapping_dict = dict()
    wasm_objs_dict = dict()
    clang_objs_dict = dict()

    @staticmethod
    def set_dict(mapping_dict: dict, wasm_objs_dict: dict, clang_objs_dict: dict) -> None:
        FuncItem.mapping_dict = mapping_dict
        FuncItem.wasm_objs_dict = wasm_objs_dict
        FuncItem.clang_objs_dict = clang_objs_dict

    def __init__(self, func_name: str, item_type='P', item_values=[], pointer_flags=[]):
        # assert item_type == 'R' or len(item_values) == len(pointer_flags) # it is possible for WASM
        self.func_name = func_name
        self.type = item_type
        self.values = item_values
        self.pointer_flags = pointer_flags

    def __eq__(self, other):
        if self.type != other.type:
            return False
        if len(self.values) != len(other.values):  # more parameters than defined in dwarf is possible for WASM, due to optimization?
            return False
        for i in range(len(self.pointer_flags)):
            assert self.pointer_flags[i] == other.pointer_flags[i]

            if not self.pointer_flags[i]:  # normal int values
                if self.values[i] != other.values[i]:
                    return False
            elif self.pointer_flags[i]:  # pointer values
                if self.values[i] in FuncItem.wasm_objs_dict or self.values[i] in FuncItem.clang_objs_dict:
                    if other.values[i] in FuncItem.wasm_objs_dict or other.values[i] in FuncItem.clang_objs_dict:
                        if (self.values[i], other.values[i]) not in FuncItem.mapping_dict:
                            return False  # point to different objs
                    else:
                        return False  # other.values[i] points to unknown obj
                elif other.values[i] in FuncItem.wasm_objs_dict or other.values[i] in FuncItem.clang_objs_dict:
                    return False  # self.values[i] points to unknown obj
                else:
                    pass  # both point to unknown objs
        return True

    def values_str(self):
        if len(self.values) == len(self.pointer_flags):
            val_str = ""
            for i in range(len(self.values)):
                if self.pointer_flags[i]:  # ptr value
                    val_str += 'ptr' + ','
                else:
                    val_str += str(self.values[i]) + ','
            val_str = val_str.strip(',')
            return '[{}]'.format(val_str)
        else:
            val_str = ""
            for i in range(len(self.values)):
                val_str += 'unknown' + ','
            val_str = val_str.strip(',')
            return '[{}]'.format(val_str)


def lcs(list1: list, list2: list):
    """ Longest Common Sequence """
    n1 = len(list1)
    n2 = len(list2)

    col = n2 + 2
    row = n1 + 2
    dp = [[0 for i in range(col)] for j in range(row)]
    # dynamic programming
    for i in range(1, n1+1):
        for j in range(1, n2+1):
            if list1[i - 1] == list2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    # debug
    # print(dp)

    # get the LCS (index of list2)
    lcs_index = []
    i = n1
    j = n2
    while i > 0 and j > 0:
        # print('i {} j {}'.format(i, j))
        if (dp[i-1][j-1] + 1) == dp[i][j] and dp[i-1][j] != dp[i][j] and dp[i][j-1] != dp[i][j]:
            if list1[i-1] == list2[j-1]:
                lcs_index.insert(0, j-1)
            # else:
            #     print(list1[i-1], list2[j-1])
            i -= 1
            j -= 1
        elif dp[i-1][j] == dp[i][j]:
            i -= 1
        elif dp[i][j-1] == dp[i][j]:
            j -= 1
        else:
            assert False

    # get the LCS (index of list1)
    lcs_index1 = []
    i = n1
    j = n2
    while i > 0 and j > 0:
        # print('i {} j {}'.format(i, j))
        if (dp[i - 1][j - 1] + 1) == dp[i][j] and dp[i - 1][j] != dp[i][j] and dp[i][j - 1] != dp[i][j]:
            if list1[i - 1] == list2[j - 1]:
                lcs_index1.insert(0, i - 1)
            # else:
            #     print(list1[i-1], list2[j-1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] == dp[i][j]:
            i -= 1
        elif dp[i][j - 1] == dp[i][j]:
            j -= 1
        else:
            assert False

    return lcs_index, lcs_index1


if __name__ == '__main__':
    A = 'We are shannonai'
    B = 'We like shannonai'
    A_list = list(A)
    B_list = list(B)
    print(lcs(A_list, B_list))


