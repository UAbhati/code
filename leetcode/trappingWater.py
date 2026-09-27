class Solution:
    def trap(self, height: list[int]) -> int:
        l = 0
        r = len(height) -1
        s = 0
        leftMax, rightMax = 0, 0
        while l <= r:
            if height[l] <= height[r]:
                if height[l] >= leftMax:
                    leftMax = height[l]
                else:
                    s += leftMax - height[l]
                l+=1
            else:
                if height[r] >= rightMax:
                    rightMax = height[r]
                else:
                    s+= rightMax - height[r]
                r-=1

        return s

