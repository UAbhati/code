from collections import Counter

class Solution:
    def minWindow(self, s: str, t: str) -> str:
        need = Counter(t)
        have = {}

        required = len(need)
        formed = 0

        left = 0
        best_len = float('inf')
        best_left = 0

        for right, c in enumerate(s):

            if c in need:
                have[c] = have.get(c, 0) + 1

                if have[c] == need[c]:
                    formed += 1

            while formed == required:

                if right - left + 1 < best_len:
                    best_len = right - left + 1
                    best_left = left

                left_char = s[left]

                if left_char in need:
                    have[left_char] -= 1

                    if have[left_char] < need[left_char]:
                        formed -= 1

                left += 1

        if best_len == float('inf'):
            return ""

        return s[best_left:best_left + best_len]