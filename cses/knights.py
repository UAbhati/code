n = int(input())
for i in range(1, n+1):
    if i == 1:
        print(0)
    else:
        print(i**2 * (i**2 - 1) // 2 - 4 * (i-1) * (i-2))