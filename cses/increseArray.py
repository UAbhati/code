n = int(input())
nums = list(map(int,input().split()))
count = 0
for i in range(n-1):
    if nums[i] > nums[i+1]:
        count += nums[i] - nums[i+1]
        nums[i+1] = nums[i]
print(count)