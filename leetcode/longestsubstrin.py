from collections import defaultdict

class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        freq = defaultdict(lambda: -1)
        i = 0
        ans = 0

        for j in range(len(s)):
            if freq[s[j]] >= i:
                i = freq[s[j]] + 1

            freq[s[j]] = j
            ans = max(ans, j - i + 1)

        return ans