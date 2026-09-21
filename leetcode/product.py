class Solution:
    def productExceptSelf(self, nums: list[int]) -> list[int]:
        prefix = list([nums[0]])
        n = len(nums)
        for i in range(1,n):
            prefix.append(prefix[i-1]*nums[i])
        suffix = list([nums[-1]])
        for i in range(n-2, -1, -1):
            suffix.append(suffix[n-i-2]*nums[i])
        ans = list([])
        for i in range(n):
            if i == 0:
                ans.append(suffix[-2])
            elif i == n-1:
                ans.append(prefix[-2])
            else:
                ans.append(prefix[i-1]*suffix[n-i-2])
        return ans