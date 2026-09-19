n = int(input())
old = []
even = []
if n == 2 or n == 3:
    print("NO SOLUTION")
    exit()
for i in range(1, n+1):
    if i % 2 == 0:
        even.append(i)
    else:
        old.append(i)
nums = even + old
print(*nums)