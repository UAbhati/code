class Solution:
    def longestConsecutive(self, nums: list[int]) -> int:
        ans = 0
        nums_set = set(nums)
        for num in nums_set:
            if num - 1 not in nums_set:
                count = 1
                current = num
                while current + 1  in nums_set:
                    count +=1
                    current += 1
                ans = max(ans, count)
        return ans
