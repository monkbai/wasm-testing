import os
import sys


class FuncItem:

    def __init__(self, item_type='P', item_values=[], check_flags=[]):
        assert len(item_values) == len(check_flags)
        self.type = item_type
        self.values = item_values
        self.check = check_flags

    def __eq__(self, other):
        if self.type != other.type:
            return False
        for i in range(len(self.check)):
            assert self.check[i] == other.check[i]
            if self.check[i] and self.values[i] != other.values[i]:
                return False
        return True


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

    return lcs_index


if __name__ == '__main__':
    A = 'We are shannonai'
    B = 'We like shannonai'
    A_list = list(A)
    B_list = list(B)
    print(lcs(A_list, B_list))


