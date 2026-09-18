n = int(input())
nums = list(map(int, input().split()))
x = 1
for i in range(1, n):
    x ^= (i+1)
for num in nums:
    x ^= num
print(x)