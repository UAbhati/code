class Solution:
    def findMin(self, nums: list[int]) -> int:
        m = float('inf')
        l, r = 0, len(nums) -1
        while(l<=r):
            mid = (l+r)//2
            if(nums[l] <= nums[mid]):
                m = min(m, nums[l])
                l = mid +1
            else:
                m = min(m, nums[mid])
                r = mid-1
        return m
